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
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, Update, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder

from mainhelp import bot, dp, run_bot, ADMIN_IDS

# Готовые хелперы из mainhelp.py — НЕ трогаем сам mainhelp.py, просто
# переиспользуем то, что там уже есть, чтобы не дублировать логику:
#  _esc          — экранирование HTML в именах игроков
#  _parse_amount — парсер сумм с суффиксами (50000 / 50к / 1.5кк и т.д.),
#                  тот же самый, что использует /addalldiamond и /gift
from mainhelp import _esc, _parse_amount

# ── Игра "Общий сундук" / ивент "Щедрый пират" — вся логика, тексты
# и реестр чатов вынесены в case.py, здесь только хендлеры команд/кнопок. ──
from case import (
    stop_case,
    try_invest, case_status_text, case_keyboard,
    case_tick_loop, case_card_refresh_loop,
    bump_card, set_chat_type, register_chat, forget_chat,
    broadcast_event_start, get_case_state, get_card_state,
    set_event_photo, get_event_photo,
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
#  РЕЕСТР ЧАТОВ — запоминаем chat_id каждого апдейта, чтобы было куда
#  разослать анонс и карточку сундука по команде /startcase. Это
#  outer-middleware: она ничего не решает и никого не блокирует, просто
#  "подсматривает" chat_id и пропускает апдейт дальше — ни один хендлер
#  в mainhelp.py об этом даже не узнает, поведение бота не меняется ни на йоту.
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
#
#  /startcase теперь — не мгновенный запуск, а маленький мастер для админа:
#    1) выбрать тип приза — 💰 монеты / 💎 артефакт / 👑 статус
#    2а) если "монеты"        — сразу стартуем с суммой вклада по умолчанию
#         (CASE_DEPOSIT из case.py), спрашивать больше нечего;
#    2б) если "артефакт"       — выбрать конкретный артефакт из списка;
#    2в) если "статус"         — выбрать VIP или Premium;
#    3) для артефакта/статуса — админ ЕЩЁ вводит текстом сумму вклада
#       (сколько монет стоит один клик "Вложить"), т.к. для этих призов
#       нет растущего банка — сумма влияет только на цену входа.
#  Мастер живёт в aiogram FSM (per-admin состояние), шаги можно отменить
#  кнопкой "Отмена" на любом этапе.
# ══════════════════════════════════════════════════════════════════════

class CaseAdminSetup(StatesGroup):
    choosing_type     = State()
    choosing_artifact = State()
    choosing_status   = State()
    entering_deposit  = State()


_CASE_ADMIN_CANCEL_CB = "city_case_admin_cancel"


def _case_prize_type_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="💰 Монеты", callback_data="city_case_admin_type:coins")
    b.button(text="💎 Артефакт", callback_data="city_case_admin_type:artifact")
    b.button(text="👑 Статус", callback_data="city_case_admin_type:status")
    b.button(text="❌ Отмена", callback_data=_CASE_ADMIN_CANCEL_CB)
    b.adjust(1)
    return b.as_markup()


def _case_artifact_choice_keyboard():
    from shop import _ARTIFACT_POOL
    b = InlineKeyboardBuilder()
    for a in _ARTIFACT_POOL:
        b.button(
            text=f'{a["name"]} · ×{a["multiplier"]}',
            callback_data=f'city_case_admin_art:{a["key"]}',
        )
    b.button(text="❌ Отмена", callback_data=_CASE_ADMIN_CANCEL_CB)
    b.adjust(1)
    return b.as_markup()


def _case_status_choice_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="👑 VIP · 30 дней", callback_data="city_case_admin_status:vip")
    b.button(text="⭐ Premium · 30 дней", callback_data="city_case_admin_status:premium")
    b.button(text="❌ Отмена", callback_data=_CASE_ADMIN_CANCEL_CB)
    b.adjust(1)
    return b.as_markup()


