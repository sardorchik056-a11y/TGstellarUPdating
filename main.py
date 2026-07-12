# main.py — точка входа бота.
#
# ВСЯ существующая рабочая логика (хендлеры, платежи, фоновые задачи,
# обмен в городе, дуэли и т.д.) лежит в mainhelp.py — туда лучше не лезть,
# чтобы случайно ничего не сломать.
#
# Здесь, в main.py, можно спокойно добавлять НОВЫЕ команды/хендлеры —
# они используют тот же bot и тот же dp (диспетчер), что и всё остальное,
# так что будут работать вместе со старой логикой без конфликтов.

import asyncio

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from mainhelp import bot, dp, run_bot, ADMIN_IDS

# Если что-то новое понадобится, обычно достаточно из mainhelp импортировать
# нужные функции/данные, например:
# from mainhelp import ADMIN_IDS, _get_user_lock
# from database import get_user, save_user

# ── Игра "Общий сундук" — вся логика и тексты вынесены в case.py,
# здесь только хендлеры команд/кнопок. ──
from case import (
    start_case, stop_case,
    try_invest, case_status_text, case_keyboard,
    send_case_card, case_tick_loop,
    CASE_DEPOSIT,
)
from database import format_amount

# ──────────────────────────────────────────────────────────────────────────
# 👇 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ НИЖЕ ЭТОЙ СТРОКИ 👇
# ──────────────────────────────────────────────────────────────────────────

# Пример (раскомментируй и поменяй под себя):
#
# from aiogram.filters import Command
# from aiogram.types import Message
#
# @dp.message(Command("hello"))
# async def cmd_hello(message: Message):
#     await message.answer("Привет! Это новая команда из main.py 👋")


# ══════════════════════════════════════════════════════════════════════
#  ИГРА "ОБЩИЙ СУНДУК" (/startcase, /stopcase, /case, кнопка "Вложить")
# ══════════════════════════════════════════════════════════════════════

@dp.message(Command("startcase"))
async def cmd_startcase(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем, как и остальные админ-команды в проекте

    chat_id = message.chat.id
    if not start_case(chat_id):
        await message.reply(
            "⚠️ <b>Цикл сундуков уже запущен</b> в этом чате.",
            parse_mode="HTML",
        )
        return

    await send_case_card(bot, chat_id)


@dp.message(Command("stopcase"))
async def cmd_stopcase(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    chat_id = message.chat.id
    if stop_case(chat_id):
        await message.reply(
            "🛑 <b>Цикл сундуков остановлен.</b>\n"
            "<blockquote>Чтобы запустить заново — <code>/startcase</code>.</blockquote>",
            parse_mode="HTML",
        )
    else:
        await message.reply(
            "❌ <b>Нельзя остановить сейчас.</b>\n"
            "<blockquote><code>/stopcase</code> работает только в паузе — "
            "если сундук активен или цикл не запущен, команда игнорируется.</blockquote>",
            parse_mode="HTML",
        )


@dp.message(Command("case"))
async def cmd_case(message: Message):
    chat_id = message.chat.id
    from case import get_case_state
    state = get_case_state(chat_id)
    sent = await message.answer(
        case_status_text(chat_id),
        parse_mode="HTML",
        reply_markup=case_keyboard(state["active"]),
    )
    state["msg_id"] = sent.message_id


@dp.message(Command("invest"))
async def cmd_invest(message: Message):
    await _handle_invest(chat_id=message.chat.id, uid=message.from_user.id,
                          name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
                          message=message)


@dp.callback_query(F.data == "case_invest")
async def cb_case_invest(call: CallbackQuery):
    await _handle_invest(chat_id=call.message.chat.id, uid=call.from_user.id,
                          name=call.from_user.first_name or call.from_user.username or str(call.from_user.id),
                          call=call)


@dp.callback_query(F.data == "case_refresh")
async def cb_case_refresh(call: CallbackQuery):
    chat_id = call.message.chat.id
    from case import get_case_state
    state = get_case_state(chat_id)
    state["msg_id"] = call.message.message_id
    try:
        await call.message.edit_text(
            case_status_text(chat_id), parse_mode="HTML",
            reply_markup=case_keyboard(state["active"]),
        )
    except Exception:
        pass  # текст не изменился — Telegram запрещает "пустой" edit, это не ошибка
    await call.answer()


async def _handle_invest(chat_id: int, uid: int, name: str,
                          message: Message | None = None, call: CallbackQuery | None = None):
    """Общая логика вклада — используется и командой /invest, и кнопкой."""
    result = await try_invest(chat_id, uid, name)

    if not result["ok"]:
        reason = result["reason"]
        if reason == "no_active":
            text = "📦 Сейчас нет активного сундука."
        elif reason == "cooldown":
            text = f"⏳ Подождите ещё {result['wait']} сек. перед следующим вкладом."
        else:  # insufficient
            text = (
                f"❌ Недостаточно монет! Нужно {format_amount(CASE_DEPOSIT)}, "
                f"у вас {format_amount(result['balance'])}."
            )
        if call:
            await call.answer(text, show_alert=True)
        else:
            await message.reply(text, parse_mode="HTML")
        return

    from case import get_case_state
    state = get_case_state(chat_id)
    new_text = case_status_text(chat_id)
    new_kb   = case_keyboard(state["active"])

    if call:
        state["msg_id"] = call.message.message_id
        try:
            await call.message.edit_text(new_text, parse_mode="HTML", reply_markup=new_kb)
        except Exception:
            pass
        await call.answer(f"💰 Вложено {format_amount(CASE_DEPOSIT)}! Банк: {format_amount(result['bank'])}")
    else:
        sent = await message.answer(new_text, parse_mode="HTML", reply_markup=new_kb)
        state["msg_id"] = sent.message_id


# ──────────────────────────────────────────────────────────────────────────
# 👆 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ ВЫШЕ ЭТОЙ СТРОКИ 👆
# ──────────────────────────────────────────────────────────────────────────


async def _entrypoint():
    # Фоновый тик сундука (закрытие по таймеру / авто-рестарт после паузы)
    # запускается здесь же, чтобы не трогать run_bot() в mainhelp.py.
    asyncio.create_task(case_tick_loop(bot))
    await run_bot()


if __name__ == "__main__":
    asyncio.run(_entrypoint())
