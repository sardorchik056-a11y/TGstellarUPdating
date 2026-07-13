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
    try_guess, has_guessed, case_status_text, case_keyboard,
    case_tick_loop, case_card_refresh_loop,
    set_chat_type, register_chat, forget_chat,
    broadcast_event_start, get_case_state, get_card_state, set_card_msg_id,
    set_event_photo, get_event_photo,
    CASE_DEFAULT_COIN_PRIZE, CASE_GUESS_CB,
    NUMBER_MIN, NUMBER_MAX,
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
#  ИГРА "УГАДАЙ ЧИСЛО" / ИВЕНТ "ЩЕДРЫЙ ПИРАТ"
#  (/startcase, /stopcase, /case, /guess, кнопка "Угадать")
#
#  Механика: бот загадывает число от 1 до 999, у каждого игрока —
#  ОДНА бесплатная попытка назвать его. Все ответы копятся молча (никто
#  их не видит), ивент идёт РОВНО 24 часа. По истечении число раскрывается
#  и выигрывает тот, кто назвал его точно (при нескольких точных —
#  кто раньше отправил), а если точных совпадений нет — ближайший по
#  модулю разницы (при равенстве — тоже кто раньше отправил).
#
#  /startcase — маленький мастер для админа:
#    1) выбрать тип приза — 💰 монеты / 💎 артефакт / 👑 статус
#    2а) если "монеты"    — админ вводит текстом сумму приза
#         (сколько получит победитель), например 500000 или 500к;
#    2б) если "артефакт"  — выбрать конкретный артефакт из списка,
#         ивент стартует сразу же (сумма не нужна — приз фиксирован);
#    2в) если "статус"    — выбрать VIP или Premium, ивент стартует
#         сразу же (тоже без ввода суммы).
#  Мастер живёт в aiogram FSM (per-admin состояние), шаги можно отменить
#  кнопкой "Отмена" на любом этапе.
# ══════════════════════════════════════════════════════════════════════

class CaseAdminSetup(StatesGroup):
    choosing_type     = State()
    choosing_artifact = State()
    choosing_status   = State()
    entering_amount   = State()


