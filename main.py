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
import time
import secrets
import hashlib
import threading
import logging
from datetime import datetime, timedelta

from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, Update, ChatMemberUpdated, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask, request

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
from database import format_amount, aio_get_or_create_user, aio_get_user, aio_save_user

# Ещё немного готовых хелперов из mainhelp.py — переиспользуем как есть:
#  _check_onboarded — проверка/продолжение онбординга для message-хендлеров
#  _get_user_lock    — персональный asyncio.Lock на пользователя (защита от гонок)
#  _text_in          — регистронезависимый фильтр текста сообщения
#  main_menu_keyboard — чтобы добавить кнопку в главное меню
import mainhelp
from mainhelp import _check_onboarded, _get_user_lock, _text_in, main_menu_keyboard
from stats import aio_track_user

# ── Раздел "Мистический сад" — вся логика (цветки, рост, слияние/эволюция,
# продажа) вынесена в green.py, здесь только хендлеры команд/кнопок. ──
import green
from green import (
    garden_text, garden_keyboard,
    plot_detail_text, plot_detail_keyboard,
    plant_menu_text, plant_menu_keyboard, plant_inventory_text, plant_inventory_keyboard,
    inventory_menu_text, inventory_menu_keyboard, inventory_tier_text, inventory_tier_keyboard,
    flower_detail_text, flower_detail_keyboard,
    merge_menu_text, merge_menu_keyboard, merge_tier_text, merge_tier_keyboard,
    plant_flower, harvest_plot, instant_grow, sell_flower,
    merge_cart_add, merge_cart_clear,
    expand_garden, ensure_garden, flower_label, FLOWERS_BY_KEY, FLOWERS_BY_TIER,
    upgrade_plot,
    GRAND_BLOOM_BONUS_ESSENCE, GRAND_BLOOM_BONUS_XP,
    fmt_essence, ESSENCE_ICON, ESSENCE_NAME, fmt_time_left,
    PLOT_PAGES,
    collection_menu_text, collection_menu_keyboard,
    collection_tier_text, collection_tier_keyboard,
    collection_flower_text, collection_flower_keyboard,
    COLLECTION_TIER_MIN,
    mass_actions_unlocked, has_empty_plots, mass_harvest,
    mass_plant_menu_text, mass_plant_menu_keyboard,
    mass_plant_inventory_text, mass_plant_inventory_keyboard,
    mass_plant_toggle_pick, mass_plant_confirm,
    MASS_ACTIONS_MIN_PLOTS,
)

# ── Реферальный ивент "Реферальный марафон" — глобальный бафф добычи
# (шахта / питомцы / урон по боссу), вся логика в ivent.py. Импорт нужен
# только для регистрации его хендлеров (/event, /startevent, /stopevent,
# /eventstats) на общем dp — сам буст в miner.py/pets.py/hunt.py уже
# работает независимо от этого импорта (через ленивый import ivent). ──
import ivent

# ══════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ FREEKASSA 💳
# ══════════════════════════════════════════════════════════════════════

FREKASSA_MERCHANT_ID = 12345  # ЗАМЕНИ НА СВОЙ ID мерчанта
FREKASSA_SECRET_KEY = "your_secret_key_here"  # ЗАМЕНИ НА СВОЙ секретный ключ
FREKASSA_SECRET_KEY2 = "your_second_secret_key"  # Второй секретный ключ (если есть)
FREKASSA_API_URL = "https://api.freekassa.ru/v1/"
FREKASSA_PAY_URL = "https://pay.freekassa.ru/"

# ══════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────────
# 👇 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ НИЖЕ ЭТОЙ СТРОКИ 👇
# ──────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════
#  ПРИЕМ ПЛАТЕЖЕЙ ЧЕРЕЗ FREEKASSA 💳
# ══════════════════════════════════════════════════════════════════════

# Flask-приложение для вебхука
freekassa_app = Flask(__name__)

# Отключаем логи Flask, чтобы не засорять консоль
log = logging.getLogger('werkzeug')
log.disabled = True


@freekassa_app.route('/freekassa/webhook', methods=['POST'])
def freekassa_webhook():
    """Принимает уведомления от Freekassa о статусе платежа."""
    try:
        data = request.form.to_dict()
        
        # Основные параметры от Freekassa
        order_id = data.get('MERCHANT_ORDER_ID')
        amount = data.get('AMOUNT')
        sign = data.get('SIGN')
        currency = data.get('CURRENCY', 'RUB')
        payment_id = data.get('MERCHANT_ID')
        email = data.get('P_EMAIL', '')
        
        # Проверка подписи
        expected_sign = hashlib.md5(
            f"{FREKASSA_MERCHANT_ID}:{amount}:{FREKASSA_SECRET_KEY}:{order_id}".encode('utf-8')
        ).hexdigest().upper()
        
        if sign != expected_sign:
            logging.warning(f"❌ Неверная подпись от Freekassa для заказа {order_id}")
            return "NO", 400
        
        # Извлекаем user_id из order_id (формат: user_123456_1234567890)
        try:
            parts = order_id.split('_')
            if len(parts) >= 2 and parts[0] == 'user':
                user_id = int(parts[1])
            else:
                user_id = None
        except:
            user_id = None
        
        if user_id:
            # Отправляем уведомление пользователю
            asyncio.create_task(
                notify_user_payment_success(
                    user_id,
                    order_id,
                    amount,
                    currency
                )
            )
            
            # Сохраняем информацию о платеже в БД
            asyncio.create_task(
                save_payment_record(
                    user_id,
                    order_id,
                    float(amount),
                    currency
                )
            )
        
        logging.info(f"✅ Платеж принят: заказ {order_id}, сумма {amount} {currency}")
        return "YES", 200
        
    except Exception as e:
        logging.error(f"❌ Ошибка в webhook Freekassa: {e}")
        return "NO", 500


