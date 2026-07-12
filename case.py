# ============================================================
#  case.py — мини-игра "Общий сундук" (TGStellar)
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
#  ВАЖНО: состояние сундука (банк, таймер, последний вкладчик) —
#  в памяти процесса и НЕ переживает рестарт бота (это ок, банки
#  игроков всё равно защищены — деньги списываются/начисляются
#  через database.aio_change_balance, то есть уже до рестарта
#  успевают сохраниться в SQLite).
# ============================================================

import time
import asyncio
import html as _html

from aiogram.types import InlineKeyboardMarkup

from database import aio_change_balance, aio_get_user, format_amount
from miner import COIN

# ---------- Параметры игры ----------

CASE_INITIAL_BANK       = 500_000   # стартовый банк сундука
CASE_DEPOSIT            = 50_000    # фиксированный вклад
CASE_TIMER_SECONDS      = 60        # таймер сундука (сбрасывается при вкладе)
PLAYER_COOLDOWN_SECONDS = 15        # кулдаун игрока между вкладами
PAUSE_SECONDS           = 30 * 60   # пауза после закрытия сундука (авто-рестарт)

# ---------- Состояние (per chat_id) ----------
# _CASES[chat_id] = {
#   "running":       bool,  # цикл запущен админом (/startcase) и не остановлен
#   "active":        bool,  # сундук сейчас открыт (принимает вклады)
#   "bank":          int,
#   "expires_at":    float, # unix ts закрытия текущего сундука
#   "last_uid":      int | None,
#   "last_name":     str | None,
#   "cooldowns":     {uid: last_invest_ts},
#   "paused_until":  float | None,
#   "msg_id":        int | None,   # сообщение-карточка сундука для редактирования
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
            "last_winner_name":   None,
            "last_winner_amount": None,
        }
    return _CASES[chat_id]


def _spawn_chest(state: dict) -> None:
    """Открывает новый сундук с нуля (стартовый банк + полный таймер)."""
    state["active"]      = True
    state["bank"]        = CASE_INITIAL_BANK
    state["expires_at"]  = time.time() + CASE_TIMER_SECONDS
    state["last_uid"]    = None
    state["last_name"]   = None
    state["cooldowns"]   = {}
    state["paused_until"] = None


# ---------- Управление циклом (админ) ----------

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

def case_keyboard(active: bool) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if active:
        builder.button(text=f"💰 Вложить {format_amount(CASE_DEPOSIT)}", callback_data="case_invest")
    builder.button(text="🔄 Обновить", callback_data="case_refresh")
    builder.adjust(1)
    return builder.as_markup()


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
            '📦 <b>Общий сундук</b>\n\n'
            f'<blockquote>'
            f'💰 Банк: <b>{bank_str}</b>{COIN}\n'
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
            '📦 <b>Сундук закрыт</b>\n\n'
            f'<blockquote>⏳ Следующий сундук через <b>{mins:02d}:{secs:02d}</b></blockquote>'
            f'{winner_line}'
        )

    return (
        '📦 <b>Сундук неактивен</b>\n\n'
        '<blockquote>Администратор ещё не запустил цикл.</blockquote>'
        '<i>Ожидайте команду <code>/startcase</code>.</i>'
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
    msg_id = state.get("msg_id")
    if msg_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=msg_id,
                parse_mode="HTML", reply_markup=case_keyboard(active),
            )
            return
        except Exception:
            pass  # сообщение могло быть удалено/устарело — просто пришлём новое
    sent = await bot.send_message(
        chat_id, text, parse_mode="HTML", reply_markup=case_keyboard(active),
    )
    state["msg_id"] = sent.message_id


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
            '🎉 <b>Сундук достался игроку!</b>\n\n'
            f'<blockquote>👑 Победитель: <b>{_esc(winner_name)}</b>\n'
            f'💰 Забрал: <b>{format_amount(bank)}</b>{COIN}</blockquote>\n'
            f'<i>Новый сундук откроется через 30 минут.</i>'
        )
    else:
        text = (
            '📦 <b>Сундук исчез...</b>\n\n'
            '<blockquote>Никто не успел вложиться — банк сгорел без победителя.</blockquote>\n'
            '<i>Новый сундук откроется через 30 минут.</i>'
        )

    await _send_or_edit(bot, chat_id, state, text, active=False)


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