# Ввод числа игроком в личной "переписке" после клика по кнопке "Угадать" —
# отдельный, не админский, FSM-стейт (см. cb_case_guess/msg_case_guess_number).
class GuessInput(StatesGroup):
    waiting_number = State()


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
        f"<blockquote>Бот загадает число от {NUMBER_MIN} до {NUMBER_MAX}. У каждого "
        "игрока — одна бесплатная попытка угадать. Через 24 часа число раскроется, "
        "и приз получит тот, кто угадал точно (или ближе всех). Выбери, каким "
        "призом наградить победителя.</blockquote>",
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
        # Для монет нужна сумма приза (сколько получит победитель) —
        # растущего банка больше нет, участие бесплатное, поэтому сумму
        # задаёт админ явно.
        await state.update_data(prize_type="coins")
        await state.set_state(CaseAdminSetup.entering_amount)
        await call.message.edit_text(
            f'💰 Приз: <b>монеты</b>\n\n'
            f'Теперь пришли сумму приза (сколько получит победитель) — '
            f'например <code>{CASE_DEFAULT_COIN_PRIZE}</code> или <code>500к</code>.',
            parse_mode="HTML",
        )
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

    if get_case_state()["running"]:
        await call.answer("Ивент уже запущен.", show_alert=True)
        await state.clear()
        return

    from shop import _ARTIFACT_POOL
    key   = call.data.split(":", 1)[1]
    found = next((a for a in _ARTIFACT_POOL if a["key"] == key), None)
    if not found:
        await call.answer("❌ Артефакт не найден.", show_alert=True)
        return

    await state.clear()
    set_chat_type(call.message.chat.id, call.message.chat.type)
    started = await broadcast_event_start(
        bot,
        prize_type="artifact",
        prize_artifact={
            "key":        found["key"],
            "name":       found["name"],
            "multiplier": found["multiplier"],
            "emoji_id":   found.get("emoji_id"),
            "emoji":      found.get("emoji"),
        },
    )
    if started:
        await call.message.edit_text(
            f'✅ <b>Ивент запущен!</b>\n'
            f'💎 Приз: {_esc(found["name"])} (×{found["multiplier"]})',
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data.startswith("city_case_admin_status:"), CaseAdminSetup.choosing_status)
async def cb_case_admin_status(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return

    if get_case_state()["running"]:
        await call.answer("Ивент уже запущен.", show_alert=True)
        await state.clear()
        return

    tier  = call.data.split(":", 1)[1]  # "vip" | "premium"
    label = "VIP" if tier == "vip" else "Premium"

    await state.clear()
    set_chat_type(call.message.chat.id, call.message.chat.type)
    started = await broadcast_event_start(bot, prize_type="status", prize_status_tier=tier)
    if started:
        await call.message.edit_text(
            f'✅ <b>Ивент запущен!</b>\n'
            f'👑 Приз: статус {label} (30 дней)',
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
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


@dp.message(StateFilter(CaseAdminSetup.entering_amount))
async def msg_case_admin_amount(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    amount = _parse_amount((message.text or "").strip())
    if amount is None or amount <= 0:
        await message.reply(
            "❌ Не удалось распознать сумму. Пришли число, например "
            "<code>500000</code> или <code>500к</code>.",
            parse_mode="HTML",
        )
        return

    if get_case_state()["running"]:
        await message.reply("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        await state.clear()
        return

    await state.clear()
    set_chat_type(message.chat.id, message.chat.type)

    started = await broadcast_event_start(bot, prize_type="coins", prize_amount=amount)
    if not started:
        await message.reply("⚠️ <b>Ивент уже запущен.</b>", parse_mode="HTML")
        return

    await message.reply(
        f'✅ <b>Ивент запущен!</b>\n💰 Приз: <b>{format_amount(amount)}</b>',
        parse_mode="HTML",
    )


# В mainhelp.py есть глобальный перехватчик ЛЮБОГО голого текста без "/"
# (handle_captcha_answer, "@dp.message(F.text & ~F.text.startswith('/'))" —
# нужен для капчи/онбординга) — он зарегистрирован раньше наших хендлеров
# из main.py, поэтому aiogram, проверяя message-хендлеры В ПОРЯДКЕ
# РЕГИСТРАЦИИ, отдавал бы "100000"/"50к" ЕМУ первым, а до
# msg_case_admin_amount/msg_case_guess_number они бы просто не доходили.
# Трогать mainhelp.py нельзя — поэтому просто переставляем НАШИ уже
# зарегистрированные хендлеры в начало внутреннего списка dp.message.handlers:
# они и так почти всегда молча пропускают сообщение (StateFilter не совпал —
# обычный текст без активного мастера/ввода числа), так что на остальной бот
# это не влияет вообще никак, просто наш ввод теперь проверяется первым.
def _prioritize_message_handlers(*callbacks) -> None:
    wanted    = list(callbacks)
    moved     = [h for h in dp.message.handlers if h.callback in wanted]
    remaining = [h for h in dp.message.handlers if h.callback not in wanted]
    moved.sort(key=lambda h: wanted.index(h.callback))
    dp.message.handlers[:] = moved + remaining



@dp.message(Command("stopcase"))
async def cmd_stopcase(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if await stop_case(bot):
        await message.reply(
            "🛑 <b>Ивент остановлен.</b>\n"
            "<blockquote>Если приём ответов ещё шёл — число раскрыто немедленно "
            "(приз, если был победитель, уже выдан). Чтобы запустить заново — "
            "<code>/startcase</code>.</blockquote>",
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
    set_card_msg_id(chat_id, sent.message_id)


# ══════════════════════════════════════════════════════════════════════
#  Ответ игрока: ТОЛЬКО в личке с ботом. /guess <число> или кнопка
#  "Угадать" (просит прислать число отдельным сообщением, т.к. inline-
#  кнопка не может принимать произвольный ввод). У каждого игрока —
#  только одна попытка, ответы копятся молча и НЕ дёргают карточку
#  немедленно (см. try_guess/case_card_refresh_loop в case.py —
#  счётчик участников подтянется на очередном тихом тике карточки).
#
#  ВАЖНО про приватность: если игрок нажал кнопку или написал /guess
#  НЕ в личке — бот НИЧЕГО не пишет в этот чат (даже напоминание),
#  чтобы не палить в общем чате сам факт "я сейчас отвечаю на ивент"
#  рядом с числом. Для кнопки это просто всплывающий алерт (его видит
#  только нажавший — Telegram сам это гарантирует, в чат он не попадает),
#  а для команды /guess из группы бот пробует достучаться личным
#  сообщением — если пользователь никогда не открывал диалог с ботом,
#  Telegram не даёт написать первым, тогда просто молчим.
# ══════════════════════════════════════════════════════════════════════

@dp.message(Command("guess"))
async def cmd_guess(message: Message):
    if message.chat.type != "private":
        # В чат НИЧЕГО не отвечаем — пробуем достучаться личным сообщением
        # (сработает, только если пользователь уже открывал диалог с ботом
        # хоть раз, таковы правила Bot API — first message must be initiated
        # by the user). Не получилось — просто молчим, ничего страшного.
        try:
            await bot.send_message(
                message.from_user.id,
                f"✏️ Отвечай на ивент здесь, в личке — пришли <code>/guess число</code> "
                f"(от {NUMBER_MIN} до {NUMBER_MAX}) или команду <code>/case</code>, "
                f"чтобы открыть карточку с кнопкой.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    set_chat_type(message.chat.id, message.chat.type)

    arg = (message.text or "").split(maxsplit=1)
    if len(arg) < 2 or not arg[1].strip().lstrip("-").isdigit():
        await message.reply(
            f"✏️ Напиши число так: <code>/guess 123</code> (от {NUMBER_MIN} до {NUMBER_MAX}).",
            parse_mode="HTML",
        )
        return

    await _submit_guess(
        uid=message.from_user.id,
        name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
        number=int(arg[1].strip()),
        message=message,
    )


@dp.callback_query(F.data == CASE_GUESS_CB)
async def cb_case_guess(call: CallbackQuery, state: FSMContext):
    set_chat_type(call.message.chat.id, call.message.chat.type)

    if not get_case_state()["active"]:
        await call.answer("📦 Сейчас нет активного ивента.", show_alert=True)
        return

    if has_guessed(call.from_user.id):
        await call.answer(
            "🔮 Ты уже назвал число в этом ивенте — результат узнаешь, когда сундук раскроют.",
            show_alert=True,
        )
        return

    if call.message.chat.type != "private":
        # Алерт видит только нажавший (Telegram показывает его всплывающим
        # окном поверх чата) — в сам чат он НЕ попадает, так что группу
        # это никак не засоряет.
        await call.answer(
            "✏️ Открой личку со мной и нажми кнопку там же, "
            "или напиши /guess число.",
            show_alert=True,
        )
        return

    await state.set_state(GuessInput.waiting_number)
    await call.message.answer(
        f'<tg-emoji emoji-id="5197269100878907942">🌟</tg-emoji> <i><b>Напиши число от {NUMBER_MIN} до {NUMBER_MAX}</b> одним сообщением — '
        f"это твоя единственная попытка в этом ивенте.</i>",
        parse_mode="HTML",
    )
    await call.answer()


@dp.message(StateFilter(GuessInput.waiting_number))
async def msg_case_guess_number(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.reply(
            f'<tg-emoji emoji-id="5334544901428229844">🌟</tg-emoji> <i>Это не похоже на число. Пришли целое число от {NUMBER_MIN} до {NUMBER_MAX}.</i>',
            parse_mode="HTML",
        )
        return  # состояние не сбрасываем — ждём корректный ввод

    await state.clear()
    set_chat_type(message.chat.id, message.chat.type)
    await _submit_guess(
        uid=message.from_user.id,
        name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
        number=int(text),
        message=message,
    )


async def _submit_guess(uid: int, name: str, number: int, message: Message):
    """Общая логика ответа — используется и командой /guess, и вводом числа
    после кнопки "Угадать". Засчитывается только один раз на игрока за
    весь ивент; сам факт ответа и число НИКОМУ не показываются до раскрытия."""
    result = await try_guess(uid, name, number)

    if not result["ok"]:
        reason = result["reason"]
        if reason == "no_active":
            text = "📦 Сейчас нет активного ивента."
        elif reason == "bad_range":
            text = f"❌ Число должно быть от {NUMBER_MIN} до {NUMBER_MAX}."
        else:  # already_guessed
            text = "🔮 Ты уже называл число в этом ивенте — второй попытки нет."
        await message.reply(text, parse_mode="HTML")
        return

    await message.reply(
        f"🔮 <b>Число {result['number']} принято!</b>\n"
        f"<blockquote>Ответ сохранён и никому не виден. Результат станет известен, "
        f"когда сундук раскроют.</blockquote>",
        parse_mode="HTML",
    )


# Оба наши хендлера голого текста (сумма приза от админа, число от игрока)
# регистрируются здесь — уже ПОСЛЕ того, как обе функции определены выше
# (см. подробное объяснение зачем это нужно рядом с определением
# _prioritize_message_handlers).
_prioritize_message_handlers(msg_case_admin_amount, msg_case_guess_number)


# ──────────────────────────────────────────────────────────────────────────
# 👆 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ ВЫШЕ ЭТОЙ СТРОКИ 👆
# ──────────────────────────────────────────────────────────────────────────


async def _entrypoint():
    # Фоновые задачи ивента:
    #  - case_tick_loop        — раз в 1 сек: раскрытие числа по истечении 24 часов
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
