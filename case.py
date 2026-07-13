# ============================================================
#  case.py — мини-игра "Общий сундук" (TGStellar), ивент "Щедрый пират"
#
#  ⚓ ГЛОБАЛЬНАЯ ВЕРСИЯ: ивент ОДИН на весь бот, а не отдельный в каждом
#  чате. Загаданное число, список ответов и таймер — общее состояние.
#  Угадать можно из ЛЮБОГО чата, а карточка с таймером синхронно
#  обновляется во ВСЕХ чатах, где бота видели (личка + группы).
#
#  ⚓ МЕХАНИКА (v2, угадайка): капитан прячет число от 1 до 999. У КАЖДОГО
#  игрока — ОДНА попытка за весь ивент, назвать его можно бесплатно.
#  Все ответы копятся молча, "на фоне" — никто не видит чужих чисел и
#  карточка их не показывает, только счётчик участников. Ивент идёт
#  РОВНО 24 часа с момента запуска. По истечении — число раскрывается,
#  и определяется победитель:
#    1) если кто-то назвал число ТОЧНО — выигрывает он (если точных
#       совпадений несколько — то, что было отправлено РАНЬШЕ по времени);
#    2) если точных совпадений нет — выигрывает ближайший по модулю
#       разницы (при равенстве разницы — снова кто раньше отправил).
#  Если за 24 часа никто не написал ни одного числа — приз никому не
#  достаётся.
#
#  Единственное, что остаётся per-chat — это КАРТОЧКА (id сообщения
#  и тип чата), потому что у каждого чата своё сообщение в Telegram,
#  которое надо редактировать/пересылать отдельно.
#
#  Модуль полностью самостоятельный: хранит игровое состояние
#  ивента в памяти и ничего не пишет в mainhelp.py.
#  Все хендлеры (/startcase, /stopcase, /case, /guess, кнопка "Угадать")
#  находятся в main.py — здесь только логика + тексты.
#
#  Тут же — маленький реестр чатов (своя SQLite-табличка в отдельном
#  файле на диске, database.py не трогаем), нужный для двух вещей:
#  1) на старте бота разослать анонс ивента "во все чаты куда можно"
#  2) знать, КУДА рассылать обновления общей карточки
#  (Telegram Bot API не даёт списка чатов бота — копим сами, отмечая
#  chat_id при каждом апдейте через middleware в main.py).
#
#  ВАЖНО: состояние ивента (число, ответы, таймер) — в памяти процесса
#  и НЕ переживает рестарт бота. Реестр чатов — на диске, он как раз
#  должен переживать рестарт, чтобы было куда слать анонс.
# ============================================================

import time
import random
import asyncio
import sqlite3
import html as _html

from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter

from database import aio_change_balance, aio_get_user, aio_save_user, format_amount
from miner import COIN

# ---------- Параметры игры ----------

NUMBER_MIN = 1
NUMBER_MAX = 999

EVENT_DURATION_SECONDS = 24 * 60 * 60   # ивент всегда длится ровно 24 часа

# Подсказка для админа в мастере /startcase — просто дефолт, который
# показывается в подсказке суммы приза для режима "монеты", ни на что
# больше не влияет (сумму всё равно вводит админ вручную).
CASE_DEFAULT_COIN_PRIZE = 500_000

# Если победителю выпадает артефакт, который у него уже есть — вместо
# повторной записи в коллекцию (это сломало бы подсчёт бонусов) выдаём
# монеты-компенсацию: множитель_артефакта × эта константа.
CASE_ARTIFACT_DUPLICATE_COMPENSATION_PER_MULT = 200_000

CARD_REFRESH_SECONDS         = 15        # частота "тихого" авто-обновления карточек в личке
                                          # (ивент идёт 24 часа — секундная точность таймера
                                          # не нужна, а лишние запросы к Telegram ни к чему)

# В группах тихий тик НЕ просто редактирует карточку на месте (там она может
# затеряться под обычной перепиской), а раз в этот интервал удаляет старое
# сообщение и шлёт новое — карточка "поднимается" наверх чата. При 24-часовом
# ивенте поднимать её часто незачем — раз в несколько минут более чем
# достаточно и не спамит чат.
GROUP_CARD_REFRESH_SECONDS   = 180

