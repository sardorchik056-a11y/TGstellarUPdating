# ============================================================
#  case.py — мини-игра "Общий сундук" (TGStellar), ивент "Щедрый пират"
#
#  Игроки скидываются в общий банк по фиксированной сумме.
#  Таймер сбрасывается при каждом вкладе. Кто вложил последним
#  перед истечением таймера — забирает ВЕСЬ банк.
#
#  Модуль полностью самостоятельный: хранит игровое состояние
#  сундука в памяти (per chat_id) и ничего не пишет в mainhelp.py.
#  Все хендлеры (/startcase, /stopcase, /case, кнопка "Вложить")
#  находятся в main.py — здесь только логика + красивые тексты.
#
#  Тут же — маленький реестр чатов (своя SQLite-табличка в отдельном
#  файле на диске, database.py не трогаем), нужный для одной вещи:
#  на старте бота разослать анонс ивента "во все чаты куда можно"
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

from database import aio_change_balance, aio_get_user, format_amount
from miner import COIN

# ---------- Параметры игры ----------

CASE_INITIAL_BANK       = 500_000   # стартовый банк сундука
CASE_DEPOSIT             = 50_000    # фиксированный вклад
CASE_TIMER_SECONDS       = 60        # таймер сундука (сбрасывается при каждом вкладе)
CASE_FIRST_DEPOSIT_SECONDS = 15 * 60  # время на ПЕРВЫЙ вклад в новом сундуке — 15 минут
PLAYER_COOLDOWN_SECONDS = 15        # кулдаун игрока между вкладами
PAUSE_SECONDS           = 30 * 60   # пауза после закрытия сундука (авто-рестарт)
CARD_REFRESH_SECONDS    = 2         # частота "тихого" авто-обновления карточки

EVENT_TITLE = "🏴‍☠️ <b>Ивент: Щедрый пират</b>"

# ВАЖНО: callback_data кнопки "Вложить" намеренно начинается с "city_".
# В mainhelp.py есть общий catch-all колбэк-хендлер (ловит ВСЁ, кроме данных
# с префиксом "city_"/"crystop_"), зарегистрированный раньше наших хендлеров —
# без этого префикса Telegram отдавал клик именно ему, и он отвечал
# "неизвестная команда", потому что не знает про нашу игру. Трогать
# mainhelp.py нельзя, поэтому просто используем префикс, который тот
# хендлер сам сознательно пропускает.
CASE_INVEST_CB = "city_case_invest"

# ═══════════════════════════════════════════════════════════
#  РЕЕСТР ЧАТОВ (для рассылки анонса на старте бота)
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


def _get_all_chats_sync() -> list[tuple[int, str]]:
    conn = _chats_conn()
    rows = conn.execute("SELECT chat_id, chat_type FROM known_chats").fetchall()
    conn.close()
    return rows


async def get_all_chats() -> list[tuple[int, str]]:
    """Список (chat_id, chat_type) всех чатов, где бота когда-либо видели."""
    return await asyncio.to_thread(_get_all_chats_sync)


# ---------- Состояние игры (per chat_id) ----------
# _CASES[chat_id] = {
#   "running":       bool,  # цикл запущен (вручную или автостартом) и не остановлен
#   "active":        bool,  # сундук сейчас открыт (принимает вклады)
#   "bank":          int,
#   "expires_at":    float, # unix ts закрытия текущего сундука
#   "last_uid":      int | None,
#   "last_name":     str | None,
#   "cooldowns":     {uid: last_invest_ts},
#   "paused_until":  float | None,
#   "msg_id":        int | None,   # сообщение-карточка сундука для редактирования
#   "chat_type":     str | None,   # "private" / "group" / "supergroup" — влияет
#                                  # на то, КАК обновляется карточка (см. ниже)
#   "last_winner_name":   str | None,
#   "last_winner_amount": int | None,
# }
_CASES: dict[int, dict] = {}


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def get_case_state(chat_id: int) -> dict:
    """Достаёт (или создаёт с нуля) состояние сундука для чата."""
    if chat_id not in _CASES:
        _CASES[chat_id] = {
            "running":            False,
            "active":             False,
            "bank":               0,
            "expires_at":         0.0,
            "last_uid":           None,
            "last_name":          None,
            "cooldowns":          {},
            "paused_until":       None,
            "msg_id":             None,
            "chat_type":          None,
            "last_winner_name":   None,
            "last_winner_amount": None,
        }
    return _CASES[chat_id]


