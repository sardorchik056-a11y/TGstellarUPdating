# ============================================================
#  case.py — мини-игра "Общий сундук" (TGStellar), ивент "Щедрый пират"
#
#  ⚓ ГЛОБАЛЬНАЯ ВЕРСИЯ: сундук ОДИН на весь бот, а не отдельный в каждом
#  чате. Банк, таймер, последний вкладчик и кулдауны игроков — общее
#  состояние. Вклад в ЛЮБОМ чате уменьшает общий кулдаун игрока и
#  продлевает ОДИН таймер, а карточка с банком/таймером синхронно
#  обновляется во ВСЕХ чатах, где бота видели (личка + группы).
#  Так это и задумано как ивент: "весь бот скидывается в один банк".
#
#  Единственное, что остаётся per-chat — это КАРТОЧКА (id сообщения
#  и тип чата), потому что у каждого чата своё сообщение в Telegram,
#  которое надо редактировать/пересылать отдельно.
#
#  Модуль полностью самостоятельный: хранит игровое состояние
#  сундука в памяти и ничего не пишет в mainhelp.py.
#  Все хендлеры (/startcase, /stopcase, /case, кнопка "Вложить")
#  находятся в main.py — здесь только логика + тексты.
#
#  Тут же — маленький реестр чатов (своя SQLite-табличка в отдельном
#  файле на диске, database.py не трогаем), нужный для двух вещей:
#  1) на старте бота разослать анонс ивента "во все чаты куда можно"
#  2) знать, КУДА рассылать обновления общей карточки при каждом вкладе
#  (Telegram Bot API не даёт списка чатов бота — копим сами, отмечая
#  chat_id при каждом апдейте через middleware в main.py).
#
#  ВАЖНО: состояние сундука (банк, таймер, последний вкладчик) —
#  в памяти процесса и НЕ переживает рестарт бота (это ок, банки
#  игроков всё равно защищены — деньги списываются/начисляются
#  через database.aio_change_balance, то есть уже до рестарта
#  успевают сохраниться в SQLite). А вот реестр чатов — на диске,
#  он как раз должен переживать рестарт, чтобы было куда слать анонс.
# ============================================================

import time
import asyncio
import sqlite3
import html as _html

from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter

from database import aio_change_balance, aio_get_user, aio_save_user, format_amount
from miner import COIN

# ---------- Параметры игры ----------

CASE_INITIAL_BANK          = 500_000   # стартовый банк сундука (режим приза "монеты")
CASE_DEPOSIT                = 50_000    # вклад по умолчанию для режима "монеты"
                                          # (для призов "артефакт"/"статус" сумму вклада
                                          # каждый раз выбирает админ через /startcase)

# Если победителю выпадает артефакт, который у него уже есть — вместо
# повторной записи в коллекцию (это сломало бы подсчёт бонусов) выдаём
# монеты-компенсацию: множитель_артефакта × эта константа.
CASE_ARTIFACT_DUPLICATE_COMPENSATION_PER_MULT = 200_000
CASE_TIMER_SECONDS          = 60        # таймер сундука (сбрасывается при каждом вкладе)
CASE_FIRST_DEPOSIT_SECONDS  = 15 * 60   # время на ПЕРВЫЙ вклад в новом сундуке — 15 минут
PLAYER_COOLDOWN_SECONDS     = 15        # кулдаун игрока между вкладами (общий, на весь бот)
PAUSE_SECONDS                = 30 * 60   # пауза после закрытия сундука (авто-рестарт)
CARD_REFRESH_SECONDS         = 3         # частота "тихого" авто-обновления карточек
                                          # (было 2 — увеличили, чтобы оставить запас
                                          # лимита Telegram на карточки, дёргаемые вкладами)

# Минимальный интервал между ЛЮБЫМИ запросами к Telegram (edit/delete/send),
# которые трогают карточку ОДНОГО чата. Telegram даёт группе примерно
# 1 сообщение/сек в среднем (с короткими бёрстами), и при частых вкладах
# (delete+send на каждый) + тике раз в CARD_REFRESH_SECONDS этот лимит легко
# словить — тогда Telegram отвечает "flood control, retry after N" и обновления
# карточки застревают. Поэтому все обновления карточки чата идут через один
# и тот же _get_card_lock + троттлинг ниже: даже если вкладов было 10 подряд,
# к Telegram уйдёт не больше одного запроса на карточку раз в этот интервал —
# итоговое состояние (банк/таймер) всё равно всегда актуальное, просто не
# каждое промежуточное значение долетает как отдельное сообщение.
MIN_CARD_UPDATE_INTERVAL = 1.5

# Сколько чатов обновляем ПАРАЛЛЕЛЬНО при рассылке общей карточки. Раз банк
# один на всех, любой вклад теперь трогает карточки СРАЗУ во всех чатах —
# без ограничения одновременности это может быть десятки/сотни запросов
# к Telegram одновременно. Троттлинг внутри каждого чата всё равно свой
# (см. MIN_CARD_UPDATE_INTERVAL), а этот семафор просто не даёт бэкенду
# слать всё вообще одним махом.
_BROADCAST_CONCURRENCY = 20