# Минимальный интервал между ЛЮБЫМИ запросами к Telegram (edit/delete/send),
# которые трогают карточку ОДНОГО чата — защита от flood control. Ответы
# игроков теперь копятся молча и НЕ дёргают карточку немедленно (см.
# try_guess/бросок в main.py — она обновится сама на следующем тихом тике
# или при значимых событиях: старт/раскрытие), так что нагрузка тут в
# принципе низкая, но троттлинг оставляем как страховку.
MIN_CARD_UPDATE_INTERVAL = 1.5

# Сколько чатов обновляем ПАРАЛЛЕЛЬНО при рассылке общей карточки (старт
# ивента / раскрытие числа). Без ограничения одновременности это могут
# быть десятки/сотни запросов к Telegram одновременно.
_BROADCAST_CONCURRENCY = 20

EVENT_TITLE = "🏴‍☠️ <b><i>ЩЕДРЫЙ ПИРАТ</i></b> 🏴‍☠️"

# ВАЖНО: callback_data кнопки "Угадать" намеренно начинается с "city_".
# В mainhelp.py есть общий catch-all колбэк-хендлер (ловит ВСЁ, кроме данных
# с префиксом "city_"/"crystop_"), зарегистрированный раньше наших хендлеров —
# без этого префикса Telegram отдавал клик именно ему, и он отвечал
# "неизвестная команда", потому что не знает про нашу игру. Трогать
# mainhelp.py нельзя, поэтому просто используем префикс, который тот
# хендлер сам сознательно пропускает.
CASE_GUESS_CB = "city_case_guess"

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
    _LAST_GROUP_REFRESH_TS.pop(chat_id, None)


def _get_all_chats_sync() -> list[tuple[int, str]]:
    conn = _chats_conn()
    rows = conn.execute("SELECT chat_id, chat_type FROM known_chats").fetchall()
    conn.close()
    return rows


async def get_all_chats() -> list[tuple[int, str]]:
    """Список (chat_id, chat_type) всех чатов, где бота когда-либо видели."""
    return await asyncio.to_thread(_get_all_chats_sync)


# ═══════════════════════════════════════════════════════════
#  ГЛОБАЛЬНОЕ СОСТОЯНИЕ ИВЕНТА — ОДНО НА ВЕСЬ БОТ
# ═══════════════════════════════════════════════════════════
#
# _CASE = {
#   "running":            bool,  # ивент запущен командой /startcase и ещё не закрылся
#   "active":             bool,  # число загадано, приём ответов идёт
#   "secret_number":      int | None,           # загаданное число (1..999), скрыто до раскрытия
#   "started_at":         float,                # unix ts запуска текущего ивента
#   "expires_at":         float,                # unix ts раскрытия (started_at + 24ч)
#   "guesses":            {uid: {"name": str, "number": int, "ts": float}},
#                                                # ответы копятся молча, никому не показываются
#
#   ---- Настройки ТЕКУЩЕГО/ПОСЛЕДНЕГО ивента (задаются админом в /startcase) ----
#   "prize_type":            str,          # "coins" | "artifact" | "status"
#   "prize_amount":          int | None,   # для "coins" — сумма приза
#   "prize_artifact_key":    str | None,
#   "prize_artifact_name":   str | None,
#   "prize_artifact_mult":   float | None,
#   "prize_artifact_emoji_id": str | None,  # custom-эмодзи артефакта (если есть у него в пуле)
#   "prize_artifact_emoji":    str | None,  # обычный юникод-эмодзи (фолбэк/аргумент tg-emoji)
#   "prize_status_tier":     str | None,   # "vip" | "premium"
#
#   ---- Итоги ПОСЛЕДНЕГО завершившегося ивента (для текста карточки в простое) ----
#   "last_secret_number":  int | None,
#   "last_winner_name":    str | None,
#   "last_winner_number":  int | None,   # какое число назвал победитель
#   "last_exact":          bool | None,  # True — угадал точно, False — ближайший
#   "last_participants":   int | None,
#   "last_prize_type":     str | None,
#   "last_prize_label":    str | None,
# }
_CASE: dict = {
    "running":            False,
    "active":             False,
    "secret_number":      None,
    "started_at":         0.0,
    "expires_at":         0.0,
    "guesses":            {},

    "prize_type":           "coins",
    "prize_amount":         None,
    "prize_artifact_key":   None,
    "prize_artifact_name":  None,
    "prize_artifact_mult":  None,
    "prize_artifact_emoji_id": None,
    "prize_artifact_emoji":    None,
    "prize_status_tier":    None,

    "last_secret_number":  None,
    "last_winner_name":    None,
    "last_winner_number":  None,
    "last_exact":          None,
    "last_participants":   None,
    "last_prize_type":     None,
    "last_prize_label":    None,

    # Картинка ивента (см. /photo в main.py) — file_id фото, которое
    # прикрепляется к карточке вместо простого текстового сообщения.
    # Живёт поверх пересоздания ивента, пока админ не пришлёт новое
    # фото командой /photo.
    "photo_file_id":       None,
}


