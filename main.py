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
from aiogram.types import Message, CallbackQuery, Update, ChatMemberUpdated

from mainhelp import bot, dp, run_bot, ADMIN_IDS

# Если что-то новое понадобится, обычно достаточно из mainhelp импортировать
# нужные функции/данные, например:
# from mainhelp import ADMIN_IDS, _get_user_lock
# from database import get_user, save_user

# ── Игра "Общий сундук" / ивент "Щедрый пират" — вся логика, тексты
# и реестр чатов вынесены в case.py, здесь только хендлеры команд/кнопок. ──
from case import (
    start_case, stop_case,
    try_invest, case_status_text, case_keyboard,
    send_case_card, case_tick_loop, case_card_refresh_loop,
    bump_card, set_chat_type, register_chat, forget_chat,
    broadcast_event_start,
    CASE_DEPOSIT, CASE_INVEST_CB,
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
#  РЕЕСТР ЧАТОВ — запоминаем chat_id каждого апдейта, чтобы на старте
#  бота было куда разослать анонс ивента. Это outer-middleware: она
#  ничего не решает и никого не блокирует, просто "подсматривает"
#  chat_id и пропускает апдейт дальше — ни один хендлер в mainhelp.py
#  об этом даже не узнает, поведение бота не меняется ни на йоту.
# ══════════════════════════════════════════════════════════════════════

@dp.update.outer_middleware()
async def _chat_registry_middleware(handler, event: Update, data: dict):
    try:
        msg = event.message or (event.callback_query.message if event.callback_query else None)
        if msg is not None and msg.chat is not None:
            chat = msg.chat
            asyncio.create_task(register_chat(chat.id, chat.type, getattr(chat, "title", None)))
    except Exception:
        pass
    return await handler(event, data)


# Telegram НЕ даёт API "покажи все чаты, где я есть" — единственный
# надёжный способ узнать это заранее (а не только когда кто-то напишет
# сообщение) — ловить my_chat_member: этот апдейт прилетает КАЖДЫЙ раз,
# когда бота добавляют в чат, делают админом, разжалуют или выгоняют,
# даже если там никто ничего не написал. Именно это и нужно для "везде,
# где есть бот".
@dp.my_chat_member()
async def _on_bot_membership_changed(update: ChatMemberUpdated):
    chat   = update.chat
    status = update.new_chat_member.status  # "member" / "administrator" / "creator" / "left" / "kicked" / "restricted"

    if status in ("member", "administrator", "creator"):
        set_chat_type(chat.id, chat.type)
        await register_chat(chat.id, chat.type, getattr(chat, "title", None))
    elif status in ("left", "kicked"):
        await forget_chat(chat.id)


# ══════════════════════════════════════════════════════════════════════
#  ИГРА "ОБЩИЙ СУНДУК" / ИВЕНТ "ЩЕДРЫЙ ПИРАТ"
#  (/startcase, /stopcase, /case, кнопка "Вложить")
# ══════════════════════════════════════════════════════════════════════

@dp.message(Command("startcase"))
async def cmd_startcase(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем, как и остальные админ-команды в проекте

    chat_id = message.chat.id
    set_chat_type(chat_id, message.chat.type)

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
    set_chat_type(chat_id, message.chat.type)

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
    set_chat_type(message.chat.id, message.chat.type)
    await _handle_invest(chat_id=message.chat.id, uid=message.from_user.id,
                          name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
                          message=message)


@dp.callback_query(F.data == CASE_INVEST_CB)
async def cb_case_invest(call: CallbackQuery):
    set_chat_type(call.message.chat.id, call.message.chat.type)
    await _handle_invest(chat_id=call.message.chat.id, uid=call.from_user.id,
                          name=call.from_user.first_name or call.from_user.username or str(call.from_user.id),
                          call=call)


async def _handle_invest(chat_id: int, uid: int, name: str,
                          message: Message | None = None, call: CallbackQuery | None = None):
    """Общая логика вклада — используется и командой /invest, и кнопкой.

    Обновление карточки после успешного вклада делает case.bump_card():
    в личке с ботом карточка редактируется на месте, а в группах старая
    удаляется и присылается новая (чтобы она "поднималась" в чате)."""
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

    await bump_card(bot, chat_id)

    if call:
        await call.answer(f"💰 Вложено {format_amount(CASE_DEPOSIT)}! Банк: {format_amount(result['bank'])}")


# ──────────────────────────────────────────────────────────────────────────
# 👆 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ ВЫШЕ ЭТОЙ СТРОКИ 👆
# ──────────────────────────────────────────────────────────────────────────


async def _startup_event_broadcast():
    """При старте бота — анонс ивента "Щедрый пират" во все чаты, где бота
    когда-либо видели (личка + группы), с автозапуском сундука там,
    где цикл ещё не был запущен. Небольшая пауза даёт mainhelp.run_bot()
    спокойно закончить свои миграции БД, прежде чем начнётся рассылка."""
    await asyncio.sleep(2)
    await broadcast_event_start(bot)


async def _entrypoint():
    # Фоновые задачи сундука:
    #  - case_tick_loop        — раз в 1 сек: закрытие истёкших сундуков / авто-рестарт
    #  - case_card_refresh_loop — раз в 2 сек: тихое обновление таймера на карточках
    # запускаются здесь же, чтобы не трогать run_bot() в mainhelp.py.
    asyncio.create_task(case_tick_loop(bot))
    asyncio.create_task(case_card_refresh_loop(bot))
    asyncio.create_task(_startup_event_broadcast())
    await run_bot()


if __name__ == "__main__":
    asyncio.run(_entrypoint())
