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

from database import aio_change_balance, aio_get_user, format_amount
from miner import COIN

# ---------- Параметры игры ----------

CASE_INITIAL_BANK          = 500_000   # стартовый банк сундука
CASE_DEPOSIT                = 50_000    # фиксированный вклад
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
#   "bank":               int,
#   "expires_at":         float, # unix ts закрытия текущего сундука
#   "window_seconds":     int,   # длина текущего окна (для прогресс-бара)
#   "last_uid":           int | None,
#   "last_name":          str | None,
#   "cooldowns":          {uid: last_invest_ts},   # общий кулдаун на весь бот
#   "paused_until":        float | None,
#   "last_winner_name":    str | None,
#   "last_winner_amount":  int | None,
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
}


def get_case_state() -> dict:
    """Возвращает глобальное состояние сундука (одно на весь бот)."""
    return _CASE


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _spawn_chest(state: dict) -> None:
    """Открывает новый сундук с нуля: стартовый банк и увеличенный таймер
    на ПЕРВЫЙ вклад (15 минут — чтобы игроки успели заметить и зайти в
    любом из чатов бота). Как только кто-то вложится первым — таймер
    начинает работать в обычном режиме (см. try_invest)."""
    state["active"]         = True
    state["bank"]            = CASE_INITIAL_BANK
    state["expires_at"]      = time.time() + CASE_FIRST_DEPOSIT_SECONDS
    state["window_seconds"]  = CASE_FIRST_DEPOSIT_SECONDS
    state["last_uid"]        = None
    state["last_name"]       = None
    state["cooldowns"]       = {}
    state["paused_until"]    = None


# ---------- Управление циклом (админ / автостарт) ----------