def get_case_state() -> dict:
    """Возвращает глобальное состояние ивента (одно на весь бот)."""
    return _CASE


def set_event_photo(file_id: str | None) -> None:
    """Задаёт (или сбрасывает, если file_id=None) картинку ивента —
    после этого карточка отправляется как фото с текстом-подписью
    вместо обычного текстового сообщения. См. команду /photo в main.py."""
    _CASE["photo_file_id"] = file_id


def get_event_photo() -> str | None:
    return _CASE["photo_file_id"]


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _spawn_event(state: dict) -> None:
    """Открывает новый ивент с нуля: загадывает число 1..999 и ставит
    таймер на 24 часа. Настройки приза (prize_*) НЕ трогаем — их задаёт
    start_case() перед вызовом этой функции."""
    now = time.time()
    state["active"]        = True
    state["secret_number"] = random.randint(NUMBER_MIN, NUMBER_MAX)
    state["started_at"]    = now
    state["expires_at"]    = now + EVENT_DURATION_SECONDS
    state["guesses"]       = {}


# ---------- Управление циклом (админ) ----------

def start_case(
    prize_type: str = "coins",
    prize_amount: int | None = None,
    prize_artifact: dict | None = None,
    prize_status_tier: str | None = None,
) -> bool:
    """/startcase — запускает ивент (на весь бот). False, если уже запущен.

    prize_type    — "coins" (фиксированная сумма монет), "artifact" (фиксированный
                     артефакт) или "status" (фиксированный VIP/Premium).
    prize_amount  — для prize_type="coins": сколько монет получит победитель.
    prize_artifact — для prize_type="artifact": {"key", "name", "multiplier",
                     "emoji_id" (опц., custom-эмодзи), "emoji" (опц., юникод-фолбэк)}.
    prize_status_tier — для prize_type="status": "vip" | "premium".
    """
    if _CASE["running"]:
        return False

    _CASE["prize_type"]   = prize_type
    _CASE["prize_amount"] = max(1, int(prize_amount)) if prize_type == "coins" else None

    if prize_type == "artifact" and prize_artifact:
        _CASE["prize_artifact_key"]      = prize_artifact.get("key")
        _CASE["prize_artifact_name"]     = prize_artifact.get("name")
        _CASE["prize_artifact_mult"]     = prize_artifact.get("multiplier")
        _CASE["prize_artifact_emoji_id"] = prize_artifact.get("emoji_id")
        _CASE["prize_artifact_emoji"]    = prize_artifact.get("emoji") or "♦️"
    else:
        _CASE["prize_artifact_key"]      = None
        _CASE["prize_artifact_name"]     = None
        _CASE["prize_artifact_mult"]     = None
        _CASE["prize_artifact_emoji_id"] = None
        _CASE["prize_artifact_emoji"]    = None

    _CASE["prize_status_tier"] = prize_status_tier if prize_type == "status" else None

    _CASE["running"] = True
    _spawn_event(_CASE)
    return True


async def stop_case(bot) -> bool:
    """
    /stopcase — останавливает ивент. False, если он и так не запущен.
    Если на момент /stopcase число ещё не раскрыто — раскрываем его
    немедленно ТЕМ ЖЕ путём, что и обычное закрытие по таймеру
    (считаем победителя по уже собранным ответам, карточка обновляется
    во всех чатах) — просто раньше срока.
    """
    if not _CASE["running"]:
        return False
    if _CASE["active"]:
        await _close_chest(bot)  # уже сам выставляет running/active в False
    else:
        _CASE["running"] = False
    return True


# ---------- Ответ игрока ----------