def set_chat_type(chat_id: int, chat_type: str) -> None:
    """Запоминает тип чата ('private' / 'group' / 'supergroup') — от этого
    зависит, как именно обновляется карточка сундука при вкладе (см. bump_card)."""
    get_case_state(chat_id)["chat_type"] = chat_type


def _spawn_chest(state: dict) -> None:
    """Открывает новый сундук с нуля: стартовый банк и увеличенный таймер
    на ПЕРВЫЙ вклад (15 минут — чтобы игроки успели заметить и зайти).
    Как только кто-то вложится первым — таймер начинает работать в обычном
    режиме (см. try_invest: сброс до CASE_TIMER_SECONDS)."""
    state["active"]      = True
    state["bank"]        = CASE_INITIAL_BANK
    state["expires_at"]  = time.time() + CASE_FIRST_DEPOSIT_SECONDS
    state["last_uid"]    = None
    state["last_name"]   = None
    state["cooldowns"]   = {}
    state["paused_until"] = None


# ---------- Управление циклом (админ / автостарт) ----------

def start_case(chat_id: int) -> bool:
    """/startcase — запускает цикл. False, если уже запущен."""
    state = get_case_state(chat_id)
    if state["running"]:
        return False
    state["running"] = True
    _spawn_chest(state)
    return True


def stop_case(chat_id: int) -> bool:
    """
    /stopcase — останавливает цикл. Работает ТОЛЬКО в паузе
    (сундук закрыт). Если сундук активен или цикл не запущен — False.
    """
    state = get_case_state(chat_id)
    if not state["running"] or state["active"]:
        return False
    state["running"]      = False
    state["paused_until"] = None
    return True


# ---------- Вклад игрока ----------

async def try_invest(chat_id: int, uid: int, name: str) -> dict:
    """
    Пытается сделать вклад за игрока uid в сундук чата chat_id.
    Возвращает dict:
      {"ok": True, "bank": int}
      {"ok": False, "reason": "no_active" | "cooldown" | "insufficient",
       "wait": int (для cooldown), "balance": int (для insufficient)}
    """
    state = get_case_state(chat_id)

    if not state["active"]:
        return {"ok": False, "reason": "no_active"}

    now     = time.time()
    last_ts = state["cooldowns"].get(uid, 0)
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

    state["bank"]      += CASE_DEPOSIT
    state["last_uid"]   = uid
    state["last_name"]  = name
    state["cooldowns"][uid] = now
    state["expires_at"] = now + CASE_TIMER_SECONDS

    return {"ok": True, "bank": state["bank"]}


# ---------- Тексты и клавиатура ----------

def case_keyboard(active: bool) -> InlineKeyboardMarkup | None:
    """Кнопка "Вложить" — только когда сундук активен. Кнопки "Обновить"
    больше нет: карточка теперь обновляется сама, каждые 2 секунды."""
    if not active:
        return None
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💰 Вложить {format_amount(CASE_DEPOSIT)}", callback_data=CASE_INVEST_CB)
    builder.adjust(1)
    return builder.as_markup()


def event_announce_text() -> str:
    """Красивый анонс ивента — отправляется во все известные чаты при старте бота."""
    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>Легендарный пират устал хранить золото в одиночку и спрятал '
        'в этом чате общий сундук! Каждый вклад продлевает ему жизнь, а игрок, '
        'который вложится последним перед закрытием — заберёт себе всё золото.</blockquote>\n\n'
        f'⚓️ <i>Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>{COIN} • '
        f'таймер сбрасывается при каждом новом вкладе!</i>'
    )