@freekassa_app.route('/freekassa/status', methods=['GET'])
def freekassa_status():
    """Проверка, что вебхук работает."""
    return "✅ Freekassa webhook is running!", 200


def run_freekassa_webhook():
    """Запускает Flask-сервер в отдельном потоке."""
    freekassa_app.run(host='0.0.0.0', port=8080, debug=False)


async def notify_user_payment_success(user_id: int, order_id: str, amount: str, currency: str):
    """Отправляет пользователю уведомление об успешной оплате."""
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"📦 Заказ: <code>{order_id}</code>\n"
            f"💰 Сумма: <b>{amount} {currency}</b>\n\n"
            f"🎉 Товар зачислен на ваш аккаунт!\n"
            f"<i>Спасибо за покупку!</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"❌ Не удалось отправить уведомление пользователю {user_id}: {e}")


async def save_payment_record(user_id: int, order_id: str, amount: float, currency: str):
    """Сохраняет информацию о платеже в БД пользователя."""
    try:
        u = await aio_get_user(user_id)
        if u:
            if "payments" not in u:
                u["payments"] = []
            u["payments"].append({
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
                "date": datetime.now().isoformat(),
                "status": "paid"
            })
            await aio_save_user(user_id, u)
    except Exception as e:
        logging.error(f"❌ Ошибка сохранения платежа: {e}")


# ── КОМАНДА ДЛЯ ПОКУПКИ МОНЕТ ──

class PaymentStates(StatesGroup):
    choosing_amount = State()