EVENT_TITLE = "🏴‍☠️ <b>ЩЕДРЫЙ ПИРАТ</b> 🏴‍☠️"

# ВАЖНО: callback_data кнопки "Вложить" намеренно начинается с "city_".
# В mainhelp.py есть общий catch-all колбэк-хендлер (ловит ВСЁ, кроме данных
# с префиксом "city_"/"crystop_"), зарегистрированный раньше наших хендлеров —
# без этого префикса Telegram отдавал клик именно ему, и он отвечал
# "неизвестная команда", потому что не знает про нашу игру. Трогать
# mainhelp.py нельзя, поэтому просто используем префикс, который тот
# хендлер сам сознательно пропускает.
CASE_INVEST_CB = "city_case_invest"

# ═══════════════════════════════════════════════════════════
#  РЕЕСТР ЧАТОВ (для рассылки анонса и общей карточки)
# ═══════════════════════════════════════════════════════════
#
#  Своя SQLite-база в отдельном файле — никак не пересекается с
#  database.py и mainhelp.py. Список переживает рестарт бота.

_CHATS_DB_PATH = "tgstellar_case_chats.db"


def _chats_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_CHATS_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS known_chats (
            chat_id   INTEGER PRIMARY KEY,
            chat_type TEXT,
            title     TEXT,
            last_seen REAL
        )
        """
    )
    return conn


def _init_chats_db_sync():
    conn = _chats_conn()
    conn.commit()
    conn.close()


_init_chats_db_sync()  # создаём таблицу сразу при импорте модуля


def _register_chat_sync(chat_id: int, chat_type: str, title: str | None):
    conn = _chats_conn()
    conn.execute(
        """
        INSERT INTO known_chats (chat_id, chat_type, title, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            chat_type = excluded.chat_type,
            title     = excluded.title,
            last_seen = excluded.last_seen
        """,
        (chat_id, chat_type, title, time.time()),
    )
    conn.commit()
    conn.close()


async def register_chat(chat_id: int, chat_type: str, title: str | None = None):
    """Запоминает/обновляет чат в реестре. Вызывается из middleware в main.py
    на КАЖДОМ апдейте — чтобы список чатов был полным и всегда свежим."""
    try:
        await asyncio.to_thread(_register_chat_sync, chat_id, chat_type, title)
    except Exception as e:
        print(f"[case.register_chat] {e}")


def _forget_chat_sync(chat_id: int):
    conn = _chats_conn()
    conn.execute("DELETE FROM known_chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


async def forget_chat(chat_id: int):
    """Убирает чат из реестра (например, если бота выгнали из группы)."""
    try:
        await asyncio.to_thread(_forget_chat_sync, chat_id)
    except Exception as e:
        print(f"[case.forget_chat] {e}")
    _CARDS.pop(chat_id, None)


def _get_all_chats_sync() -> list[tuple[int, str]]:
    conn = _chats_conn()
    rows = conn.execute("SELECT chat_id, chat_type FROM known_chats").fetchall()
    conn.close()
    return rows


async def get_all_chats() -> list[tuple[int, str]]:
    """Список (chat_id, chat_type) всех чатов, где бота когда-либо видели."""
    return await asyncio.to_thread(_get_all_chats_sync)


# ═══════════════════════════════════════════════════════════
#  ГЛОБАЛЬНОЕ СОСТОЯНИЕ СУНДУКА — ОДНО НА ВЕСЬ БОТ
# ═══════════════════════════════════════════════════════════
#
# _CASE = {
#   "running":            bool,  # цикл запущен (вручную или автостартом) и не остановлен
#   "active":             bool,  # сундук сейчас открыт (принимает вклады)
#   "bank":               int,   # копится только в режиме приза "монеты"
#   "expires_at":         float, # unix ts закрытия текущего сундука
#   "window_seconds":     int,   # длина текущего окна (для прогресс-бара)
#   "last_uid":           int | None,
#   "last_name":          str | None,
#   "cooldowns":          {uid: last_invest_ts},   # общий кулдаун на весь бот
#   "paused_until":        float | None,
#   "last_winner_name":    str | None,
#   "last_winner_amount":  int | None,   # для "монет" — сумма; для остальных призов — None
#   "last_prize_type":     str | None,   # чем был награждён ПОСЛЕДНИЙ закрытый сундук
#   "last_prize_label":     str | None,  # готовая подпись приза для текста "прошлого победителя"
#
#   ---- Настройки ТЕКУЩЕГО ивента (задаются админом в /startcase и
#        живут, пока цикл не остановлен /stopcase — при авто-рестарте
#        нового сундука после паузы используются те же настройки) ----
#   "deposit":              int,          # сумма одного вклада (выбирает админ)
#   "prize_type":           str,          # "coins" | "artifact" | "status"
#   "prize_artifact_key":   str | None,
#   "prize_artifact_name":  str | None,
#   "prize_artifact_mult":  float | None,
#   "prize_status_tier":    str | None,   # "vip" | "premium"
# }
_CASE: dict = {
    "running":            False,
    "active":             False,
    "bank":               0,
    "expires_at":         0.0,
    "window_seconds":     CASE_FIRST_DEPOSIT_SECONDS,
    "last_uid":           None,
    "last_name":          None,
    "cooldowns":          {},
    "paused_until":       None,
    "last_winner_name":   None,
    "last_winner_amount": None,
    "last_prize_type":    None,
    "last_prize_label":   None,

    "deposit":             CASE_DEPOSIT,
    "prize_type":          "coins",
    "prize_artifact_key":  None,
    "prize_artifact_name": None,
    "prize_artifact_mult": None,
    "prize_status_tier":   None,

    # Картинка ивента (см. /photo в main.py) — file_id фото, которое
    # прикрепляется к карточке сундука вместо простого текстового
    # сообщения. Живёт поверх пересоздания сундука/остановки цикла,
    # пока админ не пришлёт новое фото командой /photo.
    "photo_file_id":       None,
}


def get_case_state() -> dict:
    """Возвращает глобальное состояние сундука (одно на весь бот)."""
    return _CASE


def set_event_photo(file_id: str | None) -> None:
    """Задаёт (или сбрасывает, если file_id=None) картинку ивента —
    после этого карточка сундука отправляется как фото с текстом-подписью
    вместо обычного текстового сообщения. См. команду /photo в main.py."""
    _CASE["photo_file_id"] = file_id


def get_event_photo() -> str | None:
    return _CASE["photo_file_id"]


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _spawn_chest(state: dict) -> None:
    """Открывает новый сундук с нуля: стартовый банк (только для приза
    "монеты" — для "артефакт"/"статус" банк не используется, приз
    фиксирован заранее) и увеличенный таймер на ПЕРВЫЙ вклад (15 минут —
    чтобы игроки успели заметить и зайти в любом из чатов бота). Как
    только кто-то вложится первым — таймер начинает работать в обычном
    режиме (см. try_invest). Настройки приза/вклада (deposit, prize_*)
    НЕ трогаем — они живут поверх пересоздания сундука, пока цикл не
    остановлен /stopcase."""
    state["active"]         = True
    state["bank"]            = CASE_INITIAL_BANK if state["prize_type"] == "coins" else 0
    state["expires_at"]      = time.time() + CASE_FIRST_DEPOSIT_SECONDS
    state["window_seconds"]  = CASE_FIRST_DEPOSIT_SECONDS
    state["last_uid"]        = None
    state["last_name"]       = None
    state["cooldowns"]       = {}
    state["paused_until"]    = None


# ---------- Управление циклом (админ / автостарт) ----------

def start_case(
    deposit: int = CASE_DEPOSIT,
    prize_type: str = "coins",
    prize_artifact: dict | None = None,
    prize_status_tier: str | None = None,
) -> bool:
    """/startcase — запускает общий цикл сундука (на весь бот). False, если уже запущен.

    deposit            — сумма одного вклада, выбирает админ в мастере настройки.
    prize_type          — "coins" (обычный растущий банк), "artifact" (фиксированный
                          артефакт) или "status" (фиксированный VIP/Premium).
    prize_artifact       — для prize_type="artifact": {"key", "name", "multiplier"}.
    prize_status_tier    — для prize_type="status": "vip" | "premium".

    Настройки сохраняются в _CASE и действуют для ВСЕХ сундуков этого
    запуска цикла (в т.ч. авто-рестартующихся после паузы), пока админ
    не остановит ивент /stopcase и не запустит заново с другими настройками."""
    if _CASE["running"]:
        return False

    _CASE["deposit"]    = max(1, int(deposit))
    _CASE["prize_type"] = prize_type

    if prize_type == "artifact" and prize_artifact:
        _CASE["prize_artifact_key"]  = prize_artifact.get("key")
        _CASE["prize_artifact_name"] = prize_artifact.get("name")
        _CASE["prize_artifact_mult"] = prize_artifact.get("multiplier")
    else:
        _CASE["prize_artifact_key"]  = None
        _CASE["prize_artifact_name"] = None
        _CASE["prize_artifact_mult"] = None

    _CASE["prize_status_tier"] = prize_status_tier if prize_type == "status" else None

    _CASE["running"] = True
    _spawn_chest(_CASE)
    return True


def stop_case() -> bool:
    """
    /stopcase — останавливает общий цикл. Работает ТОЛЬКО в паузе
    (сундук закрыт). Если сундук активен или цикл не запущен — False.
    """
    if not _CASE["running"] or _CASE["active"]:
        return False
    _CASE["running"]      = False
    _CASE["paused_until"] = None
    return True


# ---------- Вклад игрока ----------

async def try_invest(uid: int, name: str) -> dict:
    """
    Пытается сделать вклад за игрока uid в ОБЩИЙ сундук (не важно, из
    какого чата пришёл вклад — банк и кулдаун одни на весь бот).
    Возвращает dict:
      {"ok": True, "bank": int, "deposit": int}
      {"ok": False, "reason": "no_active" | "cooldown" | "insufficient",
       "wait": int (для cooldown), "balance": int (для insufficient),
       "deposit": int (для insufficient — сколько было нужно)}
    """
    if not _CASE["active"]:
        return {"ok": False, "reason": "no_active"}

    now     = time.time()
    last_ts = _CASE["cooldowns"].get(uid, 0)
    elapsed = now - last_ts
    if elapsed < PLAYER_COOLDOWN_SECONDS:
        return {"ok": False, "reason": "cooldown", "wait": int(PLAYER_COOLDOWN_SECONDS - elapsed) + 1}

    deposit = _CASE["deposit"]

    # Атомарное списание — та же гарантия, что и везде в проекте:
    # если баланса не хватает, change_balance просто вернёт None и
    # ничего не спишет (см. database.change_balance).
    new_balance = await aio_change_balance(uid, -deposit, min_balance=0)
    if new_balance is None:
        u = await aio_get_user(uid)
        balance = u.get("balance", 0) if u else 0
        return {"ok": False, "reason": "insufficient", "balance": balance, "deposit": deposit}

    # Банк копится ВСЕГДА, независимо от типа приза: для "монет" это и
    # есть сам приз, а для "артефакта"/"статуса" — это дополнительный
    # бонус, который винер получит ПОВЕРХ фиксированного приза (см.
    # _close_chest) — золото, накопленное на фоне вкладов, не пропадает.
    _CASE["bank"] += deposit
    _CASE["last_uid"]        = uid
    _CASE["last_name"]       = name
    _CASE["cooldowns"][uid]  = now
    _CASE["expires_at"]      = now + CASE_TIMER_SECONDS
    _CASE["window_seconds"]  = CASE_TIMER_SECONDS

    return {"ok": True, "bank": _CASE["bank"], "deposit": deposit}


# ---------- Тексты и клавиатура ----------

DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬"


# ID premium custom-эмодзи, который рисуется ИКОНКОЙ слева на кнопке
# "Вложить" (Bot API 9.4, поле icon_custom_emoji_id). Работает ТОЛЬКО если
# у аккаунта бота есть активная Telegram Premium подписка (или куплен доп.
# юзернейм на Fragment) — иначе Telegram эту иконку молча проигнорирует.
# Как достать ID своего эмодзи — см. инструкцию в чате.
CASE_INVEST_BUTTON_EMOJI_ID = "5377544787839521766"  # ← замени на свой ID


def case_keyboard(active: bool) -> InlineKeyboardMarkup | None:
    """Кнопка "Вложить" — только когда сундук активен, и прямо на кнопке
    живой обратный отсчёт до закрытия (кнопка перерисовывается вместе с
    карточкой на каждом тике, так что таймер на ней тоже "тикает").
    Кнопки "Обновить" больше нет: карточка обновляется сама.

    Вид: [premium-иконка] 50К | ⏳ ММ:СС — иконка задаётся отдельным полем
    icon_custom_emoji_id, а не эмодзи внутри text (Telegram не рендерит
    custom-эмодзи как символ текста на кнопках, только как icon)."""
    if not active:
        return None
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    remaining  = max(0, int(_CASE["expires_at"] - time.time()))
    mins, secs = divmod(remaining, 60)

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{format_amount(_CASE['deposit'])} | ⏳ {mins:02d}:{secs:02d}",
        callback_data=CASE_INVEST_CB,
        icon_custom_emoji_id=CASE_INVEST_BUTTON_EMOJI_ID,
        style="primary",  # синяя кнопка; варианты: "success" (зелёная), "danger" (красная)
    )
    builder.adjust(1)
    return builder.as_markup()


def _bonus_bank_line(state: dict) -> str:
    """Доп. строка "золото в трюме" для призов "артефакт"/"статус" — банк
    копится на фоне вкладов (см. try_invest) и достаётся победителю ПОВЕРХ
    фиксированного приза (см. _close_chest). Пустая строка, пока в банке
    ещё ничего нет (первый вклад в новом сундуке ещё не сделан)."""
    if state["bank"] <= 0:
        return ""
    bank_str = format_amount(state["bank"])
    return f'\n<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> <b>Плюс золото в трюме:</b> <code>{bank_str}</code>{COIN}'


def _active_prize_line(state: dict) -> str:
    """Строка "что лежит в сундуке" для карточки, пока сундук открыт —
    зависит от режима приза, выбранного админом в /startcase."""
    if state["prize_type"] == "artifact":
        name = _esc(state["prize_artifact_name"] or "?")
        mult = state["prize_artifact_mult"]
        mult_str = f" (×{mult})" if mult else ""
        return (
            f'<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> <b>В сундуке артефакт:</b> {name}{mult_str}'
            f'{_bonus_bank_line(state)}'
        )
    if state["prize_type"] == "status":
        label = "VIP" if state["prize_status_tier"] == "vip" else "Premium"
        return (
            f'<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> <b>В сундуке статус:</b> {label} (30 дней)'
            f'{_bonus_bank_line(state)}'
        )
    bank_str = format_amount(state["bank"])
    return f'<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> <b>Золота в трюме:</b> <code>{bank_str}</code>{COIN}'


def case_status_text() -> str:
    """Единый текст карточки сундука — используется ВЕЗДЕ: и когда бот
    впервые анонсирует ивент по /startcase, и на обычных обновлениях
    карточки. Никакого отдельного "текста для старта" больше нет."""
    state = _CASE
    now   = time.time()

    if state["active"]:
        remaining  = max(0, int(state["expires_at"] - now))
        mins, secs = divmod(remaining, 60)
        timer_str  = f"{mins:02d}:{secs:02d}"

        if state["last_uid"]:
            last_line = f'<tg-emoji emoji-id="5402477260982731644">🌟</tg-emoji> <b>Последний, кто рискнул:</b> {_esc(state["last_name"])}'
        else:
            last_line = '<tg-emoji emoji-id="5399913388845322366">🌟</tg-emoji> <b>Пока никто не рискнул</b> — стань первым!'

        return (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<i>Тишина... только скрип старого дерева и блеск золота во тьме.</i>\n\n'
            f'<blockquote>'
            f'{_active_prize_line(state)}\n'
            f'<tg-emoji emoji-id="5382194935057372936">🌟</tg-emoji> <b>Секунды утекают:</b> <code>{timer_str}</code>\n'
            f'{last_line}'
            f'</blockquote>\n'
            f'<b>Стань последним — и сундук навсегда твой.</b>\n'
            f'<tg-emoji emoji-id="5397916757333654639">🌟</tg-emoji> Вклад: <b>{format_amount(state["deposit"])}</b>{COIN}'
        )

    if state["running"]:
        remaining  = max(0, int(state["paused_until"] - now)) if state["paused_until"] else 0
        mins, secs = divmod(remaining, 60)

        winner_block = ""
        if state.get("last_winner_name"):
            winner_block = (
                f'\n\n<blockquote>'
                f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> <b>Последний, кому повезло:</b> {_esc(state["last_winner_name"])}\n'
                f'<tg-emoji emoji-id="5438496463044752972">🌟</tg-emoji> <b>Унёс с собой:</b> {state.get("last_prize_label") or "—"}'
                f'</blockquote>'
            )

        return (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<i>Пират растворился во тьме, унеся сундук с собой... но он вернётся.</i>\n\n'
            f'<blockquote><tg-emoji emoji-id="5303479226882603449">🌟</tg-emoji> <b>Новый сундук всплывёт через:</b> <code>{mins:02d}:{secs:02d}</code></blockquote>'
            f'{winner_block}'
        )

    return (
        f'{EVENT_TITLE}\n'
        f'{DIVIDER}\n'
        f'<i>Тишина... сундук ещё не заброшен в эти воды.</i>'
    )


# ---------- Карточки: per-chat id сообщения ----------
# ══════════════════════════════════════════════════════════════════════
#  Банк/таймер общие на весь бот, но у КАЖДОГО чата своя карточка —
#  своё сообщение в Telegram, свой msg_id и свой способ обновления
#  (edit в личке, delete+send в группе). Поэтому _CARDS хранит только
#  это — id сообщения и тип чата — а не игровое состояние.
# ══════════════════════════════════════════════════════════════════════
_CARDS: dict[int, dict] = {}


def get_card_state(chat_id: int) -> dict:
    """Достаёт (или создаёт) карточку конкретного чата: {"msg_id", "chat_type"}."""
    if chat_id not in _CARDS:
        _CARDS[chat_id] = {"msg_id": None, "chat_type": None}
    return _CARDS[chat_id]


def set_chat_type(chat_id: int, chat_type: str) -> None:
    """Запоминает тип чата ('private' / 'group' / 'supergroup') — от этого
    зависит, как именно обновляется карточка сундука в этом чате."""
    get_card_state(chat_id)["chat_type"] = chat_type


# ══════════════════════════════════════════════════════════════════════
#  ЛОК НА ЧАТ ДЛЯ ОБНОВЛЕНИЯ КАРТОЧКИ
#
#  bump_card/refresh/close теперь трогают карточки СРАЗУ во всех чатах
#  (банк общий), но каждый чат по-прежнему обновляется независимо и
#  сериализованно — лок и троттлинг остались per-chat, просто теперь
#  запускаются параллельно (через asyncio.gather) для разных chat_id.
# ══════════════════════════════════════════════════════════════════════
_CARD_LOCKS: dict[int, asyncio.Lock] = {}


def _get_card_lock(chat_id: int) -> asyncio.Lock:
    lock = _CARD_LOCKS.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _CARD_LOCKS[chat_id] = lock
    return lock


# Время последнего реального запроса к Telegram по карточке этого чата —
# используется троттлингом ниже (_throttle_card), чтобы не словить flood control.
_LAST_CARD_UPDATE_TS: dict[int, float] = {}


async def _throttle_card(chat_id: int) -> None:
    """Вызывается СРАЗУ после захвата _get_card_lock(chat_id), перед любым
    edit/delete/send. Если с прошлого запроса к Telegram по карточке этого
    чата прошло меньше MIN_CARD_UPDATE_INTERVAL — ждём остаток, чтобы не
    спамить API чаще лимита."""
    now  = time.time()
    last = _LAST_CARD_UPDATE_TS.get(chat_id, 0.0)
    wait = MIN_CARD_UPDATE_INTERVAL - (now - last)
    if wait > 0:
        await asyncio.sleep(wait)
    _LAST_CARD_UPDATE_TS[chat_id] = time.time()


async def _tg_call_with_retry(coro_factory, chat_id: int, what: str):
    """Выполняет один Telegram-вызов (edit/delete/send), и если Telegram
    ответил flood control (TelegramRetryAfter) — ОДИН раз ждёт ровно
    столько, сколько он просит, и повторяет. Если поймали её снова —
    сдаёмся и пробрасываем исключение выше (там уже есть свой except
    в вызывающем коде, который просто залогирует и пойдёт дальше)."""
    try:
        return await coro_factory()
    except TelegramRetryAfter as e:
        print(f"[case] {what}: flood control chat_id={chat_id}, retry_after={e.retry_after}s — жду и повторяю")
        await asyncio.sleep(e.retry_after + 0.1)
        return await coro_factory()


async def _send_card_new(bot, chat_id: int, text: str, active: bool):
    """Отправляет карточку НОВЫМ сообщением — фото с подписью, если для
    ивента задана картинка (/photo), иначе обычный текст, как раньше."""
    photo_id = _CASE.get("photo_file_id")
    if photo_id:
        return await _tg_call_with_retry(
            lambda: bot.send_photo(
                chat_id, photo_id, caption=text,
                parse_mode="HTML", reply_markup=case_keyboard(active),
            ),
            chat_id, "send_photo",
        )
    return await _tg_call_with_retry(
        lambda: bot.send_message(
            chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active),
        ),
        chat_id, "send_message",
    )


async def _send_or_edit(bot, chat_id: int, card: dict, text: str, active: bool):
    """Тихое обновление на месте: пробуем отредактировать старую карточку
    (подпись — если это фото-карточка, текст — если обычная). ВАЖНО:
    вызывается только изнутри блока с уже захваченным _get_card_lock
    (и уже прошедшего _throttle_card) — сама лок/троттлинг не берёт, чтобы
    не было дедлока и двойного троттлинга при вложенных вызовах."""
    msg_id   = card.get("msg_id")
    photo_id = _CASE.get("photo_file_id")
    if msg_id:
        try:
            if photo_id:
                await _tg_call_with_retry(
                    lambda: bot.edit_message_caption(
                        chat_id=chat_id, message_id=msg_id, caption=text,
                        parse_mode="HTML", reply_markup=case_keyboard(active),
                    ),
                    chat_id, "edit_message_caption",
                )
            else:
                await _tg_call_with_retry(
                    lambda: bot.edit_message_text(
                        text, chat_id=chat_id, message_id=msg_id,
                        parse_mode="HTML", reply_markup=case_keyboard(active),
                    ),
                    chat_id, "edit_message_text",
                )
            return
        except Exception as e:
            err = str(e).lower()
            if "message is not modified" in err:
                # текст/подпись (и клавиатура) не изменились — это НЕ ошибка,
                # редактировать нечего, лишнее сообщение слать не нужно
                return
            if "there is no caption in the message to edit" not in err and \
               "message to edit not found" not in err and \
               "there is no text in the message to edit" not in err:
                print(f"[case] edit FAILED chat_id={chat_id} msg_id={msg_id}: {e}")
            # Сюда попадаем и когда карточка "сменила тип" (была текстом,
            # а теперь для неё включили фото, или наоборот) — Telegram не
            # даёт редактировать текст в подпись и обратно. В этом случае
            # просто присылаем карточку заново ниже.
    try:
        sent = await _send_card_new(bot, chat_id, text, active)
        card["msg_id"] = sent.message_id
    except Exception as e:
        print(f"[case] send FAILED chat_id={chat_id}: {e}")


async def _push_card(bot, chat_id: int, text: str, active: bool):
    """Обновляет карточку общего сундука в ОДНОМ конкретном чате: в личке
    редактирует сообщение на месте, в группе/супергруппе — удаляет старое
    и присылает новое (чтобы карточка "поднималась" в чате). Используется
    и для значимых событий (вклад/закрытие/новый сундук), и для рассылки
    анонса на старте."""
    card = get_card_state(chat_id)
    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)

        if card.get("chat_type") == "private":
            await _send_or_edit(bot, chat_id, card, text, active)
            return

        old_id = card.get("msg_id")
        if old_id:
            try:
                await _tg_call_with_retry(
                    lambda: bot.delete_message(chat_id, old_id),
                    chat_id, "_push_card.delete_message",
                )
            except Exception as e:
                print(f"[case] _push_card: delete_message FAILED chat_id={chat_id} msg_id={old_id}: {e}")
        try:
            sent = await _send_card_new(bot, chat_id, text, active)
            card["msg_id"] = sent.message_id
        except Exception as e:
            print(f"[case] _push_card: send FAILED chat_id={chat_id}: {e}")


async def _refresh_chat_card(bot, chat_id: int, text: str):
    """Тихий тик (раз в CARD_REFRESH_SECONDS): просто обновляет таймер на месте
    в одном чате, и в личке, и в группе — без пересоздания сообщения."""
    card = get_card_state(chat_id)
    if not card.get("msg_id"):
        return
    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)
        await _send_or_edit(bot, chat_id, card, text, active=True)


async def _broadcast(bot, text: str, active: bool):
    """Рассылает ОДИНАКОВЫЙ текст карточки во ВСЕ известные чаты параллельно
    (с ограничением конкурентности), потому что банк общий и после любого
    значимого события (вклад/закрытие/новый сундук) карточка должна
    обновиться сразу везде, а не только там, где произошло событие."""
    chats = await get_all_chats()
    if not chats:
        return

    sem = asyncio.Semaphore(_BROADCAST_CONCURRENCY)

    async def _one(chat_id: int):
        async with sem:
            await _push_card(bot, chat_id, text, active)

    await asyncio.gather(*(_one(chat_id) for chat_id, _ in chats), return_exceptions=True)


async def send_case_card(bot, chat_id: int):
    """Отправляет свежую карточку общего сундука новым сообщением в ОДНОМ
    чате (например, по команде /startcase или /case) и запоминает её id."""
    card = get_card_state(chat_id)
    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)
        text = case_status_text()
        sent = await _send_card_new(bot, chat_id, text, _CASE["active"])
        card["msg_id"] = sent.message_id
        return sent


async def bump_card(bot):
    """Обновление карточки на ЗНАЧИМЫХ событиях (новый вклад, закрытие,
    открытие нового сундука) — рассылается СРАЗУ во ВСЕ чаты бота, потому
    что банк один на всех и вклад в одном чате должен быть виден везде."""
    await _broadcast(bot, case_status_text(), _CASE["active"])


# ---------- Рассылка анонса ивента по команде /startcase ----------

async def broadcast_event_start(
    bot,
    deposit: int = CASE_DEPOSIT,
    prize_type: str = "coins",
    prize_artifact: dict | None = None,
    prize_status_tier: str | None = None,
):
    """Запускает ивент ПО КОМАНДЕ /startcase (после того, как админ прошёл
    мастер выбора приза в main.py): открывает сундук и рассылает карточку
    (тот же case_status_text(), что и везде — отдельного текста для
    "анонса" больше нет) во все известные чаты (личка + группы).
    Ошибки по отдельным чатам (бот заблокирован/выгнан) просто пропускаются.

    deposit/prize_type/prize_artifact/prize_status_tier — см. start_case().

    ВАЖНО: вызывается только из хендлера команды, НЕ на старте процесса —
    иначе ивент начинался бы сам по себе при каждом деплое/рестарте бота."""
    if not start_case(deposit, prize_type, prize_artifact, prize_status_tier):
        return False

    chats = await get_all_chats()
    text = case_status_text()
    for chat_id, chat_type in chats:
        card = get_card_state(chat_id)
        card["chat_type"] = chat_type

        try:
            sent = await _send_card_new(bot, chat_id, text, _CASE["active"])
            card["msg_id"] = sent.message_id
        except Exception as e:
            print(f"[broadcast_event_start] {chat_id}: {e}")
            continue

        await asyncio.sleep(0.05)  # небольшая пауза, чтобы не словить flood-лимит

    return True


# ---------- Выдача приза победителю (по типу) ----------

async def _grant_bonus_bank(winner_uid: int, bank: int) -> str:
    """Довыдаёт победителю приза "артефакт"/"статус" золото, накопленное
    в банке на фоне вкладов (см. try_invest — банк теперь копится всегда,
    а не только в режиме "монеты"). Возвращает готовый HTML-хвост для
    prize_label ("" если банк пуст — например, был всего один вклад и
    он же оказался последним)."""
    if bank <= 0:
        return ""
    await aio_change_balance(winner_uid, bank)
    return f' <b>+</b> <code>{format_amount(bank)}</code>{COIN}'


async def _grant_artifact_prize(winner_uid: int) -> str:
    """Выдаёт победителю зафиксированный артефакт-приз (см. state
    "prize_artifact_*", задаётся один раз в /startcase). Если артефакт у
    игрока уже есть — во избежание поломки подсчёта бонусов (та же защита,
    что и у команды /giveart в mainhelp.py) выдаём вместо повторной записи
    монеты-компенсацию. Возвращает готовую HTML-подпись приза для карточки."""
    key  = _CASE["prize_artifact_key"]
    name = _CASE["prize_artifact_name"] or "?"
    mult = _CASE["prize_artifact_mult"]

    data = await aio_get_user(winner_uid)
    if data is None:
        return f'{_esc(name)} <i>(не удалось выдать — игрок не найден в базе)</i>'

    artifacts = data.setdefault("artifacts", [])
    if any(entry.get("key") == key for entry in artifacts):
        comp = int((mult or 1) * CASE_ARTIFACT_DUPLICATE_COMPENSATION_PER_MULT)
        await aio_change_balance(winner_uid, comp)
        return f'<code>{format_amount(comp)}</code>{COIN} <i>(дубликат «{_esc(name)}», выдана компенсация)</i>'

    artifacts.append({"key": key})
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1
    await aio_save_user(winner_uid, data)

    mult_str = f" (×{mult})" if mult else ""
    return f'{_esc(name)}{mult_str}'


async def _grant_status_prize(winner_uid: int) -> str:
    """Выдаёт победителю зафиксированный статус-приз (VIP/Premium, 30 дней —
    та же activate_status(), что используют /getstatus и покупка статуса
    в mainhelp.py)."""
    from status import activate_status

    tier  = _CASE["prize_status_tier"]
    label = "VIP" if tier == "vip" else "Premium"

    data = await aio_get_user(winner_uid)
    if data is None:
        return f'статус <b>{label}</b> <i>(не удалось выдать — игрок не найден в базе)</i>'

    ok, msg = activate_status(data, tier)
    if not ok:
        return f'статус <b>{label}</b> <i>(не удалось активировать: {_esc(msg)})</i>'

    await aio_save_user(winner_uid, data)
    return f'статус <b>{label}</b> (30 дней)'


# ---------- Фоновый цикл (закрытие сундука / авто-рестарт) ----------

async def _close_chest(bot):
    state       = _CASE
    winner_uid  = state["last_uid"]
    winner_name = state["last_name"]

    state["active"]       = False
    state["paused_until"] = time.time() + PAUSE_SECONDS

    if winner_uid:
        prize_type = state["prize_type"]
        if prize_type == "artifact":
            prize_label = await _grant_artifact_prize(winner_uid)
            prize_label += await _grant_bonus_bank(winner_uid, state["bank"])
        elif prize_type == "status":
            prize_label = await _grant_status_prize(winner_uid)
            prize_label += await _grant_bonus_bank(winner_uid, state["bank"])
        else:
            bank = state["bank"]
            await aio_change_balance(winner_uid, bank)
            prize_label = f'<code>{format_amount(bank)}</code>{COIN}'

        state["last_winner_name"]   = winner_name
        state["last_winner_amount"] = state["bank"] if prize_type == "coins" else None
        state["last_prize_type"]    = prize_type
        state["last_prize_label"]   = prize_label

        text = (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<i>Волны сомкнулись над сундуком — но не раньше, чем кто-то успел к нему прикоснуться.</i>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5217822164362739968">🌟</tg-emoji> <b>Победитель:</b> {_esc(winner_name)}\n'
            f'<tg-emoji emoji-id="5402477260982731644">🌟</tg-emoji> <b>Забрал:</b> {prize_label}'
            f'</blockquote>\n'
            f'<b>Новый сундук пират спрячет через 30 минут.</b>'
        )
    else:
        text = (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<i>Никто не решился подойти — сундук исчез в тумане так же тихо, как появился.</i>\n\n'
            f'<blockquote>Приз утонул вместе с сундуком.</blockquote>\n'
            f'<b>Новый сундук появится через 30 минут.</b>'
        )

    await _broadcast(bot, text, active=False)


async def case_tick_loop(bot):
    """
    Единый фоновый тик (по аналогии с остальными циклами проекта, например
    _duel_timer_loop в mainhelp.py). Раз в секунду проверяет ОБЩИЙ сундук:
    закрывает истёкший и автоматически открывает новый после паузы —
    и рассылает карточку сразу во все чаты бота."""
    while True:
        try:
            await _tick_once(bot)
        except Exception as e:
            print(f"[case_tick_loop] {e}")
        await asyncio.sleep(1)


async def _tick_once(bot):
    now   = time.time()
    state = _CASE

    if state["active"] and now >= state["expires_at"]:
        await _close_chest(bot)
    elif (
        not state["active"]
        and state["running"]
        and state["paused_until"] is not None
        and now >= state["paused_until"]
    ):
        _spawn_chest(state)
        await bump_card(bot)


async def case_card_refresh_loop(bot):
    """Отдельный фоновый тик: раз в CARD_REFRESH_SECONDS молча обновляет
    таймер на карточках во всех чатах, пока сундук активен — без кнопки
    "Обновить", без пересоздания сообщений (это только для значимых
    событий, см. bump_card)."""
    while True:
        try:
            if _CASE["active"]:
                text = case_status_text()
                chats = await get_all_chats()
                sem = asyncio.Semaphore(_BROADCAST_CONCURRENCY)

                async def _one(chat_id: int):
                    async with sem:
                        await _refresh_chat_card(bot, chat_id, text)

                await asyncio.gather(*(_one(chat_id) for chat_id, _ in chats), return_exceptions=True)
        except Exception as e:
            print(f"[case_card_refresh_loop] {e}")
        await asyncio.sleep(CARD_REFRESH_SECONDS)