@dp.message(Command("startcase"))
async def cmd_startcase(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем, как и остальные админ-команды в проекте

    chat_id = message.chat.id
    set_chat_type(chat_id, message.chat.type)

    if get_case_state()["running"]:
        await message.reply("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        return

    await state.clear()
    await state.set_state(CaseAdminSetup.choosing_type)
    await message.reply(
        "🏴‍☠️ <b>Настройка ивента «Щедрый пират»</b>\n"
        "<blockquote>Выбери, каким призом наградить победителя — того, кто "
        "сделает последний вклад перед закрытием сундука.</blockquote>",
        parse_mode="HTML",
        reply_markup=_case_prize_type_keyboard(),
    )


@dp.callback_query(F.data.startswith("city_case_admin_type:"), CaseAdminSetup.choosing_type)
async def cb_case_admin_type(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return

    if get_case_state()["running"]:
        await call.answer("Ивент уже запущен.", show_alert=True)
        await state.clear()
        return

    prize_type = call.data.split(":", 1)[1]

    if prize_type == "coins":
        # Для монет ничего дополнительно спрашивать не нужно — сумма
        # вклада берётся по умолчанию (CASE_DEPOSIT), банк растёт как раньше.
        await state.clear()
        set_chat_type(call.message.chat.id, call.message.chat.type)
        started = await broadcast_event_start(bot, deposit=CASE_DEPOSIT, prize_type="coins")
        if started:
            await call.message.edit_text(
                f'✅ <b>Ивент запущен!</b>\n'
                f'💰 Приз: монеты (банк растёт с каждым вкладом)\n'
                f'Вклад: <b>{format_amount(CASE_DEPOSIT)}</b>',
                parse_mode="HTML",
            )
        else:
            await call.message.edit_text("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        await call.answer()
        return

    if prize_type == "artifact":
        await state.update_data(prize_type="artifact")
        await state.set_state(CaseAdminSetup.choosing_artifact)
        await call.message.edit_text(
            "💎 <b>Выбери артефакт-приз:</b>",
            parse_mode="HTML",
            reply_markup=_case_artifact_choice_keyboard(),
        )
        await call.answer()
        return

    if prize_type == "status":
        await state.update_data(prize_type="status")
        await state.set_state(CaseAdminSetup.choosing_status)
        await call.message.edit_text(
            "👑 <b>Выбери статус-приз:</b>",
            parse_mode="HTML",
            reply_markup=_case_status_choice_keyboard(),
        )
        await call.answer()
        return

    await call.answer()


@dp.callback_query(F.data.startswith("city_case_admin_art:"), CaseAdminSetup.choosing_artifact)
async def cb_case_admin_artifact(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return

    from shop import _ARTIFACT_POOL
    key   = call.data.split(":", 1)[1]
    found = next((a for a in _ARTIFACT_POOL if a["key"] == key), None)
    if not found:
        await call.answer("❌ Артефакт не найден.", show_alert=True)
        return

    await state.update_data(
        artifact_key=found["key"],
        artifact_name=found["name"],
        artifact_multiplier=found["multiplier"],
        artifact_emoji_id=found.get("emoji_id"),
        artifact_emoji=found.get("emoji"),
    )
    await state.set_state(CaseAdminSetup.entering_deposit)
    await call.message.edit_text(
        f'💎 Приз: <b>{_esc(found["name"])}</b> (×{found["multiplier"]})\n\n'
        f'Теперь пришли сумму вклада (сколько будет стоить один клик '
        f'"Вложить") — например <code>50000</code> или <code>50к</code>.',
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data.startswith("city_case_admin_status:"), CaseAdminSetup.choosing_status)
async def cb_case_admin_status(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return

    tier  = call.data.split(":", 1)[1]  # "vip" | "premium"
    label = "VIP" if tier == "vip" else "Premium"

    await state.update_data(status_tier=tier)
    await state.set_state(CaseAdminSetup.entering_deposit)
    await call.message.edit_text(
        f'👑 Приз: статус <b>{label}</b> (30 дней)\n\n'
        f'Теперь пришли сумму вклада (сколько будет стоить один клик '
        f'"Вложить") — например <code>50000</code> или <code>50к</code>.',
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == _CASE_ADMIN_CANCEL_CB)
async def cb_case_admin_cancel(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("❌ Настройка ивента отменена.")
    await call.answer()


# Ловит клики по кнопкам мастера, когда FSM-состояние админа уже не
# совпадает с шагом кнопки (например, он отменил мастер или запустил
# /startcase заново, а на экране осталась старая клавиатура) — просто
# вежливо просим начать заново, а не оставляем кнопку "зависшей".
# ВАЖНО: регистрируется ПОСЛЕДНИМ среди city_case_admin_*-хендлеров,
# чтобы не перехватывать клики, которые уже обработаны выше.
@dp.callback_query(F.data.startswith("city_case_admin_"))
async def cb_case_admin_stale(call: CallbackQuery):
    await call.answer("⌛️ Эта настройка устарела, начни заново: /startcase", show_alert=True)


@dp.message(StateFilter(CaseAdminSetup.entering_deposit))
async def msg_case_admin_deposit(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    amount = _parse_amount((message.text or "").strip())
    if amount is None or amount <= 0:
        await message.reply(
            "❌ Не удалось распознать сумму. Пришли число, например "
            "<code>50000</code> или <code>50к</code>.",
            parse_mode="HTML",
        )
        return

    if get_case_state()["running"]:
        await message.reply("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        await state.clear()
        return

    data = await state.get_data()
    await state.clear()
    set_chat_type(message.chat.id, message.chat.type)

    prize_type = data.get("prize_type")
    if prize_type == "artifact":
        started = await broadcast_event_start(
            bot,
            deposit=amount,
            prize_type="artifact",
            prize_artifact={
                "key":        data.get("artifact_key"),
                "name":       data.get("artifact_name"),
                "multiplier": data.get("artifact_multiplier"),
                "emoji_id":   data.get("artifact_emoji_id"),
                "emoji":      data.get("artifact_emoji"),
            },
        )
        prize_line = f'💎 Приз: {data.get("artifact_name")} (×{data.get("artifact_multiplier")})'
    elif prize_type == "status":
        tier  = data.get("status_tier")
        label = "VIP" if tier == "vip" else "Premium"
        started = await broadcast_event_start(
            bot, deposit=amount, prize_type="status", prize_status_tier=tier,
        )
        prize_line = f'👑 Приз: статус {label} (30 дней)'
    else:
        # Сюда попасть не должны (для "coins" этот шаг вообще не запускается),
        # но на всякий случай — не молчим, а сообщаем и откатываемся.
        await message.reply("❌ Что-то пошло не так, начни заново: /startcase", parse_mode="HTML")
        return

    if not started:
        await message.reply("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        return

    await message.reply(
        f'✅ <b>Ивент запущен!</b>\n{prize_line}\n💰 Вклад: <b>{format_amount(amount)}</b>',
        parse_mode="HTML",
    )


# В mainhelp.py есть глобальный перехватчик ЛЮБОГО голого текста без "/"
# (handle_captcha_answer, "@dp.message(F.text & ~F.text.startswith('/'))" —
# нужен для капчи/онбординга) — он зарегистрирован раньше наших хендлеров
# из main.py, поэтому aiogram, проверяя message-хендлеры В ПОРЯДКЕ
# РЕГИСТРАЦИИ, отдавал бы "100000"/"50к" ЕМУ первым, а до
# msg_case_admin_deposit они бы просто не доходили. Трогать mainhelp.py
# нельзя — поэтому просто переставляем НАШ уже зарегистрированный хендлер
# в начало внутреннего списка dp.message.handlers: он и так почти всегда
# молча пропускает сообщение (StateFilter не совпал — обычный текст без
# активного мастера /startcase), так что на остальной бот это не влияет
# вообще никак, просто наш ввод суммы вклада теперь проверяется первым.
def _prioritize_message_handlers(*callbacks) -> None:
    wanted    = list(callbacks)
    moved     = [h for h in dp.message.handlers if h.callback in wanted]
    remaining = [h for h in dp.message.handlers if h.callback not in wanted]
    moved.sort(key=lambda h: wanted.index(h.callback))
    dp.message.handlers[:] = moved + remaining


_prioritize_message_handlers(msg_case_admin_deposit)


@dp.message(Command("stopcase"))
async def cmd_stopcase(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if await stop_case(bot):
        await message.reply(
            "🛑 <b>Ивент остановлен.</b>\n"
            "<blockquote>Если сундук был активен — он закрылся немедленно (приз, если был "
            "последний вкладчик, уже выдан). Чтобы запустить заново — <code>/startcase</code>.</blockquote>",
            parse_mode="HTML",
        )
    else:
        await message.reply(
            "❌ <b>Ивент и так не запущен.</b>",
            parse_mode="HTML",
        )


# ══════════════════════════════════════════════════════════════════════
#  /photo — картинка ивента "Щедрый пират"
#
#  Админ присылает картинку (как подпись к самой команде "/photo" или
#  ответом на уже отправленное в чат фото) — бот сохраняет её file_id
#  (сама картинка при этом НИКУДА не скачивается и не хранится отдельно,
#  Telegram присылает готовый file_id, который можно переиспользовать
#  сколько угодно раз — это и есть штатный способ работы с медиа в Bot API).
#  Дальше карточка сундука (case_status_text) рассылается уже КАК ФОТО
#  с этим текстом в подписи, а не обычным текстовым сообщением — везде,
#  где раньше слался/редактировался обычный текст (см. case.py).
#
#  "/photo" без картинки и без ответа на фото — просто напоминание, как
#  пользоваться командой. "/photo off" — убирает картинку, карточка
#  снова становится обычным текстовым сообщением.
# ══════════════════════════════════════════════════════════════════════

@dp.message(Command("photo"))
async def cmd_photo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    arg = (message.text or "").split(maxsplit=1)
    if len(arg) > 1 and arg[1].strip().lower() in ("off", "выкл", "стоп"):
        set_event_photo(None)
        await message.reply(
            "🖼 <b>Картинка ивента убрана.</b>\n"
            "<blockquote>Карточка сундука снова будет обычным текстовым сообщением.</blockquote>",
            parse_mode="HTML",
        )
        return

    photo = None
    if message.photo:
        photo = message.photo[-1]
    elif message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo[-1]

    if photo is None:
        await message.reply(
            "🖼 <b>Картинка ивента</b>\n"
            "<blockquote>Пришли картинку с подписью <code>/photo</code>, либо ответь "
            "командой <code>/photo</code> на уже отправленное в чат фото — бот запомнит "
            "его и будет прикреплять к карточке сундука.\n"
            "<code>/photo off</code> — убрать картинку.</blockquote>",
            parse_mode="HTML",
        )
        return

    set_event_photo(photo.file_id)
    await message.reply(
        "✅ <b>Картинка ивента сохранена!</b>\n"
        "<blockquote>Карточка сундука теперь будет присылаться как фото с этим "
        "текстом в подписи. Учти: у подписи к фото в Telegram лимит 1024 символа "
        "(у обычного текста — 4096), так что при очень длинном тексте карточки "
        "часть может не влезть.</blockquote>",
        parse_mode="HTML",
    )


@dp.message(Command("case"))
async def cmd_case(message: Message):
    chat_id = message.chat.id
    set_chat_type(chat_id, message.chat.type)

    state = get_case_state()
    sent = await message.answer(
        case_status_text(),
        parse_mode="HTML",
        reply_markup=case_keyboard(state["active"]),
    )
    get_card_state(chat_id)["msg_id"] = sent.message_id


@dp.message(Command("invest"))
async def cmd_invest(message: Message):
    set_chat_type(message.chat.id, message.chat.type)
    await _handle_invest(uid=message.from_user.id,
                          name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
                          message=message)


@dp.callback_query(F.data == CASE_INVEST_CB)
async def cb_case_invest(call: CallbackQuery):
    set_chat_type(call.message.chat.id, call.message.chat.type)
    await _handle_invest(uid=call.from_user.id,
                          name=call.from_user.first_name or call.from_user.username or str(call.from_user.id),
                          call=call)


async def _handle_invest(uid: int, name: str,
                          message: Message | None = None, call: CallbackQuery | None = None):
    """Общая логика вклада — используется и командой /invest, и кнопкой.
    Банк общий на весь бот, поэтому вклад из ЛЮБОГО чата пополняет один
    и тот же сундук.

    Обновление карточки после успешного вклада делает case.bump_card():
    она рассылает свежую карточку СРАЗУ во все известные чаты (в личке —
    редактирует на месте, в группах — удаляет старую и присылает новую,
    чтобы карточка "поднималась" в чате)."""
    result = await try_invest(uid, name)

    if not result["ok"]:
        reason = result["reason"]
        if reason == "no_active":
            text = "📦 Сейчас нет активного сундука."
        elif reason == "cooldown":
            text = f"⏳ Подождите ещё {result['wait']} сек. перед следующим вкладом."
        else:  # insufficient — result["deposit"] содержит реальную (выбранную админом) сумму
            text = (
                f"❌ Недостаточно монет! Нужно {format_amount(result['deposit'])}, "
                f"у вас {format_amount(result['balance'])}."
            )
        if call:
            await call.answer(text, show_alert=True)
        else:
            await message.reply(text, parse_mode="HTML")
        return

    await bump_card(bot)

    if call:
        deposit_str = format_amount(result["deposit"])
        state = get_case_state()
        if state["prize_type"] == "coins":
            await call.answer(f"💰 Вложено {deposit_str}! В сундуке: {format_amount(result['bank'])}")
        else:
            await call.answer(f"💰 Вложено {deposit_str}! Ты сейчас последний претендент на приз.")


# ──────────────────────────────────────────────────────────────────────────
# 👆 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ ВЫШЕ ЭТОЙ СТРОКИ 👆
# ──────────────────────────────────────────────────────────────────────────


async def _entrypoint():
    # Фоновые задачи сундука:
    #  - case_tick_loop        — раз в 1 сек: закрытие истёкших сундуков / авто-рестарт
    #  - case_card_refresh_loop — раз в несколько сек: тихое обновление таймера на карточках
    # запускаются здесь же, чтобы не трогать run_bot() в mainhelp.py.
    #
    # Сам ивент (открытие сундука + анонс) на старте НЕ запускается —
    # только вручную, командой /startcase. Эти фоновые циклы просто ждут,
    # пока цикл не будет запущен (см. case._CASE["running"]).
    asyncio.create_task(case_tick_loop(bot))
    asyncio.create_task(case_card_refresh_loop(bot))
    await run_bot()


if __name__ == "__main__":
    asyncio.run(_entrypoint())