async def try_guess(uid: int, name: str, number: int) -> dict:
    """
    Пытается засчитать ответ игрока uid в ОБЩЕМ ивенте (не важно, из
    какого чата пришёл ответ — состояние одно на весь бот). У каждого
    игрока только одна попытка за весь ивент.

    Возвращает dict:
      {"ok": True, "number": int, "count": int}
      {"ok": False, "reason": "no_active"}
      {"ok": False, "reason": "bad_range"}
      {"ok": False, "reason": "already_guessed", "number": int}  — что игрок уже называл
    """
    if not _CASE["active"]:
        return {"ok": False, "reason": "no_active"}

    if not (NUMBER_MIN <= number <= NUMBER_MAX):
        return {"ok": False, "reason": "bad_range"}

    existing = _CASE["guesses"].get(uid)
    if existing is not None:
        return {"ok": False, "reason": "already_guessed", "number": existing["number"]}

    _CASE["guesses"][uid] = {"name": name, "number": number, "ts": time.time()}

    return {"ok": True, "number": number, "count": len(_CASE["guesses"])}


def has_guessed(uid: int) -> bool:
    """Уже называл ли этот игрок число в текущем ивенте."""
    return uid in _CASE["guesses"]


# ---------- Тексты и клавиатура ----------

DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬"


# ID premium custom-эмодзи, который рисуется ИКОНКОЙ слева на кнопке
# "Угадать" (Bot API 9.4, поле icon_custom_emoji_id). Работает ТОЛЬКО если
# у аккаунта бота есть активная Telegram Premium подписка (или куплен доп.
# юзернейм на Fragment) — иначе Telegram эту иконку молча проигнорирует.
CASE_GUESS_BUTTON_EMOJI_ID = "5377544787839521766"  # ← замени на свой ID


def case_keyboard(active: bool) -> InlineKeyboardMarkup | None:
    """Кнопка "Угадать" — только пока идёт приём ответов, с обратным
    отсчётом до раскрытия числа прямо на кнопке (кнопка перерисовывается
    вместе с карточкой на каждом тике, так что таймер на ней тоже "тикает").

    Вид: [premium-иконка] 🔮 Угадать | ⏳ ЧЧ:ММ — иконка задаётся отдельным
    полем icon_custom_emoji_id, а не эмодзи внутри text (Telegram не
    рендерит custom-эмодзи как символ текста на кнопках, только как icon)."""
    if not active:
        return None
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    remaining = max(0, int(_CASE["expires_at"] - time.time()))
    hrs, rem  = divmod(remaining, 3600)
    mins, _s  = divmod(rem, 60)

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"🔮 Угадать | ⏳ {hrs:02d}:{mins:02d}",
        callback_data=CASE_GUESS_CB,
        icon_custom_emoji_id=CASE_GUESS_BUTTON_EMOJI_ID,
        style="primary",  # синяя кнопка; варианты: "success" (зелёная), "danger" (красная)
    )
    builder.adjust(1)
    return builder.as_markup()


def _artifact_icon(state: dict) -> str:
    """Иконка артефакта-приза: если у самого артефакта в пуле есть свой
    custom-эмодзи (emoji_id) — используем именно его, иначе показываем
    обычный юникод-эмодзи (по умолчанию ♦️, как в shop._artifact_desc), заданный при выборе приза
    в /startcase (см. start_case в этом же файле)."""
    emoji_id = state.get("prize_artifact_emoji_id")
    emoji    = state.get("prize_artifact_emoji") or "♦️"
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>'
    return emoji


def _active_prize_line(state: dict) -> str:
    """Строка "что достанется победителю" для карточки, пока приём ответов
    идёт — зависит от режима приза, выбранного админом в /startcase."""
    if state["prize_type"] == "artifact":
        name = _esc(state["prize_artifact_name"] or "?")
        mult = state["prize_artifact_mult"]
        mult_str = f" (×{mult})" if mult else ""
        return f'{_artifact_icon(state)} <b><i>Приз: {name}{mult_str}</i></b>'
    if state["prize_type"] == "status":
        label = "VIP" if state["prize_status_tier"] == "vip" else "Premium"
        return (
            f'<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> '
            f'<b><i>Приз: статус {label} (30 дней)</i></b>'
        )
    amount_str = format_amount(state["prize_amount"] or 0)
    return (
        f'<tg-emoji emoji-id="5278467510604160626">🌟</tg-emoji> '
        f'<b><i>Приз: <code>{amount_str}</code>{COIN}</i></b>'
    )