def start_case() -> bool:
    """/startcase — запускает общий цикл сундука (на весь бот). False, если уже запущен."""
    if _CASE["running"]:
        return False
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
      {"ok": True, "bank": int}
      {"ok": False, "reason": "no_active" | "cooldown" | "insufficient",
       "wait": int (для cooldown), "balance": int (для insufficient)}
    """
    if not _CASE["active"]:
        return {"ok": False, "reason": "no_active"}

    now     = time.time()
    last_ts = _CASE["cooldowns"].get(uid, 0)
    elapsed = now - last_ts
    if elapsed < PLAYER_COOLDOWN_SECONDS:
        return {"ok": False, "reason": "cooldown", "wait": int(PLAYER_COOLDOWN_SECONDS - elapsed) + 1}

    # Атомарное списание — та же гарантия, что и везде в проекте:
    # если баланса не хватает, change_balance просто вернёт None и
    # ничего не спишет (см. database.change_balance).
    new_balance = await aio_change_balance(uid, -CASE_DEPOSIT, min_balance=0)
    if new_balance is None:
        u = await aio_get_user(uid)
        balance = u.get("balance", 0) if u else 0
        return {"ok": False, "reason": "insufficient", "balance": balance}

    _CASE["bank"]           += CASE_DEPOSIT
    _CASE["last_uid"]        = uid
    _CASE["last_name"]       = name
    _CASE["cooldowns"][uid]  = now
    _CASE["expires_at"]      = now + CASE_TIMER_SECONDS
    _CASE["window_seconds"]  = CASE_TIMER_SECONDS

    return {"ok": True, "bank": _CASE["bank"]}


# ---------- Тексты и клавиатура ----------

def case_keyboard(active: bool) -> InlineKeyboardMarkup | None:
    """Кнопка "Вложить" — только когда сундук активен. Кнопки "Обновить"
    больше нет: карточка теперь обновляется сама, каждые несколько секунд."""
    if not active:
        return None
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💰 Вложить {format_amount(CASE_DEPOSIT)}", callback_data=CASE_INVEST_CB)
    builder.adjust(1)
    return builder.as_markup()


def event_announce_text() -> str:
    """Красивый анонс ивента — отправляется во все известные чаты по команде /startcase."""
    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>Где-то в этих водах затонул корабль легендарного пирата, '
        'а вместе с ним — сундук, доверху набитый золотом. Каждый вклад '
        'приближает момент, когда сундук всплывёт... но заберёт добычу лишь тот, '
        'кто окажется рядом последним.</blockquote>\n\n'
        f'🎟 <i>Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>{COIN} • '
        f'таймер сбрасывается с каждым новым вкладом!</i>'
    )


def case_status_text() -> str:
    """Текст карточки сундука."""
    state = _CASE
    now   = time.time()

    if state["active"]:
        remaining  = max(0, int(state["expires_at"] - now))
        mins, secs = divmod(remaining, 60)
        timer_str  = f"{mins:02d}:{secs:02d}"
        bank_str   = format_amount(state["bank"])

        if state["last_uid"]:
            last_line = f'👤 Последним вложился: <b>{_esc(state["last_name"])}</b>'
        else:
            last_line = '👤 Пока никто не рискнул — стань первым!'

        return (
            f'{EVENT_TITLE}\n\n'
            f'<blockquote>'
            f'💰 <b>В сундуке:</b> {bank_str}{COIN}\n'
            f'⏳ <b>Уплывает через:</b> {timer_str}\n'
            f'{last_line}'
            f'</blockquote>\n'
            f'✨ <i>Вложись последним перед закрытием — и всё золото твоё.</i>\n'
            f'🎟 Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>{COIN}'
        )

    if state["running"]:
        remaining  = max(0, int(state["paused_until"] - now)) if state["paused_until"] else 0
        mins, secs = divmod(remaining, 60)

        winner_line = ""
        if state.get("last_winner_name"):
            winner_line = (
                f'\n\n<blockquote>👑 Последний счастливчик: <b>{_esc(state["last_winner_name"])}</b>\n'
                f'💰 Унёс с собой: <b>{format_amount(state["last_winner_amount"])}</b>{COIN}</blockquote>'
            )

        return (
            f'{EVENT_TITLE}\n\n'
            f'<blockquote>🌊 Пират снова прячет добычу на дне...\n'
            f'🕰 Сундук покажется через <b>{mins:02d}:{secs:02d}</b></blockquote>'
            f'{winner_line}'
        )

    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>🗺 Пока тихо — сундук ещё не заброшен в эти воды.</blockquote>'
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


async def _send_or_edit(bot, chat_id: int, card: dict, text: str, active: bool):
    """Тихое обновление на месте: пробуем отредактировать старую карточку.
    ВАЖНО: вызывается только изнутри блока с уже захваченным _get_card_lock
    (и уже прошедшего _throttle_card) — сама лок/троттлинг не берёт, чтобы
    не было дедлока и двойного троттлинга при вложенных вызовах."""
    msg_id = card.get("msg_id")
    if msg_id:
        try:
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
                # текст (и клавиатура) не изменились — это НЕ ошибка,
                # редактировать нечего, лишнее сообщение слать не нужно
                return
            print(f"[case] edit_message_text FAILED chat_id={chat_id} msg_id={msg_id}: {e}")
    try:
        sent = await _tg_call_with_retry(
            lambda: bot.send_message(
                chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active),
            ),
            chat_id, "send_message",
        )
        card["msg_id"] = sent.message_id
    except Exception as e:
        print(f"[case] send_message FAILED chat_id={chat_id}: {e}")


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
            sent = await _tg_call_with_retry(
                lambda: bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active)),
                chat_id, "_push_card.send_message",
            )
            card["msg_id"] = sent.message_id
        except Exception as e:
            print(f"[case] _push_card: send_message FAILED chat_id={chat_id}: {e}")


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
        sent = await _tg_call_with_retry(
            lambda: bot.send_message(
                chat_id, text, parse_mode="HTML",
                reply_markup=case_keyboard(_CASE["active"]),
            ),
            chat_id, "send_case_card",
        )
        card["msg_id"] = sent.message_id
        return sent


async def bump_card(bot):
    """Обновление карточки на ЗНАЧИМЫХ событиях (новый вклад, закрытие,
    открытие нового сундука) — рассылается СРАЗУ во ВСЕ чаты бота, потому
    что банк один на всех и вклад в одном чате должен быть виден везде."""
    await _broadcast(bot, case_status_text(), _CASE["active"])


# ---------- Рассылка анонса ивента на старте бота ----------

def _broadcast_card_text() -> str:
    """Анонс + статус сундука ОДНИМ сообщением (флавор-текст ивента сразу
    вместе с банком/таймером), чтобы при запуске бот не слал два сообщения подряд."""
    state = _CASE
    now = time.time()
    remaining  = max(0, int(state["expires_at"] - now))
    mins, secs = divmod(remaining, 60)

    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>Где-то в этих водах затонул корабль легендарного пирата, '
        'а вместе с ним — сундук, доверху набитый золотом. Каждый вклад '
        'приближает момент, когда сундук всплывёт... но заберёт добычу лишь тот, '
        'кто окажется рядом последним.\n\n'
        f'💰 В сундуке: <b>{format_amount(state["bank"])}</b>{COIN}\n'
        f'⏳ Уплывает через: <b>{mins:02d}:{secs:02d}</b></blockquote>\n\n'
        f'🎟 <i>Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>{COIN} • '
        f'таймер сбрасывается с каждым новым вкладом!</i>'
    )


async def broadcast_event_start(bot):
    """Запускает ивент ПО КОМАНДЕ /startcase: открывает сундук и рассылает
    анонс + карточку одним сообщением во все известные чаты (личка + группы).
    Ошибки по отдельным чатам (бот заблокирован/выгнан) просто пропускаются.

    ВАЖНО: вызывается только из хендлера команды, НЕ на старте процесса —
    иначе ивент начинался бы сам по себе при каждом деплое/рестарте бота."""
    if not start_case():
        return False

    chats = await get_all_chats()
    for chat_id, chat_type in chats:
        card = get_card_state(chat_id)
        card["chat_type"] = chat_type

        try:
            sent = await bot.send_message(
                chat_id, _broadcast_card_text(), parse_mode="HTML",
                reply_markup=case_keyboard(_CASE["active"]),
            )
            card["msg_id"] = sent.message_id
        except Exception as e:
            print(f"[broadcast_event_start] {chat_id}: {e}")
            continue

        await asyncio.sleep(0.05)  # небольшая пауза, чтобы не словить flood-лимит

    return True


# ---------- Фоновый цикл (закрытие сундука / авто-рестарт) ----------

async def _close_chest(bot):
    state       = _CASE
    bank        = state["bank"]
    winner_uid  = state["last_uid"]
    winner_name = state["last_name"]

    state["active"]       = False
    state["paused_until"] = time.time() + PAUSE_SECONDS

    if winner_uid:
        await aio_change_balance(winner_uid, bank)
        state["last_winner_name"]   = winner_name
        state["last_winner_amount"] = bank
        text = (
            f'{EVENT_TITLE}\n\n'
            f'🎉 <b>СУНДУК НАЙДЕН!</b> 🎉\n\n'
            f'<blockquote>👑 Победитель: <b>{_esc(winner_name)}</b>\n'
            f'💰 Забрал: <b>{format_amount(bank)}</b>{COIN}</blockquote>\n'
            f'⏳ <i>Новый сундук пират спрячет через 30 минут.</i>'
        )
    else:
        text = (
            f'{EVENT_TITLE}\n\n'
            '💨 <b>Сундук исчез в тумане...</b>\n\n'
            '<blockquote>Никто не успел вложиться — золото утонуло вместе с сундуком.</blockquote>\n'
            '⏳ <i>Новый сундук появится через 30 минут.</i>'
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