def case_status_text(chat_id: int) -> str:
    state = get_case_state(chat_id)
    now   = time.time()

    if state["active"]:
        remaining   = max(0, int(state["expires_at"] - now))
        mins, secs  = divmod(remaining, 60)
        timer_str   = f"{mins:02d}:{secs:02d}"
        bank_str    = format_amount(state["bank"])

        if state["last_uid"]:
            last_line = f'👤 Последний вкладчик: <b>{_esc(state["last_name"])}</b>'
        else:
            last_line = '👤 Вкладчиков ещё не было'

        return (
            f'{EVENT_TITLE}\n\n'
            f'<blockquote>'
            f'📦 Банк сундука: <b>{bank_str}</b>{COIN}\n'
            f'⏳ До закрытия: <b>{timer_str}</b>\n'
            f'{last_line}'
            f'</blockquote>\n'
            f'<i>Кто вложит последним — заберёт всё! Вклад: '
            f'<b>{format_amount(CASE_DEPOSIT)}</b>{COIN}</i>'
        )

    if state["running"]:
        remaining  = max(0, int(state["paused_until"] - now)) if state["paused_until"] else 0
        mins, secs = divmod(remaining, 60)

        winner_line = ""
        if state.get("last_winner_name"):
            winner_line = (
                f'\n\n<blockquote>👑 Последний победитель: <b>{_esc(state["last_winner_name"])}</b>\n'
                f'💰 Забрал: <b>{format_amount(state["last_winner_amount"])}</b>{COIN}</blockquote>'
            )

        return (
            f'{EVENT_TITLE}\n\n'
            f'<blockquote>⏳ Пират прячет новый сундук... Открытие через '
            f'<b>{mins:02d}:{secs:02d}</b></blockquote>'
            f'{winner_line}'
        )

    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>Пират ещё не заглядывал в этот чат.</blockquote>'
        '<i>Ожидайте начала ивента!</i>'
    )


# ---------- Отправка / обновление карточки сундука ----------

async def send_case_card(bot, chat_id: int):
    """Отправляет свежую карточку сундука новым сообщением и запоминает её id."""
    state = get_case_state(chat_id)
    text  = case_status_text(chat_id)
    sent  = await bot.send_message(
        chat_id, text, parse_mode="HTML",
        reply_markup=case_keyboard(state["active"]),
    )
    state["msg_id"] = sent.message_id
    return sent


async def _send_or_edit(bot, chat_id: int, state: dict, text: str, active: bool):
    """Тихое обновление на месте: пробуем отредактировать старую карточку,
    если не вышло (удалена/устарела) — шлём новую."""
    msg_id = state.get("msg_id")
    if msg_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=msg_id,
                parse_mode="HTML", reply_markup=case_keyboard(active),
            )
            return
        except Exception:
            pass  # текст не изменился, либо сообщение недоступно — не страшно
    try:
        sent = await bot.send_message(
            chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active),
        )
        state["msg_id"] = sent.message_id
    except Exception:
        pass


async def refresh_card(bot, chat_id: int):
    """Тихий тик (раз в CARD_REFRESH_SECONDS): просто обновляет таймер на месте,
    и в личке, и в группе — без пересоздания сообщения."""
    state = get_case_state(chat_id)
    if not state.get("msg_id"):
        return
    text = case_status_text(chat_id)
    await _send_or_edit(bot, chat_id, state, text, state["active"])


async def bump_card(bot, chat_id: int):
    """Обновление карточки на ЗНАЧИМЫХ событиях (новый вклад, закрытие сундука,
    открытие нового): в личке с ботом — редактирует то же сообщение,
    в группах/супергруппах — удаляет старое и присылает новое, чтобы карточка
    "поднималась" в чате и не терялась среди сообщений участников."""
    state = get_case_state(chat_id)
    text   = case_status_text(chat_id)
    active = state["active"]

    if state.get("chat_type") == "private":
        await _send_or_edit(bot, chat_id, state, text, active)
        return

    # группа / супергруппа — удаляем старую карточку и шлём новую
    old_id = state.get("msg_id")
    if old_id:
        try:
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass
    try:
        sent = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active))
        state["msg_id"] = sent.message_id
    except Exception:
        pass


# ---------- Рассылка анонса ивента на старте бота ----------