def case_status_text() -> str:
    """Единый текст карточки ивента — используется ВЕЗДЕ: и когда бот
    впервые анонсирует ивент по /startcase, и на обычных обновлениях
    карточки. Никакого отдельного "текста для старта" нет.

    Весь текст (кроме иконок-эмодзи) — жирным И курсивом одновременно."""
    state = _CASE
    now   = time.time()

    if state["active"]:
        remaining = max(0, int(state["expires_at"] - now))
        hrs, rem  = divmod(remaining, 3600)
        mins, secs = divmod(rem, 60)
        timer_str  = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        count = len(state["guesses"])
        if count:
            players_line = (
                f'<tg-emoji emoji-id="5402477260982731644">🌟</tg-emoji> '
                f'<b><i>Уже рискнули: {count} {_players_word(count)}</i></b>'
            )
        else:
            players_line = (
                f'<tg-emoji emoji-id="5399913388845322366">🌟</tg-emoji> '
                f'<b><i>Пока никто не рискнул — стань первым!</i></b>'
            )

        return (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<b><i>Капитан спрятал число от {NUMBER_MIN} до {NUMBER_MAX} на дне сундука. '
            f'У каждого — только одна попытка назвать его.</i></b>\n\n'
            f'<blockquote>'
            f'{_active_prize_line(state)}\n'
            f'<tg-emoji emoji-id="5382194935057372936">🌟</tg-emoji> '
            f'<b><i>До раскрытия: <code>{timer_str}</code></i></b>\n'
            f'{players_line}'
            f'</blockquote>\n'
            f'<b><i>Назови число ближе всех к загаданному — и приз твой.</i></b>\n'
            f'<tg-emoji emoji-id="5397916757333654639">🌟</tg-emoji> '
            f'<b><i>Участие бесплатное, один шанс на игрока.</i></b>'
        )

    if state.get("last_secret_number") is not None:
        secret_str = str(state["last_secret_number"])
        if state.get("last_winner_name"):
            exact = state.get("last_exact")
            guess_line = (
                f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> '
                f'<b><i>Победитель: {_esc(state["last_winner_name"])} '
                f'(назвал {state["last_winner_number"]}'
                f'{" — точно в яблочко!" if exact else ""})</i></b>\n'
            )
            prize_line = (
                f'<tg-emoji emoji-id="5438496463044752972">🌟</tg-emoji> '
                f'<b><i>Забрал: {state.get("last_prize_label") or "—"}</i></b>'
            )
            result_block = guess_line + prize_line
        else:
            result_block = (
                f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> '
                f'<b><i>Никто не рискнул — приз остался на дне.</i></b>'
            )

        return (
            f'{EVENT_TITLE}\n'
            f'{DIVIDER}\n'
            f'<b><i>Сундук раскрыт — загаданное число было: <code>{secret_str}</code></i></b>\n\n'
            f'<blockquote>'
            f'{result_block}'
            f'</blockquote>\n'
            f'<i>Ждём, пока капитан не решит начать новый ивент.</i>'
        )

    return (
        f'{EVENT_TITLE}\n'
        f'{DIVIDER}\n'
        f'<b><i>Тишина... сундук с загадкой ещё не заброшен в эти воды.</i></b>'
    )


def _players_word(n: int) -> str:
    """Русское склонение слова "игрок" под число (1 игрок / 2 игрока / 5 игроков)."""
    n10, n100 = n % 10, n % 100
    if 11 <= n100 <= 14:
        return "игроков"
    if n10 == 1:
        return "игрок"
    if 2 <= n10 <= 4:
        return "игрока"
    return "игроков"