@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда для покупки игровой валюты."""
    u = await aio_get_or_create_user(message.from_user)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u):
        return
    
    kb = InlineKeyboardBuilder()
    kb.button(text="100 💎", callback_data="buy:100")
    kb.button(text="500 💎", callback_data="buy:500")
    kb.button(text="1000 💎", callback_data="buy:1000")
    kb.button(text="5000 💎", callback_data="buy:5000")
    kb.button(text="💎 Своя сумма", callback_data="buy:custom")
    kb.button(text="❌ Отмена", callback_data="buy:cancel")
    kb.adjust(2, 2, 2)
    
    await message.answer(
        "💎 <b>Покупка игровой валюты</b>\n\n"
        "Выбери сумму или укажи свою:\n"
        "💰 1 💎 = 1 RUB\n\n"
        "<i>После оплаты алмазы будут зачислены автоматически.</i>",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    
    if action == "cancel":
        await state.clear()
        await call.message.delete()
        await call.answer("❌ Покупка отменена")
        return
    
    if action == "custom":
        await state.set_state(PaymentStates.choosing_amount)
        await call.message.edit_text(
            "💎 <b>Введи сумму в рублях</b>\n\n"
            "Например: <code>250</code> или <code>1500</code>\n"
            "1 💎 = 1 RUB",
            parse_mode="HTML"
        )
        await call.answer()
        return
    
    # Обработка фиксированных сумм
    try:
        amount = int(action)
        if amount <= 0:
            raise ValueError
    except:
        await call.answer("❌ Неверная сумма", show_alert=True)
        return
    
    await process_payment(call.message, call.from_user, amount)
    await call.answer()


@dp.message(StateFilter(PaymentStates.choosing_amount))
async def msg_custom_amount(message: Message, state: FSMContext):
    """Обработка ввода своей суммы."""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await message.answer(
            "❌ Введи целое положительное число, например: <code>250</code>",
            parse_mode="HTML"
        )
        return
    
    await state.clear()
    await process_payment(message, message.from_user, amount)


async def process_payment(message: Message, user, amount: int):
    """Создает платеж в Freekassa."""
    # Генерируем уникальный ID заказа
    order_id = f"user_{user.id}_{int(time.time())}_{secrets.token_hex(4)}"
    
    # Создаем ссылку на оплату
    pay_url = (
        f"{FREKASSA_PAY_URL}?"
        f"m={FREKASSA_MERCHANT_ID}"
        f"&oa={amount}"
        f"&o={order_id}"
        f"&currency=RUB"
        f"&s="  # подпись для формы
    )
    
    # Формируем подпись для формы (для безопасности)
    sign = hashlib.md5(
        f"{FREKASSA_MERCHANT_ID}:{amount}:{FREKASSA_SECRET_KEY2}:{order_id}".encode('utf-8')
    ).hexdigest().upper()
    
    pay_url += sign
    
    # Сохраняем заказ в БД (ожидание оплаты)
    u = await aio_get_user(user.id)
    if u:
        if "pending_payments" not in u:
            u["pending_payments"] = {}
        u["pending_payments"][order_id] = {
            "amount": amount,
            "status": "pending",
            "date": datetime.now().isoformat(),
            "currency": "RUB"
        }
        await aio_save_user(user.id, u)
    
    await message.answer(
        f"💳 <b>Оплата</b>\n\n"
        f"💰 Сумма: <b>{amount} RUB</b>\n"
        f"📦 Заказ: <code>{order_id}</code>\n\n"
        f"🔗 <a href='{pay_url}'>Нажмите здесь, чтобы оплатить</a>\n\n"
        f"<i>После оплаты алмазы будут зачислены автоматически в течение 1-2 минут.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ══════════════════════════════════════════════════════════════════════
#  АДМИН-КОМАНДА ДЛЯ РУЧНОГО НАЧИСЛЕНИЯ АЛМАЗОВ
# ══════════════════════════════════════════════════════════════════════

@dp.message(Command("adddiamonds"))
async def cmd_add_diamonds(message: Message):
    """Админская команда для ручного начисления алмазов."""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply(
            "❌ Использование: <code>/adddiamonds @username 100</code>\n"
            "или <code>/adddiamonds 123456789 100</code>",
            parse_mode="HTML"
        )
        return
    
    # Определяем user_id
    user_id = None
    if args[1].startswith('@'):
        # По username
        try:
            # Пытаемся получить пользователя по username (не всегда работает)
            username = args[1][1:]
            # Простой поиск по БД (нужно расширить)
            # Здесь можно добавить поиск по username в БД
            pass
        except:
            pass
    else:
        try:
            user_id = int(args[1])
        except:
            pass
    
    if not user_id:
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    try:
        amount = int(args[2])
        if amount <= 0:
            raise ValueError
    except:
        await message.reply("❌ Укажите положительное число")
        return
    
    # Начисляем алмазы
    u = await aio_get_user(user_id)
    if not u:
        await message.reply("❌ Пользователь не найден")
        return
    
    u["diamonds"] = u.get("diamonds", 0) + amount
    await aio_save_user(user_id, u)
    
    await message.reply(
        f"✅ Начислено <b>{amount} 💎</b> пользователю ID: {user_id}",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ "МИСТИЧЕСКИЙ САД" 🌺
#  (код остался без изменений)
# ══════════════════════════════════════════════════════════════════════

_orig_main_reply_keyboard = mainhelp.main_reply_keyboard


def _garden_main_reply_keyboard(lang: str = "ru"):
    kb = _orig_main_reply_keyboard(lang)
    garden_btn = KeyboardButton(
        text="🌺 Мистический Сад" if lang == "ru" else "🌺 Mystic Garden",
        style="primary",
    )
    if kb.keyboard:
        kb.keyboard[-1].append(garden_btn)
    else:
        kb.keyboard.append([garden_btn])
    return kb


mainhelp.main_reply_keyboard = _garden_main_reply_keyboard


def _safe_int(s: str, default: int = -1) -> int:
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


async def _garden_open(uid: int, u: dict, page: int = 0):
    ensure_garden(u)
    await aio_save_user(uid, u)
    return garden_text(u, page), garden_keyboard(u, page)


_garden_owners: dict[tuple[int, int], int] = {}
_GARDEN_OWNERS_LIMIT = 5000


def _garden_claim_owner(chat_id: int, message_id: int, uid: int) -> None:
    key = (chat_id, message_id)
    if key not in _garden_owners:
        if len(_garden_owners) >= _GARDEN_OWNERS_LIMIT:
            _garden_owners.pop(next(iter(_garden_owners)))
        _garden_owners[key] = uid


async def _garden_owner_ok(call: CallbackQuery) -> bool:
    key = (call.message.chat.id, call.message.message_id)
    owner = _garden_owners.get(key)
    if owner is None:
        _garden_claim_owner(key[0], key[1], call.from_user.id)
        return True
    if owner != call.from_user.id:
        await call.answer("🔒 Это чужой сад — открой свой командой /garden.", show_alert=True)
        return False
    return True


@dp.message(Command("garden", "сад", "mysticgarden"))
@dp.message(_text_in(
    "сад", "garden", "мистический сад", "mystic garden",
    "🌺 сад", "🌺 garden", "🌺 мистический сад", "🌺 mystic garden",
))
async def cmd_garden(message: Message):
    u = await aio_get_or_create_user(message.from_user)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u):
        return
    text, kb = await _garden_open(message.from_user.id, u)
    sent = await message.reply(text, parse_mode="HTML", reply_markup=kb)
    _garden_claim_owner(sent.chat.id, sent.message_id, message.from_user.id)


@dp.callback_query(F.data == "garden")
async def cb_garden_main(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    text, kb = await _garden_open(uid, u)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data == "garden_noop")
async def cb_garden_noop(call: CallbackQuery):
    await call.answer()


@dp.callback_query(F.data.startswith("garden_page:"))
async def cb_garden_page(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    page = _safe_int(parts[1])
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    text, kb = await _garden_open(uid, u, page)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("garden_plot:"))
async def cb_garden_plot(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if not (0 <= plot_idx < u["garden"]["plot_count"]):
        await call.answer()
        return
    await call.message.edit_text(
        plot_detail_text(u, plot_idx), parse_mode="HTML",
        reply_markup=plot_detail_keyboard(u, plot_idx),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_plantmenu:"))
async def cb_garden_plantmenu(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if not (0 <= plot_idx < u["garden"]["plot_count"]):
        await call.answer()
        return
    await call.message.edit_text(
        plant_menu_text(plot_idx, page), parse_mode="HTML",
        reply_markup=plant_menu_keyboard(u, plot_idx, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_plantinv:"))
async def cb_garden_plantinv(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if not (0 <= plot_idx < u["garden"]["plot_count"]):
        await call.answer()
        return
    await call.message.edit_text(
        plant_inventory_text(u, plot_idx, page), parse_mode="HTML",
        reply_markup=plant_inventory_keyboard(u, plot_idx, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_plant:"))
async def cb_garden_plant(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":", 2)
    if len(parts) < 3:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    flower_key = parts[2]
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = plant_flower(u, plot_idx, flower_key)
        if not result["ok"]:
            reasons = {
                "occupied": "🪴 Грядка уже занята.",
                "unknown_flower": "❌ Неизвестное семя.",
                "no_essence": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()} (нужно {fmt_essence(result.get("cost", 0))}).',
                "no_seed": "🎒 В инвентаре нет такого семени.",
                "bad_plot": "❌ Некорректная грядка.",
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось посадить."), show_alert=True)
            return
        await aio_save_user(uid, u)

    await call.message.edit_text(
        plot_detail_text(u, plot_idx), parse_mode="HTML",
        reply_markup=plot_detail_keyboard(u, plot_idx),
    )
    await call.answer(f'🌱 Посажено: {flower_label(result["flower"])}')


@dp.callback_query(F.data.startswith("garden_harvest:"))
async def cb_garden_harvest(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = harvest_plot(u, plot_idx)
        if not result["ok"]:
            reasons = {
                "empty": "🪴 Грядка пуста.",
                "not_ready": "⏳ Цветок ещё не вырос.",
                "bad_plot": "❌ Некорректная грядка.",
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось собрать."), show_alert=True)
            return
        mainhelp._apply_xp(u, result["xp"])
        await aio_save_user(uid, u)

    await call.message.edit_text(
        plot_detail_text(u, plot_idx), parse_mode="HTML",
        reply_markup=plot_detail_keyboard(u, plot_idx),
    )
    jackpot_note = "\n🎰 ДЖЕКПОТ! Награда удвоена!" if result.get("jackpot") else ""
    await call.answer(
        f'🌾 Собрано: {flower_label(result["flower"])}\n'
        f'+{fmt_essence(result["essence"])}  +{result["xp"]} XP{jackpot_note}',
        show_alert=True,
    )

    if result.get("grand_bloom"):
        try:
            await call.message.answer(
                '🏆 <b>ПОЛНОЕ ЦВЕТЕНИЕ!</b>\n'
                '<blockquote><i>Ты когда-либо собрал все 5 сигнатурных цветков высшего тира '
                f'«Изначальный»! Награда:</i> <b>+{fmt_essence(GRAND_BLOOM_BONUS_ESSENCE)}</b></blockquote>',
                parse_mode="HTML",
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("garden_grow:"))
async def cb_garden_grow(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = instant_grow(u, plot_idx)
        if not result["ok"]:
            reasons = {
                "empty": "🪴 Грядка пуста.",
                "already_ready": "✅ Цветок уже готов к сбору!",
                "already_boosted": "⚡ Ускорение уже использовано для этого цветка — доступно только 1 раз за посадку.",
                "no_essence": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()} (нужно {fmt_essence(result.get("cost", 0))}).',
                "bad_plot": "❌ Некорректная грядка.",
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось ускорить."), show_alert=True)
            return
        await aio_save_user(uid, u)

    await call.message.edit_text(
        plot_detail_text(u, plot_idx), parse_mode="HTML",
        reply_markup=plot_detail_keyboard(u, plot_idx),
    )
    left_note = "Готов к сбору! ✅" if result["left"] <= 0 else f'осталось {fmt_time_left(result["left"])}'
    await call.answer(f'⚡ Рост ускорен в 2 раза за {fmt_essence(result["cost"])} — {left_note}')


@dp.callback_query(F.data.startswith("garden_plotup:"))
async def cb_garden_plotup(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    plot_idx = _safe_int(parts[1])
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = upgrade_plot(u, plot_idx)
        if not result["ok"]:
            reasons = {
                "max_level": "🏆 Грядка уже максимального уровня.",
                "no_essence": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()} (нужно {fmt_essence(result.get("cost", 0))}).',
                "bad_plot": "❌ Некорректная грядка.",
                "low_reserve": (
                    f'{ESSENCE_ICON} После улучшения должно остаться больше '
                    f'{fmt_essence(result.get("reserve", 0))} — на семя. '
                    f'Накопите ещё {ESSENCE_NAME.lower()}.'
                ),
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось улучшить грядку."), show_alert=True)
            return
        await aio_save_user(uid, u)

    await call.message.edit_text(
        plot_detail_text(u, plot_idx), parse_mode="HTML",
        reply_markup=plot_detail_keyboard(u, plot_idx),
    )
    await call.answer(
        f'⬆️ Грядка улучшена до уровня {result["level"]} (скорость ×{result["mult"]:g}) '
        f'за {fmt_essence(result["cost"])}',
        show_alert=True,
    )


@dp.callback_query(F.data == "garden_inventory")
async def cb_garden_inventory(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        inventory_menu_text(u), parse_mode="HTML",
        reply_markup=inventory_menu_keyboard(u),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_invtier:"))
async def cb_garden_invtier(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    tier = _safe_int(parts[1])
    page = _safe_int(parts[2]) if len(parts) > 2 else 0
    if tier not in FLOWERS_BY_TIER:
        await call.answer()
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        inventory_tier_text(u, tier, page), parse_mode="HTML",
        reply_markup=inventory_tier_keyboard(u, tier, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_flower:"))
async def cb_garden_flower(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    flower_key = parts[1]
    page = _safe_int(parts[2]) if len(parts) > 2 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u or flower_key not in FLOWERS_BY_KEY:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        flower_detail_text(u, flower_key), parse_mode="HTML",
        reply_markup=flower_detail_keyboard(u, flower_key, page),
    )
    await call.answer()


@dp.callback_query(F.data == "garden_merge")
async def cb_garden_merge_menu(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        merge_menu_text(u), parse_mode="HTML",
        reply_markup=merge_menu_keyboard(u),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_mergetier:"))
async def cb_garden_mergetier(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    tier = _safe_int(parts[1])
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    if tier not in FLOWERS_BY_TIER:
        await call.answer()
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        merge_tier_text(u, tier, page), parse_mode="HTML",
        reply_markup=merge_tier_keyboard(u, tier, page),
    )
    await call.answer()


@dp.callback_query(F.data == "garden_mergeclear")
async def cb_garden_mergeclear(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id
    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        merge_cart_clear(u)
        await aio_save_user(uid, u)
    await call.message.edit_text(
        merge_menu_text(u), parse_mode="HTML",
        reply_markup=merge_menu_keyboard(u),
    )
    await call.answer("🗑 Котёл очищен.")


@dp.callback_query(F.data.startswith("garden_mergeadd:"))
async def cb_garden_mergeadd(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    flower_key = parts[1]
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = merge_cart_add(u, flower_key)
        if not result["ok"]:
            reasons = {
                "max_tier": "🏆 Это уже высший тир — сливать дальше некуда.",
                "not_enough": "🧬 В инвентаре не осталось свободных штук этого цветка.",
                "tier_mismatch": "⚠️ В котле уже цветки другого тира — сначала очисти котёл.",
                "unknown_flower": "❌ Неизвестный цветок.",
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось добавить в котёл."), show_alert=True)
            return
        await aio_save_user(uid, u)
        tier_for_view = FLOWERS_BY_KEY[flower_key]["tier"]

    if not result.get("done"):
        await call.message.edit_text(
            merge_tier_text(u, tier_for_view, page), parse_mode="HTML",
            reply_markup=merge_tier_keyboard(u, tier_for_view, page),
        )
        await call.answer(f'🔥 Добавлено в котёл! Ещё нужно: {result["need"]} шт.')
        return

    # Слияние произошло автоматически
    surge_note = " · ✨ ПРОРЫВ!" if result["surge"] else ""
    mixed_note = " · 🎭 разные цветки" if result["mixed"] else ""
    consumed_label = ", ".join(f'{flower_label(f)} ×{c}' for f, c in result["consumed"])
    saved_back = result.get("saved_back") or []
    saved_note = ""
    if saved_back:
        saved_label = ", ".join(f'{flower_label(f)} ×{c}' for f, c in saved_back)
        saved_note = f'\n🔁 Не сгорели в котле: {saved_label}'

    await call.message.edit_text(
        merge_menu_text(u), parse_mode="HTML",
        reply_markup=merge_menu_keyboard(u),
    )
    await call.answer(
        f'🧬 Слияние: {consumed_label} → {flower_label(result["result"])}{surge_note}{mixed_note}{saved_note}',
        show_alert=True,
    )

    if result.get("new_discovery"):
        try:
            await call.message.answer(
                f'📖 <b>Новый вид в коллекции!</b>\n'
                f'<blockquote>{flower_label(result["result"])} впервые добавлен в твою коллекцию.\n'
                f'Награда за открытие: <b>+{fmt_essence(result["discovery_reward"])}</b></blockquote>',
                parse_mode="HTML",
            )
        except Exception:
            pass

    if result.get("grand_bloom"):
        try:
            await call.message.answer(
                '🏆 <b>ПОЛНОЕ ЦВЕТЕНИЕ!</b>\n'
                '<blockquote><i>Ты когда-либо собрал все 5 сигнатурных цветков высшего тира '
                f'«Изначальный»! Награда:</i> <b>+{fmt_essence(GRAND_BLOOM_BONUS_ESSENCE)}</b></blockquote>',
                parse_mode="HTML",
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("garden_sell:"))
async def cb_garden_sell(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer()
        return
    _, flower_key, count_s = parts[0], parts[1], parts[2]
    page = _safe_int(parts[3], 0) if len(parts) > 3 else 0
    if flower_key not in FLOWERS_BY_KEY:
        await call.answer()
        return
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        ensure_garden(u)
        have = u["garden"]["inventory"].get(flower_key, 0)
        count = have if count_s == "all" else 1
        result = sell_flower(u, flower_key, count)
        if not result["ok"]:
            await call.answer("❌ Нечего продавать.", show_alert=True)
            return
        await aio_save_user(uid, u)

    still_have = u["garden"]["inventory"].get(flower_key, 0) > 0
    if still_have:
        await call.message.edit_text(
            flower_detail_text(u, flower_key), parse_mode="HTML",
            reply_markup=flower_detail_keyboard(u, flower_key, page),
        )
    else:
        tier = FLOWERS_BY_KEY[flower_key]["tier"]
        await call.message.edit_text(
            inventory_tier_text(u, tier, page), parse_mode="HTML",
            reply_markup=inventory_tier_keyboard(u, tier, page),
        )
    await call.answer(f'💰 Продано {result["count"]} шт. за {fmt_essence(result["essence"])}')


@dp.callback_query(F.data == "garden_collection")
async def cb_garden_collection(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        collection_menu_text(u), parse_mode="HTML",
        reply_markup=collection_menu_keyboard(u),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_colltier:"))
async def cb_garden_colltier(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    tier = _safe_int(parts[1])
    if tier not in FLOWERS_BY_TIER or tier < COLLECTION_TIER_MIN:
        await call.answer()
        return
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    await call.message.edit_text(
        collection_tier_text(u, tier, page), parse_mode="HTML",
        reply_markup=collection_tier_keyboard(u, tier, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_collflower:"))
async def cb_garden_collflower(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    if len(parts) < 2:
        await call.answer()
        return
    flower_key = parts[1]
    if flower_key not in FLOWERS_BY_KEY:
        await call.answer()
        return
    page = _safe_int(parts[2], 0) if len(parts) > 2 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if flower_key not in u["garden"]["stats"]["discovered"]:
        await call.answer("🔒 Этот вид ещё не открыт.", show_alert=True)
        return
    await call.message.edit_text(
        collection_flower_text(u, flower_key), parse_mode="HTML",
        reply_markup=collection_flower_keyboard(u, flower_key, page),
    )
    await call.answer()


@dp.callback_query(F.data == "garden_expand")
async def cb_garden_expand(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        result = expand_garden(u)
        if not result["ok"]:
            reasons = {
                "max_plots": "🪴 Достигнут максимум грядок.",
                "no_essence": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()} (нужно {fmt_essence(result.get("cost", 0))}).',
                "low_reserve": (
                    f'{ESSENCE_ICON} После открытия должно остаться больше '
                    f'{fmt_essence(result.get("reserve", 0))} — на семя. '
                    f'Накопите ещё {ESSENCE_NAME.lower()}.'
                ),
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось открыть грядку."), show_alert=True)
            return
        await aio_save_user(uid, u)
        page = (result["plot_count"] - 1) // 4

    await call.message.edit_text(
        garden_text(u, page), parse_mode="HTML",
        reply_markup=garden_keyboard(u, page),
    )
    await call.answer(f'🪴 Грядка открыта! Теперь их: {result["plot_count"]}')


# ── Массовая посадка / массовый сбор урожая ──

def _mass_locked_alert(plot_count: int) -> str:
    return (
        f'🔒 Массовые действия открываются после {MASS_ACTIONS_MIN_PLOTS} '
        f'открытых грядок (сейчас: {plot_count}/{MASS_ACTIONS_MIN_PLOTS}).'
    )


@dp.callback_query(F.data.startswith("garden_massplantinv:"))
async def cb_garden_massplant_inv(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    page = _safe_int(parts[1], 0) if len(parts) > 1 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if not mass_actions_unlocked(u["garden"]):
        await call.answer(_mass_locked_alert(u["garden"]["plot_count"]), show_alert=True)
        return
    if not has_empty_plots(u["garden"]):
        await call.answer("🪴 Нет свободных грядок для посадки.", show_alert=True)
        return
    await call.message.edit_text(
        mass_plant_inventory_text(u, page), parse_mode="HTML",
        reply_markup=mass_plant_inventory_keyboard(u, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_massplant:"))
async def cb_garden_massplant_menu(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":")
    page = _safe_int(parts[1], 0) if len(parts) > 1 else 0
    uid = call.from_user.id
    u = await aio_get_user(uid)
    if not u:
        await call.answer()
        return
    ensure_garden(u)
    if not mass_actions_unlocked(u["garden"]):
        await call.answer(_mass_locked_alert(u["garden"]["plot_count"]), show_alert=True)
        return
    if not has_empty_plots(u["garden"]):
        await call.answer("🪴 Нет свободных грядок для посадки.", show_alert=True)
        return
    await call.message.edit_text(
        mass_plant_menu_text(u, page), parse_mode="HTML",
        reply_markup=mass_plant_menu_keyboard(u, page),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("garden_masspick:"))
async def cb_garden_masspick(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    parts = call.data.split(":", 3)
    if len(parts) < 4:
        await call.answer()
        return
    source, flower_key, page_raw = parts[1], parts[2], parts[3]
    page = _safe_int(page_raw, 0)
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        ensure_garden(u)
        result = mass_plant_toggle_pick(u, flower_key)
        if not result["ok"]:
            reasons = {
                "locked": _mass_locked_alert(u["garden"]["plot_count"]),
                "unknown_flower": "❌ Неизвестное семя.",
                "not_affordable": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()} даже на одно семя.',
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось выбрать."), show_alert=True)
            return
        await aio_save_user(uid, u)

    if source == "inv":
        await call.message.edit_text(
            mass_plant_inventory_text(u, page), parse_mode="HTML",
            reply_markup=mass_plant_inventory_keyboard(u, page),
        )
    else:
        await call.message.edit_text(
            mass_plant_menu_text(u, page), parse_mode="HTML",
            reply_markup=mass_plant_menu_keyboard(u, page),
        )
    await call.answer()


@dp.callback_query(F.data == "garden_massplantgo")
async def cb_garden_massplantgo(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        ensure_garden(u)
        result = mass_plant_confirm(u)
        if not result["ok"]:
            reasons = {
                "locked": _mass_locked_alert(u["garden"]["plot_count"]),
                "no_pick": "🌱 Сначала выбери хотя бы одно семя, которым будем сажать.",
                "no_empty": "🪴 Нет свободных грядок для посадки.",
                "no_essence": f'{ESSENCE_ICON} Не хватает {ESSENCE_NAME.lower()}/семян даже на одну грядку.',
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось посадить."), show_alert=True)
            return
        await aio_save_user(uid, u)
        text, kb = await _garden_open(uid, u)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    lines = [f'{flower_label(result["flowers"][key])} ×{cnt}' for key, cnt in result["counts"].items()]
    stop_note = ""
    if result.get("stop_reason") == "exhausted":
        stop_note = f'\n{ESSENCE_ICON} Пыльца/семена закончились раньше, чем свободные грядки.'
    await call.answer(
        f'🌱 Засажено грядок: {result["planted"]}\n' + "\n".join(lines) + stop_note,
        show_alert=True,
    )


@dp.callback_query(F.data == "garden_massharvest")
async def cb_garden_massharvest(call: CallbackQuery):
    if not await _garden_owner_ok(call):
        return
    uid = call.from_user.id

    async with await _get_user_lock(uid):
        u = await aio_get_user(uid)
        if not u:
            await call.answer()
            return
        ensure_garden(u)
        result = mass_harvest(u)
        if not result["ok"]:
            reasons = {
                "locked": _mass_locked_alert(u["garden"]["plot_count"]),
                "none_ready": "⏳ Пока нет готовых к сбору грядок.",
            }
            await call.answer(reasons.get(result["reason"], "❌ Не удалось собрать урожай."), show_alert=True)
            return
        mainhelp._apply_xp(u, result["xp"])
        await aio_save_user(uid, u)
        text, kb = await _garden_open(uid, u)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    jackpot_note = f'\n🎰 Джекпотов: {result["jackpots"]}' if result.get("jackpots") else ""
    await call.answer(
        f'🌾 Собрано грядок: {result["count"]}\n'
        f'+{fmt_essence(result["essence"])}  +{result["xp"]} XP{jackpot_note}',
        show_alert=True,
    )

    if result.get("grand_bloom"):
        try:
            await call.message.answer(
                '🏆 <b>ПОЛНОЕ ЦВЕТЕНИЕ!</b>\n'
                '<blockquote><i>Ты когда-либо собрал все 5 сигнатурных цветков высшего тира '
                f'«Изначальный»! Награда:</i> <b>+{fmt_essence(GRAND_BLOOM_BONUS_ESSENCE)}</b></blockquote>',
                parse_mode="HTML",
            )
        except Exception:
            pass


# По той же причине, что и с текстовыми хендлерами сада выше (см.
# _prioritize_message_handlers) — если где-то в mainhelp.py раньше
# зарегистрирован «широкий» callback_query-хендлер (например, общий
# обработчик неизвестных/старых callback'ов), он мог перехватывать
# инлайн-кнопки сада раньше, чем до них доходила очередь, и кнопки
# "молчали" (call.answer() не приходил / ничего не происходило).
# Переставляем ВСЕ callback-хендлеры сада в начало списка dp.callback_query,
# ничего в mainhelp.py при этом не трогая.
def _prioritize_callback_handlers(*callbacks) -> None:
    wanted    = list(callbacks)
    moved     = [h for h in dp.callback_query.handlers if h.callback in wanted]
    remaining = [h for h in dp.callback_query.handlers if h.callback not in wanted]
    moved.sort(key=lambda h: wanted.index(h.callback))
    dp.callback_query.handlers[:] = moved + remaining


_prioritize_callback_handlers(
    cb_garden_main, cb_garden_noop, cb_garden_page,
    cb_garden_plot, cb_garden_plantmenu, cb_garden_plantinv,
    cb_garden_plant, cb_garden_harvest, cb_garden_grow, cb_garden_plotup, cb_garden_inventory,
    cb_garden_invtier, cb_garden_flower, cb_garden_merge_menu, cb_garden_mergetier,
    cb_garden_mergeclear, cb_garden_mergeadd, cb_garden_sell, cb_garden_expand,
    cb_garden_collection, cb_garden_colltier, cb_garden_collflower,
    cb_garden_massplant_inv, cb_garden_massplant_menu, cb_garden_masspick,
    cb_garden_massplantgo, cb_garden_massharvest,
)


# ══════════════════════════════════════════════════════════════════════
#  РЕЕСТР ЧАТОВ — запоминаем chat_id каждого апдейта
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


@dp.my_chat_member()
async def _on_bot_membership_changed(update: ChatMemberUpdated):
    chat   = update.chat
    status = update.new_chat_member.status

    if status in ("member", "administrator", "creator"):
        set_chat_type(chat.id, chat.type)
        await register_chat(chat.id, chat.type, getattr(chat, "title", None))
    elif status in ("left", "kicked"):
        await forget_chat(chat.id)


# ══════════════════════════════════════════════════════════════════════
#  ИГРА "УГАДАЙ ЧИСЛО" / ИВЕНТ "ЩЕДРЫЙ ПИРАТ"
# ══════════════════════════════════════════════════════════════════════

class CaseAdminSetup(StatesGroup):
    choosing_type     = State()
    choosing_artifact = State()
    choosing_status   = State()
    entering_amount   = State()


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
        return

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

    tier  = call.data.split(":", 1)[1]
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


@dp.message(Command("guess"))
async def cmd_guess(message: Message):
    if message.chat.type != "private":
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
        return

    await state.clear()
    set_chat_type(message.chat.id, message.chat.type)
    await _submit_guess(
        uid=message.from_user.id,
        name=message.from_user.first_name or message.from_user.username or str(message.from_user.id),
        number=int(text),
        message=message,
    )


async def _submit_guess(uid: int, name: str, number: int, message: Message):
    result = await try_guess(uid, name, number)

    if not result["ok"]:
        reason = result["reason"]
        if reason == "no_active":
            text = "📦 Сейчас нет активного ивента."
        elif reason == "bad_range":
            text = f"❌ Число должно быть от {NUMBER_MIN} до {NUMBER_MAX}."
        else:
            text = "🔮 Ты уже называл число в этом ивенте — второй попытки нет."
        await message.reply(text, parse_mode="HTML")
        return

    await message.reply(
        f"🔮 <b>Число {result['number']} принято!</b>\n"
        f"<blockquote>Ответ сохранён и никому не виден. Результат станет известен, "
        f"когда сундук раскроют.</blockquote>",
        parse_mode="HTML",
    )


_prioritize_message_handlers(msg_case_admin_amount, msg_case_guess_number, cmd_garden)

# ──────────────────────────────────────────────────────────────────────────
# 👆 ДОБАВЛЯЙ СВОИ НОВЫЕ КОМАНДЫ/ХЕНДЛЕРЫ ВЫШЕ ЭТОЙ СТРОКИ 👆
# ──────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════
#  ЗАПУСК БОТА С ВЕБХУКОМ
# ══════════════════════════════════════════════════════════════════════

async def _entrypoint_with_webhook():
    # Запускаем Flask в отдельном потоке (неблокирующем)
    webhook_thread = threading.Thread(target=run_freekassa_webhook, daemon=True)
    webhook_thread.start()
    print("✅ Freekassa webhook запущен на порту 8080")
    print("📡 Проверка: http://localhost:8080/freekassa/status")
    
    # Фоновые задачи ивента
    asyncio.create_task(case_tick_loop(bot))
    asyncio.create_task(case_card_refresh_loop(bot))
    
    # Запускаем бота
    await run_bot()


if __name__ == "__main__":
    asyncio.run(_entrypoint_with_webhook())