def _broadcast_card_text(chat_id: int) -> str:
    """Анонс + статус сундука ОДНИМ сообщением (флавор-текст ивента сразу
    вместе с банком/таймером), чтобы при старте бот не слал два сообщения подряд."""
    state = get_case_state(chat_id)
    now = time.time()
    remaining  = max(0, int(state["expires_at"] - now))
    mins, secs = divmod(remaining, 60)

    return (
        f'{EVENT_TITLE}\n\n'
        '<blockquote>Легендарный пират устал хранить золото в одиночку и спрятал '
        'в этом чате общий сундук! Каждый вклад продлевает ему жизнь, а игрок, '
        'который вложится последним перед закрытием — заберёт себе всё золото.\n\n'
        f'💰 Банк: <b>{format_amount(state["bank"])}</b>{COIN}\n'
        f'⏳ До закрытия: <b>{mins:02d}:{secs:02d}</b></blockquote>\n\n'
        f'<i>Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>{COIN} • '
        f'таймер сбрасывается при каждом вкладе!</i>'
    )


async def broadcast_event_start(bot):
    """Рассылает анонс ивента во все известные чаты (личка + группы) ОДНИМ
    сообщением на чат (анонс + карточка сундука вместе) и, если цикл там
    ещё не запущен, сразу открывает первый сундук.
    Ошибки по отдельным чатам (бот заблокирован/выгнан) просто пропускаются."""
    chats = await get_all_chats()
    for chat_id, chat_type in chats:
        state = get_case_state(chat_id)
        state["chat_type"] = chat_type

        try:
            if not state["running"]:
                start_case(chat_id)
            sent = await bot.send_message(
                chat_id, _broadcast_card_text(chat_id), parse_mode="HTML",
                reply_markup=case_keyboard(state["active"]),
            )
            state["msg_id"] = sent.message_id
        except Exception as e:
            print(f"[broadcast_event_start] {chat_id}: {e}")
            continue

        await asyncio.sleep(0.05)  # небольшая пауза, чтобы не словить flood-лимит


# ---------- Фоновый цикл (закрытие сундука / авто-рестарт) ----------

async def _close_chest(bot, chat_id: int, state: dict):
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
            f'🎉 <b>Сундук достался игроку!</b>\n\n'
            f'<blockquote>👑 Победитель: <b>{_esc(winner_name)}</b>\n'
            f'💰 Забрал: <b>{format_amount(bank)}</b>{COIN}</blockquote>\n'
            f'<i>Новый сундук откроется через 30 минут.</i>'
        )
    else:
        text = (
            f'{EVENT_TITLE}\n\n'
            '📦 <b>Сундук исчез...</b>\n\n'
            '<blockquote>Никто не успел вложиться — банк сгорел без победителя.</blockquote>\n'
            '<i>Новый сундук откроется через 30 минут.</i>'
        )

    if state.get("chat_type") == "private":
        await _send_or_edit(bot, chat_id, state, text, active=False)
        return

    old_id = state.get("msg_id")
    if old_id:
        try:
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass
    try:
        sent = await bot.send_message(chat_id, text, parse_mode="HTML")
        state["msg_id"] = sent.message_id
    except Exception:
        pass


async def case_tick_loop(bot):
    """
    Единый фоновый тик для всех чатов (по аналогии с остальными
    циклами проекта, например _duel_timer_loop в mainhelp.py).
    Раз в секунду проверяет все активные сундуки: закрывает истёкшие
    и автоматически открывает новые после паузы.
    """
    while True:
        try:
            await _tick_once(bot)
        except Exception as e:
            print(f"[case_tick_loop] {e}")
        await asyncio.sleep(1)


async def _tick_once(bot):
    now = time.time()
    for chat_id, state in list(_CASES.items()):
        if state["active"] and now >= state["expires_at"]:
            await _close_chest(bot, chat_id, state)
        elif (
            not state["active"]
            and state["running"]
            and state["paused_until"] is not None
            and now >= state["paused_until"]
        ):
            _spawn_chest(state)
            await send_case_card(bot, chat_id)


async def case_card_refresh_loop(bot):
    """Отдельный фоновый тик: раз в CARD_REFRESH_SECONDS (2 сек) молча
    обновляет таймер на карточках активных сундуков — без кнопки "Обновить",
    без пересоздания сообщений (это только для значимых событий, см. bump_card)."""
    while True:
        try:
            for chat_id, state in list(_CASES.items()):
                if state["active"]:
                    await refresh_card(bot, chat_id)
        except Exception as e:
            print(f"[case_card_refresh_loop] {e}")
        await asyncio.sleep(CARD_REFRESH_SECONDS)