# ---------- Карточки: per-chat id сообщения ----------
# ══════════════════════════════════════════════════════════════════════
#  Состояние ивента общее на весь бот, но у КАЖДОГО чата своя карточка —
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
    зависит, как именно обновляется карточка ивента в этом чате."""
    get_card_state(chat_id)["chat_type"] = chat_type


# ══════════════════════════════════════════════════════════════════════
#  ЛОК НА ЧАТ ДЛЯ ОБНОВЛЕНИЯ КАРТОЧКИ
#
#  bump_card/refresh/close теперь трогают карточки СРАЗУ во всех чатах,
#  но каждый чат по-прежнему обновляется независимо и сериализованно —
#  лок и троттлинг остались per-chat, просто теперь запускаются
#  параллельно (через asyncio.gather) для разных chat_id.
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

# Время последнего delete+send карточки в ГРУППЕ (отдельно от
# _LAST_CARD_UPDATE_TS) — используется тихим тиком (_refresh_chat_card),
# чтобы поднимать карточку не чаще раза в GROUP_CARD_REFRESH_SECONDS.
# Обновляется и значимыми событиями (_push_card), чтобы старт/раскрытие
# прямо перед тиком не приводили к двойному перевыпуску подряд.
_LAST_GROUP_REFRESH_TS: dict[int, float] = {}


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


async def _delete_and_resend(bot, chat_id: int, card: dict, text: str, active: bool, what: str):
    """Удаляет старую карточку и присылает новую — общий кусок для
    _push_card (значимые события в группах) и _refresh_chat_card (тихий
    "подъём" карточки в группах раз в GROUP_CARD_REFRESH_SECONDS).
    Вызывающий уже держит _get_card_lock(chat_id) и прошёл _throttle_card."""
    old_id = card.get("msg_id")
    if old_id:
        try:
            await _tg_call_with_retry(
                lambda: bot.delete_message(chat_id, old_id),
                chat_id, f"{what}.delete_message",
            )
        except Exception as e:
            print(f"[case] {what}: delete_message FAILED chat_id={chat_id} msg_id={old_id}: {e}")
    try:
        sent = await _send_card_new(bot, chat_id, text, active)
        card["msg_id"] = sent.message_id
    except Exception as e:
        print(f"[case] {what}: send FAILED chat_id={chat_id}: {e}")


async def _push_card(bot, chat_id: int, text: str, active: bool):
    """Обновляет карточку ивента в ОДНОМ конкретном чате на значимом
    событии (старт/раскрытие) — И В ЛИЧКЕ, И В ГРУППЕ просто редактирует
    текст на месте, без пересоздания сообщения. Пересоздание (удалить
    старое + прислать новое) в группах происходит ТОЛЬКО на тихом тике
    раз в GROUP_CARD_REFRESH_SECONDS (см. _refresh_chat_card)."""
    card = get_card_state(chat_id)
    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)
        await _send_or_edit(bot, chat_id, card, text, active)


async def _refresh_chat_card(bot, chat_id: int, text: str):
    """Тихий тик (раз в CARD_REFRESH_SECONDS): в личке просто обновляет
    таймер/счётчик на месте — дёшево, можно часто. В группе/супергруппе
    вместо этого раз в GROUP_CARD_REFRESH_SECONDS удаляет старое сообщение
    и шлёт новое — иначе отредактированная "на месте" карточка тихо тонет
    под обычной перепиской и её никто не видит."""
    card = get_card_state(chat_id)
    if not card.get("msg_id"):
        return

    if card.get("chat_type") in ("group", "supergroup"):
        now  = time.time()
        last = _LAST_GROUP_REFRESH_TS.get(chat_id, 0.0)
        if now - last < GROUP_CARD_REFRESH_SECONDS:
            return
        async with _get_card_lock(chat_id):
            await _throttle_card(chat_id)
            await _delete_and_resend(bot, chat_id, card, text, True, "_refresh_chat_card")
        _LAST_GROUP_REFRESH_TS[chat_id] = time.time()
        return

    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)
        await _send_or_edit(bot, chat_id, card, text, active=True)


async def _broadcast(bot, text: str, active: bool):
    """Рассылает ОДИНАКОВЫЙ текст карточки во ВСЕ известные чаты параллельно
    (с ограничением конкурентности) — используется на значимых событиях
    (старт ивента / раскрытие числа)."""
    chats = await get_all_chats()
    if not chats:
        return

    sem = asyncio.Semaphore(_BROADCAST_CONCURRENCY)

    async def _one(chat_id: int):
        async with sem:
            await _push_card(bot, chat_id, text, active)

    await asyncio.gather(*(_one(chat_id) for chat_id, _ in chats), return_exceptions=True)


async def send_case_card(bot, chat_id: int):
    """Отправляет свежую карточку ивента новым сообщением в ОДНОМ
    чате (например, по команде /startcase или /case) и запоминает её id."""
    card = get_card_state(chat_id)
    async with _get_card_lock(chat_id):
        await _throttle_card(chat_id)
        text = case_status_text()
        sent = await _send_card_new(bot, chat_id, text, _CASE["active"])
        card["msg_id"] = sent.message_id
        return sent


async def bump_card(bot):
    """Обновление карточки на ЗНАЧИМЫХ событиях (старт ивента, раскрытие
    числа) — рассылается СРАЗУ во ВСЕ чаты бота. Ответы игроков (см.
    try_guess) карточку НЕ дёргают — они копятся молча и попадут в
    счётчик "уже рискнули" только на следующем тихом тике, чтобы частая
    отгадка не превращалась в спам обновлений на 24 часа вперёд."""
    await _broadcast(bot, case_status_text(), _CASE["active"])


# ---------- Рассылка анонса ивента по команде /startcase ----------

async def broadcast_event_start(
    bot,
    prize_type: str = "coins",
    prize_amount: int | None = None,
    prize_artifact: dict | None = None,
    prize_status_tier: str | None = None,
):
    """Запускает ивент ПО КОМАНДЕ /startcase (после того, как админ прошёл
    мастер выбора приза в main.py): загадывает число и рассылает карточку
    (тот же case_status_text(), что и везде — отдельного текста для
    "анонса" больше нет) во все известные чаты (личка + группы).
    Ошибки по отдельным чатам (бот заблокирован/выгнан) просто пропускаются.

    prize_type/prize_amount/prize_artifact/prize_status_tier — см. start_case().

    ВАЖНО: вызывается только из хендлера команды, НЕ на старте процесса —
    иначе ивент начинался бы сам по себе при каждом деплое/рестарте бота."""
    if not start_case(prize_type, prize_amount, prize_artifact, prize_status_tier):
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


# ---------- Определение победителя ----------

def _determine_winner(state: dict) -> tuple[int | None, dict | None]:
    """Выбирает победителя по уже собранным ответам:
    1) если есть точные совпадения с secret_number — среди них побеждает
       тот, кто ответил РАНЬШЕ по времени;
    2) иначе — среди ВСЕХ ответов побеждает ближайший по модулю разницы
       (при равенстве разницы — снова кто раньше ответил).
    Возвращает (uid, guess_dict) или (None, None), если ответов не было."""
    guesses = state["guesses"]
    if not guesses:
        return None, None

    secret = state["secret_number"]
    exact  = [(uid, g) for uid, g in guesses.items() if g["number"] == secret]

    if exact:
        candidates = exact
    else:
        min_diff   = min(abs(g["number"] - secret) for g in guesses.values())
        candidates = [(uid, g) for uid, g in guesses.items() if abs(g["number"] - secret) == min_diff]

    candidates.sort(key=lambda item: item[1]["ts"])
    winner_uid, winner_g = candidates[0]
    return winner_uid, winner_g


# ---------- Фоновый цикл (раскрытие числа) ----------

async def _close_chest(bot):
    state  = _CASE
    secret = state["secret_number"]

    winner_uid, winner_g = _determine_winner(state)
    participants = len(state["guesses"])

    state["active"]  = False
    state["running"] = False

    state["last_secret_number"] = secret
    state["last_participants"]  = participants

    if winner_uid:
        prize_type = state["prize_type"]
        if prize_type == "artifact":
            prize_label = await _grant_artifact_prize(winner_uid)
        elif prize_type == "status":
            prize_label = await _grant_status_prize(winner_uid)
        else:
            amount = state["prize_amount"] or 0
            await aio_change_balance(winner_uid, amount)
            prize_label = f'<code>{format_amount(amount)}</code>{COIN}'

        exact = winner_g["number"] == secret

        state["last_winner_name"]   = winner_g["name"]
        state["last_winner_number"] = winner_g["number"]
        state["last_exact"]         = exact
        state["last_prize_type"]    = prize_type
        state["last_prize_label"]   = prize_label
    else:
        state["last_winner_name"]   = None
        state["last_winner_number"] = None
        state["last_exact"]         = None
        state["last_prize_type"]    = None
        state["last_prize_label"]   = None

    await _broadcast(bot, case_status_text(), active=False)


async def case_tick_loop(bot):
    """
    Единый фоновый тик (по аналогии с остальными циклами проекта, например
    _duel_timer_loop в mainhelp.py). Раз в секунду проверяет ивент:
    как только истекли 24 часа — раскрывает число, определяет победителя
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


async def case_card_refresh_loop(bot):
    """Отдельный фоновый тик: раз в CARD_REFRESH_SECONDS молча обновляет
    таймер и счётчик участников на карточках во всех чатах, пока ивент
    активен — без кнопки "Обновить", без пересоздания сообщений (это
    только для значимых событий, см. bump_card). Именно здесь, а не
    сразу при каждом ответе, карточка узнаёт о новых участниках —
    ответы копятся "на фоне" и не дёргают рассылку немедленно."""
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
