import asyncio
import html as _html
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import Command

from database import (
    init_db, get_or_create_user, save_user,
    profile_text, format_amount,
    aio_is_charge_processed, aio_mark_charge_processed,
    aio_get_or_create_user, aio_save_user,
)
from miner import (
    ORES, PICKAXES, PICKAXES_ORDER,
    DURATIONS, DURATIONS_ORDER,
    now_ts,
    mine_text, mine_keyboard,
    workshop_text, workshop_keyboard,
    pickaxe_detail_text, pickaxe_detail_keyboard,
    duration_shop_text, duration_shop_keyboard,
    duration_detail_text, duration_detail_keyboard,
    sell_screen_text, sell_keyboard,
    shop_pickaxes_text, shop_pickaxes_keyboard,
    inventory_screen_text, inventory_keyboard,
    init_mine_data,
    collect_mine,
    stop_mine,
    can_stop_mine,
    sell_all_ores,
    buy_pickaxe, select_pickaxe,
    buy_duration, select_duration,
    get_pickaxe_page,
    calc_mine_progress,
    mine_finished_notify_text,
    EMOJI_BACK,
)
from pets import (
    PETS,
    pets_main_text, pets_main_keyboard,
    pet_detail_text, pet_detail_keyboard,
    buy_pet,
    get_pending_income, get_pending_notifications,
    pet_income_text,
)

from hunt import (
    init_hunt_db,
    hunt_main_text, hunt_main_keyboard,
    sword_shop_text, sword_shop_keyboard,
    sword_detail_text, sword_detail_keyboard,
    my_swords_text, my_swords_keyboard,
    boss_select_text, boss_select_keyboard,
    boss_tier_menu_text, boss_tier_menu_keyboard,
    boss_attack_text, boss_attack_keyboard,
    boss_strike_result_text, boss_strike_keyboard,
    buy_sword, equip_sword, attack_boss,
    get_boss_state,
    BOSSES_BY_KEY as _BOSSES_BY_KEY,
    # Арсенал
    is_arsenal_cmd,
    arsenal_main_text, arsenal_main_keyboard,
    arsenal_equip_menu_text, arsenal_equip_menu_keyboard,
    arsenal_gift_sword, arsenal_transfer_sword, arsenal_rent_sword,
    arsenal_gift_confirm_text, arsenal_transfer_confirm_text, arsenal_rent_confirm_text,
    arsenal_received_text,
    parse_arsenal_cmd, get_sword_by_arsenal_index,
    arsenal_error_text, arsenal_back_keyboard,
    cleanup_expired_rentals,
    # Зелья
    POTIONS_BY_KEY,
    potions_shop_text, potions_shop_keyboard,
    potions_menu_text, potions_menu_keyboard,
    my_potions_text, my_potions_keyboard,
    potion_use_detail_text, potion_use_detail_keyboard,
    potion_detail_text, potion_detail_keyboard,
    potion_invoice_params, confirm_potion_purchase,
    is_potion_cmd,
    ACTIVE_BOSS_SLOTS,
    _load_slot as _hunt_load_slot,
    revival_pick_slot_text, revival_pick_slot_keyboard,
    use_potion,
    get_all_slots,
    _E,
)

from achieves import (
    check_achievements, achievement_unlocked_text, notify_new_achievements,
    achievements_list_text, achievements_keyboard, achievements_summary_line,
    achievements_menu_text, achievements_menu_keyboard,
    init_achievements_db,
    DEFAULT_CATEGORY,
)

from stats import init_stats_db, track_user, aio_track_user, stats_text, aio_stats_text, stats_keyboard
from settings import (
    settings_text, settings_keyboard,
    lang_choose_text, lang_choose_keyboard, lang_choose_keyboard_start,
)
from lang import t, get_lang

from leaders import (
    init_leaders_db,
    # ВАЖНО: aio_-обёртки — прямой вызов синхронных версий из async-хэндлера
    # блокирует весь event loop (record_boss_hit особенно горячая точка —
    # вызывается на каждый удар по боссу).
    aio_record_boss_hit as record_boss_hit,
    aio_leaders_text as leaders_text,
    leaders_keyboard,
    aio_leaders_main_text as leaders_main_text,
    leaders_main_keyboard,
    CATEGORIES as _LEADERS_CATEGORIES,
    PERIODS    as _LEADERS_PERIODS,
)

from leaders_crystals import (
    router as leaders_crystals_router,
    init_crystal_leaders_db,
    crystal_leaders_main_text, crystal_leaders_main_keyboard,
)


from status import (
    status_main_text, status_main_keyboard,
    status_vip_text, status_vip_keyboard, status_vip_keyboard_invoice,
    status_premium_text, status_premium_keyboard, status_premium_keyboard_invoice,
    status_upgrade_keyboard_invoice,
    activate_status,
    VIP_COST_STARS, PREMIUM_COST_STARS, UPGRADE_COST_STARS,
)
from refs import (
    init_refs_db,
    aio_register_referral as register_referral,
    aio_is_captcha_passed as is_captcha_passed,
    aio_is_captcha_blocked as is_captcha_blocked,
    aio_get_captcha_state as get_captcha_state,
    aio_create_captcha as create_captcha,
    aio_check_captcha as check_captcha,
    aio_set_captcha_msg as set_captcha_msg,
    aio_get_captcha_msg as get_captcha_msg,
    aio_reward_inviter as reward_inviter,
    aio_get_inviter as get_inviter,
    aio_refs_main_text as refs_main_text,
    refs_main_keyboard,
    aio_refs_list_text as refs_list_text,
    refs_list_keyboard,
    captcha_start_text, captcha_wrong_text,
    captcha_blocked_text,
    refs_notif_text,
    aio_reftop_text as reftop_text,
    reftop_keyboard,
)
from klan import (
    init_klan_db,
    # ВАЖНО: используем только aio_-обёртки (asyncio.to_thread) для всех
    # функций, читающих/пишущих БД кланов — прямой вызов синхронных версий
    # из async-хэндлера блокирует ВЕСЬ event loop бота на время диск-I/O
    # (тот же класс бага, что был с cdl.py/database.py — см. коммент ниже).
    aio_get_member as get_member,
    aio_get_clan as get_clan,
    aio_get_clan_members as get_clan_members,
    aio_get_member_count as get_member_count,
    aio_search_clans as search_clans,
    aio_get_top_clans as get_top_clans,
    aio_create_clan as create_clan,
    aio_disband_clan as disband_clan,
    aio_leave_clan as leave_clan,
    aio_kick_member as kick_member,
    aio_apply_to_clan as apply_to_clan,
    aio_get_applications as get_applications,
    aio_accept_application as accept_application,
    aio_reject_application as reject_application,
    aio_accept_all_applications as accept_all_applications,
    aio_reject_all_applications as reject_all_applications,
    aio_deposit_treasury as deposit_treasury,
    aio_request_withdrawal as request_withdrawal,
    aio_get_withdrawal_requests as get_withdrawal_requests,
    aio_approve_withdrawal as approve_withdrawal,
    aio_reject_withdrawal as reject_withdrawal,
    aio_set_clan_chat as set_clan_chat,
    aio_remove_clan_chat as remove_clan_chat,
    klan_main_text, klan_main_keyboard,
    klan_search_text, klan_search_keyboard,
    klan_card_text, klan_card_keyboard,
    my_klan_text, my_klan_keyboard,
    klan_members_text,
    klan_treasury_text, klan_treasury_keyboard,
    klan_applications_text, klan_applications_keyboard,
    klan_withdrawal_requests_text, klan_withdrawal_keyboard,
    klan_top_text, klan_top_keyboard,
    klan_stats_text, klan_stats_keyboard,
    klan_back_keyboard,
    aio_add_clan_boss_damage as add_clan_boss_damage,
    aio_register_clan_boss_kill as register_clan_boss_kill,
    aio_add_clan_mine_earnings as add_clan_mine_earnings,
    aio_get_daily_quests as get_daily_quests,
    aio_get_personal_quests as get_personal_quests,
    aio_get_clan_mining_bonus_multiplier as get_clan_mining_bonus_multiplier,
    aio_add_clan_antimatter as add_clan_antimatter,
    aio_level_up_clan as level_up_clan,
    klan_quests_text, klan_quests_keyboard,
    CREATE_COST, MIN_CLAN_NAME, MAX_CLAN_NAME,
    CLANS_PER_PAGE,
)
from checks import (
    init_checks_db,
    aio_create_check as create_check,
    aio_get_check as get_check,
    aio_activate_check as activate_check,
    aio_list_checks as list_checks,
    aio_delete_check as delete_check,
    aio_create_promo as create_promo,
    aio_get_promo as get_promo,
    aio_activate_promo as activate_promo,
    aio_list_promos as list_promos,
    aio_delete_promo as delete_promo,
    check_activate_text, check_error_text,
    promo_activate_text, promo_error_text, promo_input_text,
)
from cdl import (
    init_cdl_db,
    DEPOSITS_BY_KEY as _CDL_DEPOSITS_BY_KEY,
    cdl_main_text, cdl_main_keyboard,
    cdl_detail_text, cdl_detail_keyboard,
    cdl_input_text, cdl_input_keyboard,
    cdl_confirm_text, cdl_confirm_keyboard,
    cdl_opened_text,
    cdl_claim_text,
    # ВАЖНО: используем только aio_-обёртки (asyncio.to_thread) — прямой
    # вызов синхронных версий (_open_deposit, _claim_deposit и т.д.) из
    # async-хэндлера блокирует ВЕСЬ event loop бота на время диск-I/O
    # и был причиной многоминутных зависаний для всех пользователей сразу.
    aio_open_deposit as _cdl_open_deposit,
    aio_get_ready_deposits as _cdl_get_ready,
    aio_claim_deposit as _cdl_claim,
    aio_count_active as _cdl_count_active,
    aio_get_matured_deposits_for_all_users as _cdl_get_matured_all,
    DEPOSITS_BY_KEY as _CDL_DEP_BY_KEY_REF,
)
from shop import (
    cases_shop_text, cases_shop_keyboard,
    inventory_main_text, inventory_main_keyboard,
    boosters_inventory_text, boosters_inventory_keyboard,
    booster_detail_text, booster_detail_keyboard,
    booster_confirm_replace_text, booster_confirm_replace_keyboard,
    xp_inventory_text, xp_inventory_keyboard,
    xp_item_detail_text, xp_item_detail_keyboard,
    xp_confirm_replace_text, xp_confirm_replace_keyboard,
    enh_inventory_text, enh_inventory_keyboard,
    enh_item_detail_text, enh_item_detail_keyboard,
    enh_confirm_replace_text, enh_confirm_replace_keyboard,
    open_case, activate_booster, sell_booster,
    use_xp_item, sell_xp_item,
    use_poison, activate_enh_boost, sell_enh_item,
    # Артефакты
    artifact_case_detail_text, artifact_case_keyboard,
    artifact_collection_text, artifact_collection_keyboard,
    open_artifact_case, ARTIFACT_CASE_COST_STARS, ARTIFACT_POOL_BY_KEY,
    # Единый инвентарь
    unified_inventory_text, get_unified_inventory,
    use_item_by_slot_id, cancel_active_by_type,
    get_all_active_boosters_text,
    sell_item_by_slot_id,
    transfer_item_by_slot_id,
    open_case_multi, CASE_NUM_TO_KEY,
)
from donate import (
    DONATE_PACKAGES, DONATE_BY_KEY,
    donate_main_text, donate_main_keyboard,
    donate_package_text, donate_package_keyboard,
    apply_donate,
)

from city import (
    router as city_router,
    init_city_db,
    city_prices_loop, city_travel_loop, city_news_loop, city_exchange_loop,
    cmd_city_profile, cmd_city_shop,
)

from rass import (
    is_in_rass,
    rass_start,
    rass_cancel,
    rass_fsm_message,
    rass_fsm_callback,
)
from duel import (
    duel_main_text, duel_main_keyboard,
    is_duel_main_cmd, is_duel_equip_cmd, is_duel_skills_cmd, is_duel_stats_cmd, is_duel_invite_cmd, is_any_duel_cmd,
    cmd_no_hp_text, cmd_already_in_battle_text, cmd_invite_usage_text,
    cmd_invite_self_text, cmd_invite_not_found_text, cmd_invite_in_battle_text,
    cmd_invite_blocked_text,
    duel_soon_text, duel_back_keyboard,
    duel_equip_text, duel_equip_keyboard,
    duel_equip_slot_text, duel_equip_slot_keyboard,
    duel_item_card_text, duel_item_card_keyboard,
    duel_charstats_text, duel_charstats_keyboard,
    duel_skills_text, duel_skills_keyboard,
    duel_skills_shop_text, duel_skills_shop_keyboard,
    duel_skill_card_text, duel_skill_card_keyboard,
    duel_search_text, duel_search_keyboard,
    duel_challenge_screen_text, duel_challenge_screen_keyboard,
    duel_challenge_sent_text, duel_challenge_sent_keyboard,
    duel_hp_status_text,
    battle_text, battle_keyboard,
    battle_use_skill,
    join_queue, leave_queue, in_queue,
    GEAR_CATALOG,
    SKILLS,
    get_owned_skills,
    get_equipped_skills,
    equip_skill,
    unequip_skill,
    _name as duel_skill_name,
    owned_level, equipped_level,
    apply_gear_purchase, apply_gear_equip, apply_gear_unequip,
    MAX_EQUIPPED_SKILLS,
    # HP система
    get_player_hp, set_player_hp, is_player_ready, player_hp_regen_seconds,
    HP_REGEN_INTERVAL, HP_REGEN_AMOUNT,
    # Вызов на дуэль
    create_challenge, get_incoming_challenge, cancel_challenge,
    accept_challenge, decline_challenge, start_challenge_battle,
    challenge_invite_text, challenge_invite_keyboard,
    seconds_until_challenge_slot, cmd_invite_limit_text,
    # Титулы
    get_duel_title, TITLE_REWARDS,
)

# ── In-memory хранилище активных боёв (uid -> battle_state) ─────────
_active_battles: dict[int, dict] = {}
# ── Хранилище message_id боевого экрана (uid -> (chat_id, message_id)) ─
_battle_msgs: dict[int, tuple] = {}

BOT_TOKEN = '8693034024:AAEjOqhChUGq8IvZHYIOw2-RcfJLSyK7ZBI'
bot = Bot(token=BOT_TOKEN)


async def _notify_ach(uid: int, data: dict, newly: list) -> None:
    """
    Шлёт уведомления о только что открытых достижениях СРАЗУ, в момент
    выполнения действия. Вызывается ПОСЛЕ await aio_save_user(...), сразу следом за
    check_achievements(...) (который нужно вызывать ДО save_user, чтобы
    награды монет/опыта тоже попали в сохранённые данные).

    Использование:
        _ach_newly = check_achievements(u)
        await aio_save_user(uid, u)
        await _notify_ach(uid, u, _ach_newly)
    """
    if not newly:
        return
    try:
        await notify_new_achievements(bot, uid, newly, get_lang(data))
    except Exception:
        pass


import re as _re


def _esc(s) -> str:
    """Экранирует HTML-спецсимволы в пользовательском тексте (имя/username и т.п.)
    перед вставкой в сообщение с parse_mode="HTML" — защита от поломки разметки
    и от подмены форматирования через специально подобранное имя профиля."""
    return _html.escape(str(s)) if s else ""


def _fmt_d(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def _plain(text: str) -> str:
    """Убирает HTML-теги и обрезает до 200 символов для call.answer()."""
    return _re.sub(r'<[^>]+>', '', text).strip()[:200]


def _text_in(*variants: str):
    """Регистронезависимый фильтр текста сообщения.
    Сравнивает message.text.strip().lower() с lower-версиями variants,
    поэтому 'Шахта', 'ШАХТА', 'шахта' и т.п. — все будут совпадать.
    """
    lowered = {v.lower() for v in variants}

    def _check(message: Message) -> bool:
        if not message.text:
            return False
        return message.text.strip().lower() in lowered

    return F.func(_check)


dp  = Dispatcher()
dp.include_router(city_router)
dp.include_router(leaders_crystals_router)


# ---------- Глобальный перехват "протухших" callback-запросов ----------
# Если между нажатием кнопки и call.answer() прошло слишком много времени
# (event loop был занят/задержан), Telegram отвечает "query is too old" —
# это НЕ баг логики хендлера, а нормальная ситуация под нагрузкой.
# Раньше это исключение всплывало необработанным и могло рвать обработку
# апдейта на середине (например, после уже начатого списания/сохранения).
# Тут просто гасим именно эту ошибку, всё остальное пробрасываем дальше.
from aiogram.exceptions import TelegramBadRequest as _TgBadRequest
from aiogram.types import ErrorEvent as _ErrorEvent

@dp.errors()
async def _global_error_handler(event: _ErrorEvent):
    exc = event.exception
    msg = str(exc).lower()
    if isinstance(exc, _TgBadRequest) and ("query is too old" in msg or "query id is invalid" in msg):
        return True  # подавляем — callback устарел, это не критично
    logging.exception("Unhandled error while processing update", exc_info=exc)
    return True  # True = ошибка обработана, апдейт не будет "падать" дальше

# ---------- БЛОКИРОВКИ ПО ПОЛЬЗОВАТЕЛЯМ (защита от race condition / дюпов) ----------
import asyncio as _asyncio
_user_locks: dict[int, _asyncio.Lock] = {}
_user_locks_mutex = _asyncio.Lock()



# Хранит message_id экрана кирки перед оплатой: uid -> (chat_id, message_id, pick_key)
_pending_stars_msg: dict[int, tuple] = {}

# Хранит message_id экрана кейса артефактов перед оплатой: uid -> (chat_id, message_id)
_pending_artifact_msg: dict[int, tuple] = {}

# Хранит message_id экрана статуса перед оплатой: uid -> (chat_id, message_id, tier)
_pending_status_msg: dict[int, tuple] = {}

# Хранит message_id экрана зелий перед оплатой: uid -> (chat_id, message_id)
_pending_potion_msg: dict[int, tuple] = {}

# Хранит message_id экрана доната перед оплатой: uid -> (chat_id, message_id, pkg_key)
_pending_donate_msg: dict[int, tuple] = {}

# Защита от повторной обработки одного charge_id (replay-attack)
_processed_charge_ids: set[str] = set()

# Ожидание ввода промокода: uid -> True
_promo_pending: dict[int, bool] = {}

# Ожидание ввода суммы вклада: uid -> dep_key
_cdl_input_pending: dict[int, str] = {}
# Сообщение экрана ввода суммы: uid -> (chat_id, message_id)
_cdl_input_msg: dict[int, tuple] = {}

# Ожидание ввода цели для вызова на дуэль: uid -> True
_challenge_input_pending: dict[int, bool] = {}

# Ожидание подтверждения полного удаления данных игрока: admin_id -> target_uid
_pending_delete_bd: dict[int, int] = {}

EMOJI_DEPOSITS = "5427168083074628963"


async def _get_user_lock(uid: int) -> _asyncio.Lock:
    """Возвращает персональный Lock для пользователя uid."""
    async with _user_locks_mutex:
        if uid not in _user_locks:
            _user_locks[uid] = _asyncio.Lock()
        return _user_locks[uid]


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ОХОТЫ ----------

def _apply_xp(data: dict, xp_gain: int):
    """
    Начисляет XP пользователю и повышает уровень если накоплено достаточно.
    Работает с любой формулой xp_for_level из miner.py.
    """
    from miner import xp_for_level, MAX_LEVEL
    data["xp"] = data.get("xp", 0) + xp_gain
    # Повышаем уровень пока XP >= порога
    while True:
        lvl = data.get("level", 1)
        if lvl >= MAX_LEVEL:
            # На максимальном уровне — обнуляем XP прогресс
            data["xp"]    = 0
            data["xp_max"] = xp_for_level(lvl)
            break
        xp_needed = xp_for_level(lvl)
        data["xp_max"] = xp_needed
        if data["xp"] >= xp_needed:
            data["xp"]    -= xp_needed
            data["level"]  = lvl + 1
            data["xp_max"] = xp_for_level(lvl + 1)
        else:
            break


async def _distribute_boss_rewards(killer_uid: int, damage_rewards: dict):
    """
    Начисляет монеты и XP всем участникам убийства босса кроме убийцы
    (убийца получил награду уже внутри attack_boss).
    Сохраняет каждого пользователя в БД.

    Асинхронная версия: использует aio_get_user/aio_save_user (обёртки
    над старыми синхронными get_user/save_user через asyncio.to_thread),
    поэтому работа со старой БД (schema, файл, функции) не меняется —
    меняется только то, что вызовы не блокируют event loop.
    """
    from database import aio_get_user, aio_save_user
    for uid_str, (coins, xp) in damage_rewards.items():
        try:
            uid = int(uid_str)
        except ValueError:
            continue
        if uid == killer_uid:
            continue  # убийца уже получил всё в attack_boss
        u = await aio_get_user(uid)
        if not u:
            continue
        # Бонус за @TGStellarr_bot в bio — у каждого участника свой флаг,
        # поэтому множитель считаем персонально по его же данным `u`.
        try:
            from bio_bonus import get_bio_bonus_multiplier as _bio_part_mult
            coins = int(coins * _bio_part_mult(u))
        except Exception:
            pass
        u["balance"] = u.get("balance", 0) + coins
        u["ref_income"] = u.get("ref_income", 0) + coins
        _apply_xp(u, xp)
        await aio_save_user(uid, u)
        # Уведомление участнику
        try:
            from miner import COIN as _COIN_ICON
            _notif = (
                f'<tg-emoji emoji-id="5438496463044752972">💰</tg-emoji> '
                f'<b>Награда за участие в убийстве босса!</b>\n\n'
                f'<blockquote>'
                f'<tg-emoji emoji-id="5199552030615558774">💰</tg-emoji> <b>Монеты: +{format_amount(coins)}</b>\n'
                f'<tg-emoji emoji-id="5341498088408234504">✨</tg-emoji> <b>XP: +{format_amount(xp)}</b>'
                f'</blockquote>'
            )
            import asyncio as _aio
            _aio.ensure_future(bot.send_message(uid, _notif, parse_mode="HTML"))
        except Exception:
            pass


# ---------- ЭМОДЗИ ГЛАВНОГО МЕНЮ ----------
EMOJI_PROFILE  = "5906622905894050515"
EMOJI_STATS    = "5231200819986047254"
EMOJI_SHOP     = "5406683434124859552"
EMOJI_MINE     = "5197371802136892976"
EMOJI_HUNT     = "5424972470023104089"
EMOJI_STATUS   = "5438496463044752972"
EMOJI_EXCHANGE = "5402186569006210455"
EMOJI_PETS     = "5337047059180566409"
EMOJI_LEADERS  = "5440539497383087970"
EMOJI_SETTINGS = "5341715473882955310"

# Кастомная монета (используется в сообщениях кланов вместо обычного 🪙)
_COIN = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'

def _back_btn(callback: str, label: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback, icon_custom_emoji_id=EMOJI_BACK)


def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎮 Меню" if lang == "ru" else "🎮 Menu", style="primary"),
        KeyboardButton(text="⚔️ Клан" if lang == "ru" else "⚔️ Clan", style="primary"),
        KeyboardButton(text="🏙 Город" if lang == "ru" else "🏙 City", style="primary"),
    )
    builder.row(
        KeyboardButton(text="🏆 Достижения" if lang == "ru" else "🏆 Achievements", style="primary"),
    )
    return builder.as_markup(resize_keyboard=True)


def main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_profile"),  callback_data="profile",    icon_custom_emoji_id=EMOJI_PROFILE),
        InlineKeyboardButton(text=t(lang, "btn_stats"),    callback_data="stats",      icon_custom_emoji_id=EMOJI_STATS),
        InlineKeyboardButton(text=t(lang, "btn_cases"),    callback_data="shop_cases", icon_custom_emoji_id="5442939099906325301"),
    )
    builder.row(InlineKeyboardButton(text=t(lang, "btn_mine"), callback_data="mine", icon_custom_emoji_id=EMOJI_MINE))
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_hunt"),   callback_data="hunt",   icon_custom_emoji_id=EMOJI_HUNT),
        InlineKeyboardButton(text=t(lang, "btn_status"), callback_data="status", icon_custom_emoji_id=EMOJI_STATUS),
    )
    builder.row(InlineKeyboardButton(text=t(lang, "btn_pets"), callback_data="pets", icon_custom_emoji_id=EMOJI_PETS))
    builder.row(InlineKeyboardButton(
        text=" Дуэли" if lang == "ru" else " Duels",
        callback_data="duel_main",
        icon_custom_emoji_id="5454014806950429357",
    ))
    builder.row(InlineKeyboardButton(
        text=" Вклады" if lang == "ru" else " Deposits",
        callback_data="cdl_main",
        icon_custom_emoji_id=EMOJI_DEPOSITS,
    ))
    builder.row(
        InlineKeyboardButton(text=t(lang, "btn_leaders"),  callback_data="leaders",  icon_custom_emoji_id=EMOJI_LEADERS),
        InlineKeyboardButton(text=t(lang, "btn_settings"), callback_data="settings", icon_custom_emoji_id=EMOJI_SETTINGS),
    )
    return builder.as_markup()


def profile_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=" Инвентарь" if lang == "ru" else " Inventory",
            callback_data="profile_inv",
            icon_custom_emoji_id="5445221832074483553"
        ),
        InlineKeyboardButton(
            text=" Друзья" if lang == "ru" else " Friends",
            callback_data="refs_main",
            icon_custom_emoji_id="5332724926216428039"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=" Промокод" if lang == "ru" else " Promo",
            callback_data="promo_input",
            icon_custom_emoji_id="5359664288241829619"
        ),
        InlineKeyboardButton(
            text=" Донат" if lang == "ru" else " Donate",
            callback_data="donate_main",
            icon_custom_emoji_id="5262643974912355126"
        ),
    )
    builder.row(_back_btn("back_to_menu", t(lang, "btn_back")))
    return builder.as_markup()


def back_button(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_back_btn("back_to_menu", t(lang, "btn_back")))
    return builder.as_markup()


def stars_confirm_keyboard(pick_key: str, page: int, invoice_url: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if invoice_url:
        builder.row(InlineKeyboardButton(
            text="Оплатить",
            url=invoice_url,
            icon_custom_emoji_id="5999336376342940892",
            style="success"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="Оплатить",
            callback_data=f"pick_pay_stars_{pick_key}",
            icon_custom_emoji_id="5999336376342940892",
            style="success"
        ))
    builder.row(InlineKeyboardButton(
        text="Мои звёзды",
        url="tg://stars/",
        icon_custom_emoji_id="5348570868752595928",
        style="primary"
    ))
    builder.row(_back_btn(f"pick_info_{pick_key}", "Назад"))
    return builder.as_markup()


def stars_confirm_text(p: dict) -> str:
    from miner import STAR, COIN, TIER_LABELS
    tier  = TIER_LABELS.get(p.get("tier", ""), "")
    return (
        f'<tg-emoji emoji-id="5197371802136892976">⭐</tg-emoji> <b>{p["name"]}</b>\n'
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<blockquote>'
        f'<tg-emoji emoji-id="5197269100878907942">⭐</tg-emoji><b>Тир: {tier}</b>\n'
        f'<tg-emoji emoji-id="5310278924616356636">⭐</tg-emoji><b>Ударов за кампанию: {format_amount(p["dig_min"])}–{format_amount(p["dig_max"])}</b>\n'
        f'<tg-emoji emoji-id="5445353829304387411">⭐</tg-emoji><b>Стоимость: {format_amount(p["cost_stars"])}</b> {STAR}'
        f'</blockquote>'
    )


SHOP_TEXT = '<blockquote><tg-emoji emoji-id="5406683434124859552">🛒</tg-emoji> <b>МАГАЗИН</b>\n\n<b>Выбери категорию:</b></blockquote>'


def shop_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Кейсы", callback_data="shop_cases",
        icon_custom_emoji_id="5442939099906325301"
    ))
    builder.row(_back_btn("back_to_menu", "Назад"))
    return builder.as_markup()


# ---------- КОМАНДЫ ----------

ADMIN_IDS = {8118184388}

GUIDE_URL = "https://telegra.ph/POLNOE-RUKOVODSTVO-POLZOVATELYA-06-24"


def guide_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📖 Открыть гайд",
        url=GUIDE_URL,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ПРИОРИТЕТНЫЙ ХЕНДЛЕР: состояния "ждём свободный текст от юзера"
#  (промокод / цель дуэли / сумма вклада / текст кланов / рассылка админа)
#
#  ВАЖНО: зарегистрирован ПЕРВЫМ, до всех текстовых алиасов команд ниже.
#  aiogram проверяет хендлеры в порядке регистрации и останавливается на
#  первом совпавшем фильтре — значит если бы этот блок стоял в конце (как
#  было раньше), любой ввод, случайно совпавший с зарезервированным словом
#  ("клан", "шахта", "профиль" и т.п.), перехватывался бы более ранним
#  хендлером-алиасом меню, а состояние ожидания ввода оставалось "висеть"
#  (для кланов — даже в БД, так как _klan_*_pending хранится в самой
#  записи юзера). Именно это приводило к тому, что часть заявок в клан
#  не отправлялась: если юзер вводил текст заявки, совпавший с командным
#  словом, вместо отправки заявки открывалось меню клана.
# ════════════════════════════════════════════════════════════

_MAIN_MENU_RESERVED_TEXTS = {
    "🎮 меню", "🎮 menu", "⚔️ клан", "⚔️ clan", "🏙 город", "🏙 city",
}


async def _has_pending_text_input(message: Message) -> bool:
    """True, если для этого юзера сейчас ожидается свободный текстовый ввод."""
    if not message.text or message.text.startswith("/"):
        return False
    # Кнопки постоянного reply-меню — это однозначная навигация, а не данные
    # для промокода/заявки/поиска и т.п. Не даём им "провалиться" в pending-ввод.
    if message.text.strip().lower() in _MAIN_MENU_RESERVED_TEXTS:
        return False
    uid = message.from_user.id
    if uid in ADMIN_IDS and is_in_rass(uid):
        return True
    if _promo_pending.get(uid):
        return True
    if _challenge_input_pending.get(uid):
        return True
    if uid in _cdl_input_pending:
        return True
    u = await aio_get_or_create_user(message.from_user)
    if any(k in u for k in _KLAN_PENDING_KEYS):
        return True
    return False


@dp.message(_has_pending_text_input)
async def handle_pending_text_input(message: Message):
    """Единая точка входа для всех состояний 'ждём текст от юзера'."""
    uid  = message.from_user.id
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)

    # ── Рассылка: FSM-ввод от админа ──
    if uid in ADMIN_IDS and is_in_rass(uid):
        if await rass_fsm_message(message, ADMIN_IDS):
            return

    # ── Ожидание ввода промокода ──
    if _promo_pending.pop(uid, False):
        promo_name = (message.text or "").strip()
        if promo_name and u.get("onboarded", True):
            lock = await _get_user_lock(uid)
            async with lock:
                u = await aio_get_or_create_user(message.from_user)
                ok, reason, amount = await activate_promo(promo_name, uid)
                if ok:
                    u["balance"] = u.get("balance", 0) + amount
                    u["promo_activations"] = u.get("promo_activations", 0) + 1
                    _ach_newly = check_achievements(u)
                    await aio_save_user(uid, u)
                    await _notify_ach(uid, u, _ach_newly)
                    await message.reply(promo_activate_text(amount, lang), parse_mode="HTML")
                else:
                    await message.reply(promo_error_text(reason, lang), parse_mode="HTML")
        return

    # ── Ожидание ввода цели вызова на дуэль ──
    if _challenge_input_pending.pop(uid, False):
        from database import aio_get_user_by_id_or_username as _find_ch
        target_raw = (message.text or "").strip().lstrip("@")
        if not target_raw:
            await message.reply(cmd_invite_usage_text(lang), parse_mode="HTML")
            return
        target = await _find_ch(target_raw)
        if not target:
            await message.reply(cmd_invite_not_found_text(lang), parse_mode="HTML")
            return
        if target["id"] == uid:
            await message.reply(cmd_invite_self_text(lang), parse_mode="HTML")
            return
        if target["id"] in _active_battles:
            await message.reply(cmd_invite_in_battle_text(lang), parse_mode="HTML")
            return
        target_name = _esc(target.get("first_name") or target.get("username") or str(target["id"]))
        # Создаём вызов (с учётом лимита в 10 вызовов одному игроку за 24 часа)
        if not create_challenge(uid, target["id"], target_name):
            secs = seconds_until_challenge_slot(uid, target["id"])
            await message.reply(cmd_invite_limit_text(target_name, secs, lang=lang), parse_mode="HTML")
            return
        # Уведомляем цель в ЛС
        try:
            _target_lang = get_lang(target)
            await bot.send_message(
                target["id"],
                challenge_invite_text(u, _target_lang),
                parse_mode="HTML",
                reply_markup=challenge_invite_keyboard(uid, _target_lang),
            )
        except Exception:
            await message.reply(
                cmd_invite_blocked_text(target_name, lang),
                parse_mode="HTML"
            )
            cancel_challenge(uid)
            return
        await message.reply(
            duel_challenge_sent_text(target_name, lang),
            parse_mode="HTML",
            reply_markup=duel_challenge_sent_keyboard(lang),
        )
        return

    # ── Ожидание ввода суммы для вклада ──
    if uid in _cdl_input_pending:
        dep_key  = _cdl_input_pending.pop(uid)   # сразу сбрасываем — больше не ждём
        msg_info = _cdl_input_msg.pop(uid, None)
        raw = (message.text or "").strip().replace(" ", "").replace("_", "")

        async def _cdl_edit(text: str, kb=None):
            """Редактирует бот-сообщение (окно ввода). НЕ удаляет сообщение юзера."""
            if msg_info:
                try:
                    await bot.edit_message_text(
                        text, chat_id=msg_info[0], message_id=msg_info[1],
                        parse_mode="HTML", reply_markup=kb
                    )
                    return
                except Exception as _e:
                    if "message is not modified" in str(_e).lower():
                        return
            # Если окно недоступно — шлём новое
            await bot.send_message(
                msg_info[0] if msg_info else message.chat.id,
                text, parse_mode="HTML", reply_markup=kb
            )

        if not raw.isdigit():
            await _cdl_edit(
                f'❌ <b>Некорректный ввод.</b>\nОткрой вклад снова и введи число.',
                cdl_input_keyboard(dep_key)
            )
            return

        amount = int(raw)
        dep    = _CDL_DEPOSITS_BY_KEY.get(dep_key)
        if dep is None:
            return

        lock = await _get_user_lock(uid)
        async with lock:
            u2  = await aio_get_or_create_user(message.from_user)
            bal = u2.get("balance", 0)
            if amount < dep["min"]:
                await _cdl_edit(
                    f'❌ <b>Минимум:</b> {format_amount(dep["min"])}\nОткрой вклад снова и введи сумму.',
                    cdl_input_keyboard(dep_key)
                )
                return
            if amount > bal:
                await _cdl_edit(
                    f'❌ <b>Не хватает монет.</b> Баланс: {format_amount(bal)}\nОткрой вклад снова и введи сумму.',
                    cdl_input_keyboard(dep_key)
                )
                return

        await _cdl_edit(
            cdl_confirm_text(dep_key, amount),
            cdl_confirm_keyboard(dep_key, amount)
        )
        return

    # ── Ожидающие текстовые вводы для системы кланов (поиск/создание/кик/
    #    депозит/вывод/заявка/привязка чата) ──
    if await _handle_klan_text_input(message, u):
        return


async def _clear_all_pending_inputs(uid: int, u: dict) -> None:
    """Сбрасывает все состояния 'ждём текст от юзера' (промокод / цель дуэли /
    сумма вклада / текстовые вводы кланов). Вызывается при явной навигации
    через постоянные reply-кнопки (Меню/Клан/Город), чтобы клик по ним не
    мог быть перепутан с ответом на предыдущий запрос ввода, и чтобы после
    такого клика pending-флаги не оставались висеть."""
    _promo_pending.pop(uid, None)
    _challenge_input_pending.pop(uid, None)
    _cdl_input_pending.pop(uid, None)
    _cdl_input_msg.pop(uid, None)
    if _clear_klan_pending(u):
        # Раньше здесь был прямой (блокирующий) save_user — уводим запись
        # в БД в отдельный поток, чтобы event loop не морозился на этой
        # одной из самых частых точек навигации (Меню/Клан/Город/Ачивки).
        await aio_save_user(uid, u)


@dp.message(Command("guide", "гайд", "Guide", "Гайд"))
@dp.message(_text_in("гайд", "guide", "/guide", "/гайд", "как играть", "/как играть"))
async def cmd_guide(message: Message):
    await message.answer(
        '<tg-emoji emoji-id="5334544901428229844">📖</tg-emoji> <b><i>Гайд для новых игроков!</i></b>\n',
        parse_mode="HTML",
        reply_markup=guide_keyboard(),
    )


@dp.message(Command("add"))
async def cmd_add_balance(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split()
    # /add <username|id> <сумма>
    if len(parts) != 3:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/add username|id сумма</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    try:
        amount = int(parts[2])
    except ValueError:
        await message.reply("❌ Сумма должна быть целым числом.", parse_mode="HTML")
        return

    # Поиск пользователя в БД
    from database import aio_get_user_by_id_or_username, aio_save_user as _save
    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    old_balance = found.get("balance", 0)
    new_balance = old_balance + amount
    if new_balance < 0:
        new_balance = 0  # не уходим в минус

    found["balance"] = new_balance
    await _save(found["id"], found)

    name   = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    action = "➕ Выдано" if amount >= 0 else "➖ Снято"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'

    await message.reply(
        f"✅ <b>Готово!</b>\n\n"
        f"<blockquote>👤 Игрок: <b>{name}</b> (<code>{found['id']}</code>)\n"
        f"{action}: <b>{format_amount(abs(amount))}</b> {coin}\n"
        f"Было: <b>{format_amount(old_balance)}</b> {coin}\n"
        f"Стало: <b>{format_amount(new_balance)}</b> {coin}</blockquote>",
        parse_mode="HTML"
    )


@dp.message(Command("getallart"))
async def cmd_getallart(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    from shop import _ARTIFACT_POOL, ARTIFACT_POOL_BY_KEY, get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier
    from database import aio_get_user, aio_get_user_by_id_or_username, aio_save_user as _save

    parts = message.text.strip().split()

    # Определяем целевого пользователя
    if len(parts) >= 2:
        # /getallart @username  или  /getallart 123456789
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        if not data:
            await message.reply(
                f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
                parse_mode="HTML",
            )
            return
        uid = data["id"]
    else:
        # без аргумента — выдаём себе
        uid  = message.from_user.id
        data = await aio_get_user(uid)
        if not data:
            await message.reply(
                "❌ Пользователь не найден в БД. Напиши /start сначала.",
                parse_mode="HTML",
            )
            return

    artifacts = data.setdefault("artifacts", [])
    already   = {e["key"] for e in artifacts}
    added     = []
    for a in _ARTIFACT_POOL:
        if a["key"] not in already:
            artifacts.append({"key": a["key"]})
            added.append(a)
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + len(added)
    await _save(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    name = _esc(data.get("first_name") or data.get("username") or str(uid))
    if added:
        lines  = "\n".join(f'<b>✅ {a["name"]} — {a["multiplier"]}×</b>' for a in added)
        status = f"<b>Добавлено: {len(added)} шт.</b>\n{lines}"
    else:
        status = "<b>Все артефакты уже были в коллекции.</b>"

    await message.reply(
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GETALLART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{status}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>',
        parse_mode="HTML",
    )


@dp.message(Command("updamage"))
async def cmd_updamage(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/updamage username|id</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    from database import aio_get_user_by_id_or_username, aio_save_user as _save
    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    current = found.get("infinite_dmg", False)
    found["infinite_dmg"] = not current
    await _save(found["id"], found)

    name = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    status = "✅ <b>Включён</b>" if found["infinite_dmg"] else "❌ <b>Выключен</b>"

    await message.reply(
        f'⚔️ <b>Бесконечный урон для {name}:</b> {status}',
        parse_mode="HTML"
    )


@dp.message(Command("checkmine"))
async def cmd_checkmine(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    from miner import PICKAXES, PICKAXES_ORDER, TIER_LABELS, fmt_time, calc_mine_progress
    from database import aio_get_user, aio_get_user_by_id_or_username

    parts = message.text.strip().split()

    # Определяем целевого пользователя: реплай > @username/id аргумент > себя
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
    elif len(parts) >= 2:
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
    else:
        uid  = message.from_user.id
        data = await aio_get_user(uid)

    if not data:
        await message.reply(
            "❌ Пользователь не найден в базе.\n"
            "Использование: <code>/checkmine @username</code> или <code>/checkmine id</code>, "
            "либо ответом (reply) на сообщение игрока.",
            parse_mode="HTML",
        )
        return

    name    = _esc(data.get("first_name") or data.get("username") or str(uid))
    owned   = data.get("owned_pickaxes", ["wood_1"])
    current = data.get("pickaxe", "wood_1")

    # Сортируем открытые кирки в порядке их появления в игре
    owned_sorted = [k for k in PICKAXES_ORDER if k in owned]

    lines = []
    for key in owned_sorted:
        p = PICKAXES.get(key)
        if not p:
            continue
        tier = TIER_LABELS.get(p.get("tier", ""), "")
        mark = "✅" if key == current else "▫️"
        lines.append(
            f"{mark} <b>{_esc(p['name'])}</b> {tier}\n"
            f"    ⛏ {p['dig_min']}–{p['dig_max']} за удар"
        )
    pickaxes_block = "\n".join(lines) if lines else "<i>Нет открытых кирок</i>"

    # Статус текущей добычи
    if data.get("mine_start"):
        prog = calc_mine_progress(data)
        if prog["finished"]:
            mine_status = "✅ <b>Добыча завершена, ждёт сбора</b>"
        else:
            mine_status = f"⏳ <b>Идёт добыча</b> — осталось {fmt_time(prog['time_left'])}"
    else:
        mine_status = "⛔️ <b>Шахта не запущена</b>"

    await message.reply(
        f'⛏ <b>CHECKMINE</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{mine_status}</blockquote>\n\n'
        f'<b>Открытые кирки ({len(owned_sorted)}/{len(PICKAXES_ORDER)}):</b>\n'
        f'<blockquote>{pickaxes_block}</blockquote>',
        parse_mode="HTML",
    )


@dp.message(Command("deletebd"))
async def cmd_deletebd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    from database import aio_get_user, aio_get_user_by_id_or_username

    parts = message.text.strip().split()

    # Определяем целевого пользователя: реплай > @username/id аргумент
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
    elif len(parts) >= 2:
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
    else:
        await message.reply(
            "❌ Не указан игрок.\n"
            "Использование: <code>/deletebd @username</code> или <code>/deletebd id</code>, "
            "либо ответом (reply) на сообщение игрока.",
            parse_mode="HTML",
        )
        return

    if not data:
        await message.reply("❌ Пользователь не найден в базе.", parse_mode="HTML")
        return

    if uid in ADMIN_IDS:
        await message.reply("❌ Нельзя удалить данные администратора этой командой.", parse_mode="HTML")
        return

    name = _esc(data.get("first_name") or data.get("username") or str(uid))
    _pending_delete_bd[message.from_user.id] = uid

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить всё", callback_data=f"delbd_yes:{uid}")
    kb.button(text="❌ Отмена", callback_data="delbd_no")
    kb.adjust(1)

    await message.reply(
        f'⚠️ <b>ВНИМАНИЕ — ПОЛНОЕ УДАЛЕНИЕ ДАННЫХ</b>\n\n'
        f'<blockquote>Игрок: <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'Будут стёрты <b>все</b> данные: баланс, шахта, кирки, питомцы, '
        f'оружие/бои, статус, инвентарь, достижения и весь прогресс.\n'
        f'Игрок начнёт игру полностью заново, как новый пользователь.\n\n'
        f'<b>Это действие необратимо!</b></blockquote>',
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


def _delete_user_row_sync(uid: int):
    """
    Синхронная часть удаления игрока — выполняется ТОЛЬКО через
    asyncio.to_thread (см. вызов в cb_deletebd_confirm), никогда напрямую
    из event loop. Те же PRAGMA, что и в остальных местах файла/database.py,
    чтобы соединение вело себя предсказуемо (WAL + busy_timeout).
    """
    import sqlite3 as _sq
    _conn = _sq.connect("tgstellar.db", timeout=30)
    try:
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=30000")
        _conn.execute("DELETE FROM users WHERE uid=?", (uid,))
        _conn.commit()
    finally:
        # `with _conn:` управляет только транзакцией (commit/rollback), но
        # НЕ закрывает соединение — close() обязателен, иначе fd на
        # tgstellar.db копятся и БД начинает "залипать" (database is locked).
        _conn.close()


@dp.callback_query(F.data.startswith("delbd_yes:"))
async def cb_deletebd_confirm(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа.", show_alert=True)
        return

    target_uid = int(call.data.split(":", 1)[1])

    # Подтверждение должно приходить именно от админа, запустившего команду,
    # и совпадать с сохранённой целью — защита от гонок/устаревших кнопок
    if _pending_delete_bd.get(call.from_user.id) != target_uid:
        await call.answer("Запрос устарел, повтори команду заново.", show_alert=True)
        return
    _pending_delete_bd.pop(call.from_user.id, None)

    # Best-effort: аккуратно выходим из клана, чтобы не оставить "мёртвого" участника
    # (get_member/leave_clan здесь — это aio_-обёртки, импортированные под
    # этими именами в шапке файла; отдельный локальный импорт НЕ нужен и раньше
    # маскировал их, подставляя синхронные версии из klan.py — тогда await
    # падал с ошибкой уже ПОСЛЕ того, как sqlite3-запрос успел выполниться
    # прямо в event loop, блокируя всех пользователей бота.)
    try:
        if await get_member(target_uid):
            await leave_clan(target_uid)
    except Exception as _e:
        print(f"[deletebd] leave_clan error: {_e}")

    # Полное удаление записи игрока — при следующем /start он создастся заново с нуля.
    # Синхронный sqlite-доступ выполняется в отдельном потоке (asyncio.to_thread),
    # чтобы не блокировать event loop для всех остальных пользователей, как и
    # в остальных местах файла (см. _cdl_payout_apply_sync).
    try:
        await asyncio.to_thread(_delete_user_row_sync, target_uid)
    except Exception as _e:
        await call.message.edit_text(f"❌ Ошибка при удалении: {_e}")
        return

    await call.message.edit_text(
        f'🗑 <b>Данные игрока <code>{target_uid}</code> полностью удалены.</b>\n\n'
        f'<blockquote>При следующем /start он начнёт игру с чистого листа.</blockquote>',
        parse_mode="HTML",
    )
    await call.answer("Удалено.")


@dp.callback_query(F.data == "delbd_no")
async def cb_deletebd_cancel(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    _pending_delete_bd.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Удаление отменено.")
    await call.answer()


@dp.message(Command("giveart"))
async def cmd_giveart(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    from shop import _ARTIFACT_POOL, get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier
    from database import aio_get_user, aio_get_user_by_id_or_username, aio_save_user as _save

    text = message.text.strip()

    # Определяем целевого пользователя и название артефакта:
    # /giveart @username Название артефакта
    # /giveart 123456789 Название артефакта
    # ответом (reply) на игрока: /giveart Название артефакта
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
        rest = text.split(maxsplit=1)
        name_query = rest[1] if len(rest) >= 2 else ""
    else:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply(
                "❌ Использование: <code>/giveart @username Название артефакта</code>\n"
                "или <code>/giveart id Название артефакта</code>,\n"
                "либо ответом (reply) на игрока: <code>/giveart Название артефакта</code>.",
                parse_mode="HTML",
            )
            return
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
        name_query = parts[2]

    if not data:
        await message.reply("❌ Пользователь не найден в базе.", parse_mode="HTML")
        return

    name_query = name_query.strip()
    if not name_query:
        await message.reply("❌ Не указано название артефакта.", parse_mode="HTML")
        return

    # Поиск артефакта: точное совпадение по RU/EN названию или ключу,
    # затем — частичное совпадение (по подстроке)
    q = name_query.lower()
    found = None
    for a in _ARTIFACT_POOL:
        if q in (a["name"].lower(), a.get("name_en", "").lower(), a["key"].lower()):
            found = a
            break
    if not found:
        for a in _ARTIFACT_POOL:
            if q in a["name"].lower() or q in a.get("name_en", "").lower():
                found = a
                break

    if not found:
        listing = "\n".join(f"• {a['name']} ({a.get('name_en', '')})" for a in _ARTIFACT_POOL)
        await message.reply(
            f"❌ Артефакт «{_esc(name_query)}» не найден.\n\n"
            f"<b>Доступные артефакты:</b>\n{_esc(listing)}",
            parse_mode="HTML",
        )
        return

    artifacts = data.setdefault("artifacts", [])
    name  = _esc(data.get("first_name") or data.get("username") or str(uid))

    if any(entry["key"] == found["key"] for entry in artifacts):
        await message.reply(
            f'⚠️ У игрока <b>{name}</b> (<code>{uid}</code>) артефакт '
            f'«<b>{_esc(found["name"])}</b>» уже есть. Повторно не выдаю.',
            parse_mode="HTML",
        )
        return

    artifacts.append({"key": found["key"]})
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1
    await _save(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    art_name_line = f'{found["name"]} ({found.get("name_en", "")}) — {found["multiplier"]}×'

    await message.reply(
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GIVEART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote><b>✅ Выдан артефакт:</b>\n{_esc(art_name_line)}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>',
        parse_mode="HTML",
    )


@dp.message(Command("addalldiamond"))
async def cmd_addalldiamond(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/addalldiamond сумма</code>\n"
            "<i>Например: /addalldiamond 500 или /addalldiamond 1к</i>",
            parse_mode="HTML"
        )
        return

    amount = _parse_amount(parts[1])
    if amount is None or amount == 0:
        await message.reply("❌ Не удалось распознать сумму.", parse_mode="HTML")
        return

    from city import aio_add_crystals_to_all
    count = await aio_add_crystals_to_all(amount)

    sign = "+" if amount > 0 else ""
    await message.reply(
        f"💎 <b>Кристаллы начислены!</b>\n"
        f"Всем игрокам города ({count}) выдано <b>{sign}{amount}</b> кристаллов.",
        parse_mode="HTML"
    )


@dp.message(Command("getstatus"))
async def cmd_getstatus(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.strip().split()
    # /getstatus <username|id> <vip|pr>
    if len(parts) != 3 or parts[2].lower() not in ("vip", "pr", "premium"):
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/getstatus username|id vip|pr</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    tier_arg   = parts[2].lower()
    tier       = "premium" if tier_arg in ("pr", "premium") else "vip"

    from database import aio_get_user_by_id_or_username, aio_save_user as _save
    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    ok, msg = activate_status(found, tier)
    if ok:
        await _save(found["id"], found)

    name  = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    label = "VIP" if tier == "vip" else "Premium"
    await message.reply(
        f'✅ <b>Статус {label} выдан!</b>\n\n'
        f'<blockquote>👤 Игрок: <b>{name}</b> (<code>{found["id"]}</code>)\n'
        f'📅 Срок: <b>30 дней</b></blockquote>',
        parse_mode="HTML"
    )


@dp.message(Command("addcheck"))
async def cmd_addcheck(message: Message):
    """/addcheck <сумма> <кол-во активаций>"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.reply(
            "❌ Формат: <code>/addcheck сумма кол-во</code>\n"
            "Пример: <code>/addcheck 10000 10</code>",
            parse_mode="HTML"
        )
        return
    try:
        amount = int(parts[1])
        uses   = int(parts[2])
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    bot_me = await bot.get_me()
    code   = await create_check(amount, uses)
    link   = f"https://t.me/{bot_me.username}?start=check_{code}"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    await message.reply(
        f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Чек создан!</b>\n\n'
        f'<blockquote>'
        f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
        f'<tg-emoji emoji-id="5330320040883411678">🎁</tg-emoji> <b>Активаций:</b> {uses}\n'
        f'<tg-emoji emoji-id="5444856076954520455">🔗</tg-emoji> <b>Код:</b> <code>{code}</code>'
        f'</blockquote>\n\n'
        f'<b><tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji>Ссылка:</b> {link}',
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@dp.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
    """/addpromo <название> <сумма> <кол-во активаций>"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 4:
        await message.reply(
            "❌ Формат: <code>/addpromo название сумма кол-во</code>\n"
            "Пример: <code>/addpromo stars 1000 10</code>",
            parse_mode="HTML"
        )
        return
    name = parts[1]
    try:
        amount = int(parts[2])
        uses   = int(parts[3])
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    ok, reason = await create_promo(name, amount, uses)
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    if ok:
        await message.reply(
            f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Промокод создан!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5444856076954520455">🎁</tg-emoji> <b>Код:</b> <code>{name}</code>\n'
            f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
            f'<tg-emoji emoji-id="5330320040883411678">🎟</tg-emoji> <b>Активаций:</b> {uses}'
            f'</blockquote>',
            parse_mode="HTML",
        )
    else:
        await message.reply(
            f'❌ Промокод <code>{name}</code> уже существует.',
            parse_mode="HTML"
        )


@dp.message(Command("checks"))
async def cmd_list_checks(message: Message):
    """Список активных чеков."""
    if message.from_user.id not in ADMIN_IDS:
        return
    items = await list_checks()
    if not items:
        await message.reply("📭 Чеков нет.", parse_mode="HTML")
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{c["code"]}</code> — {coin} {format_amount(c["amount"])} · [{c["uses_left"]}/{c["uses_total"]}]'
        for c in items
    ]
    await message.reply(
        f'<b>📋 Чеки ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML"
    )


@dp.message(Command("promos"))
async def cmd_list_promos(message: Message):
    """Список промокодов."""
    if message.from_user.id not in ADMIN_IDS:
        return
    items = await list_promos()
    if not items:
        await message.reply("📭 Промокодов нет.", parse_mode="HTML")
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{p["name"]}</code> — {coin} {format_amount(p["amount"])} · [{p["uses_left"]}/{p["uses_total"]}]'
        for p in items
    ]
    await message.reply(
        f'<b>📋 Промокоды ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML"
    )


@dp.message(Command("delcheck"))
async def cmd_delcheck(message: Message):
    """Удалить чек. /delcheck код"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/delcheck код</code>", parse_mode="HTML")
        return
    ok = await delete_check(parts[1])
    await message.reply("✅ Чек удалён." if ok else "❌ Чек не найден.", parse_mode="HTML")


@dp.message(Command("delpromo"))
async def cmd_delpromo(message: Message):
    """Удалить промокод. /delpromo название"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/delpromo название</code>", parse_mode="HTML")
        return
    ok = await delete_promo(parts[1])
    await message.reply("✅ Промокод удалён." if ok else "❌ Промокод не найден.", parse_mode="HTML")


# ── /rass — рассылка ─────────────────────────────────────────────────

@dp.message(Command("rass"))
async def cmd_rass(message: Message):
    await rass_start(message, ADMIN_IDS)


@dp.message(Command("rass_cancel"))
async def cmd_rass_cancel(message: Message):
    await rass_cancel(message, ADMIN_IDS)


# ── /daily, "бонус", "bonus" — теперь это статус bio-бонуса ──────────
#  Старая логика (случайные монеты раз в 24ч) убрана полностью.
#  Команда больше НИЧЕГО не выдаёт — она только проверяет и показывает,
#  активен ли бонус за @TGStellarr_bot в описании профиля.
#  Сама проверка идёт напрямую в Telegram (bot.get_chat) — то есть
#  подделать статус через клиент нельзя, ответ всегда авторитетный.

_COIN_DAILY = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'

@dp.message(Command("daily", "бонус", "bonus", ignore_case=True))
@dp.message(_text_in("daily", "бонус", "bonus"))
async def cmd_daily(message: Message):
    uid  = message.from_user.id
    lock = await _get_user_lock(uid)
    async with lock:
        u = await aio_get_or_create_user(message.from_user)

        if not u.get("onboarded", True):
            return  # онбординг ещё не пройден — молча игнорируем

        from bio_bonus import (
            refresh_bio_bonus, get_bio_bonus_multiplier,
            BOT_USERNAME, BIO_BONUS_MULTIPLIER,
        )

        # Форсируем свежую проверку прямо сейчас (не ждём фоновый цикл раз
        # в 30 мин) — так пользователь сразу видит актуальный статус после
        # того, как вписал юзернейм в bio. Если Telegram API недоступен
        # (флуд-контроль/ошибка) — просто покажем последний известный флаг,
        # ничего не ломаем.
        ok = await refresh_bio_bonus(bot, uid, u)
        if ok:
            await aio_save_user(uid, u)

        active = get_bio_bonus_multiplier(u) > 1.0
        lang   = get_lang(u)
        mult_str = str(BIO_BONUS_MULTIPLIER).rstrip("0").rstrip(".")

        _OK    = '<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji>'
        _GEM   = '<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji>'
        _DMG   = '<tg-emoji emoji-id="5373173798633752502">⚔️</tg-emoji>'
        _TROPHY = '<tg-emoji emoji-id="5449683594425410231">🏆</tg-emoji>'
        _TIMER = '<tg-emoji emoji-id="5440621591387980068">⏱</tg-emoji>'
        _LOCK  = '<tg-emoji emoji-id="5240241223632954241">🔒</tg-emoji>'
        _STAR  = '<tg-emoji emoji-id="5262643974912355126">✨</tg-emoji>'

        if active:
            if lang == "en":
                text = (
                    f'{_COIN_DAILY} <b>BIO BONUS — ACTIVE</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'{_OK} <b><i>@{BOT_USERNAME}</i></b> <i>found in your profile bio</i>\n\n'
                    f'{_GEM} <b><i>+{mult_str}× to all ore mining loot</i></b>\n'
                    f'{_DMG} <b><i>+{mult_str}× to boss damage</i></b>\n'
                    f'{_TROPHY} <b><i>+{mult_str}× to boss kill rewards</i></b>'
                    f'</blockquote>\n\n'
                    f'{_TIMER} <i>Rechecked automatically every 30 minutes — '
                    f'keep the tag in your bio and the bonus stays with you.</i>'
                )
            else:
                text = (
                    f'{_COIN_DAILY} <b>BIO-БОНУС — АКТИВЕН</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'{_OK} <b><i>@{BOT_USERNAME}</i></b> <i>найден в описании профиля</i>\n\n'
                    f'{_GEM} <b><i>+{mult_str}× ко всей добыче руды</i></b>\n'
                    f'{_DMG} <b><i>+{mult_str}× к урону по боссу</i></b>\n'
                    f'{_TROPHY} <b><i>+{mult_str}× к награде за убийство босса</i></b>'
                    f'</blockquote>\n\n'
                    f'{_TIMER} <i>Статус обновляется автоматически каждые 30 минут — '
                    f'держи метку в bio, и бонус останется с тобой.</i>'
                )
        else:
            if lang == "en":
                text = (
                    f'{_LOCK} <b>BIO BONUS — NOT ACTIVE</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<b><i>1.</i></b> <i>Open Telegram → Settings → Edit Profile</i>\n'
                    f'<b><i>2.</i></b> <i>In the "Bio" field add:</i> <code>@{BOT_USERNAME}</code>\n'
                    f'<b><i>3.</i></b> <i>Save changes</i>'
                    f'</blockquote>\n\n'
                    f'{_STAR} <b><i>Reward for it:</i></b>\n'
                    f'{_GEM} <i>+{mult_str}× ore mining loot</i>\n'
                    f'{_DMG} <i>+{mult_str}× boss damage</i>\n'
                    f'{_TROPHY} <i>+{mult_str}× boss kill rewards</i>\n\n'
                    f'{_TIMER} <i>Checked automatically every 30 minutes — or just '
                    f'send /daily again right after editing your bio.</i>'
                )
            else:
                text = (
                    f'{_LOCK} <b>BIO-БОНУС — НЕ АКТИВЕН</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<b><i>1.</i></b> <i>Открой Telegram → Настройки → Изменить профиль</i>\n'
                    f'<b><i>2.</i></b> <i>В поле «О себе» (bio) добавь:</i> <code>@{BOT_USERNAME}</code>\n'
                    f'<b><i>3.</i></b> <i>Сохрани изменения</i>'
                    f'</blockquote>\n\n'
                    f'{_STAR} <b><i>Награда за это:</i></b>\n'
                    f'{_GEM} <i>+{mult_str}× к добыче руды</i>\n'
                    f'{_DMG} <i>+{mult_str}× к урону по боссу</i>\n'
                    f'{_TROPHY} <i>+{mult_str}× к награде за убийство босса</i>\n\n'
                    f'{_TIMER} <i>Проверяется автоматически каждые 30 минут — либо '
                    f'просто пришли /daily ещё раз сразу после правки bio.</i>'
                )

        await message.reply(text, parse_mode="HTML")


async def _send_onboarding_step(message: Message, uid: int) -> bool:
    """
    Показывает очередной шаг онбординга нового пользователя:
    1) капча (если не пройдена / если есть блок)
    2) выбор языка (когда капча уже пройдена)
    Возвращает True всегда — обработку сообщения нужно прекратить.
    """
    # 1) Проверяем, не заблокирован ли пользователь капчей
    blocked, secs_left = await is_captcha_blocked(uid)
    if blocked:
        mins = (secs_left + 59) // 60
        await message.answer(
            captcha_blocked_text(mins),
            parse_mode="HTML",
        )
        return True

    # 2) Капча ещё не пройдена → показываем (или повторяем) вопрос
    if not await is_captcha_passed(uid):
        state = await create_captcha(uid)
        sent = await message.answer(
            captcha_start_text(state["question"]),
            parse_mode="HTML",
        )
        await set_captcha_msg(uid, sent.chat.id, sent.message_id)
        return True

    # 3) Капча пройдена, но язык ещё не выбран → выбор языка
    await message.answer(
        lang_choose_text("ru"),
        parse_mode="HTML",
        reply_markup=lang_choose_keyboard_start(),
    )
    return True


@dp.message(Command("start"))
@dp.message(Command("menu", "меню"))
@dp.message(_text_in("меню", "menu"))
async def send_welcome(message: Message):
    from database import aio_load_raw
    uid          = message.from_user.id
    existing     = await aio_load_raw(uid)
    is_brand_new = existing is None

    # ── Определяем пригласителя из deep-link (?start=ref_XXXXX) ──
    args        = message.text.split()
    inviter_uid = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            inviter_uid = int(args[1].split("_")[1])
            if inviter_uid == uid:
                inviter_uid = None  # нельзя пригласить себя
        except (ValueError, IndexError):
            pass

    # Создаём/получаем пользователя в БД бота
    u = await aio_get_or_create_user(message.from_user)
    await aio_track_user(uid)

    # Регистрируем в реф. таблице — только для совсем новых пользователей,
    # чтобы повторные /start не теряли и не путали данные о пригласителе
    if is_brand_new:
        await register_referral(uid, inviter_uid)

    lang = get_lang(u)

    # ── Активация чека через deep-link: /start check_XXXXXXXX ──
    # Чек активируется СРАЗУ при запуске, ДО капчи/онбординга —
    # не важно, прошёл пользователь капчу или нет.
    if len(args) > 1 and args[1].startswith("check_"):
        check_code = args[1][6:]
        lock = await _get_user_lock(uid)
        async with lock:
            u = await aio_get_or_create_user(message.from_user)
            ok, reason, amount = await activate_check(check_code, uid)
            if ok:
                u["balance"] = u.get("balance", 0) + amount
                _ach_newly = check_achievements(u)
                await aio_save_user(uid, u)
                await _notify_ach(uid, u, _ach_newly)
                await message.answer(check_activate_text(amount, lang), parse_mode="HTML")
            else:
                await message.answer(check_error_text(reason, lang), parse_mode="HTML")

        # После активации чека — если онбординг (капча → язык) ещё не пройден,
        # продолжаем его как обычно.
        if not u.get("onboarded", True):
            await _send_onboarding_step(message, uid)
        return

    # ── Новый пользователь → онбординг: капча → язык → меню ──
    if not u.get("onboarded", True):
        if message.chat.type == "private":
            await _send_onboarding_step(message, uid)
        return

    # ── Уже онбордженный пользователь → главное меню ──
    # Reply-клавиатуру (кнопки Menu/Clan) показываем только в личке
    if message.chat.type == "private":
        await message.answer(
            "🎮",
            reply_markup=main_reply_keyboard(lang),
        )
    await message.reply(
        t(lang, "welcome"),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard(lang),
    )


@dp.message(_text_in("🎮 Меню", "🎮 Menu"), F.chat.type == "private")
async def reply_btn_menu(message: Message):
    from database import aio_get_or_create_user as _gou
    uid  = message.from_user.id
    u    = await _gou(message.from_user)
    lang = get_lang(u)
    await aio_track_user(uid)
    await _clear_all_pending_inputs(uid, u)

    # Если онбординг (капча/язык) ещё не пройден — продолжаем его
    if not u.get("onboarded", True):
        await _send_onboarding_step(message, uid)
        return

    await message.reply(
        t(lang, "welcome"),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard(lang),
    )


@dp.message(_text_in("⚔️ Клан", "⚔️ Clan"), F.chat.type == "private")
@dp.message(Command("klan", "клан"))
@dp.message(_text_in("клан", "клан-", "klan", "klan-"))
async def reply_btn_clan(message: Message):
    from database import aio_get_or_create_user as _gou
    uid  = message.from_user.id
    u    = await _gou(message.from_user)
    lang = get_lang(u)
    await aio_track_user(uid)

    if await _check_onboarded(message, u): return
    await _clear_all_pending_inputs(uid, u)

    await message.reply(
        await klan_main_text(lang),
        parse_mode="HTML",
        reply_markup=await klan_main_keyboard(uid, lang),
    )


@dp.message(_text_in("🏙 Город", "🏙 City"), F.chat.type == "private")
async def reply_btn_city(message: Message):
    from database import aio_get_or_create_user as _gou
    uid  = message.from_user.id
    u    = await _gou(message.from_user)
    await aio_track_user(uid)

    if await _check_onboarded(message, u): return
    await _clear_all_pending_inputs(uid, u)

    await cmd_city_profile(message)


@dp.message(_text_in("🏆 Достижения", "🏆 Achievements"), F.chat.type == "private")
async def reply_btn_achievements(message: Message):
    from database import aio_get_or_create_user as _gou
    uid = message.from_user.id
    u   = await _gou(message.from_user)
    await aio_track_user(uid)

    if await _check_onboarded(message, u): return
    await _clear_all_pending_inputs(uid, u)

    await cmd_achievements(message)


# ---------- КОМАНДЫ-АЛИАСЫ ДЛЯ РАЗДЕЛОВ ----------

async def _check_onboarded(message: Message, u: dict) -> bool:
    """Возвращает True если нужно прервать (онбординг не пройден).
    В групповых чатах онбординг не показываем — только в личке."""
    if not u.get("onboarded", True):
        if message.chat.type == "private":
            await _send_onboarding_step(message, message.from_user.id)
            return True
    return False


@dp.message(Command("mine", "шахта", "добыча", "mining"))
@dp.message(_text_in("шахта", "mine", "добыча", "mining"))
async def cmd_mine(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        mine_text(u, lang),
        parse_mode="HTML",
        reply_markup=mine_keyboard(u, lang),
    )


@dp.message(Command("profile", "профиль", "prof", "я"))
@dp.message(_text_in("профиль", "profile", "prof", "я"))
async def cmd_profile(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        profile_text(u),
        parse_mode="HTML",
        reply_markup=profile_keyboard(lang),
    )


@dp.message(Command("донат", "донаты", "donate", "donates"))
@dp.message(_text_in("донат", "донаты", "donate", "donates"))
async def cmd_donate(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        donate_main_text(lang),
        parse_mode="HTML",
        reply_markup=donate_main_keyboard(lang),
    )


@dp.message(Command("hunt", "охота", "boss", "босс"))
@dp.message(_text_in("охота", "hunt", "boss", "босс"))
async def cmd_hunt(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    # hunt_main_text/keyboard читают состояние боссов из БД (get_all_slots →
    # 5x _load_slot, может ещё и писать при респавне) — уводим в отдельный
    # поток, чтобы не морозить event loop для всех при каждом /hunt.
    _txt, _kb = await asyncio.to_thread(
        lambda: (hunt_main_text(u, lang), hunt_main_keyboard(u, lang))
    )
    await message.reply(
        _txt,
        parse_mode="HTML",
        reply_markup=_kb,
    )


@dp.message(Command("арс", "арсенал", "arsenal", "ars"))
@dp.message(_text_in("арс", "арсенал", "arsenal", "ars"))
async def cmd_arsenal(message: Message):
    u   = await aio_get_or_create_user(message.from_user)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    cleanup_expired_rentals(u)
    _ach_newly = check_achievements(u)
    await aio_save_user(message.from_user.id, u)
    await message.reply(
        arsenal_main_text(u),
        parse_mode="HTML",
        reply_markup=arsenal_main_keyboard(u),
    )
    await _notify_ach(message.from_user.id, u, _ach_newly)


@dp.message(Command("достижения", "ачивки", "achievements", "ach", "ач", "достижени", "дс"))
@dp.message(_text_in("достижения", "ачивки", "achievements", "ach", "ач", "достижени", "дс"))
async def cmd_achievements(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u):
        return
    _ach_newly = check_achievements(u)
    await aio_save_user(message.from_user.id, u)
    # achievements_menu_text читает глобальные счётчики открытий из
    # отдельной achievements_stats.db синхронно — уводим в поток.
    _ach_menu_txt = await asyncio.to_thread(achievements_menu_text, u, lang)
    await message.reply(
        _ach_menu_txt,
        parse_mode="HTML",
        reply_markup=achievements_menu_keyboard(lang),
    )
    await _notify_ach(message.from_user.id, u, _ach_newly)



@dp.message(Command("pets", "питомцы", "pet", "питомец"))
@dp.message(_text_in("питомцы", "pets", "питомец", "pet"))
async def cmd_pets(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        pets_main_text(u, lang),
        parse_mode="HTML",
        reply_markup=pets_main_keyboard(u, 0, lang),
    )


@dp.message(Command("cases", "кейсы", "case", "кейс", "shop"))
@dp.message(_text_in("кейсы", "cases", "кейс", "case", "shop"))
async def cmd_cases(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        cases_shop_text(u, lang),
        parse_mode="HTML",
        reply_markup=cases_shop_keyboard(lang),
    )


@dp.message(Command("ref", "реф", "рефералы", "refs", "friends", "друзья", "invite", "пригласить"))
@dp.message(_text_in("реф", "ref", "рефералы", "refs", "friends", "друзья", "invite", "пригласить"))
async def cmd_refs(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    bot_me = await bot.get_me()
    _refs_txt = await refs_main_text(message.from_user.id, bot_me.username, lang)
    await message.reply(
        _refs_txt,
        parse_mode="HTML",
        reply_markup=refs_main_keyboard(bot_me.username, message.from_user.id, lang),
    )


@dp.message(Command("reftop", "topref", "топреф", "рефтоп"))
@dp.message(_text_in("reftop", "topref", "топреф", "рефтоп"))
async def cmd_reftop(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    _reftop_txt = await reftop_text("alltime", message.from_user.id, lang)
    await message.reply(
        _reftop_txt,
        parse_mode="HTML",
        reply_markup=reftop_keyboard("alltime", lang),
    )


@dp.message(Command("stats", "статы", "статистика", "stat", "онлайн"))
@dp.message(_text_in("статистика", "статы", "stats", "stat", "онлайн"))
async def cmd_stats(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        await aio_stats_text(lang),
        parse_mode="HTML",
        reply_markup=stats_keyboard(lang),
    )


@dp.message(Command("leaders", "лидеры", "top", "топ", "leaderboard"))
@dp.message(_text_in("лидеры", "leaders", "top", "топ", "leaderboard"))
async def cmd_leaders(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        await leaders_main_text(viewer_uid=message.from_user.id, lang=lang),
        parse_mode="HTML",
        reply_markup=leaders_main_keyboard(lang),
    )


@dp.message(Command("status", "статус", "vip", "premium"))
@dp.message(_text_in("статус", "status", "vip", "premium"))
async def cmd_status(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        status_main_text(u, lang),
        parse_mode="HTML",
        reply_markup=status_main_keyboard(u, lang),
    )


@dp.message(Command("settings", "настройки", "lang", "язык", "language"))
@dp.message(_text_in("настройки", "settings", "lang", "язык", "language"))
async def cmd_settings(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        settings_text(u),
        parse_mode="HTML",
        reply_markup=settings_keyboard(u),
    )


@dp.message(Command("cdl", "вклад", "вклады", "deposit", "deposits", "vklad", "vklady"))
@dp.message(_text_in("вклад", "вклады", "cdl", "deposit", "deposits", "vklad", "vklady"))
async def cmd_cdl(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return
    await message.reply(
        cdl_main_text(u),
        parse_mode="HTML",
        reply_markup=cdl_main_keyboard(message.from_user.id),
    )


@dp.message(Command("promo", "промо"))
async def cmd_promo(message: Message):
    """/promo <название> или /промо <название>"""
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    if await _check_onboarded(message, u): return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        _promo_pending[uid] = True
        await message.reply(promo_input_text(lang), parse_mode="HTML")
        return

    promo_name = parts[1].strip()
    lock = await _get_user_lock(uid)
    async with lock:
        u = await aio_get_or_create_user(message.from_user)
        ok, reason, amount = await activate_promo(promo_name, uid)
        if ok:
            u["balance"] = u.get("balance", 0) + amount
            u["promo_activations"] = u.get("promo_activations", 0) + 1
            _ach_newly = check_achievements(u)
            await aio_save_user(uid, u)
            await _notify_ach(uid, u, _ach_newly)
            await message.reply(promo_activate_text(amount, lang), parse_mode="HTML")
        else:
            await message.reply(promo_error_text(reason, lang), parse_mode="HTML")



# ── /gift /дать /пер — перевод баланса другому игроку ────────────────────────
# Форматы:
#   1) Ответ на сообщение + команда с суммой:
#      /gift 500   /дать 500   /пер 500   gift 500   дать 500   пер 500
#   2) Явное указание получателя:
#      /gift @username 500   /gift 123456789 500   gift @user 500   gift 123456789 500

def _fmt_full(n) -> str:
    """
    Полная запись числа с разделителями разрядов, без буквенных
    сокращений (K/M/B/...) — используется в команде передачи монет,
    чтобы игрок видел точную сумму: 1_000_000_000 -> "1 000 000 000",
    а не "1B".
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if n < 0 else ""
    return f"{sign}{abs(n):,}".replace(",", " ")


def _fmt_num(n) -> str:
    """
    Сокращённая запись числа буквенными суффиксами — единый стиль со всем
    проектом (database.py -> format_amount/fmt, miner.py -> _fmt_num):
      999 -> "999", 1500 -> "1.5K", 100000 -> "100K", 2300000 -> "2.3M",
      1500000000 -> "1.5B", 10**12 -> "1T", 10**15 -> "1Qa", 10**18 -> "1Qi", ...
    В отличие от _fmt_full (точная сумма с пробелами, используется для самого
    факта перевода/баланса), применяется там, где нужна быстрочитаемая
    приблизительная величина — например, суточный лимит перевода.
    Локальная копия во избежание циклического импорта с database.py.
    """
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)

    sign = "-" if n < 0 else ""
    n = abs(n)

    if n < 1000:
        if n == int(n):
            return f"{sign}{int(n)}"
        return f"{sign}{n:.1f}"

    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]
    idx = 0
    val = n
    while val >= 1000:
        val /= 1000
        idx += 1

    val = int(val * 10) / 10

    if idx < len(suffixes):
        suffix = suffixes[idx]
    else:
        suffix = f"Dc{idx - len(suffixes) + 2}"

    if val == int(val):
        return f"{sign}{int(val)}{suffix}"
    return f"{sign}{val:.1f}{suffix}"


_GIFT_MIN = 1          # минимум перевода
_COIN_GIFT = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
_GIFT_WINDOW = 86400   # 24 часа — окно суточного лимита

# Суточный лимит перевода монет в зависимости от уровня игрока.
# (макс_уровень_включительно, лимит_в_день). После уровня 100 — лимита нет.
_GIFT_LEVEL_LIMITS = [
    (5,   10_000),
    (10,  150_000),
    (15,  1_000_000),
    (20,  5_000_000),
    (30,  50_000_000),
    (50,  500_000_000),
    (70,  2_000_000_000),
    (100, 10_000_000_000),
]


def _gift_daily_limit(level: int) -> int | None:
    """Возвращает суточный лимит перевода монет для данного уровня, либо None — лимита нет."""
    for cap, limit in _GIFT_LEVEL_LIMITS:
        if level <= cap:
            return limit
    return None


def _parse_amount(s: str) -> int | None:
    """
    Парсит число с суффиксами: 100м → 100000000, 1.5к → 1500, 2млрд → 2000000000.
    Поддерживает: к/k, м/m/mil, млрд/b/bil, трлн/t/tri.
    Возвращает int или None если не распознано.
    """
    import re as _r
    s = s.strip().lower().replace(" ", "").replace("_", "")
    # Суффиксы: самые длинные сначала чтобы не срезать часть
    _SUFFIXES = [
        (("трлн", "tri", "t"), 1_000_000_000_000),
        (("млрд", " млд", "bil", "b"),  1_000_000_000),
        (("mil", "м", "m"),             1_000_000),
        (("к", "k"),                    1_000),
    ]
    for aliases, multiplier in _SUFFIXES:
        for alias in aliases:
            if s.endswith(alias):
                num_str = s[:-len(alias)]
                if not num_str:
                    return None
                try:
                    num = float(num_str)
                    return int(num * multiplier)
                except ValueError:
                    return None
    # Без суффикса — целое число
    try:
        return int(s)
    except ValueError:
        return None


def _parse_gift_args(message: Message):
    """
    Разбирает аргументы команды перевода.
    Возвращает (target_raw: str | None, amount: int | None, error: str | None).
    target_raw — @username или числовой id в виде строки, либо None если цель = reply.
    Поддерживает суффиксы: дать 100м, дать @user 1.5к, дать @user 2млрд
    """
    text = (message.text or "").strip()
    import re as _r
    text = _r.sub(
        r'^[/]?(gift|дать|пер|transfer|give|дарю)\s*',
        '', text, count=1, flags=_r.IGNORECASE
    ).strip()

    parts = text.split()

    # Случай 1: одно слово — либо сумма (цель из reply), либо плохой ввод
    if len(parts) == 1:
        amount = _parse_amount(parts[0])
        if amount is not None:
            return None, amount, None
        return None, None, "bad_amount"

    # Случай 2: два слова — @username/id + сумма
    if len(parts) == 2:
        target_raw = parts[0].lstrip("@")
        amount = _parse_amount(parts[1])
        if amount is not None:
            return target_raw, amount, None
        return None, None, "bad_amount"

    return None, None, "bad_format"


@dp.message(Command("gift", "дать", "пер", "transfer", "give", "дарю"))
@dp.message(F.text.regexp(r'^[/]?(gift|дать|пер|transfer|give|дарю)(\s+[@\d]\S*(\s+\S+)?\s*|\s*$)', flags=_re.IGNORECASE))
async def cmd_gift(message: Message):
    """Перевод монет другому игроку."""
    from database import save_user as _save, aio_get_user

    uid  = message.from_user.id
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(uid)

    if await _check_onboarded(message, u):
        return

    target_raw, amount, error = _parse_gift_args(message)

    # Команда без аргументов — показываем подсказку
    text_stripped = (message.text or "").strip()
    import re as _re_gift
    bare = _re_gift.fullmatch(r"[/]?(gift|дать|пер|transfer|give|дарю)", text_stripped, flags=_re_gift.IGNORECASE)
    if bare and not amount and not target_raw and not error:
        hint = (
            "\u274c <b>\u0423\u043a\u0430\u0436\u0438 \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044f \u0438 \u0441\u0443\u043c\u043c\u0443.</b>\n\n"
            "<blockquote>"
            "\u041e\u0442\u0432\u0435\u0442\u044c \u043d\u0430 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0438\u0433\u0440\u043e\u043a\u0430 \u0438 \u043d\u0430\u043f\u0438\u0448\u0438:\n"
            "<code>\u0434\u0430\u0442\u044c 500</code>\n\n"
            "\u0418\u043b\u0438 \u0443\u043a\u0430\u0436\u0438 \u044f\u0432\u043d\u043e:\n"
            "<code>\u0434\u0430\u0442\u044c @username 500</code>\n"
            "<code>\u0434\u0430\u0442\u044c 123456789 500</code>"
            "</blockquote>"
        )
        await message.reply(hint, parse_mode="HTML")
        return

    # Ошибка разбора
    if error == "bad_format":
        hint = (
            "❌ <b>Неверный формат.</b>\n\n"
            "<blockquote>"
            "Ответьте на сообщение игрока и напишите:\n"
            "<code>gift 500</code>\n\n"
            "Или укажите получателя явно:\n"
            "<code>gift @username 500</code>\n"
            "<code>gift 123456789 500</code>"
            "</blockquote>"
        )
        await message.reply(hint, parse_mode="HTML")
        return

    if error == "bad_amount":
        await message.reply("❌ Сумма должна быть целым числом.", parse_mode="HTML")
        return

    if amount is None or amount < _GIFT_MIN:
        await message.reply(
            f"❌ Минимальная сумма перевода: <b>{_fmt_num(_GIFT_MIN)}</b> {_COIN_GIFT}",
            parse_mode="HTML"
        )
        return

    # ── Определяем получателя ──────────────────────────────────────────
    recipient_data = None

    if target_raw:
        # Явно указан @username или id
        from database import aio_get_user_by_id_or_username as _find_user
        recipient_data = await _find_user(target_raw)
    else:
        # Цель берётся из ответа на сообщение
        if not message.reply_to_message:
            hint = (
                "❌ <b>Укажите получателя.</b>\n\n"
                "<blockquote>"
                "Ответьте на сообщение игрока и напишите:\n"
                "<code>gift 500</code>\n\n"
                "Или укажите явно:\n"
                "<code>gift @username 500</code>\n"
                "<code>gift 123456789 500</code>"
                "</blockquote>"
            )
            await message.reply(hint, parse_mode="HTML")
            return

        target_uid = message.reply_to_message.from_user.id
        recipient_data = await aio_get_user(target_uid)

    if not recipient_data:
        await message.reply(
            "❌ Игрок не найден в базе. Он должен хотя бы раз написать боту.",
            parse_mode="HTML"
        )
        return

    if recipient_data["id"] == uid:
        await message.reply("❌ Нельзя переводить монеты самому себе.", parse_mode="HTML")
        return

    # ── Атомарный перевод (единая SQL-транзакция, см. database.transfer_coins) ──
    from database import aio_transfer_coins as _transfer_coins

    recipient_level = recipient_data.get("level", 1)
    daily_limit      = _gift_daily_limit(recipient_level)

    result = await _transfer_coins(uid, recipient_data["id"], amount, daily_limit=daily_limit, gift_window=_GIFT_WINDOW)

    if not result["ok"]:
        if result["reason"] == "insufficient":
            sender_balance = result["sender_balance"]
            await message.reply(
                f"❌ Недостаточно монет.\n\n"
                f"<blockquote>"
                f"Ваш баланс: <b>{_fmt_num(sender_balance)}</b> {_COIN_GIFT}\n"
                f"Нужно: <b>{_fmt_num(amount)}</b> {_COIN_GIFT}"
                f"</blockquote>",
                parse_mode="HTML"
            )
            return
        if result["reason"] == "limit":
            recipient_name_err = _esc(
                recipient_data.get("first_name")
                or recipient_data.get("username")
                or str(recipient_data["id"])
            )
            remaining = result.get("remaining", result["daily_limit"])
            await message.reply(
                f'<tg-emoji emoji-id="5420323339723881652">🌟</tg-emoji><b><i> Игроку <b>{recipient_name_err}</b> можно передать  '
                f"<b>{_fmt_num(remaining)}/{_fmt_num(result['daily_limit'])}</b>{_COIN_GIFT} в день.</i></b>",
                parse_mode="HTML"
            )
            return
        # no_sender / no_recipient — на этом этапе уже не должно случаться,
        # т.к. обоих проверили выше, но на всякий случай не падаем молча
        await message.reply("❌ Не удалось выполнить перевод. Попробуйте ещё раз.", parse_mode="HTML")
        return

    sender_data = {"balance": result["sender_balance"]}
    recipient_data["balance"] = result["recipient_balance"]

    # ── Уведомления ───────────────────────────────────────────────────
    sender_name    = _esc(message.from_user.first_name or message.from_user.username or str(uid))
    recipient_name = _esc(
        recipient_data.get("first_name")
        or recipient_data.get("username")
        or str(recipient_data["id"])
    )

    # Отправителю
    await message.reply(
        f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Перевод выполнен!</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5452085950022707790">✅</tg-emoji> <i><b>Получатель: {recipient_name}</b></i>\n'
        f'<tg-emoji emoji-id="5224257782013769471">✅</tg-emoji> <i><b>Сумма: {_fmt_num(amount)}{_COIN_GIFT}</b></i>\n'
        f'<tg-emoji emoji-id="5278467510604160626">✅</tg-emoji> <i><b>Ваш баланс: {_fmt_num(sender_data["balance"])}</b></i>'
        f'</blockquote>',
        parse_mode="HTML"
    )

    # Получателю (тихо — не падаем если бот заблокирован)
    try:
        await bot.send_message(
            recipient_data["id"],
            f'<tg-emoji emoji-id="5222113468051629260">🎁</tg-emoji> <b>Вам перевели монеты!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5452085950022707790">✅</tg-emoji> <i><b>От: {sender_name}</b></i>\n'
            f'<tg-emoji emoji-id="5224257782013769471">✅</tg-emoji> <i><b>Сумма: {_fmt_num(amount)}{_COIN_GIFT}</b></i>\n'
            f'<tg-emoji emoji-id="5278467510604160626">✅</tg-emoji> <i><b>Ваш баланс: {_fmt_num(recipient_data["balance"])}</b></i>'
            f'</blockquote>',
            parse_mode="HTML"
        )
    except Exception:
        pass


def _parse_limit_target(message: Message) -> str | None:
    """Извлекает опциональный @username/id из текста команды 'лимит'.
    Без аргумента и без reply — цель не указана (None)."""
    text = (message.text or "").strip()
    import re as _r
    text = _r.sub(
        r'^[/]?(лимит|лим|limit|lim)\s*',
        '', text, count=1, flags=_r.IGNORECASE
    ).strip()
    if not text:
        return None
    return text.split()[0].lstrip("@")


@dp.message(Command("лимит", "лим", "limit", "lim", ignore_case=True))
@dp.message(_text_in("лимит", "лим", "limit", "lim"))
async def cmd_limit(message: Message):
    """Показывает суточный лимит на перевод монет (свой или указанного игрока)."""
    u    = await aio_get_or_create_user(message.from_user)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return

    target_raw = _parse_limit_target(message)

    target_data = None
    if target_raw:
        from database import aio_get_user_by_id_or_username as _find_limit_target
        target_data = await _find_limit_target(target_raw)
        if not target_data:
            await message.reply(
                "❌ Игрок не найден в базе. Он должен хотя бы раз написать боту.",
                parse_mode="HTML"
            )
            return
    elif message.reply_to_message:
        from database import aio_get_user as _gu_limit
        target_data = await _gu_limit(message.reply_to_message.from_user.id)

    is_self = False
    if target_data is None:
        target_data = u
        is_self = True

    level       = target_data.get("level", 1)
    daily_limit = _gift_daily_limit(level)

    import time as _time_limit
    now            = int(_time_limit.time())
    window_start   = target_data.get("gift_window_start", 0)
    received_today = target_data.get("gift_received_today", 0)
    if now - window_start >= _GIFT_WINDOW:
        received_today = 0

    if is_self:
        title = "Ваш лимит на получение монет"
    else:
        name  = _esc(target_data.get("first_name") or target_data.get("username") or str(target_data["id"]))
        title = f"Лимит игрока <b>{name}</b> на получение монет"

    if daily_limit is None:
        text = (
            f'<tg-emoji emoji-id="5420323339723881652">🌟</tg-emoji> <b>{title}: без ограничений</b>\n\n'
            f'<blockquote>Уровень: <b>{level}</b></blockquote>'
        )
    else:
        remaining = max(daily_limit - received_today, 0)
        text = (
            f'<tg-emoji emoji-id="5420323339723881652">🌟</tg-emoji> <b>{title}:</b>\n\n'
            f'<blockquote>'
            f'Уровень: <b>{level}</b>\n'
            f'Можно получить сегодня: <b>{_fmt_num(remaining)}/{_fmt_num(daily_limit)}</b>{_COIN_GIFT}'
            f'</blockquote>'
        )

    await message.reply(text, parse_mode="HTML")


@dp.message(Command("баланс", "бал", "balance", "bal", "б", "b", ignore_case=True))
@dp.message(_text_in("баланс", "бал", "balance", "bal", "б", "b"))
async def cmd_balance(message: Message):
    """Показывает только баланс монет (без остального профиля)."""
    u = await aio_get_or_create_user(message.from_user)
    await aio_track_user(message.from_user.id)
    if await _check_onboarded(message, u): return

    await message.reply(
        f'<blockquote>'
        f'<tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>Баланс — {format_amount(u.get("balance", 0))}</b>{_COIN_GIFT}'
        f'</blockquote>',
        parse_mode="HTML"
    )


_KLAN_PENDING_KEYS = (
    "_klan_search_pending", "_klan_create_pending", "_klan_kick_pending",
    "_klan_deposit_pending", "_klan_withdraw_pending", "_klan_apply_pending",
    "_klan_chat_pending",
)


def _clear_klan_pending(d: dict) -> bool:
    """Сбрасывает все флаги ожидания текстового ввода для системы кланов.
    Возвращает True, если хотя бы один флаг был установлен."""
    changed = False
    for key in _KLAN_PENDING_KEYS:
        if key in d:
            d.pop(key, None)
            changed = True
    return changed


async def _handle_klan_text_input(message: Message, data: dict) -> bool:
    """
    Обрабатывает текстовый ввод, который пользователь отправляет в ответ
    на промпты системы кланов (поиск, создание клана, исключение участника,
    пополнение/вывод казны, заявка на вступление).
    Возвращает True, если сообщение было обработано (дальше обрабатывать не нужно).
    """
    uid = message.from_user.id

    if not any(k in data for k in _KLAN_PENDING_KEYS):
        return False

    lock = await _get_user_lock(uid)
    async with lock:
        # Перечитываем актуальные данные на случай гонки с callback-хендлером
        data = await aio_get_or_create_user(message.from_user)
        lang = get_lang(data)
        text = (message.text or "").strip()

        if not any(k in data for k in _KLAN_PENDING_KEYS):
            return False

        # --- Поиск клана ---
        if "_klan_search_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            results, total = await search_clans(text, page=0)
            await message.answer(
                klan_search_text(text, results, 0, total, lang),
                parse_mode="HTML",
                reply_markup=klan_search_keyboard(results, text, 0, total, lang),
            )
            return True

        # --- Создание клана ---
        if "_klan_create_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            name = text.strip()
            if not name:
                err = (
                    "❌ Название не может быть пустым."
                    if lang == "ru" else
                    "❌ Name cannot be empty."
                )
                await message.answer(err, parse_mode="HTML")
                return True
            res = await create_clan(uid, name)
            if res["ok"]:
                m    = await get_member(uid)
                clan = await get_clan(m["clan_id"])
                cnt  = await get_member_count(m["clan_id"])
                # ВАЖНО: create_clan уже сделал свой get_user/save_user внутри
                # (списал баланс, записал last_clan_create_ts). Локальный `data`
                # был загружен ДО этого и не знает о тех изменениях — если
                # сохранить его как есть, это затрёт и списание монет, и штамп
                # кулдауна на создание клана (баг: клан создавался бесплатно
                # и без ограничения раз в сутки). Поэтому перечитываем свежие
                # данные из базы и вносим только новые флаги поверх них.
                data = await aio_get_or_create_user(message.from_user)
                data["clan_created"] = True
                data["clan_created_count"] = data.get("clan_created_count", 0) + 1
                _ach_newly = check_achievements(data)
                await aio_save_user(uid, data)
                await _notify_ach(uid, data, _ach_newly)
                ok_text = "✅ <b>Клан создан!</b>" if lang == "ru" else "✅ <b>Clan created!</b>"
                await message.answer(ok_text, parse_mode="HTML")
                await message.answer(
                    my_klan_text(clan, m, cnt, lang),
                    parse_mode="HTML",
                    reply_markup=await my_klan_keyboard(uid, lang),
                )
            else:
                errs_ru = {
                    "user_not_found":  "❌ Ошибка профиля. Попробуй /start.",
                    "already_in_clan": "❌ Ты уже в клане!",
                    "bad_name_length": f"❌ Название должно быть от {MIN_CLAN_NAME} до {MAX_CLAN_NAME} символов.",
                    "no_coins":        f"❌ Недостаточно монет. Нужно {format_amount(CREATE_COST)} {_COIN}.",
                    "name_taken":      "❌ Клан с таким названием уже существует.",
                }
                errs_en = {
                    "user_not_found":  "❌ Profile error. Try /start.",
                    "already_in_clan": "❌ You are already in a clan!",
                    "bad_name_length": f"❌ Name must be {MIN_CLAN_NAME}-{MAX_CLAN_NAME} characters.",
                    "no_coins":        f"❌ Not enough coins. Need {format_amount(CREATE_COST)} {_COIN}.",
                    "name_taken":      "❌ A clan with that name already exists.",
                }
                if res["error"] == "create_cooldown":
                    retry_after = res.get("retry_after", 0)
                    hrs, rem = divmod(max(retry_after, 0), 3600)
                    mins = rem // 60
                    time_str = f"{hrs}ч {mins}м" if lang == "ru" else f"{hrs}h {mins}m"
                    err = (
                        f"❌ Клан можно создавать не чаще одного раза в сутки.\n\n"
                        f"<blockquote>Попробуй снова через <b>{time_str}</b></blockquote>"
                        if lang == "ru" else
                        f"❌ You can only create a clan once per day.\n\n"
                        f"<blockquote>Try again in <b>{time_str}</b></blockquote>"
                    )
                    await message.answer(err, parse_mode="HTML")
                    return True
                errs = errs_en if lang == "en" else errs_ru
                hint = (
                    "\n\nНажми «➕ Создать клан» ещё раз, чтобы попробовать снова."
                    if lang == "ru" else
                    '\n\nTap "➕ Create clan" again to try again.'
                )
                await message.answer(errs.get(res["error"], f"❌ {res['error']}") + hint, parse_mode="HTML")
            return True

        # --- Исключение участника ---
        if "_klan_kick_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            m = await get_member(uid)
            if not m or m["role"] != "creator":
                err = "❌ Только создатель может исключать участников." if lang == "ru" \
                    else "❌ Only the creator can kick members."
                await message.answer(err, parse_mode="HTML")
                return True
            target     = text.lstrip("@").strip()
            target_uid = None
            if target.isdigit():
                target_uid = int(target)
            else:
                for mem in await get_clan_members(m["clan_id"]):
                    if (mem.get("username") or "").lower() == target.lower():
                        target_uid = mem["uid"]
                        break
            if not target_uid:
                err = "❌ Участник не найден. Отправь @username или ID." if lang == "ru" \
                    else "❌ Member not found. Send @username or ID."
                await message.answer(err, parse_mode="HTML")
                return True
            res = await kick_member(uid, target_uid)
            if res["ok"]:
                try:
                    ntf = "🚫 Ты был исключён из клана." if lang == "ru" else "🚫 You were kicked from the clan."
                    await bot.send_message(target_uid, ntf, parse_mode="HTML")
                except Exception:
                    pass
                data["clan_kicks_done"] = data.get("clan_kicks_done", 0) + 1
                _ach_newly = check_achievements(data)
                await aio_save_user(uid, data)
                await _notify_ach(uid, data, _ach_newly)
                ok_text = "✅ Участник исключён из клана." if lang == "ru" else "✅ Member kicked from the clan."
                await message.answer(ok_text, parse_mode="HTML")
            else:
                errs_ru = {
                    "not_creator":         "❌ Только создатель может исключать участников.",
                    "not_in_your_clan":    "❌ Этот пользователь не состоит в твоём клане.",
                    "cannot_kick_creator": "❌ Невозможно исключить создателя клана.",
                }
                errs_en = {
                    "not_creator":         "❌ Only the creator can kick members.",
                    "not_in_your_clan":    "❌ This user is not in your clan.",
                    "cannot_kick_creator": "❌ Cannot kick the clan creator.",
                }
                errs = errs_en if lang == "en" else errs_ru
                await message.answer(errs.get(res["error"], f"❌ {res['error']}"), parse_mode="HTML")
            return True

        # --- Пополнение казны ---
        if "_klan_deposit_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            cleaned = text.replace(" ", "").replace(",", "").replace("_", "")
            if not cleaned.isdigit() or int(cleaned) <= 0:
                err = "❌ Отправь положительное число." if lang == "ru" else "❌ Send a positive number."
                await message.answer(err, parse_mode="HTML")
                return True
            amount = int(cleaned)
            res    = await deposit_treasury(uid, amount)
            if res["ok"]:
                m    = await get_member(uid)
                clan = await get_clan(m["clan_id"])
                # deposit_treasury() уже списал баланс и сохранил его в БД
                # своим отдельным save_user(). Наша локальная копия `data`
                # была загружена ДО этого списания, поэтому перечитываем
                # актуальные данные — иначе save_user(uid, data) ниже
                # затрёт баланс обратно на старое значение (деньги как бы
                # "не списывались").
                from database import aio_get_user as _gu_klan_dep
                data = await _gu_klan_dep(uid) or data
                data["clan_treasury_deposited"] = data.get("clan_treasury_deposited", 0) + amount
                _ach_newly = check_achievements(data)
                await aio_save_user(uid, data)
                await _notify_ach(uid, data, _ach_newly)
                ok_text = (f"✅ В казну клана внесено <b>{format_amount(amount)}</b> {_COIN}." if lang == "ru"
                           else f"✅ Deposited <b>{format_amount(amount)}</b> {_COIN} to the clan treasury.")
                await message.answer(ok_text, parse_mode="HTML")
                await message.answer(
                    klan_treasury_text(clan, lang),
                    parse_mode="HTML",
                    reply_markup=klan_treasury_keyboard(lang),
                )
            else:
                errs_ru = {
                    "not_in_clan": "❌ Ты не состоишь в клане.",
                    "bad_amount":  "❌ Сумма должна быть больше нуля.",
                    "no_coins":    "❌ У тебя недостаточно монет.",
                }
                errs_en = {
                    "not_in_clan": "❌ You are not in a clan.",
                    "bad_amount":  "❌ Amount must be greater than zero.",
                    "no_coins":    "❌ You don't have enough coins.",
                }
                errs = errs_en if lang == "en" else errs_ru
                await message.answer(errs.get(res["error"], f"❌ {res['error']}"), parse_mode="HTML")
            return True

        # --- Запрос на вывод из казны ---
        if "_klan_withdraw_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            raw_parts  = text.split("|", 1)
            amount_str = raw_parts[0].strip().replace(" ", "").replace(",", "").replace("_", "")
            reason     = raw_parts[1].strip() if len(raw_parts) > 1 else ""
            if not amount_str.isdigit() or int(amount_str) <= 0:
                err = (
                    "❌ Неверный формат. Используй: <code>1000 | причина</code>" if lang == "ru"
                    else "❌ Invalid format. Use: <code>1000 | reason</code>"
                )
                await message.answer(err, parse_mode="HTML")
                return True
            amount = int(amount_str)
            res    = await request_withdrawal(uid, amount, reason)
            if res["ok"]:
                ok_text = (f"✅ Запрос на вывод <b>{format_amount(amount)}</b> {_COIN} отправлен создателю клана." if lang == "ru"
                           else f"✅ Withdrawal request for <b>{format_amount(amount)}</b> {_COIN} sent to the clan creator.")
                await message.answer(ok_text, parse_mode="HTML")
                m = await get_member(uid)
                if m:
                    clan = await get_clan(m["clan_id"])
                    if clan:
                        try:
                            from database import aio_get_user as _gu
                            _cd    = await _gu(clan["creator_uid"])
                            _clang = get_lang(_cd) if _cd else "ru"
                            name   = _esc(data.get("first_name") or data.get("username") or str(uid))
                            ntf = (
                                f"📤 {name} запросил вывод <b>{format_amount(amount)}</b> {_COIN} из казны клана."
                                if _clang == "ru" else
                                f"📤 {name} requested a withdrawal of <b>{format_amount(amount)}</b> {_COIN} from the clan treasury."
                            )
                            await bot.send_message(clan["creator_uid"], ntf, parse_mode="HTML")
                        except Exception:
                            pass
            else:
                errs_ru = {
                    "not_in_clan":         "❌ Ты не состоишь в клане.",
                    "bad_amount":          "❌ Сумма должна быть больше нуля.",
                    "not_enough_treasury": "❌ В казне клана недостаточно монет.",
                    "already_pending":     "❌ У тебя уже есть ожидающий запрос на вывод.",
                }
                errs_en = {
                    "not_in_clan":         "❌ You are not in a clan.",
                    "bad_amount":          "❌ Amount must be greater than zero.",
                    "not_enough_treasury": "❌ Not enough coins in the clan treasury.",
                    "already_pending":     "❌ You already have a pending withdrawal request.",
                }
                if res["error"] == "withdraw_limit_exceeded":
                    remaining = res.get("remaining", 0)
                    limit     = res.get("limit", 0)
                    err_text = (
                        f"❌ Лимит на вывод для новых участников клана.\n\n"
                        f"<blockquote>Тебе доступно ещё <b>{format_amount(remaining)}/{format_amount(limit)}</b> {_COIN}</blockquote>"
                        if lang == "ru" else
                        f"❌ Withdrawal limit for new clan members.\n\n"
                        f"<blockquote>You still have <b>{format_amount(remaining)}/{format_amount(limit)}</b> {_COIN} available</blockquote>"
                    )
                    await message.answer(err_text, parse_mode="HTML")
                    return True
                errs = errs_en if lang == "en" else errs_ru
                await message.answer(errs.get(res["error"], f"❌ {res['error']}"), parse_mode="HTML")
            return True

        # --- Заявка на вступление в клан ---
        if "_klan_apply_pending" in data:
            clan_id = data.get("_klan_apply_pending")
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            app_msg = "" if text in ("—", "-", "") else text[:200]
            res     = await apply_to_clan(uid, clan_id, app_msg)
            if res["ok"]:
                ok_text = "✅ Заявка отправлена! Ожидай решения создателя в разделе «Заявки»." \
                    if lang == "ru" else "✅ Application sent! Wait for the creator's decision in the Applications section."
                await message.answer(ok_text, parse_mode="HTML")

                # ── Уведомление создателю клана ──────────────────────────
                try:
                    _clan_info = await get_clan(clan_id)
                    if _clan_info:
                        _creator_uid = _clan_info["creator_uid"]
                        from database import aio_get_user as _get_user_db
                        _creator_data = await _get_user_db(_creator_uid)
                        _creator_lang = _creator_data.get("lang", "ru") if _creator_data else "ru"
                        _applicant_name = _esc(
                            data.get("first_name") or
                            (f"@{data.get('username')}" if data.get("username") else None) or
                            str(uid)
                        )
                        _clan_name = _clan_info.get("name", "")
                        if _creator_lang == "en":
                            _notif = (
                                f'<tg-emoji emoji-id="5222113468051629260">🎁</tg-emoji> '
                                f'<b>New application to clan «{_clan_name}»!</b>\n'
                                f'👤 <b>{_applicant_name}</b> wants to join.\n'
                                f'<i>Go to Clan → Applications to review.</i>'
                            )
                        else:
                            _notif = (
                                f'<tg-emoji emoji-id="5222113468051629260">🎁</tg-emoji> '
                                f'<b>Новая заявка в клан «{_clan_name}»!</b>\n'
                                f'👤 <b>{_applicant_name}</b> хочет вступить.\n'
                                f'<i>Зайди в Клан → Заявки, чтобы рассмотреть.</i>'
                            )
                        await bot.send_message(_creator_uid, _notif, parse_mode="HTML")
                except Exception:
                    pass  # Уведомление не критично — не ломаем основной флоу
            else:
                errs_ru = {
                    "already_in_clan": "❌ Ты уже в клане!",
                    "clan_full":       "❌ Клан заполнен.",
                    "already_applied": "❌ Ты уже подал заявку в этот клан.",
                    "apps_full":       "❌ Очередь заявок в этот клан переполнена.",
                }
                errs_en = {
                    "already_in_clan": "❌ You are already in a clan!",
                    "clan_full":       "❌ The clan is full.",
                    "already_applied": "❌ You already applied to this clan.",
                    "apps_full":       "❌ This clan's application queue is full.",
                }
                errs = errs_en if lang == "en" else errs_ru
                await message.answer(errs.get(res["error"], f"❌ {res['error']}"), parse_mode="HTML")
            return True

        # --- Привязка чата клана ---
        if "_klan_chat_pending" in data:
            _clear_klan_pending(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)
            m = await get_member(uid)
            if not m or m["role"] != "creator":
                await message.answer("❌ Только создатель клана!" if lang == "ru" else "❌ Creator only!", parse_mode="HTML")
                return True
            clan_id = m["clan_id"]
            # Парсим ввод: ссылка t.me/username или @username или числовой ID
            import re as _re_chat
            raw = text.strip()
            chat_obj = None
            try:
                if raw.lstrip("-").isdigit():
                    chat_obj = await bot.get_chat(int(raw))
                else:
                    username = _re_chat.sub(r'^(https?://)?(t\.me/|@)', '@', raw)
                    if not username.startswith("@"):
                        username = "@" + username
                    chat_obj = await bot.get_chat(username)
            except Exception as e:
                err = (
                    f"❌ Чат не найден. Убедись что:\n"
                    f"• Бот добавлен в чат как <b>администратор</b>\n"
                    f"• Ссылка или username введены верно\n"
                    f"<i>({e})</i>"
                    if lang == "ru" else
                    f"❌ Chat not found. Make sure:\n"
                    f"• The bot is added to the chat as an <b>admin</b>\n"
                    f"• The link or username is correct\n"
                    f"<i>({e})</i>"
                )
                await message.answer(err, parse_mode="HTML")
                return True

            # Проверяем что чат — группа или супергруппа
            if chat_obj.type not in ("group", "supergroup"):
                err = "❌ Можно привязать только группу или супергруппу." if lang == "ru" else "❌ Only groups or supergroups can be linked."
                await message.answer(err, parse_mode="HTML")
                return True

            # Проверяем что бот является администратором
            try:
                bot_member = await bot.get_chat_member(chat_obj.id, (await bot.get_me()).id)
                if bot_member.status not in ("administrator", "creator"):
                    err = (
                        "❌ Бот не является администратором в этом чате.\n"
                        "Добавь бота как администратора и попробуй снова."
                        if lang == "ru" else
                        "❌ The bot is not an administrator in this chat.\n"
                        "Add the bot as admin and try again."
                    )
                    await message.answer(err, parse_mode="HTML")
                    return True
            except Exception:
                err = "❌ Не удалось проверить права бота в чате." if lang == "ru" else "❌ Failed to check bot permissions in the chat."
                await message.answer(err, parse_mode="HTML")
                return True

            # Сохраняем
            import html as _html_chat
            chat_title   = chat_obj.title or "Chat"
            chat_username = chat_obj.username  # может быть None у закрытых чатов
            await set_clan_chat(clan_id, chat_obj.id, chat_username, chat_title)
            data["clan_chat_linked"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(uid, data)
            await _notify_ach(uid, data, _ach_newly)

            clan = await get_clan(clan_id)
            cnt  = await get_member_count(clan_id)
            ok_text = (
                f'✅ <b>Чат привязан:</b> {_html_chat.escape(chat_title)}'
                if lang == "ru" else
                f'✅ <b>Chat linked:</b> {_html_chat.escape(chat_title)}'
            )
            await message.answer(ok_text, parse_mode="HTML")
            await message.answer(
                my_klan_text(clan, m, cnt, lang),
                parse_mode="HTML",
                reply_markup=await my_klan_keyboard(uid, lang),
            )
            return True

    return False



# ════════════════════════════════════════════════════════════
#  БЫСТРЫЕ КОМАНДЫ ДУЭЛИ (со слешем и без, RU + EN)
# ════════════════════════════════════════════════════════════

async def _handle_duel_cmd(message: Message):
    """Общий обработчик быстрых команд дуэли. Вызывается из slash и text хендлеров."""
    uid  = message.from_user.id
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    text = (message.text or "").strip()
    # Сбрасываем ожидание ввода цели вызова — команда дуэли сама управляет флагом
    _challenge_input_pending.pop(uid, None)

    if is_duel_main_cmd(text):
        # /дуэли — главный раздел дуэлей
        await message.reply(
            duel_main_text(u, lang),
            parse_mode="HTML",
            reply_markup=duel_main_keyboard(lang),
        )
        return

    if is_duel_equip_cmd(text):
        # /снар — открыть снаряжение
        await message.reply(
            duel_equip_text(u, lang),
            parse_mode="HTML",
            reply_markup=duel_equip_keyboard(u, lang),
        )
        return

    if is_duel_skills_cmd(text):
        # /навыки — открыть навыки
        await message.reply(
            duel_skills_text(u, lang),
            parse_mode="HTML",
            reply_markup=duel_skills_keyboard(lang),
        )
        return

    if is_duel_stats_cmd(text):
        # /хар — характеристики
        await message.reply(
            duel_charstats_text(u, uid=uid, lang=lang),
            parse_mode="HTML",
            reply_markup=duel_charstats_keyboard(lang),
        )
        return

    if is_duel_invite_cmd(text):
        # /вз — бросить вызов
        lock = await _get_user_lock(uid)
        async with lock:
            if uid in _active_battles:
                await message.reply(cmd_already_in_battle_text(lang), parse_mode="HTML")
                return
            if not is_player_ready(uid, u):
                hp_now = get_player_hp(uid, u)
                secs   = player_hp_regen_seconds(uid, u)
                await message.reply(cmd_no_hp_text(hp_now, secs, lang), parse_mode="HTML")
                return

            # Определяем цель: reply или аргумент
            target_raw = None
            if message.reply_to_message and message.reply_to_message.from_user:
                target_raw = str(message.reply_to_message.from_user.id)
            else:
                parts = text.lstrip("/").split(maxsplit=1)
                if len(parts) > 1:
                    target_raw = parts[1].strip().lstrip("@")

            if not target_raw:
                await message.reply(cmd_invite_usage_text(lang), parse_mode="HTML")
                return

            from database import aio_get_user_by_id_or_username as _find_duel_target
            target = await _find_duel_target(target_raw)

            if not target:
                await message.reply(cmd_invite_not_found_text(lang), parse_mode="HTML")
                return
            if target["id"] == uid:
                await message.reply(cmd_invite_self_text(lang), parse_mode="HTML")
                return
            if target["id"] in _active_battles:
                await message.reply(cmd_invite_in_battle_text(lang), parse_mode="HTML")
                return

            target_name = _esc(target.get("first_name") or target.get("username") or str(target["id"]))
            if not create_challenge(uid, target["id"], target_name):
                secs = seconds_until_challenge_slot(uid, target["id"])
                await message.reply(cmd_invite_limit_text(target_name, secs, lang=lang), parse_mode="HTML")
                return
            try:
                _target_lang2 = get_lang(target)
                await bot.send_message(
                    target["id"],
                    challenge_invite_text(u, _target_lang2),
                    parse_mode="HTML",
                    reply_markup=challenge_invite_keyboard(uid, _target_lang2),
                )
            except Exception:
                await message.reply(cmd_invite_blocked_text(target_name, lang), parse_mode="HTML")
                cancel_challenge(uid)
                return
            await message.reply(
                duel_challenge_sent_text(target_name, lang),
                parse_mode="HTML",
                reply_markup=duel_challenge_sent_keyboard(lang),
            )
            return


@dp.message(F.text.regexp(
    r"^/?(?:дуэли|дуель|duel|duels"
    r"|дуэли-duel-екип|снаряжение|снар|equip|gear|duel-equip"
    r"|нвык|навыки|skills|skill|умения"
    r"|стата|хк|хар|stats|charstats|характеристики"
    r"|вз|вызов|challenge)(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def handle_duel_cmd_text(message: Message):
    """Текстовые алиасы дуэльных команд (без слеша)."""
    await _handle_duel_cmd(message)


@dp.message(F.text.regexp(
    r"^/(?:дуэли|дуель|duel|duels"
    r"|дуэли-duel-екип|снаряжение|снар|equip|gear|duel-equip"
    r"|нвык|навыки|skills|skill|умения"
    r"|стата|хк|хар|stats|charstats|характеристики"
    r"|вз|вызов|challenge)(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def handle_duel_cmd_slash(message: Message):
    """Слеш-команды дуэлей."""
    await _handle_duel_cmd(message)



# ============================================================
#  КОМАНДЫ ЕДИНОГО ИНВЕНТАРЯ
#  /инв /inv /инвентарь inventory
#  исп #N / use #N / -use #N
#  стоп буст / stop boost  и т.д.
#  /boost /буст  — активные бусты
# ============================================================

import re as _re_inv

@dp.message(Command("inv", "инв", "инвентарь", "inventory"))
@dp.message(F.text.regexp(r'^/?(инв|inv|инвентарь|inventory)\s*$', flags=_re_inv.IGNORECASE))
async def cmd_inv(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return
    await message.reply(unified_inventory_text(u, lang), parse_mode="HTML")


@dp.message(Command("sell"))
@dp.message(F.text.regexp(r'^/sell\s+#(\d+)(?:\s+(\d+))?\s*$', flags=_re_inv.IGNORECASE))
async def cmd_sell(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return
    import re as _re_sell
    m = _re_sell.match(r'/sell\s+#(\d+)(?:\s+(\d+))?\s*$', message.text.strip(), _re_sell.IGNORECASE)
    if not m:
        hint = (
            "Использование: <code>/sell #N</code> или <code>/sell #N 5</code>"
            if lang == "ru" else
            "Usage: <code>/sell #N</code> or <code>/sell #N 5</code>"
        )
        await message.reply(f"❌ {hint}", parse_mode="HTML")
        return
    slot_id = int(m.group(1))
    qty     = int(m.group(2)) if m.group(2) else 1
    ok, msg = sell_item_by_slot_id(u, slot_id, qty, lang)
    if ok:
        from database import aio_save_user
        _ach_newly = check_achievements(u)
        await aio_save_user(uid, u)
        await _notify_ach(uid, u, _ach_newly)
    await message.reply(msg, parse_mode="HTML")


# ── отп/пер/перевести/отправить #N [qty] [@user|id] — передать предмет ──────
# Форматы:
#   отп #45              — 1 шт., получатель из reply
#   отп #45 3            — 3 шт., получатель из reply
#   отп #45 @username    — 1 шт., явный получатель
#   отп #45 3 @username  — 3 шт., явный получатель
#   пер / перевести / отправить — синонимы

_TRANSFER_RE = _re_inv.compile(
    r'^/?(отп|пер|перевести|отправить|transfer_item)\s+'
    r'#(\d+)'
    r'(?:\s+(\d+))?'
    r'(?:\s+[@]?(\S+))?'
    r'\s*$',
    _re_inv.IGNORECASE,
)

@dp.message(F.text.regexp(
    r'^/?(отп|пер|перевести|отправить|transfer_item)\s+#\d+',
    flags=_re_inv.IGNORECASE,
))
async def cmd_transfer_item(message: Message):
    """Передача предмета из инвентаря другому игроку."""
    from database import aio_save_user as _save, aio_get_user

    uid  = message.from_user.id
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    await aio_track_user(uid)
    if await _check_onboarded(message, u):
        return

    text = (message.text or "").strip()
    m = _TRANSFER_RE.match(text)
    if not m:
        hint = (
            "❌ <b>Неверный формат.</b>\n\n"
            "<blockquote>"
            "Ответь на сообщение игрока и напиши:\n"
            "<code>отп #45</code> — 1 шт.\n"
            "<code>отп #45 3</code> — 3 шт.\n\n"
            "Или укажи получателя явно:\n"
            "<code>отп #45 @username</code>\n"
            "<code>отп #45 3 @username</code>\n"
            "<code>отп #45 123456789</code>"
            "</blockquote>"
        )
        await message.reply(hint, parse_mode="HTML")
        return

    slot_id    = int(m.group(2))
    qty_raw    = m.group(3)
    target_raw = m.group(4)
    qty        = int(qty_raw) if qty_raw else 1

    # ── Определяем получателя ──────────────────────────────────────────
    recipient_data = None

    if target_raw:
        from database import aio_get_user_by_id_or_username as _find_transfer
        recipient_data = await _find_transfer(target_raw.lstrip("@"))
    else:
        if not message.reply_to_message:
            hint = (
                "❌ <b>Укажи получателя.</b>\n\n"
                "<blockquote>"
                "Ответь на сообщение игрока и напиши:\n"
                "<code>отп #45</code>\n\n"
                "Или укажи явно:\n"
                "<code>отп #45 @username</code>\n"
                "<code>отп #45 3 @username</code>"
                "</blockquote>"
            )
            await message.reply(hint, parse_mode="HTML")
            return
        target_uid     = message.reply_to_message.from_user.id
        recipient_data = await aio_get_user(target_uid)

    if not recipient_data:
        await message.reply(
            "❌ Игрок не найден в базе. Он должен хотя бы раз написать боту.",
            parse_mode="HTML",
        )
        return

    if recipient_data["id"] == uid:
        await message.reply("❌ Нельзя передавать предметы самому себе.", parse_mode="HTML")
        return

    # ── Атомарный перенос ─────────────────────────────────────────────
    lock_sender    = await _get_user_lock(uid)
    lock_recipient = await _get_user_lock(recipient_data["id"])

    first_lock, second_lock = (
        (lock_sender, lock_recipient)
        if uid < recipient_data["id"]
        else (lock_recipient, lock_sender)
    )

    async with first_lock:
        async with second_lock:
            sender_data    = await aio_get_or_create_user(message.from_user)
            recipient_data = await aio_get_user(recipient_data["id"])

            ok, sender_msg, recip_msg = transfer_item_by_slot_id(
                sender_data, recipient_data, slot_id, qty, lang
            )
            if ok:
                await _save(uid, sender_data)
                await _save(recipient_data["id"], recipient_data)

    await message.reply(sender_msg if ok else sender_msg, parse_mode="HTML")

    if ok and recip_msg:
        try:
            await bot.send_message(recipient_data["id"], recip_msg, parse_mode="HTML")
        except Exception:
            pass


@dp.message(Command("boost", "буст", "бусты", "boosts"))
@dp.message(F.text.regexp(r'^/?(boost|буст|бусты|boosts)\s*$', flags=_re_inv.IGNORECASE))
async def cmd_boost_status(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return
    await message.reply(get_all_active_boosters_text(u, lang), parse_mode="HTML")


@dp.message(F.text.regexp(r'^(?:исп|use|-use)\s+#(\d+)\s*$', flags=_re_inv.IGNORECASE))
async def cmd_use_item(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return

    m = _re_inv.match(r'^(?:исп|use|-use)\s+#(\d+)\s*$', (message.text or '').strip(), _re_inv.IGNORECASE)
    if not m:
        return
    slot_id = int(m.group(1))

    lock = await _get_user_lock(uid)
    async with lock:
        u = await aio_get_or_create_user(message.from_user)
        ok, msg = use_item_by_slot_id(u, slot_id, lang)
        if ok:
            _ach_newly = check_achievements(u)
            await aio_save_user(uid, u)
            await _notify_ach(uid, u, _ach_newly)
        await message.reply(msg, parse_mode="HTML")



# ── открыть/купить/open #N qty — открыть кейсы пачкой ───────────────────────
# Форматы (слеш опционален):
#   открыть #1 5        купить #2 10        open #3 1
#   /открыть #1 5       /купить #2 10       /open #3 1

_OPEN_CASE_RE = _re_inv.compile(
    r'^/?(?:открыть|купить|open)\s+#([123])(?:\s+(\d+))?\s*$',
    _re_inv.IGNORECASE,
)

@dp.message(F.text.regexp(
    r'^/?(?:открыть|купить|open)\s+#[123](?:\s+\d+)?\s*$',
    flags=_re_inv.IGNORECASE,
))
async def cmd_open_case_multi(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return

    m = _OPEN_CASE_RE.match((message.text or '').strip())
    if not m:
        return
    case_num = int(m.group(1))
    qty      = int(m.group(2)) if m.group(2) else 1

    lock = await _get_user_lock(uid)
    async with lock:
        u = await aio_get_or_create_user(message.from_user)
        ok, msg = open_case_multi(u, case_num, qty, lang)
        if ok:
            _ach_newly = check_achievements(u)
            await aio_save_user(uid, u)
            await _notify_ach(uid, u, _ach_newly)
        await message.reply(msg, parse_mode="HTML")


# стоп буст / stop boost / стоп xp / stop xp / стоп урон / stop dmg / стоп яд / stop poison
_STOP_PATTERNS = {
    "boost":  _re_inv.compile(r'^/(?:стоп|stop)\s+(?:буст|boost)\s*$', _re_inv.IGNORECASE),
    "xp":     _re_inv.compile(r'^/(?:стоп|stop)\s+xp\s*$', _re_inv.IGNORECASE),
    "enh":    _re_inv.compile(r'^/(?:стоп|stop)\s+(?:урон|dmg|damage)\s*$', _re_inv.IGNORECASE),
    "poison": _re_inv.compile(r'^/(?:стоп|stop)\s+(?:яд|poison)\s*$', _re_inv.IGNORECASE),
}

@dp.message(F.text.regexp(
    r'^/(?:стоп|stop)\s+(?:буст|boost|xp|урон|dmg|damage|яд|poison)\s*$',
    flags=_re_inv.IGNORECASE
))
async def cmd_stop_boost(message: Message):
    u    = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)
    uid  = message.from_user.id
    await aio_track_user(uid)
    if await _check_onboarded(message, u): return

    text = (message.text or '').strip()
    boost_type = None
    for btype, pat in _STOP_PATTERNS.items():
        if pat.match(text):
            boost_type = btype
            break
    if not boost_type:
        return

    lock = await _get_user_lock(uid)
    async with lock:
        u = await aio_get_or_create_user(message.from_user)
        ok, msg = cancel_active_by_type(u, boost_type, lang)
        if ok:
            _ach_newly = check_achievements(u)
            await aio_save_user(uid, u)
            await _notify_ach(uid, u, _ach_newly)
        await message.reply(msg, parse_mode="HTML")


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_captcha_answer(message: Message):
    """Перехватчик текстовых сообщений для прохождения капчи при онбординге."""
    uid = message.from_user.id
    u   = await aio_get_or_create_user(message.from_user)
    lang = get_lang(u)

    # ── Текстовые алиасы раздела города (без слеша): тор/торговля/город/рынок ──
    _city_word = (message.text or "").strip().split()[0].lower() if (message.text or "").strip() else ""
    if _city_word in ("торг", "торговля", "город"):
        await cmd_city_profile(message)
        return
    if _city_word == "рынок":
        await cmd_city_shop(message)
        return

    # ── Текстовые алиасы промокода: «промо stars», «promo stars» ──
    if u.get("onboarded", True):
        _txt = (message.text or "").strip()
        _txt_low = _txt.lower()
        for _pfx in ("промо ", "promo ", "старт ", "start "):
            if _txt_low.startswith(_pfx):
                promo_name = _txt[len(_pfx):].strip()
                if promo_name:
                    lock = await _get_user_lock(uid)
                    async with lock:
                        u = await aio_get_or_create_user(message.from_user)
                        ok, reason, amount = await activate_promo(promo_name, uid)
                        if ok:
                            u["balance"] = u.get("balance", 0) + amount
                            u["promo_activations"] = u.get("promo_activations", 0) + 1
                            _ach_newly = check_achievements(u)
                            await aio_save_user(uid, u)
                            await _notify_ach(uid, u, _ach_newly)
                            await message.reply(promo_activate_text(amount, lang), parse_mode="HTML")
                        else:
                            await message.reply(promo_error_text(reason, lang), parse_mode="HTML")
                return

    # ── Команды арсенала: подарить/передать/арн ──
    if u.get("onboarded", True):
        _ars_parsed = parse_arsenal_cmd((message.text or "").strip())
        if _ars_parsed:
            from database import aio_get_user_by_id_or_username as _find_ars, aio_get_user as _gu_ars, aio_save_user as _su_ars
            action       = _ars_parsed["action"]
            sword_idx    = _ars_parsed["index"]
            target_raw   = _ars_parsed["target"].lstrip("@")
            duration_secs = _ars_parsed["duration_secs"]

            # Ищем меч по индексу в арсенале
            cleanup_expired_rentals(u)
            sword_key = get_sword_by_arsenal_index(u, sword_idx)
            if not sword_key:
                await message.reply(
                    arsenal_error_text(f"❌ Меча <b>#{sword_idx}</b> нет в арсенале. Открой <code>арс</code> и проверь номера."),
                    parse_mode="HTML", reply_markup=arsenal_back_keyboard()
                )
                return

            # Ищем получателя
            recipient_data = await _find_ars(target_raw)
            if not recipient_data:
                await message.reply(
                    arsenal_error_text("❌ Игрок не найден. Он должен хотя бы раз написать боту."),
                    parse_mode="HTML", reply_markup=arsenal_back_keyboard()
                )
                return
            if recipient_data["id"] == uid:
                await message.reply(
                    arsenal_error_text("❌ Нельзя отправить меч самому себе."),
                    parse_mode="HTML", reply_markup=arsenal_back_keyboard()
                )
                return

            sender_name = _esc(message.from_user.first_name or message.from_user.username or str(uid))
            recip_name  = _esc(recipient_data.get("first_name") or recipient_data.get("username") or str(recipient_data["id"]))

            lock_s = await _get_user_lock(uid)
            lock_r = await _get_user_lock(recipient_data["id"])
            first_lock, second_lock = (lock_s, lock_r) if uid < recipient_data["id"] else (lock_r, lock_s)

            async with first_lock:
                async with second_lock:
                    u_fresh   = await aio_get_or_create_user(message.from_user)
                    r_fresh   = await _gu_ars(recipient_data["id"]) or recipient_data
                    cleanup_expired_rentals(u_fresh)

                    if action == "gift":
                        ok, msg = arsenal_gift_sword(u_fresh, r_fresh, sword_key, sender_name)
                        confirm_text = arsenal_gift_confirm_text(sword_key, recip_name) if ok else None
                        notif_mode   = "gift"
                    elif action == "transfer":
                        ok, msg = arsenal_transfer_sword(u_fresh, r_fresh, sword_key, sender_name)
                        confirm_text = arsenal_transfer_confirm_text(sword_key, recip_name) if ok else None
                        notif_mode   = "transfer"
                    else:  # rent
                        if not duration_secs:
                            await message.reply(
                                arsenal_error_text("❌ Неверный срок аренды.\nПример: <code>арн #1 2ч @user</code>\nМин: 5м, макс: 48ч"),
                                parse_mode="HTML", reply_markup=arsenal_back_keyboard()
                            )
                            return
                        ok, msg = arsenal_rent_sword(u_fresh, r_fresh, sword_key, duration_secs, sender_name, recip_name)
                        confirm_text = arsenal_rent_confirm_text(sword_key, recip_name, duration_secs) if ok else None
                        notif_mode   = "rent"

                    if ok:
                        _new_ach_sender    = check_achievements(u_fresh)
                        _new_ach_recipient = check_achievements(r_fresh)
                        await _su_ars(uid, u_fresh)
                        await _su_ars(recipient_data["id"], r_fresh)
                        await message.reply(confirm_text, parse_mode="HTML", reply_markup=arsenal_back_keyboard())
                        # Уведомление получателю
                        try:
                            await bot.send_message(
                                recipient_data["id"],
                                arsenal_received_text(sword_key, sender_name, notif_mode),
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                        # Уведомления о новых достижениях (у отправителя и получателя)
                        for _ach in _new_ach_sender:
                            try:
                                await message.answer(achievement_unlocked_text(_ach, lang), parse_mode="HTML")
                            except Exception:
                                pass
                        for _ach in _new_ach_recipient:
                            try:
                                _recip_lang = get_lang(r_fresh)
                                await bot.send_message(
                                    recipient_data["id"], achievement_unlocked_text(_ach, _recip_lang), parse_mode="HTML"
                                )
                            except Exception:
                                pass
                    else:
                        await message.reply(
                            arsenal_error_text(msg),
                            parse_mode="HTML", reply_markup=arsenal_back_keyboard()
                        )
            return

    # Этот хендлер нужен только пока пользователь проходит онбординг
    if u.get("onboarded", True):
        return

    # Если заблокирован — просто игнорируем (сообщение от пользователя удаляем)
    blocked, secs_left = await is_captcha_blocked(uid)
    if blocked:
        try:
            await message.delete()
        except Exception:
            pass
        return

    # Капча уже пройдена, осталось только выбрать язык
    if await is_captcha_passed(uid):
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(
            lang_choose_text("ru"),
            parse_mode="HTML",
            reply_markup=lang_choose_keyboard_start(),
        )
        return

    # Пробуем распарсить число
    try:
        user_ans = int(message.text.strip())
    except ValueError:
        try:
            await message.delete()
        except Exception:
            pass
        return

    result = await check_captcha(uid, user_ans)

    # Удаляем сообщение пользователя с ответом
    try:
        await message.delete()
    except Exception:
        pass

    pending = await get_captcha_msg(uid)

    if result["status"] == "ok":
        # Капча пройдена — начисляем награду пригласителю
        is_premium       = bool(getattr(message.from_user, "is_premium", False))
        rewarded, amount = await reward_inviter(uid, is_premium)

        # Уведомление пригласителю
        if rewarded:
            inv_uid = await get_inviter(uid)
            if inv_uid:
                from database import aio_get_user as _get_inv
                _inv_data = await _get_inv(inv_uid)
                _inv_lang = get_lang(_inv_data) if _inv_data else "ru"
                name = _esc(message.from_user.first_name or message.from_user.username or "Новый игрок")
                try:
                    await bot.send_message(
                        inv_uid,
                        refs_notif_text(name, amount, is_premium, _inv_lang),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

        # Капча пройдена → обновляем старое сообщение на выбор языка
        if pending:
            try:
                await bot.edit_message_text(
                    lang_choose_text("ru"),
                    chat_id=pending[0],
                    message_id=pending[1],
                    parse_mode="HTML",
                    reply_markup=lang_choose_keyboard_start(),
                )
                return
            except Exception:
                pass
        await message.answer(
            lang_choose_text("ru"),
            parse_mode="HTML",
            reply_markup=lang_choose_keyboard_start(),
        )

    elif result["status"] == "wrong":
        if pending:
            try:
                await bot.edit_message_text(
                    captcha_wrong_text(result["question"], result["tries_left"]),
                    chat_id=pending[0],
                    message_id=pending[1],
                    parse_mode="HTML",
                )
                return
            except Exception:
                pass
        sent = await message.answer(
            captcha_wrong_text(result["question"], result["tries_left"]),
            parse_mode="HTML",
        )
        await set_captcha_msg(uid, sent.chat.id, sent.message_id)

    elif result["status"] == "blocked":
        if pending:
            try:
                await bot.edit_message_text(
                    captcha_blocked_text(result["unblock_in_min"]),
                    chat_id=pending[0],
                    message_id=pending[1],
                    parse_mode="HTML",
                )
                return
            except Exception:
                pass
        await message.answer(
            captcha_blocked_text(result["unblock_in_min"]),
            parse_mode="HTML",
        )


# ── Рассылка: медиа (фото/видео) от админа ───────────────────────────

@dp.message(F.photo | F.video)
async def handle_rass_media(message: Message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS or not is_in_rass(uid):
        return
    await rass_fsm_message(message, ADMIN_IDS)


# ============================================================
#  ПОТОКИ ЗЕЛИЙ (POTIONS) — обработчики кнопок
# ============================================================

@dp.callback_query(F.data == "hunt_potions_menu")
async def potion_menu_callback(call: CallbackQuery):
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)
    text = potions_menu_text(lang)
    keyboard = potions_menu_keyboard(lang)
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "hunt_shop_potions")
async def potion_shop_callback(call: CallbackQuery):
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)
    text = potions_shop_text(lang)
    keyboard = potions_shop_keyboard(lang)
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "hunt_my_potions")
async def potion_my_callback(call: CallbackQuery):
    uid = call.from_user.id
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)
    text, keyboard = await asyncio.to_thread(
        lambda: (my_potions_text(uid, lang), my_potions_keyboard(uid, lang))
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("potion_info_"))
async def potion_info_callback(call: CallbackQuery):
    potion_key = call.data.replace("potion_info_", "")
    uid = call.from_user.id
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)
    text, keyboard = await asyncio.to_thread(
        lambda: (potion_detail_text(potion_key, uid, lang), potion_detail_keyboard(potion_key, lang))
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("potion_use_info_"))
async def potion_use_info_callback(call: CallbackQuery):
    potion_key = call.data.replace("potion_use_info_", "")
    uid = call.from_user.id
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)

    if potion_key == "revival":
        slots = await asyncio.to_thread(get_all_slots)
        any_dead = any(not st.get("boss_alive") for _, st in slots)
        if not any_dead:
            text = await asyncio.to_thread(potion_use_detail_text, potion_key, uid, lang)
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text="Back" if lang == "en" else "Назад",
                callback_data="hunt_my_potions",
                icon_custom_emoji_id=EMOJI_BACK
            ))
            await call.message.edit_text(
                text + "\n\n" + ("❌ No dead bosses to revive." if lang == "en" else "❌ Нет мёртвых боссов для возрождения."),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            await call.answer()
            return

    text, keyboard = await asyncio.to_thread(
        lambda: (potion_use_detail_text(potion_key, uid, lang), potion_use_detail_keyboard(potion_key, lang))
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "potion_use_revival_pick_slot")
async def potion_use_revival_pick_callback(call: CallbackQuery):
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)
    text, keyboard = await asyncio.to_thread(
        lambda: (revival_pick_slot_text(lang), revival_pick_slot_keyboard(lang))
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("use_potion_revival_"))
async def potion_use_revival_confirm_callback(call: CallbackQuery):
    slot = int(call.data.replace("use_potion_revival_", ""))
    uid = call.from_user.id
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)

    ok, msg = await asyncio.to_thread(use_potion, "revival", uid, slot, lang)

    if ok:
        _ach_newly = check_achievements(data)
        await aio_save_user(uid, data)
        await _notify_ach(uid, data, _ach_newly)
        text, keyboard = await asyncio.to_thread(
            lambda: (hunt_main_text(data, lang), hunt_main_keyboard(data, lang))
        )
        await call.message.edit_text(
            f"{msg}\n\n{text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await call.answer(msg, show_alert=True)
        text, keyboard = await asyncio.to_thread(
            lambda: (revival_pick_slot_text(lang), revival_pick_slot_keyboard(lang))
        )
        await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    await call.answer()

@dp.callback_query(F.data.startswith("use_potion_"))
async def potion_use_callback(call: CallbackQuery):
    potion_key = call.data.replace("use_potion_", "")
    uid = call.from_user.id
    data = await aio_get_or_create_user(call.from_user)
    lang = get_lang(data)

    ok, msg = await asyncio.to_thread(use_potion, potion_key, uid, None, lang)

    if ok:
        _ach_newly = check_achievements(data)
        await aio_save_user(uid, data)
        await _notify_ach(uid, data, _ach_newly)
        text, keyboard = await asyncio.to_thread(
            lambda: (my_potions_text(uid, lang), my_potions_keyboard(uid, lang))
        )
        await call.message.edit_text(
            f"{msg}\n\n{text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await call.answer(msg, show_alert=True)

    await call.answer()


# ---------- CALLBACK HANDLER ----------

@dp.callback_query(~F.data.startswith("city_") & ~F.data.startswith("crystop_"))
async def handle_callback(call: CallbackQuery):
    chat_id    = call.message.chat.id
    message_id = call.message.message_id
    user       = call.from_user

    # ── Берём персональный Lock и держим его на всё время обработки ──
    lock = await _get_user_lock(user.id)
    async with lock:
        data = await aio_get_or_create_user(user)
        await aio_track_user(user.id)
        lang = get_lang(data)

        async def edit(text, kb, md="HTML"):
            for attempt in range(2):
                try:
                    await call.message.edit_text(
                        text,
                        parse_mode=md,
                        reply_markup=kb,
                        disable_web_page_preview=True
                    )
                    return
                except Exception as e:
                    if "message is not modified" in str(e):
                        return
                    if attempt == 0:
                        await asyncio.sleep(0.4)
                        continue
                    print(e)

        cd = call.data

        # ── Рассылка: кнопки подтверждения ──
        if cd in ("rass_confirm_yes", "rass_confirm_no"):
            await rass_fsm_callback(call, ADMIN_IDS, bot)
            return

        # ── Проверка владельца кнопок ──
        # Кнопки может нажимать только тот пользователь, который вызвал команду.
        # Определяем владельца по reply_to_message (наши хендлеры используют message.reply)
        _owner_msg = call.message.reply_to_message
        if _owner_msg and _owner_msg.from_user:
            _owner_uid = _owner_msg.from_user.id
            if user.id != _owner_uid:
                _err = "❌ Это не ваша кнопка!" if lang == "ru" else "❌ This is not your button!"
                await call.answer(_err, show_alert=True)
                return

        # Если пользователь уходит из экрана с ожиданием текстового ввода
        # для клана (поиск/создание/кик/депозит/вывод/заявка) на любой другой
        # экран — сбрасываем "висящие" флаги, чтобы случайный текст потом
        # не был принят за этот ввод
        _KLAN_INPUT_CALLBACKS = {"klan_search", "klan_create", "klan_kick", "klan_deposit", "klan_withdraw", "klan_chat_link", "klan_do_search"}
        if cd not in _KLAN_INPUT_CALLBACKS and not cd.startswith("klan_apply_"):
            if _clear_klan_pending(data):
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)

        # Сбрасываем ожидание ввода цели вызова при любом callback,
        # кроме самого экрана ввода (duel_challenge_start) и кнопки отмены.
        if cd not in ("duel_challenge_start", "duel_challenge_cancel"):
            _challenge_input_pending.pop(user.id, None)

        # ===== ЗЕЛЬЯ — НОВЫЕ ОБРАБОТЧИКИ (добавлены выше) =====
        # Обработчики зелий находятся выше в секции "ПОТОКИ ЗЕЛИЙ"

        # ===== ВКЛАДЫ =====

        if cd == "cdl_main":
            await edit(cdl_main_text(data), cdl_main_keyboard(user.id))
            await call.answer()
            return

        if cd.startswith("cdl_info_"):
            dep_key = cd[len("cdl_info_"):]
            if dep_key not in _CDL_DEPOSITS_BY_KEY:
                await call.answer("Неизвестный вклад", show_alert=True)
                return
            can = data.get("balance", 0) >= _CDL_DEPOSITS_BY_KEY[dep_key]["min"]
            await edit(cdl_detail_text(dep_key, data), cdl_detail_keyboard(dep_key, can, uid=user.id))
            await call.answer()
            return

        if cd.startswith("cdl_open_"):
            dep_key = cd[len("cdl_open_"):]
            if dep_key not in _CDL_DEPOSITS_BY_KEY:
                await call.answer("Неизвестный вклад", show_alert=True)
                return
            dep = _CDL_DEPOSITS_BY_KEY[dep_key]
            if data.get("balance", 0) < dep["min"]:
                await call.answer("❌ Недостаточно монет!", show_alert=True)
                return
            if await _cdl_count_active(user.id) >= 8:
                await call.answer("❌ Максимум 8 активных вкладов!", show_alert=True)
                return
            from cdl import aio_check_deposit_limit as _cdl_check_limit
            _lim_ok, _lim_used, _lim_max = await _cdl_check_limit(user.id, dep_key)
            if not _lim_ok:
                await call.answer(f"🚫 Лимит исчерпан ({_lim_used}/{_lim_max}). Попробуй позже.", show_alert=True)
                return
            _cdl_input_pending[user.id] = dep_key
            _cdl_input_msg[user.id] = (call.message.chat.id, call.message.message_id)
            await edit(cdl_input_text(dep_key, data), cdl_input_keyboard(dep_key))
            await call.answer()
            return

        if cd == "cdl_cant_afford":
            await call.answer("❌ Пополни баланс — добывай монеты!", show_alert=True)
            return

        if cd == "cdl_limit_reached":
            await call.answer("🚫 Лимит вкладов исчерпан. Попробуй позже.", show_alert=True)
            return

        if cd.startswith("cdl_confirm_"):
            rest = cd[len("cdl_confirm_"):]
            idx  = rest.rfind("_")
            if idx < 0:
                await call.answer("Ошибка", show_alert=True)
                return
            dep_key = rest[:idx]
            try:
                amount = int(rest[idx + 1:])
            except ValueError:
                await call.answer("Ошибка суммы", show_alert=True)
                return
            if dep_key not in _CDL_DEPOSITS_BY_KEY:
                await call.answer("Неизвестный вклад", show_alert=True)
                return
            dep = _CDL_DEPOSITS_BY_KEY[dep_key]
            bal = data.get("balance", 0)
            if amount < dep["min"]:
                await call.answer("❌ Сумма ниже минимума!", show_alert=True)
                return
            if amount > bal:
                await call.answer("❌ Недостаточно монет!", show_alert=True)
                return
            if await _cdl_count_active(user.id) >= 8:
                await call.answer("❌ Максимум 8 активных вкладов!", show_alert=True)
                return
            from cdl import aio_check_deposit_limit as _cdl_check_limit2
            _lim_ok2, _lim_used2, _lim_max2 = await _cdl_check_limit2(user.id, dep_key)
            if not _lim_ok2:
                await call.answer(f"🚫 Лимит исчерпан ({_lim_used2}/{_lim_max2}). Попробуй позже.", show_alert=True)
                return
            data["balance"] = bal - amount
            data["deposits_opened"] = data.get("deposits_opened", 0) + 1
            _dep_types = data.setdefault("deposits_types_opened", [])
            if dep_key not in _dep_types:
                _dep_types.append(dep_key)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await _cdl_open_deposit(user.id, dep_key, amount)
            await edit(cdl_opened_text(dep_key, amount), cdl_main_keyboard(user.id))
            await call.answer("✅ Вклад открыт!")
            return

        if cd == "cdl_claim_all":
            ready = await _cdl_get_ready(user.id)
            if not ready:
                await call.answer("Нет готовых вкладов!", show_alert=True)
                return
            total_payout = 0
            total_profit = 0
            count = 0
            for dep in ready:
                payout = await _cdl_claim(dep["id"])
                if payout is not None:
                    total_payout += payout
                    total_profit += payout - dep["amount"]
                    count += 1
            if count == 0:
                await call.answer("Нет готовых вкладов!", show_alert=True)
                return
            data["balance"] = data.get("balance", 0) + total_payout
            data["ref_income"] = data.get("ref_income", 0) + total_payout
            data["deposits_claimed"] = data.get("deposits_claimed", 0) + count
            data["deposits_total_profit"] = data.get("deposits_total_profit", 0) + total_profit
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await edit(cdl_claim_text(total_payout, total_profit, count), cdl_main_keyboard(user.id))
            await call.answer(f"💰 +{format_amount(total_payout)} монет!")
            return

        # ===== РЕФЕРАЛЫ =====
        if cd == "refs_main":
            bot_me = await bot.get_me()
            _txt = await refs_main_text(user.id, bot_me.username, lang)
            await edit(_txt, refs_main_keyboard(bot_me.username, user.id, lang))
            await call.answer()
            return

        if cd == "refs_list":
            _txt = await refs_list_text(user.id, lang)
            await edit(_txt, refs_list_keyboard(lang))
            await call.answer()
            return

        if cd.startswith("reftop_"):
            period = cd.removeprefix("reftop_")
            if period not in ("today", "week", "alltime"):
                period = "alltime"
            _txt = await reftop_text(period, user.id, lang)
            await edit(_txt, reftop_keyboard(period, lang))
            await call.answer()
            return

        # ===== КЛАНЫ =====

        if cd == "klan_main":
            await edit(await klan_main_text(lang), await klan_main_keyboard(user.id, lang))
            await call.answer()
            return

        if cd == "klan_top":
            clans = await get_top_clans(10)
            await edit(klan_top_text(clans, lang), klan_top_keyboard(lang))
            await call.answer()
            return

        if cd == "klan_stats":
            await edit(await klan_stats_text(lang), klan_stats_keyboard(lang))
            await call.answer()
            return

        if cd == "klan_my":
            m = await get_member(user.id)
            if not m:
                await call.answer("⚔️ Ты не в клане!" if lang == "ru" else "⚔️ You are not in a clan!", show_alert=True)
                return
            clan = await get_clan(m["clan_id"])
            cnt  = await get_member_count(m["clan_id"])
            await edit(my_klan_text(clan, m, cnt, lang), await my_klan_keyboard(user.id, lang))
            await call.answer()
            return

        if cd == "klan_members":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            clan    = await get_clan(m["clan_id"])
            members = await get_clan_members(m["clan_id"])
            await edit(klan_members_text(clan, members, lang), klan_back_keyboard("klan_my", lang))
            await call.answer()
            return

        if cd == "klan_treasury":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            clan = await get_clan(m["clan_id"])
            await edit(klan_treasury_text(clan, lang), klan_treasury_keyboard(lang))
            await call.answer()
            return

        if cd == "klan_level_up":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            res = await level_up_clan(user.id)
            if res.get("ok"):
                alert = (
                    f'✅ Клан прокачан до {res["new_level"]} уровня! (-{res["cost"]} 🟣)'
                    if lang == "ru" else
                    f'✅ Clan leveled up to {res["new_level"]}! (-{res["cost"]} 🟣)'
                )
            else:
                err = res.get("error")
                if err == "not_creator":
                    alert = "Только создатель клана может прокачивать уровень." if lang == "ru" else "Only the clan creator can level up the clan."
                elif err == "max_level":
                    alert = "Уже максимальный уровень клана." if lang == "ru" else "Clan is already at max level."
                elif err == "not_enough_antimatter":
                    alert = (
                        f'Недостаточно антиматерии: {res.get("have", 0)}/{res.get("cost", 0)} 🟣'
                        if lang == "ru" else
                        f'Not enough antimatter: {res.get("have", 0)}/{res.get("cost", 0)} 🟣'
                    )
                else:
                    alert = "Не удалось прокачать уровень, попробуй ещё раз." if lang == "ru" else "Couldn't level up, try again."
            clan = await get_clan(m["clan_id"])
            if clan:
                cnt = await get_member_count(m["clan_id"])
                await edit(my_klan_text(clan, m, cnt, lang), await my_klan_keyboard(user.id, lang))
            await call.answer(alert, show_alert=True)
            return

        if cd == "klan_quests":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            clan     = await get_clan(m["clan_id"])
            quests   = await get_daily_quests(m["clan_id"])
            personal = await get_personal_quests(user.id)
            await edit(
                klan_quests_text(clan, quests, lang, personal=personal, member=m),
                klan_quests_keyboard(lang),
            )
            await call.answer()
            return

        if cd == "klan_apps":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель клана!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            clan = await get_clan(m["clan_id"])
            apps, total = await get_applications(m["clan_id"], page=0)
            await edit(klan_applications_text(clan, apps, 0, total, lang), klan_applications_keyboard(apps, 0, total, lang))
            await call.answer()
            return

        if cd == "klan_withdraw_list":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель клана!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            clan = await get_clan(m["clan_id"])
            reqs = await get_withdrawal_requests(m["clan_id"])
            await edit(klan_withdrawal_requests_text(clan, reqs, lang), klan_withdrawal_keyboard(reqs, lang))
            await call.answer()
            return

        if cd == "klan_search":
            # Показываем все кланы сразу, страница 0
            results, total = await search_clans("", page=0)
            await edit(
                klan_search_text("", results, 0, total, lang),
                klan_search_keyboard(results, "", 0, total, lang),
            )
            await call.answer()
            return

        if cd == "klan_create":
            if await get_member(user.id):
                await call.answer("❌ Ты уже в клане!" if lang == "ru" else "❌ You are already in a clan!", show_alert=True)
                return
            bal = data.get("balance", 0)
            prompt = (
                f'➕ <b>Создание клана</b>\n\n'
                f'<blockquote>'
                f'Стоимость: <b>{format_amount(CREATE_COST)}</b> {_COIN}  ·  Твой баланс: <b>{format_amount(bal)}</b> {_COIN}\n\n'
                f'Отправь <b>название</b> клана ({MIN_CLAN_NAME}–{MAX_CLAN_NAME} символов):'
                f'</blockquote>'
            ) if lang == "ru" else (
                f'➕ <b>Create Clan</b>\n\n'
                f'<blockquote>'
                f'Cost: <b>{format_amount(CREATE_COST)}</b> {_COIN}  ·  Your balance: <b>{format_amount(bal)}</b> {_COIN}\n\n'
                f'Send the clan <b>name</b> ({MIN_CLAN_NAME}–{MAX_CLAN_NAME} chars):'
                f'</blockquote>'
            )
            await edit(prompt, klan_back_keyboard("klan_main", lang))
            data["_klan_create_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        if cd == "klan_leave":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            if m["role"] == "creator":
                err = (
                    "❌ Создатель не может покинуть клан — сначала расформируй его."
                    if lang == "ru" else
                    "❌ Creator cannot leave — disband the clan instead."
                )
                await call.answer(err, show_alert=True)
                return
            clan = await get_clan(m["clan_id"])
            clan_name = clan["name"] if clan else "?"
            if lang == "ru":
                confirm_text = (
                    f'<tg-emoji emoji-id="5325547803936572038">⚠️</tg-emoji> <b>Покинуть клан?</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>Клан:</b> {clan_name}\n\n'
                    f'Ты уверен, что хочешь покинуть клан?\n'
                    f'Это действие <b>необратимо</b>.'
                    f'</blockquote>'
                )
            else:
                confirm_text = (
                    f'<tg-emoji emoji-id="5325547803936572038">⚠️</tg-emoji> <b>Leave Clan?</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>Clan:</b> {clan_name}\n\n'
                    f'Are you sure you want to leave this clan?\n'
                    f'This action is <b>irreversible</b>.'
                    f'</blockquote>'
                )
            builder_conf = InlineKeyboardBuilder()
            builder_conf.row(
                InlineKeyboardButton(
                    text="✅ Да, покинуть" if lang == "ru" else "✅ Yes, leave",
                    callback_data="klan_leave_confirm",
                    style="danger"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена" if lang == "ru" else "❌ Cancel",
                    callback_data="klan_my"
                ),
            )
            await edit(confirm_text, builder_conf.as_markup())
            await call.answer()
            return

        if cd == "klan_leave_confirm":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            res = await leave_clan(user.id)
            if res["ok"]:
                if lang == "ru":
                    success_text = (
                        f'<tg-emoji emoji-id="5325547803936572038">👋</tg-emoji> <b>Ты покинул клан</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>Ты успешно вышел из клана.\nУдачи в поисках нового братства!</blockquote>'
                    )
                else:
                    success_text = (
                        f'<tg-emoji emoji-id="5325547803936572038">👋</tg-emoji> <b>You left the clan</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>You have successfully left the clan.\nGood luck finding a new one!</blockquote>'
                    )
                builder_back = InlineKeyboardBuilder()
                builder_back.row(InlineKeyboardButton(
                    text="🏠 К кланам" if lang == "ru" else "🏠 Clans",
                    callback_data="klan_main"
                ))
                await edit(success_text, builder_back.as_markup())
            else:
                err = (
                    "❌ Создатель не может покинуть клан — расформируй его."
                    if lang == "ru" else
                    "❌ Creator cannot leave — disband the clan instead."
                )
                await call.answer(err, show_alert=True)
            return

        if cd == "klan_disband":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            clan = await get_clan(m["clan_id"])
            clan_name = clan["name"] if clan else "?"
            treasury  = clan.get("treasury", 0) if clan else 0
            if lang == "ru":
                confirm_text = (
                    f'<tg-emoji emoji-id="5325547803936572038">💥</tg-emoji> <b>Расформировать клан?</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>Клан:</b> {clan_name}\n'
                    f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Казна:</b> {format_amount(treasury)} монет\n\n'
                    f'Все участники будут исключены.\n'
                    f'Казна вернётся тебе на баланс.\n'
                    f'Это действие <b>необратимо</b>!'
                    f'</blockquote>'
                )
            else:
                confirm_text = (
                    f'<tg-emoji emoji-id="5325547803936572038">💥</tg-emoji> <b>Disband Clan?</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>Clan:</b> {clan_name}\n'
                    f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Treasury:</b> {format_amount(treasury)} coins\n\n'
                    f'All members will be removed.\n'
                    f'Treasury will be returned to you.\n'
                    f'This action is <b>irreversible</b>!'
                    f'</blockquote>'
                )
            builder_conf = InlineKeyboardBuilder()
            builder_conf.row(
                InlineKeyboardButton(
                    text="💥 Да, расформировать" if lang == "ru" else "💥 Yes, disband",
                    callback_data="klan_disband_confirm",
                    style="danger"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена" if lang == "ru" else "❌ Cancel",
                    callback_data="klan_my"
                ),
            )
            await edit(confirm_text, builder_conf.as_markup())
            await call.answer()
            return

        if cd == "klan_disband_confirm":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            res = await disband_clan(user.id)
            if res["ok"]:
                data = await aio_get_or_create_user(user)  # обновляем баланс в data
                if lang == "ru":
                    success_text = (
                        f'<tg-emoji emoji-id="5325547803936572038">💥</tg-emoji> <b>Клан расформирован</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>'
                        f'Клан был расформирован.\n'
                        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Казна возвращена на твой баланс.'
                        f'</blockquote>'
                    )
                else:
                    success_text = (
                        f'<tg-emoji emoji-id="5325547803936572038">💥</tg-emoji> <b>Clan Disbanded</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>'
                        f'The clan has been disbanded.\n'
                        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Treasury returned to your balance.'
                        f'</blockquote>'
                    )
                builder_back = InlineKeyboardBuilder()
                builder_back.row(InlineKeyboardButton(
                    text="🏠 К кланам" if lang == "ru" else "🏠 Clans",
                    callback_data="klan_main"
                ))
                await edit(success_text, builder_back.as_markup())
            return

        if cd == "klan_kick":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            prompt = (
                "🚫 <b>Исключить участника</b>\n\n"
                "<blockquote>Отправь юзернейм (@username) или ID участника которого хочешь исключить:</blockquote>"
            ) if lang == "ru" else (
                "🚫 <b>Kick Member</b>\n\n"
                "<blockquote>Send the @username or ID of the member you want to kick:</blockquote>"
            )
            await edit(prompt, klan_back_keyboard("klan_my", lang))
            data["_klan_kick_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        if cd == "klan_deposit":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            bal = data.get("balance", 0)
            prompt = (
                f'➕ <b>Пополнить казну</b>\n\n'
                f'<blockquote>Твой баланс: <b>{format_amount(bal)}</b> {_COIN}\n\nОтправь сумму для пополнения:</blockquote>'
            ) if lang == "ru" else (
                f'➕ <b>Deposit to Treasury</b>\n\n'
                f'<blockquote>Your balance: <b>{format_amount(bal)}</b> {_COIN}\n\nSend the amount to deposit:</blockquote>'
            )
            await edit(prompt, klan_back_keyboard("klan_treasury", lang))
            data["_klan_deposit_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        if cd == "klan_withdraw":
            m = await get_member(user.id)
            if not m:
                await call.answer()
                return
            clan = await get_clan(m["clan_id"])
            prompt = (
                f'➖ <b>Запрос на вывод</b>\n\n'
                f'<blockquote>Казна клана: <b>{format_amount(clan["treasury"])}</b> {_COIN}\n\n'
                f'Отправь сумму и причину через «|»:\n'
                f'<code>1000 | нужно на апгрейд</code></blockquote>'
            ) if lang == "ru" else (
                f'➖ <b>Withdrawal Request</b>\n\n'
                f'<blockquote>Clan treasury: <b>{format_amount(clan["treasury"])}</b> {_COIN}\n\n'
                f'Send amount and reason separated by «|»:\n'
                f'<code>1000 | need for upgrade</code></blockquote>'
            )
            await edit(prompt, klan_back_keyboard("klan_treasury", lang))
            data["_klan_withdraw_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        # Поиск кланов — активация текстового ввода через отдельную кнопку
        if cd == "klan_do_search":
            prompt = (
                f'<tg-emoji emoji-id="5231012545799666522">🔍</tg-emoji> <b>Поиск клана</b>\n\n'
                f'<blockquote>Отправь <b>название</b> или <b>ID</b> клана:</blockquote>'
            ) if lang == "ru" else (
                f'<tg-emoji emoji-id="5231012545799666522">🔍</tg-emoji> <b>Clan Search</b>\n\n'
                f'<blockquote>Send the clan <b>name</b> or <b>ID</b>:</blockquote>'
            )
            await edit(prompt, klan_back_keyboard("klan_search", lang))
            data["_klan_search_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        # Привязать чат клана
        if cd == "klan_chat_link":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            prompt = (
                f'<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> <b>Привязать чат клана</b>\n\n'
                f'<blockquote>'
                f'Отправь <b>ссылку</b> или <b>@username</b> чата.\n\n'
                f'⚠️ Бот должен быть <b>администратором</b> в этом чате.\n\n'
                f'Примеры:\n'
                f'<code>@myClanChat</code>\n'
                f'<code>https://t.me/myClanChat</code>'
                f'</blockquote>'
            ) if lang == "ru" else (
                f'<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> <b>Link Clan Chat</b>\n\n'
                f'<blockquote>'
                f'Send the chat <b>link</b> or <b>@username</b>.\n\n'
                f'⚠️ The bot must be an <b>administrator</b> in that chat.\n\n'
                f'Examples:\n'
                f'<code>@myClanChat</code>\n'
                f'<code>https://t.me/myClanChat</code>'
                f'</blockquote>'
            )
            await edit(prompt, klan_back_keyboard("klan_my", lang))
            data["_klan_chat_pending"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        # Открепить чат клана
        if cd == "klan_chat_unlink":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            await remove_clan_chat(m["clan_id"])
            clan = await get_clan(m["clan_id"])
            cnt  = await get_member_count(m["clan_id"])
            ok_msg = "✅ Чат откреплён." if lang == "ru" else "✅ Chat unlinked."
            await call.answer(ok_msg, show_alert=True)
            await edit(my_klan_text(clan, m, cnt, lang), await my_klan_keyboard(user.id, lang))
            return

        # Открыть чат клана (ссылка — через answer alert или InlineKeyboardButton url)
        # Закрытый чат — показываем alert (публичные чаты открываются через URL-кнопку напрямую)
        if cd == "klan_chat_private":
            await call.answer(
                "💬 Чат закрытый — обратись к создателю клана за инвайтом." if lang == "ru"
                else "💬 Chat is private — ask the clan creator for an invite.",
                show_alert=True
            )
            return

        # Просмотр карточки клана
        if cd.startswith("klan_view_"):
            clan_id = int(cd.split("_")[-1])
            clan    = await get_clan(clan_id)
            if not clan:
                await call.answer("❌ Клан не найден" if lang == "ru" else "❌ Clan not found", show_alert=True)
                return
            cnt = await get_member_count(clan_id)
            await edit(klan_card_text(clan, cnt, lang), await klan_card_keyboard(clan_id, user.id, lang))
            await call.answer()
            return

        # Подача заявки в клан
        if cd.startswith("klan_apply_"):
            clan_id = int(cd.split("_")[-1])
            clan    = await get_clan(clan_id)
            if not clan:
                await call.answer()
                return
            import html as _html_klan
            _clan_name = _html_klan.escape(clan["name"])
            prompt = (
                f'📩 <b>Заявка в {_clan_name}</b>\n\n'
                f'<blockquote>Отправь сопроводительное сообщение (или «—» чтобы пропустить):</blockquote>'
            ) if lang == "ru" else (
                f'📩 <b>Apply to {_clan_name}</b>\n\n'
                f'<blockquote>Send a short message (or «—» to skip):</blockquote>'
            )
            await edit(prompt, klan_back_keyboard(f"klan_view_{clan_id}", lang))
            data["_klan_apply_pending"] = clan_id
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            return

        # Принять заявку
        if cd.startswith("klan_app_accept_"):
            app_id = int(cd.split("_")[-1])
            res    = await accept_application(user.id, app_id)
            m      = await get_member(user.id)
            if res["ok"]:
                # Уведомить принятого
                try:
                    ntf = "✅ Твоя заявка в клан принята!" if lang == "ru" else "✅ Your clan application was accepted!"
                    await bot.send_message(res["uid"], ntf, parse_mode="HTML")
                except Exception:
                    pass
                data["clan_applications_accepted"] = data.get("clan_applications_accepted", 0) + 1
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)
                await call.answer("✅ Принят!" if lang == "ru" else "✅ Accepted!", show_alert=True)
            else:
                await call.answer(f"❌ {res['error']}", show_alert=True)
            # Обновить список заявок
            if m:
                clan = await get_clan(m["clan_id"])
                apps, total = await get_applications(m["clan_id"], page=0)
                await edit(klan_applications_text(clan, apps, 0, total, lang), klan_applications_keyboard(apps, 0, total, lang))
            return

        # Отклонить заявку
        if cd.startswith("klan_app_reject_"):
            app_id = int(cd.split("_")[-1])
            res    = await reject_application(user.id, app_id)
            m      = await get_member(user.id)
            if res["ok"]:
                try:
                    ntf = "❌ Твоя заявка в клан отклонена." if lang == "ru" else "❌ Your clan application was rejected."
                    await bot.send_message(res["uid"], ntf, parse_mode="HTML")
                except Exception:
                    pass
                await call.answer("❌ Отклонено." if lang == "ru" else "❌ Rejected.", show_alert=True)
            if m:
                clan = await get_clan(m["clan_id"])
                apps, total = await get_applications(m["clan_id"], page=0)
                await edit(klan_applications_text(clan, apps, 0, total, lang), klan_applications_keyboard(apps, 0, total, lang))
            return

        # Принять все заявки
        if cd == "klan_app_accept_all":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            res = await accept_all_applications(user.id)
            if res["ok"]:
                msg = (f'✅ Принято: {res["accepted"]}' + (f', пропущено: {res["skipped"]}' if res["skipped"] else '')) \
                    if lang == "ru" else \
                    (f'✅ Accepted: {res["accepted"]}' + (f', skipped: {res["skipped"]}' if res["skipped"] else ''))
                data["clan_applications_accepted"] = data.get("clan_applications_accepted", 0) + res["accepted"]
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)
                await call.answer(msg, show_alert=True)
            clan = await get_clan(m["clan_id"])
            apps, total = await get_applications(m["clan_id"], page=0)
            await edit(klan_applications_text(clan, apps, 0, total, lang), klan_applications_keyboard(apps, 0, total, lang))
            return

        # Отклонить все заявки
        if cd == "klan_app_reject_all":
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer("❌ Только создатель!" if lang == "ru" else "❌ Creator only!", show_alert=True)
                return
            res = await reject_all_applications(user.id)
            if res["ok"]:
                msg = f'❌ Отклонено: {res["rejected"]}' if lang == "ru" else f'❌ Rejected: {res["rejected"]}'
                await call.answer(msg, show_alert=True)
            clan = await get_clan(m["clan_id"])
            apps, total = await get_applications(m["clan_id"], page=0)
            await edit(klan_applications_text(clan, apps, 0, total, lang), klan_applications_keyboard(apps, 0, total, lang))
            return

        # Пагинация заявок
        if cd.startswith("klan_apps_page_"):
            m = await get_member(user.id)
            if not m or m["role"] != "creator":
                await call.answer()
                return
            page = int(cd.removeprefix("klan_apps_page_"))
            clan = await get_clan(m["clan_id"])
            apps, total = await get_applications(m["clan_id"], page=page)
            await edit(klan_applications_text(clan, apps, page, total, lang), klan_applications_keyboard(apps, page, total, lang))
            await call.answer()
            return

        # Пагинация поиска кланов
        if cd.startswith("klan_search_page_"):
            raw   = cd.removeprefix("klan_search_page_")
            parts = raw.split("_", 1)
            page  = int(parts[0])
            query = parts[1] if len(parts) > 1 else ""
            results, total = await search_clans(query, page=page)
            await edit(klan_search_text(query, results, page, total, lang), klan_search_keyboard(results, query, page, total, lang))
            await call.answer()
            return

        # Одобрить запрос на вывод
        if cd.startswith("klan_wd_approve_"):
            req_id = int(cd.split("_")[-1])
            res    = await approve_withdrawal(user.id, req_id)
            m      = await get_member(user.id)
            if res["ok"]:
                try:
                    ntf = f'✅ Твой запрос на вывод <b>{format_amount(res["amount"])}</b> {_COIN} из казны одобрен!' \
                        if lang == "ru" else \
                        f'✅ Your withdrawal request for <b>{format_amount(res["amount"])}</b> {_COIN} was approved!'
                    await bot.send_message(res["uid"], ntf, parse_mode="HTML")
                except Exception:
                    pass
                data["clan_withdrawals_approved"] = data.get("clan_withdrawals_approved", 0) + 1
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)
                await call.answer("✅ Одобрено!" if lang == "ru" else "✅ Approved!", show_alert=True)
            else:
                await call.answer(f"❌ {res['error']}", show_alert=True)
            if m:
                clan = await get_clan(m["clan_id"])
                reqs = await get_withdrawal_requests(m["clan_id"])
                await edit(klan_withdrawal_requests_text(clan, reqs, lang), klan_withdrawal_keyboard(reqs, lang))
            return

        # Отклонить запрос на вывод
        if cd.startswith("klan_wd_reject_"):
            req_id = int(cd.split("_")[-1])
            res    = await reject_withdrawal(user.id, req_id)
            m      = await get_member(user.id)
            if res["ok"]:
                try:
                    ntf = "❌ Твой запрос на вывод из казны отклонён." \
                        if lang == "ru" else "❌ Your withdrawal request was rejected."
                    await bot.send_message(res["uid"], ntf, parse_mode="HTML")
                except Exception:
                    pass
                await call.answer("❌ Отклонено." if lang == "ru" else "❌ Rejected.", show_alert=True)
            if m:
                clan = await get_clan(m["clan_id"])
                reqs = await get_withdrawal_requests(m["clan_id"])
                await edit(klan_withdrawal_requests_text(clan, reqs, lang), klan_withdrawal_keyboard(reqs, lang))
            return

        # ===== NOOP =====
        if cd == "noop":
            await call.answer()
            return

        # ===== ПРОФИЛЬ =====
        if cd == "profile":
            await edit(profile_text(data), profile_keyboard(lang))
            return

        # ===== ПРОМОКОД — кнопка в профиле =====
        if cd == "promo_input":
            uid = call.from_user.id
            _promo_pending[uid] = True
            await call.answer()
            await call.message.answer(
                promo_input_text(lang),
                parse_mode="HTML",
            )
            return

        # ===== МАГАЗИН =====
        if cd == "shop":
            await edit(SHOP_TEXT, shop_main_keyboard())
            return

        if cd == "shop_cases":
            await edit(cases_shop_text(data, lang), cases_shop_keyboard(lang))
            return

        # ===== КЕЙСЫ: карточка кейса (инфо + кнопка купить) =====
        if cd.startswith("case_info_"):
            case_key = cd.removeprefix("case_info_")
            from shop import case_detail_text, case_detail_keyboard, CASES
            case     = CASES.get(case_key)
            if not case:
                await call.answer("❌ Кейс не найден.", show_alert=True)
                return
            can_buy = data.get("balance", 0) >= case["cost"]
            await edit(case_detail_text(data, case_key, lang), case_detail_keyboard(case_key, can_buy, lang))
            return

        # ===== КЕЙСЫ: купить и открыть =====
        if cd.startswith("case_open_"):
            case_key = cd.removeprefix("case_open_")
            ok, msg, instance = open_case(data, case_key, lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await edit(msg, cases_shop_keyboard(lang))
            else:
                await call.answer(_plain(msg), show_alert=True)
            return

        # ===== ИНВЕНТАРЬ — кнопка из профиля =====
        if cd == "profile_inv":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=" Активные" if lang == "ru" else " Active",
                        callback_data="inv_active_boosters",
                        icon_custom_emoji_id="5206607081334906820",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(lang, "btn_back"),
                        callback_data="profile",
                        icon_custom_emoji_id=EMOJI_BACK,
                    )
                ],
            ])
            await edit(unified_inventory_text(data, lang), kb)
            return

        # ===== ИНВЕНТАРЬ — активные бусты =====
        if cd == "inv_active_boosters":
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=t(lang, "btn_back"),
                    callback_data="profile_inv",
                    icon_custom_emoji_id=EMOJI_BACK,
                )
            ]])
            await edit(get_all_active_boosters_text(data, lang), kb)
            return

        # ===== ИНВЕНТАРЬ — главная страница выбора раздела =====
        if cd == "profile_boosters":
            await edit(inventory_main_text(data, lang), inventory_main_keyboard(lang))
            return

        # ===== ИНВЕНТАРЬ — раздел ускорителей кирки =====
        if cd == "inv_boosters":
            await edit(boosters_inventory_text(data, lang), boosters_inventory_keyboard(data, lang))
            return

        # ===== ИНВЕНТАРЬ — раздел XP-предметов =====
        if cd == "inv_xp":
            await edit(xp_inventory_text(data, lang), xp_inventory_keyboard(data, lang))
            return

        # ===== КАРТОЧКА УСКОРИТЕЛЯ КИРКИ =====
        if cd.startswith("boost_info_"):
            instance_id = cd.removeprefix("boost_info_")
            await edit(booster_detail_text(data, instance_id, lang), booster_detail_keyboard(data, instance_id, lang))
            return

        # ===== АКТИВАЦИЯ УСКОРИТЕЛЯ КИРКИ =====
        if cd.startswith("boost_activate_"):
            instance_id = cd.removeprefix("boost_activate_")
            ok, msg = activate_booster(data, instance_id, lang=lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer("⚡ Ускоритель активирован!" if lang == "ru" else "⚡ Booster activated!", show_alert=True)
                await edit(boosters_inventory_text(data, lang), boosters_inventory_keyboard(data, lang))
            elif msg.startswith("CONFIRM_REPLACE:"):
                await edit(booster_confirm_replace_text(data, instance_id, lang), booster_confirm_replace_keyboard(instance_id, lang))
            else:
                await call.answer(msg, show_alert=True)
            return

        # ===== ПОДТВЕРЖДЕНИЕ ЗАМЕНЫ УСКОРИТЕЛЯ КИРКИ =====
        if cd.startswith("boost_replace_"):
            instance_id = cd.removeprefix("boost_replace_")
            ok, msg = activate_booster(data, instance_id, force=True, lang=lang)
            await call.answer(("⚡ Ускоритель заменён!" if lang == "ru" else "⚡ Booster replaced!") if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(boosters_inventory_text(data, lang), boosters_inventory_keyboard(data, lang))
            return

        # ===== ПРОДАЖА УСКОРИТЕЛЯ КИРКИ =====
        if cd.startswith("boost_sell_"):
            instance_id = cd.removeprefix("boost_sell_")
            ok, msg, price = sell_booster(data, instance_id, lang)
            await call.answer(f"💸 {'Продано' if lang == 'ru' else 'Sold'} {format_amount(price)}!" if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(boosters_inventory_text(data, lang), boosters_inventory_keyboard(data, lang))
            return

        # ===== КАРТОЧКА XP-ПРЕДМЕТА =====
        if cd.startswith("xp_info_"):
            instance_id = cd.removeprefix("xp_info_")
            inv  = data.get("xp_inventory", [])
            item = next((x for x in inv if x["instance_id"] == instance_id), None)
            if not item:
                await call.answer("❌ Предмет не найден.", show_alert=True)
                return
            is_boost = item["type"] == "xp_boost"
            await edit(xp_item_detail_text(data, instance_id, lang), xp_item_detail_keyboard(instance_id, is_boost, lang))
            return

        # ===== ИСПОЛЬЗОВАНИЕ XP-ПРЕДМЕТА =====
        if cd.startswith("xp_use_"):
            instance_id = cd.removeprefix("xp_use_")
            ok, msg = use_xp_item(data, instance_id, lang=lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer("✅ Применено!" if lang == "ru" else "✅ Applied!", show_alert=True)
                await edit(xp_inventory_text(data, lang), xp_inventory_keyboard(data, lang))
            elif msg.startswith("CONFIRM_REPLACE_XP:"):
                await edit(xp_confirm_replace_text(data, instance_id, lang), xp_confirm_replace_keyboard(instance_id, lang))
            else:
                await call.answer(msg, show_alert=True)
            return

        # ===== ПОДТВЕРЖДЕНИЕ ЗАМЕНЫ XP-УСКОРИТЕЛЯ =====
        if cd.startswith("xp_replace_"):
            instance_id = cd.removeprefix("xp_replace_")
            ok, msg = use_xp_item(data, instance_id, force=True, lang=lang)
            await call.answer(("✅ XP-ускоритель заменён!" if lang == "ru" else "✅ XP booster replaced!") if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(xp_inventory_text(data, lang), xp_inventory_keyboard(data, lang))
            return

        # ===== ПРОДАЖА XP-ПРЕДМЕТА =====
        if cd.startswith("xp_sell_"):
            instance_id = cd.removeprefix("xp_sell_")
            ok, msg, price = sell_xp_item(data, instance_id, lang)
            await call.answer(f"💸 {'Продано' if lang == 'ru' else 'Sold'} {format_amount(price)}!" if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(xp_inventory_text(data, lang), xp_inventory_keyboard(data, lang))
            return

        # ===== ИНВЕНТАРЬ — раздел усилителей и ядов =====
        if cd == "inv_enh":
            await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            return

        # ===== КАРТОЧКА УСИЛИТЕЛЯ / ЯДА =====
        if cd.startswith("enh_info_"):
            instance_id = cd.removeprefix("enh_info_")
            inv  = data.get("enh_inventory", [])
            item = next((x for x in inv if x["instance_id"] == instance_id), None)
            if not item:
                await call.answer("❌ Предмет не найден.", show_alert=True)
                return
            await edit(enh_item_detail_text(data, instance_id, lang), enh_item_detail_keyboard(item["type"], instance_id, lang))
            return

        # ===== ПРИМЕНИТЬ ЯД =====
        if cd.startswith("enh_use_"):
            instance_id = cd.removeprefix("enh_use_")
            ok, msg = use_poison(data, instance_id, lang=lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer("☠️ Яд применён!" if lang == "ru" else "☠️ Poison applied!", show_alert=True)
                await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            elif msg.startswith("CONFIRM_REPLACE_POISON:"):
                await edit(enh_confirm_replace_text(data, instance_id, "poison", lang), enh_confirm_replace_keyboard(instance_id, "poison", lang))
            else:
                await call.answer(msg, show_alert=True)
            return

        # ===== АКТИВИРОВАТЬ УСИЛИТЕЛЬ УРОНА =====
        if cd.startswith("enh_activate_"):
            instance_id = cd.removeprefix("enh_activate_")
            ok, msg = activate_enh_boost(data, instance_id, lang=lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer("⚡ Усилитель активирован!" if lang == "ru" else "⚡ Booster activated!", show_alert=True)
                await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            elif msg.startswith("CONFIRM_REPLACE_ENH:"):
                await edit(enh_confirm_replace_text(data, instance_id, "enh_boost", lang), enh_confirm_replace_keyboard(instance_id, "enh_boost", lang))
            else:
                await call.answer(msg, show_alert=True)
            return

        # ===== ПОДТВЕРЖДЕНИЕ ЗАМЕНЫ ЯДА =====
        if cd.startswith("enh_poison_replace_"):
            instance_id = cd.removeprefix("enh_poison_replace_")
            ok, msg = use_poison(data, instance_id, force=True, lang=lang)
            await call.answer(("☠️ Яд заменён!" if lang == "ru" else "☠️ Poison replaced!") if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            return

        # ===== ПОДТВЕРЖДЕНИЕ ЗАМЕНЫ УСИЛИТЕЛЯ УРОНА =====
        if cd.startswith("enh_boost_replace_"):
            instance_id = cd.removeprefix("enh_boost_replace_")
            ok, msg = activate_enh_boost(data, instance_id, force=True, lang=lang)
            await call.answer(("⚡ Усилитель заменён!" if lang == "ru" else "⚡ Booster replaced!") if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            return

        # ===== ПРОДАЖА УСИЛИТЕЛЯ / ЯДА =====
        if cd.startswith("enh_sell_"):
            instance_id = cd.removeprefix("enh_sell_")
            ok, msg, price = sell_enh_item(data, instance_id, lang)
            await call.answer(f"💸 {'Продано' if lang == 'ru' else 'Sold'} {format_amount(price)}!" if ok else msg, show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(enh_inventory_text(data, lang), enh_inventory_keyboard(data, lang))
            return
            await edit(shop_pickaxes_text(), shop_pickaxes_keyboard(data))
            return

        # ===== КИРКИ: просмотр карточки =====
        if cd.startswith("pick_info_"):
            pick_key = cd.removeprefix("pick_info_")
            page     = get_pickaxe_page(pick_key)
            await edit(pickaxe_detail_text(data, pick_key, lang), pickaxe_detail_keyboard(data, pick_key, page, lang))
            return

        # ===== КИРКИ: купить за монеты =====
        if cd.startswith("pick_buy_") and not cd.startswith("pick_buy_stars_"):
            pick_key = cd.removeprefix("pick_buy_")
            ok, msg  = buy_pickaxe(data, pick_key, lang)
            await call.answer(_plain(msg), show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            page = get_pickaxe_page(pick_key)
            await edit(pickaxe_detail_text(data, pick_key, lang), pickaxe_detail_keyboard(data, pick_key, page, lang))
            return

        # ===== КИРКИ: покупка за звёзды ОТКЛЮЧЕНА =====
        # Кирки теперь покупаются только за монеты (cost_stars убран из
        # PICKAXES в miner.py). Если где-то у пользователя осталась старая
        # кнопка "pick_buy_stars_" (например, несвежий экран из старого
        # сообщения) — просто мягко сообщаем и не даём упасть на
        # p["cost_stars"], которого больше нет.
        if cd.startswith("pick_buy_stars_"):
            pick_key = cd.removeprefix("pick_buy_stars_")
            p = PICKAXES.get(pick_key)
            await call.answer(
                "Покупка кирок за звёзды отключена — теперь кирки покупаются только за монеты."
                if lang != "en" else
                "Buying pickaxes with Stars is disabled — pickaxes are coins-only now.",
                show_alert=True
            )
            if p:
                page = get_pickaxe_page(pick_key)
                await edit(pickaxe_detail_text(data, pick_key, lang), pickaxe_detail_keyboard(data, pick_key, page, lang))
            return


        # ===== КИРКИ: выбрать =====
        if cd.startswith("pick_select_"):
            pick_key = cd.removeprefix("pick_select_")
            ok, msg  = select_pickaxe(data, pick_key, lang)
            await call.answer(_plain(msg), show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            page = get_pickaxe_page(pick_key)
            await edit(pickaxe_detail_text(data, pick_key, lang), pickaxe_detail_keyboard(data, pick_key, page, lang))
            return

        # ===== ДЛИТЕЛЬНОСТИ: просмотр карточки =====
        if cd.startswith("dur_info_"):
            dur_key = cd.removeprefix("dur_info_")
            await edit(duration_detail_text(data, dur_key, lang), duration_detail_keyboard(data, dur_key, lang))
            return

        # ===== ДЛИТЕЛЬНОСТИ: купить =====
        if cd.startswith("dur_buy_"):
            dur_key = cd.removeprefix("dur_buy_")
            ok, msg = buy_duration(data, dur_key, lang)
            await call.answer(_plain(msg), show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(duration_detail_text(data, dur_key, lang), duration_detail_keyboard(data, dur_key, lang))
            return

        # ===== ДЛИТЕЛЬНОСТИ: выбрать =====
        if cd.startswith("dur_select_"):
            dur_key = cd.removeprefix("dur_select_")
            ok, msg = select_duration(data, dur_key, lang)
            await call.answer(_plain(msg), show_alert=True)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            await edit(duration_detail_text(data, dur_key, lang), duration_detail_keyboard(data, dur_key, lang))
            return

        # ===== ШАХТА =====
        if cd == "mine":
            await edit(mine_text(data, lang), mine_keyboard(data, lang))
            return

        if cd == "mine_start":
            if data["mine_start"] is not None and not data["mine_collected"]:
                await call.answer(t(lang, "mine_already_running"), show_alert=True)
                return
            data["mine_start"]          = now_ts()
            data["mine_campaigns_done"] = 0
            data["mine_collected"]      = False
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            await edit(mine_text(data, lang), mine_keyboard(data, lang))
            return

        if cd == "mine_refresh":
            await edit(mine_text(data, lang), mine_keyboard(data, lang))
            return

        if cd == "mine_collect":
            if data["mine_start"] is None:
                await call.answer(t(lang, "mine_start_first"), show_alert=True)
                return
            # На топовых кирках с бустерами roll_ore может перебирать
            # миллионы ударов кирки — считаем в отдельном потоке, чтобы
            # не морозить event loop бота для всех остальных игроков.
            prog, result_text = await asyncio.to_thread(collect_mine, data, lang)
            if not result_text:
                await call.answer(t(lang, "mine_no_campaigns"), show_alert=True)
                return
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            await edit(result_text, mine_keyboard(data, lang))
            return

        if cd == "mine_stop":
            if data["mine_start"] is None or data.get("mine_collected"):
                await call.answer("Шахта не запущена.", show_alert=True)
                return
            # Тот же тяжёлый roll_ore внутри — тоже уводим в отдельный поток.
            prog, result_text = await asyncio.to_thread(stop_mine, data, lang)
            if prog is None:
                # can_stop вернул False — показываем причину алертом
                await call.answer(_plain(result_text), show_alert=True)
                return
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            await edit(result_text, mine_keyboard(data, lang))
            return

        if cd == "mine_sell_screen":
            await edit(sell_screen_text(data, lang), sell_keyboard(data, lang))
            return

        if cd == "mine_sell_all":
            total, report = sell_all_ores(data, lang)
            if total == 0:
                await call.answer(t(lang, "mine_sell_nothing"), show_alert=True)
                return
            is_clan_member = bool(await get_member(user.id))
            if is_clan_member:
                data["clan_mine_contributed"] = data.get("clan_mine_contributed", 0) + total
            # ── Клановый бонус на добычу (по уровню клана, только если
            #    игрок выполнил личное клановое задание за последние 24ч) ──
            bonus_mult  = 1.0
            bonus_extra = 0
            if is_clan_member:
                try:
                    bonus_mult = await get_clan_mining_bonus_multiplier(user.id)
                except Exception as _be:
                    print(f"[klan] mining bonus error: {_be}")
                    bonus_mult = 1.0
                if bonus_mult > 1.0:
                    bonus_extra = int(total * (bonus_mult - 1))
                    if bonus_extra > 0:
                        data["balance"] = data.get("balance", 0) + bonus_extra
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            try:
                await add_clan_mine_earnings(user.id, total)
            except Exception as _qe:
                print(f"[klan] mine daily quest error: {_qe}")
            bonus_line = (
                f'\n🚀 <b>Клановый бонус ×{bonus_mult:g}:</b> +{format_amount(bonus_extra)} <tg-emoji emoji-id="5199552030615558774">🎟</tg-emoji>'
                if bonus_extra > 0 else ""
            )
            sell_text = (
                f'<tg-emoji emoji-id="5206607081334906820">🎟</tg-emoji> <b>{t(lang, "mine_sell_success")}</b>\n'
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{report}\n\n"
                f'<tg-emoji emoji-id="5429651785352501917">🎟</tg-emoji> <b>{t(lang, "mine_sell_earned")}: {format_amount(total)}</b> <tg-emoji emoji-id="5199552030615558774">🎟</tg-emoji>'
                f'{bonus_line}\n'
                f'<tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_balance_lbl")}: {format_amount(data["balance"])}</b> <tg-emoji emoji-id="5199552030615558774">🎟</tg-emoji>'
            )
            await edit(sell_text, mine_keyboard(data, lang))
            return

        # ===== ИНВЕНТАРЬ =====
        if cd == "mine_inventory":
            await edit(inventory_screen_text(data, lang), inventory_keyboard(data, lang))
            return

        # ===== МАСТЕРСКАЯ (с поддержкой страниц) =====
        if cd == "mine_workshop" or cd == "mine_workshop_0":
            await edit(workshop_text(data, 0, lang), workshop_keyboard(data, 0, lang))
            return

        if cd.startswith("mine_workshop_"):
            try:
                page = int(cd.removeprefix("mine_workshop_"))
            except ValueError:
                page = 0
            await edit(workshop_text(data, page, lang), workshop_keyboard(data, page, lang))
            return

        if cd == "mine_duration_shop":
            await edit(duration_shop_text(data, lang), duration_shop_keyboard(data, lang))
            return

        # ===== НАЗАД В МЕНЮ =====
        if cd == "back_to_menu":
            try:
                await call.message.edit_text(
                    t(lang, "welcome"),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=main_menu_keyboard(lang)
                )
            except Exception as e:
                if "message is not modified" not in str(e):
                    print(e)
            return

        # ===== ПИТОМЦЫ: главный экран =====
        if cd == "pets" or cd == "pets_page_0":
            await edit(pets_main_text(data, lang), pets_main_keyboard(data, 0, lang))
            return

        if cd.startswith("pets_page_"):
            try:
                page = int(cd.removeprefix("pets_page_"))
            except ValueError:
                page = 0
            await edit(pets_main_text(data, lang), pets_main_keyboard(data, page, lang))
            return

        # ===== ПИТОМЦЫ: карточка =====
        if cd.startswith("pet_info_"):
            pk   = cd.removeprefix("pet_info_")
            idx  = next((i for i, p in enumerate(PETS) if p["key"] == pk), 0)
            page = idx // 5
            await edit(pet_detail_text(data, pk, lang), pet_detail_keyboard(data, pk, page, lang))
            return

        # ===== ПИТОМЦЫ: покупка =====
        if cd.startswith("pet_buy_"):
            pk      = cd.removeprefix("pet_buy_")
            ok, msg = buy_pet(data, pk, lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer("✅", show_alert=False)
            else:
                import re
                plain = re.sub(r'<[^>]+>', '', msg)
                await call.answer(plain[:200], show_alert=True)
            idx  = next((i for i, p in enumerate(PETS) if p["key"] == pk), 0)
            page = idx // 5
            await edit(pet_detail_text(data, pk, lang), pet_detail_keyboard(data, pk, page, lang))
            return

        # ===== ОХОТА: главный экран =====
        if cd == "hunt":
            _txt, _kb = await asyncio.to_thread(
                lambda: (hunt_main_text(data, lang), hunt_main_keyboard(data, lang))
            )
            await edit(_txt, _kb)
            return

        # ===== ОХОТА: экран выбора уровня сложности =====
        if cd == "hunt_boss_select":
            _txt, _kb = await asyncio.to_thread(
                lambda: (boss_tier_menu_text(lang), boss_tier_menu_keyboard(lang))
            )
            await edit(_txt, _kb)
            await call.answer()
            return

        # ===== ОХОТА: список боссов внутри выбранного уровня сложности =====
        if cd.startswith("hunt_tier_"):
            tier_key = cd.removeprefix("hunt_tier_")
            if tier_key not in ("easy", "medium", "hard"):
                await call.answer("❌ Неизвестный уровень." if lang == "ru" else "❌ Unknown tier.", show_alert=True)
                return
            _txt, _kb = await asyncio.to_thread(
                lambda: (boss_select_text(lang, tier_key), boss_select_keyboard(lang, tier_key))
            )
            await edit(_txt, _kb)
            await call.answer()
            return

        # ===== ОХОТА: мёртвый босс — тихо отвечаем =====
        if cd == "hunt_boss_dead":
            await call.answer(
                "Boss is dead, wait for respawn." if lang == "en" else "Босс мёртв, жди респауна.",
                show_alert=True
            )
            return

        # ===== ОХОТА: магазин мечей =====
        if cd == "hunt_shop_swords":
            await edit(sword_shop_text(data, 0, lang), sword_shop_keyboard(data, 0, lang))
            return

        # ===== ОХОТА: пагинация магазина мечей =====
        if cd.startswith("sword_shop_page_"):
            page = int(cd.removeprefix("sword_shop_page_"))
            await call.answer()
            await edit(sword_shop_text(data, page, lang), sword_shop_keyboard(data, page, lang))
            return

        # ===== ОХОТА: магазин зелий =====
        if cd == "hunt_shop_potions":
            await call.answer()
            await edit(potions_shop_text(lang), potions_shop_keyboard(lang))
            return

        # ===== ОХОТА: купить зелье за звёзды (создаём инвойс) =====
        if cd.startswith("buy_potion_"):
            potion_key = cd.removeprefix("buy_potion_")
            p = POTIONS_BY_KEY.get(potion_key)
            if not p:
                await call.answer("❌ Неизвестное зелье." if lang == "ru" else "❌ Unknown potion.", show_alert=True)
                return
            params = potion_invoice_params(potion_key, lang)
            try:
                invoice_url = await bot.create_invoice_link(
                    title=params["title"],
                    description=params["description"],
                    payload=params["payload"],
                    provider_token="",
                    currency=params["currency"],
                    prices=[LabeledPrice(label=pr["label"], amount=pr["amount"]) for pr in params["prices"]],
                )
            except Exception as e:
                print(f"Potion invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice creation error.", show_alert=True)
                return
            _pending_potion_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
            )
            pay_kb = InlineKeyboardBuilder()
            pay_kb.row(InlineKeyboardButton(
                text=f'Купить за {p["price_stars"]} ⭐' if lang == "ru" else f'Buy for {p["price_stars"]} ⭐',
                url=invoice_url,
                icon_custom_emoji_id="5267500801240092311",
                style="success"
            ))
            pay_kb.row(InlineKeyboardButton(
                text="Назад" if lang == "ru" else "Back",
                callback_data="hunt_shop_potions"
            ))
            await edit(await asyncio.to_thread(potion_detail_text, potion_key, call.from_user.id, lang), pay_kb.as_markup())
            await call.answer()
            return

        # ===== ОХОТА: мои мечи =====
        if cd == "hunt_my_swords":
            await edit(my_swords_text(data, lang), my_swords_keyboard(data, lang))
            return

        # ===== АРСЕНАЛ: главный экран =====
        if cd == "hunt_arsenal":
            cleanup_expired_rentals(data)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer()
            await edit(arsenal_main_text(data), arsenal_main_keyboard(data))
            return

        # ===== ДОСТИЖЕНИЯ: кнопка-индикатор страницы (X/Y) — просто отвечаем, ничего не меняем =====
        if cd == "ach_noop":
            await call.answer()
            return

        # ===== ДОСТИЖЕНИЯ: возврат в меню достижений (список разделов) =====
        if cd == "ach_menu":
            await call.answer()
            await edit(
                await asyncio.to_thread(achievements_menu_text, data, lang),
                achievements_menu_keyboard(lang),
            )
            return

        # ===== ДОСТИЖЕНИЯ: фильтр по категории (всегда открывает страницу 1) =====
        if cd.startswith("ach_cat_"):
            cat = cd.removeprefix("ach_cat_")
            await call.answer()
            await edit(
                await asyncio.to_thread(achievements_list_text, data, lang, cat, 0),
                achievements_keyboard(lang, category=cat, page=0),
            )
            return

        # ===== ДОСТИЖЕНИЯ: листание страниц внутри раздела =====
        if cd.startswith("ach_page_"):
            _cat, _page_str = cd.removeprefix("ach_page_").rsplit("_", 1)
            page = int(_page_str)
            await call.answer()
            await edit(
                await asyncio.to_thread(achievements_list_text, data, lang, _cat, page),
                achievements_keyboard(lang, category=_cat, page=page),
            )
            return

        # ===== АРСЕНАЛ: меню выбора меча для экипировки =====
        if cd == "arsenal_equip_menu":
            await call.answer()
            await edit(arsenal_equip_menu_text(data), arsenal_equip_menu_keyboard(data))
            return

        # ===== ОХОТА: карточка меча =====
        if cd.startswith("sword_info_"):
            sk = cd.removeprefix("sword_info_")
            await edit(sword_detail_text(data, sk, lang), sword_detail_keyboard(data, sk, lang))
            return

        # ===== ОХОТА: купить меч =====
        if cd.startswith("sword_buy_"):
            sk = cd.removeprefix("sword_buy_")
            ok, msg = buy_sword(data, sk, lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer(_plain(msg), show_alert=False)
            else:
                import re as _re2
                plain = _re2.sub(r'<[^>]+>', '', msg)
                await call.answer(plain[:200], show_alert=True)
            await edit(sword_detail_text(data, sk, lang), sword_detail_keyboard(data, sk, lang))
            return

        # ===== ОХОТА: экипировать меч =====
        if cd.startswith("sword_equip_"):
            sk = cd.removeprefix("sword_equip_")
            ok, msg = equip_sword(data, sk, lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                await call.answer(_plain(msg), show_alert=False)
            await edit(my_swords_text(data, lang), my_swords_keyboard(data, lang))
            return

        # ===== ОХОТА: экран атаки конкретного босса (hunt_boss_N) =====
        if cd.startswith("hunt_boss_") and cd != "hunt_boss_select" and cd != "hunt_boss_dead":
            try:
                slot = int(cd.removeprefix("hunt_boss_"))
            except ValueError:
                await call.answer("❌ Неизвестный слот." if lang == "ru" else "❌ Unknown slot.", show_alert=True)
                return
            # boss_attack_text/keyboard читают состояние босса из БД
            # (_load_slot) синхронно — уводим в отдельный поток, чтобы не
            # морозить event loop для всех пользователей при каждом
            # открытии экрана босса.
            _txt, _kb = await asyncio.to_thread(
                lambda: (boss_attack_text(data, lang, slot), boss_attack_keyboard(data, lang, slot))
            )
            await edit(_txt, _kb)
            await call.answer()
            return

        # ===== ОХОТА: удар по боссу (hunt_strike_N) =====
        if cd.startswith("hunt_strike"):
            # Парсим слот из hunt_strike_N, дефолт 0
            try:
                slot = int(cd.removeprefix("hunt_strike_"))
            except ValueError:
                slot = 0
            # attack_boss делает синхронную запись в БД с BEGIN IMMEDIATE
            # (эксклюзивная блокировка файла БД) + threading.Lock на слот —
            # это самая частая кнопка в игре, поэтому именно она была
            # основным источником многоминутных зависаний бота для ВСЕХ
            # пользователей. Уводим в отдельный поток.
            result = await asyncio.to_thread(attack_boss, data, slot)
            # Кулдаун — тихий игнор, просто отвечаем на callback без действий
            if result.get("error") == "cooldown":
                await call.answer()
                return
            # cleanup_expired_rentals внутри attack_boss мог снять истёкший
            # арендованный меч с экипировки — сохраняем это, даже если сам
            # удар не засчитался (например sword_rented_out/no_sword).
            if result.get("needs_save") and not (result.get("boss_killed") or result.get("hit")):
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            if result.get("boss_killed") or result.get("hit"):
                # ── Повышение уровня убийцы ──
                if result.get("xp", 0) > 0:
                    _apply_xp(data, result["xp"])
                if result.get("dmg", 0) > 0 and await get_member(user.id):
                    data["clan_boss_damage_total"] = data.get("clan_boss_damage_total", 0) + result["dmg"]
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
                # ── Запись статистики для лидерборда ──
                try:
                    from hunt import _load_slot as _ld_slot
                    _boss_state = await asyncio.to_thread(_ld_slot, slot)
                    _boss_key   = _boss_state.get("boss_key", "unknown")
                    await record_boss_hit(
                        uid        = user.id,
                        username   = user.username or "",
                        first_name = user.first_name or "",
                        boss_key   = _boss_key,
                        damage     = result.get("dmg", 0),
                        killed     = bool(result.get("boss_killed")),
                    )
                except Exception as _le:
                    print(f"[leaders] record_boss_hit error: {_le}")
                # ── Ежедневные задания клана ──
                try:
                    if result.get("dmg", 0) > 0:
                        await add_clan_boss_damage(user.id, result["dmg"])
                    if result.get("boss_killed"):
                        await register_clan_boss_kill(user.id)
                        # ── Антиматерия за убийство босса (по сложности) ──
                        try:
                            from hunt import _tier_for_slot as _tier_for_slot_fn
                            _tier_key = _tier_for_slot_fn(slot).get("key")
                            await add_clan_antimatter(user.id, _tier_key)
                        except Exception as _ae:
                            print(f"[klan] antimatter reward error: {_ae}")
                except Exception as _qe:
                    print(f"[klan] daily quest error: {_qe}")
                # ── Раздача наград остальным участникам урона ──
                if result.get("boss_killed"):
                    await _distribute_boss_rewards(user.id, result.get("damage_rewards", {}))
            txt, kb = await asyncio.to_thread(
                lambda: (boss_strike_result_text(data, result, lang, slot), boss_strike_keyboard(data, lang, slot))
            )
            if result.get("crit"):
                await call.answer("⭐ CRITICAL HIT!" if lang == "en" else "⭐ КРИТИЧЕСКИЙ УДАР!", show_alert=False)
            else:
                await call.answer()
            await edit(txt, kb)
            # ── Уведомления о новых достижениях (за удар/убийство босса) ──
            for _new_ach in result.get("new_achievements", []):
                try:
                    await bot.send_message(
                        user.id, achievement_unlocked_text(_new_ach, lang), parse_mode="HTML"
                    )
                except Exception:
                    pass
            return

        # ===== КЕЙС АРТЕФАКТОВ: экран информации =====
        if cd == "artifact_case_info":
            await edit(artifact_case_detail_text(data, lang), artifact_case_keyboard(lang=lang))
            return

        # ===== КЕЙС АРТЕФАКТОВ: создать инвойс и обновить сообщение =====
        if cd == "artifact_case_buy":
            if lang == "en":
                _inv_title = "Artifact Case"
                _inv_desc  = "Open a case and get a permanent artifact bonus forever!"
                _inv_label = "Artifact Case"
            else:
                _inv_title = "Кейс Артефактов"
                _inv_desc  = "Открой кейс и получи постоянный артефакт с бонусом навсегда!"
                _inv_label = "Кейс Артефактов"
            try:
                invoice_url = await bot.create_invoice_link(
                    title=_inv_title,
                    description=_inv_desc,
                    payload="artifact_case",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=_inv_label, amount=ARTIFACT_CASE_COST_STARS)],
                )
            except Exception as e:
                print(f"Artifact invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice creation error.", show_alert=True)
                return
            _pending_artifact_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
            )
            await edit(artifact_case_detail_text(data, lang), artifact_case_keyboard(invoice_url=invoice_url, lang=lang))
            return

        # ===== КЕЙС АРТЕФАКТОВ: коллекция =====
        if cd == "artifact_collection":
            await edit(artifact_collection_text(data, lang), artifact_collection_keyboard(lang))
            return

        # ===== ДОНАТЫ: главный экран =====
        if cd == "donate_main":
            await edit(donate_main_text(lang), donate_main_keyboard(lang))
            return

        # ===== ДОНАТЫ: экран конкретного пакета =====
        if cd.startswith("donate_pkg_"):
            pkg_key = cd.removeprefix("donate_pkg_")
            await edit(donate_package_text(pkg_key, lang), donate_package_keyboard(pkg_key, lang=lang))
            return

        # ===== ДОНАТЫ: создать инвойс и обновить сообщение =====
        if cd.startswith("donate_buy_"):
            pkg_key = cd.removeprefix("donate_buy_")
            pkg = DONATE_BY_KEY.get(pkg_key)
            if not pkg:
                await call.answer("❌ Пакет не найден." if lang == "ru" else "❌ Package not found.", show_alert=True)
                return
            name = pkg["label"] if lang == "ru" else pkg["label_en"]
            from shop import _fmt_num as _shop_fmt
            desc_ru = f"Получи {_shop_fmt(pkg['coins'])} монет мгновенно!"
            desc_en = f"Get {_shop_fmt(pkg['coins'])} coins instantly!"
            try:
                invoice_url = await bot.create_invoice_link(
                    title=name,
                    description=desc_ru if lang == "ru" else desc_en,
                    payload=f"donate:{pkg_key}",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=name, amount=pkg["stars"])],
                )
            except Exception as e:
                print(f"Donate invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice error.", show_alert=True)
                return
            _pending_donate_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
                pkg_key,
            )
            await edit(donate_package_text(pkg_key, lang), donate_package_keyboard(pkg_key, invoice_url=invoice_url, lang=lang))
            return
        if cd == "status":
            await call.answer()
            await edit(status_main_text(data, lang), status_main_keyboard(data, lang))
            return

        # ===== СТАТУС: карточка VIP =====
        if cd == "status_vip_info":
            await call.answer()
            _pending_status_msg.pop(call.from_user.id, None)
            await edit(status_vip_text(data, lang), status_vip_keyboard(data, lang))
            return

        # ===== СТАТУС: карточка Premium =====
        if cd == "status_premium_info":
            await call.answer()
            _pending_status_msg.pop(call.from_user.id, None)
            await edit(status_premium_text(data, lang), status_premium_keyboard(data, lang))
            return

        # ===== СТАТУС: купить VIP (создать инвойс) =====
        if cd == "status_buy_vip":
            invoice_url = None
            if lang == "en":
                _title = "VIP Status — 30 days"
                _desc  = "×1.3 to mining, +15% crit, luck in cases, Viper Poison as a gift"
                _label = "VIP for 30 days"
            else:
                _title = "Статус VIP — 30 дней"
                _desc  = "×1.3 к добыче, +15% крит, удача в кейсах, Яд Гадюки в подарок"
                _label = "VIP на 30 дней"
            try:
                invoice_url = await bot.create_invoice_link(
                    title=_title,
                    description=_desc,
                    payload="status_vip",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=_label, amount=VIP_COST_STARS)],
                )
            except Exception as e:
                print(f"VIP invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice creation error.", show_alert=True)
                return
            await call.answer()
            _pending_status_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
                "vip",
            )
            await edit(status_vip_text(data, lang), status_vip_keyboard_invoice(invoice_url, lang))
            return

        # ===== СТАТУС: купить Premium (создать инвойс) =====
        if cd == "status_buy_premium":
            invoice_url = None
            if lang == "en":
                _title = "Premium Status — 30 days"
                _desc  = "×1.6 to mining, +25% crit, max luck, Cobra Poison as a gift"
                _label = "Premium for 30 days"
            else:
                _title = "Статус Premium — 30 дней"
                _desc  = "×1.6 к добыче, +25% крит, макс. удача, Яд Кобры в подарок"
                _label = "Premium на 30 дней"
            try:
                invoice_url = await bot.create_invoice_link(
                    title=_title,
                    description=_desc,
                    payload="status_premium",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=_label, amount=PREMIUM_COST_STARS)],
                )
            except Exception as e:
                print(f"Premium invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice creation error.", show_alert=True)
                return
            await call.answer()
            _pending_status_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
                "premium",
            )
            await edit(status_premium_text(data, lang), status_premium_keyboard_invoice(invoice_url, lang))
            return

        # ===== СТАТУС: апгрейд VIP → Premium (создать инвойс за 59 Stars) =====
        if cd == "status_upgrade_premium":
            # Только если VIP активен
            from status import get_active_status as _gas
            if _gas(data) != "vip":
                await call.answer("❌ Апгрейд доступен только при активном VIP." if lang == "ru" else "❌ Upgrade is only available with active VIP.", show_alert=True)
                return
            invoice_url = None
            if lang == "en":
                _title = "VIP → Premium Upgrade"
                _desc  = "×1.6 to mining, +25% crit, max luck, Cobra Poison as a gift"
                _label = "Upgrade to Premium"
            else:
                _title = "Улучшение VIP → Premium"
                _desc  = "×1.6 к добыче, +25% крит, макс. удача, Яд Кобры в подарок"
                _label = "Апгрейд до Premium"
            try:
                invoice_url = await bot.create_invoice_link(
                    title=_title,
                    description=_desc,
                    payload="status_upgrade_premium",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=_label, amount=UPGRADE_COST_STARS)],
                )
            except Exception as e:
                print(f"Upgrade invoice error: {e}")
                await call.answer("❌ Ошибка при создании инвойса." if lang == "ru" else "❌ Invoice creation error.", show_alert=True)
                return
            await call.answer()
            _pending_status_msg[call.from_user.id] = (
                call.message.chat.id,
                call.message.message_id,
                "premium",
            )
            await edit(status_premium_text(data, lang), status_upgrade_keyboard_invoice(invoice_url, lang))
            return


        # ===== ЛИДЕРЫ: главный экран =====
        if cd == "leaders":
            await edit(await leaders_main_text(viewer_uid=user.id, lang=lang), leaders_main_keyboard(lang))
            return

        # ===== ЛИДЕРЫ: переключение категории / периода =====
        # Формат: leaders_{category}_{period}
        if cd.startswith("leaders_"):
            parts = cd.split("_", 2)  # ["leaders", category, period]
            if len(parts) == 3:
                _lcat, _lper = parts[1], parts[2]
                if _lcat in _LEADERS_CATEGORIES and _lper in _LEADERS_PERIODS:
                    await edit(
                        await leaders_text(_lcat, _lper, viewer_uid=user.id, lang=lang),
                        leaders_keyboard(_lcat, _lper, lang)
                    )
                    return

        # ===== СТАТИСТИКА =====
        if cd == "stats":
            await edit(await aio_stats_text(lang), stats_keyboard(lang))
            await call.answer()
            return

        # ===== НАСТРОЙКИ =====
        if cd == "settings":
            await edit(settings_text(data), settings_keyboard(data))
            await call.answer()
            return

        # ===== НАСТРОЙКИ: смена языка (из настроек) =====
        if cd == "settings_lang":
            await edit(lang_choose_text(lang), lang_choose_keyboard())
            await call.answer()
            return

        if cd in ("set_lang_ru", "set_lang_en"):
            new_lang = "ru" if cd == "set_lang_ru" else "en"
            data["lang"] = new_lang
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            alert = "🇷🇺 Язык установлен: Русский" if new_lang == "ru" else "🇬🇧 Language set: English"
            await call.answer(alert, show_alert=True)
            await edit(settings_text(data), settings_keyboard(data))
            return

        # ===== ВЫБОР ЯЗЫКА ПРИ СТАРТЕ =====
        if cd in ("start_lang_ru", "start_lang_en"):
            new_lang = "ru" if cd == "start_lang_ru" else "en"
            data["lang"] = new_lang
            data["onboarded"] = True
            _ach_newly = check_achievements(data)
            await aio_save_user(data["id"], data)
            await _notify_ach(data["id"], data, _ach_newly)
            await call.message.answer(
                "🎮",
                reply_markup=main_reply_keyboard(new_lang),
            )
            await call.message.edit_text(
                t(new_lang, "welcome"),
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=main_menu_keyboard(new_lang),
            )
            await call.answer()
            return

        # ===== ДУЭЛИ: главный экран =====
        if cd == "duel_main":
            await call.answer()
            await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
            return

        # ===== ДУЭЛИ: экипировка — список слотов =====
        if cd == "duel_equip":
            await call.answer()
            await edit(duel_equip_text(data, lang), duel_equip_keyboard(data, lang))
            return

        # ===== ДУЭЛИ: список уровней слота =====
        if cd.startswith("duel_equip_slot:"):
            slot_key = cd.split(":", 1)[1]
            await call.answer()
            await edit(duel_equip_slot_text(slot_key, data, 0, lang), duel_equip_slot_keyboard(slot_key, data, 0, lang))
            return

        # ===== ДУЭЛИ: пагинация уровней слота =====
        if cd.startswith("duel_slot_page:"):
            parts    = cd.split(":", 2)
            slot_key = parts[1]
            page     = int(parts[2])
            await call.answer()
            await edit(duel_equip_slot_text(slot_key, data, page, lang), duel_equip_slot_keyboard(slot_key, data, page, lang))
            return

        # ===== ДУЭЛИ: карточка предмета (отдельное окно) =====
        if cd.startswith("duel_item_card:"):
            parts    = cd.split(":", 2)
            item_key = parts[1]
            page     = int(parts[2]) if len(parts) > 2 else 0
            await call.answer()
            await edit(duel_item_card_text(item_key, data, lang), duel_item_card_keyboard(item_key, data, page, lang))
            return

        # ===== ДУЭЛИ: купить предмет =====
        if cd.startswith("duel_gear_buy:"):
            parts    = cd.split(":", 2)
            item_key = parts[1]
            page     = int(parts[2]) if len(parts) > 2 else 0
            item     = GEAR_CATALOG.get(item_key)
            if not item:
                await call.answer(t(lang, "duel_alert_unknown_item"), show_alert=True)
                return
            price   = item["price"]
            balance = data.get("balance", 0)
            if balance < price:
                await call.answer(
                    t(lang, "duel_alert_not_enough_coins_full").format(
                        price=f"{price:,}".replace(",", " "), balance=f"{balance:,}".replace(",", " ")
                    ),
                    show_alert=True,
                )
                return
            data["balance"] -= price
            apply_gear_purchase(item_key, data)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer(t(lang, "duel_alert_bought_item").format(name=item['name']), show_alert=True)
            await edit(duel_item_card_text(item_key, data, lang), duel_item_card_keyboard(item_key, data, page, lang))
            return

        # ===== ДУЭЛИ: недостаточно монет (заглушка кнопки) =====
        if cd == "duel_gear_nofunds":
            await call.answer(t(lang, "duel_alert_no_funds_buy"), show_alert=True)
            return

        # ===== ДУЭЛИ: карточка навыка (подробное окно) =====
        if cd.startswith("duel_skill_card:"):
            parts = cd.split(":", 2)
            sk_key   = parts[1]
            from_page = int(parts[2]) if len(parts) > 2 else 0
            await call.answer()
            await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, from_page, lang))
            return

        # ===== ДУЭЛИ: экипировать навык в бой =====
        if cd.startswith("duel_skill_equip:"):
            sk_key = cd.split(":", 1)[1]
            ok, msg = equip_skill(sk_key, data, lang)
            await call.answer(msg, show_alert=not ok)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)
            # Возвращаемся на карточку
            await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, lang=lang))
            return

        # ===== ДУЭЛИ: снять навык из боя =====
        if cd.startswith("duel_skill_unequip:"):
            sk_key = cd.split(":", 1)[1]
            ok, msg = unequip_skill(sk_key, data, lang)
            await call.answer(msg, show_alert=not ok)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(user.id, data)
                await _notify_ach(user.id, data, _ach_newly)
            await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, lang=lang))
            return

        # ===== ДУЭЛИ: все слоты заняты =====
        if cd == "duel_skill_slots_full":
            await call.answer(t(lang, "duel_skill_slots_full_alert").format(max=MAX_EQUIPPED_SKILLS), show_alert=True)
            return

        # ===== ДУЭЛИ: магазин навыков =====
        if cd == "duel_skills_shop":
            await call.answer()
            await edit(duel_skills_shop_text(data, 0, lang), duel_skills_shop_keyboard(data, 0, lang))
            return

        # ===== ДУЭЛИ: пагинация магазина навыков =====
        if cd.startswith("duel_skills_shop_page:"):
            page = int(cd.split(":", 1)[1])
            await call.answer()
            await edit(duel_skills_shop_text(data, page, lang), duel_skills_shop_keyboard(data, page, lang))
            return

        # ===== ДУЭЛИ: купить навык =====
        if cd.startswith("duel_skill_buy:"):
            sk_key = cd.split(":", 1)[1]
            sk = SKILLS.get(sk_key)
            if not sk:
                await call.answer(t(lang, "duel_skill_unknown"), show_alert=True)
                return
            price = sk["price"]
            balance = data.get("balance", 0)
            if balance < price:
                _no_money_msg = t(lang, "duel_skill_not_enough").format(need=_fmt_d(price), have=_fmt_d(balance))
                await call.answer(_no_money_msg, show_alert=True)
                return
            owned_sk = data.setdefault("duel_owned_skills", [])
            if sk_key in owned_sk:
                await call.answer(t(lang, "duel_skill_already_bought"), show_alert=True)
                await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, lang=lang))
                return
            data["balance"] -= price
            owned_sk.append(sk_key)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer(t(lang, "duel_skill_bought_alert").format(name=duel_skill_name(sk, lang)), show_alert=True)
            # Открываем карточку навыка — теперь можно экипировать
            await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, lang=lang))
            return

        # ===== ДУЭЛИ: навык уже куплен (заглушка) =====
        if cd.startswith("duel_skill_owned:"):
            sk_key = cd.split(":", 1)[1]
            await call.answer()
            await edit(duel_skill_card_text(sk_key, data, lang), duel_skill_card_keyboard(sk_key, data, lang=lang))
            return

        # ===== ДУЭЛИ: недостаточно монет (навык) =====
        if cd == "duel_skill_nofunds":
            await call.answer(t(lang, "duel_skill_nofunds_alert"), show_alert=True)
            return

        # ===== ДУЭЛИ: надеть предмет =====
        if cd.startswith("duel_gear_equip:"):
            parts    = cd.split(":", 2)
            item_key = parts[1]
            page     = int(parts[2]) if len(parts) > 2 else 0
            item     = GEAR_CATALOG.get(item_key)
            owned    = data.get("duel_owned_gear", [])
            if item_key not in owned:
                await call.answer(t(lang, "duel_alert_equip_buy_first"), show_alert=True)
                return
            apply_gear_equip(item_key, data)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer(t(lang, "duel_alert_equipped_item").format(name=item['name']), show_alert=True)
            await edit(duel_item_card_text(item_key, data, lang), duel_item_card_keyboard(item_key, data, page, lang))
            return

        # ===== ДУЭЛИ: снять предмет =====
        if cd.startswith("duel_gear_unequip:"):
            parts    = cd.split(":", 2)
            item_key = parts[1]
            page     = int(parts[2]) if len(parts) > 2 else 0
            item     = GEAR_CATALOG.get(item_key)
            apply_gear_unequip(item_key, data)
            _ach_newly = check_achievements(data)
            await aio_save_user(user.id, data)
            await _notify_ach(user.id, data, _ach_newly)
            await call.answer(t(lang, "duel_alert_unequipped_item").format(name=item['name']), show_alert=True)
            await edit(duel_item_card_text(item_key, data, lang), duel_item_card_keyboard(item_key, data, page, lang))
            return

        # ===== ДУЭЛИ: поиск — сразу начинаем поиск =====
        if cd == "duel_search":
            if user.id in _active_battles:
                await call.answer()
                battle = _active_battles[user.id]
                await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
                return
            if not is_player_ready(user.id, data):
                hp_now = get_player_hp(user.id, data)
                secs   = player_hp_regen_seconds(user.id, data)
                await call.answer(
                    t(lang, "duel_hp_too_low_regen").format(hp=hp_now, secs=secs),
                    show_alert=True
                )
                return
            await call.answer()
            battle = join_queue(user.id, data)
            if battle:
                p1_uid = battle["p1_uid"]
                p2_uid = battle["p2_uid"]
                from database import aio_get_user as _gu_battle
                _d1 = await _gu_battle(p1_uid) or {}
                _d2 = await _gu_battle(p2_uid) or {}
                battle["p1_skills"] = get_equipped_skills(_d1) or get_owned_skills(_d1)
                battle["p2_skills"] = get_equipped_skills(_d2) or get_owned_skills(_d2)
                _active_battles[p1_uid] = battle
                _active_battles[p2_uid] = battle
                await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
                foe_msg = _battle_msgs.get(p2_uid)
                try:
                    if foe_msg:
                        await bot.edit_message_text(
                            chat_id=foe_msg[0],
                            message_id=foe_msg[1],
                            text=battle_text(battle, p2_uid, await _lang_for_uid(p2_uid)),
                            parse_mode="HTML",
                            reply_markup=battle_keyboard(battle, p2_uid, await _lang_for_uid(p2_uid))
                        )
                    else:
                        sent = await bot.send_message(
                            p2_uid,
                            battle_text(battle, p2_uid, await _lang_for_uid(p2_uid)),
                            parse_mode="HTML",
                            reply_markup=battle_keyboard(battle, p2_uid, await _lang_for_uid(p2_uid))
                        )
                        _battle_msgs[p2_uid] = (sent.chat.id, sent.message_id)
                except Exception:
                    pass
            else:
                await edit(duel_search_text(True, lang), duel_search_keyboard(True, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
            return

        # ===== ДУЭЛИ: начать поиск =====
        if cd == "duel_search_start":
            if user.id in _active_battles:
                await call.answer()
                battle = _active_battles[user.id]
                await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
                return
            if not is_player_ready(user.id, data):
                hp_now = get_player_hp(user.id, data)
                secs   = player_hp_regen_seconds(user.id, data)
                await call.answer(
                    t(lang, "duel_hp_too_low_tick").format(hp=hp_now, secs=secs),
                    show_alert=True
                )
                return
            await call.answer()
            battle = join_queue(user.id, data)
            if battle:
                p1_uid = battle["p1_uid"]
                p2_uid = battle["p2_uid"]
                # Сохраняем список навыков каждого игрока в бой
                from database import aio_get_user as _gu_battle
                _d1 = await _gu_battle(p1_uid) or {}
                _d2 = await _gu_battle(p2_uid) or {}
                battle["p1_skills"] = get_equipped_skills(_d1) or get_owned_skills(_d1)
                battle["p2_skills"] = get_equipped_skills(_d2) or get_owned_skills(_d2)
                _active_battles[p1_uid] = battle
                _active_battles[p2_uid] = battle
                # Показываем боевой экран инициатору (p1) — редактируем его сообщение
                await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
                # Соперник (p2) был в экране поиска — обновляем его сообщение если знаем
                foe_msg = _battle_msgs.get(p2_uid)
                try:
                    if foe_msg:
                        await bot.edit_message_text(
                            chat_id=foe_msg[0],
                            message_id=foe_msg[1],
                            text=battle_text(battle, p2_uid, await _lang_for_uid(p2_uid)),
                            parse_mode="HTML",
                            reply_markup=battle_keyboard(battle, p2_uid, await _lang_for_uid(p2_uid))
                        )
                    else:
                        sent = await bot.send_message(
                            p2_uid,
                            battle_text(battle, p2_uid, await _lang_for_uid(p2_uid)),
                            parse_mode="HTML",
                            reply_markup=battle_keyboard(battle, p2_uid, await _lang_for_uid(p2_uid))
                        )
                        _battle_msgs[p2_uid] = (sent.chat.id, sent.message_id)
                except Exception:
                    pass
            else:
                await edit(duel_search_text(True, lang), duel_search_keyboard(True, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
            return

        # ===== ДУЭЛИ: проверить поиск =====
        if cd == "duel_search_check":
            await call.answer()
            if user.id in _active_battles:
                battle = _active_battles[user.id]
                await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
                _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
                return
            in_q = in_queue(user.id)
            await edit(duel_search_text(in_q, lang), duel_search_keyboard(in_q, lang))
            return

        # ===== ДУЭЛИ: отменить поиск =====
        if cd == "duel_search_cancel":
            leave_queue(user.id)
            _battle_msgs.pop(user.id, None)
            await call.answer(t(lang, "duel_search_cancelled_toast"))
            await edit(duel_search_text(False, lang), duel_search_keyboard(False, lang))
            return

        # ===== ДУЭЛИ: применить навык =====
        if cd.startswith("duel_skill:"):
            skill_key = cd.split(":", 1)[1]
            if user.id not in _active_battles:
                await call.answer(t(lang, "duel_battle_not_in_battle"), show_alert=True)
                return
            battle = _active_battles[user.id]
            battle, result = battle_use_skill(battle, user.id, skill_key, lang)
            if not result["ok"]:
                await call.answer(result["msg"], show_alert=True)
                return
            foe_uid = battle["p2_uid"] if battle["p1_uid"] == user.id else battle["p1_uid"]
            # ВАЖНО: запоминаем msg_id соперника ДО возможного pop ниже —
            # раньше это читалось ПОСЛЕ _battle_msgs.pop(foe_uid, ...), из-за
            # чего при завершении боя (например, если соперника убивают
            # этим же ударом) foe_msg всегда оказывался None и экран
            # соперника с финальным результатом боя просто не обновлялся.
            foe_msg = _battle_msgs.get(foe_uid)
            # Если бой завершён — сначала считаем награду и пишем в battle,
            # потом уже рендерим battle_text (чтобы reward отобразился)
            if battle.get("finished"):
                from database import aio_get_user as _gu_hp, aio_save_user as _su_hp
                _d1 = await _gu_hp(battle["p1_uid"]) or {}
                _d2 = await _gu_hp(battle["p2_uid"]) or {}
                set_player_hp(battle["p1_uid"], battle["p1_hp"], _d1)
                set_player_hp(battle["p2_uid"], battle["p2_hp"], _d2)
                winner_uid = battle.get("winner_uid")
                if winner_uid is not None:
                    loser_uid = battle["p2_uid"] if winner_uid == battle["p1_uid"] else battle["p1_uid"]
                    _dw = await _gu_hp(winner_uid) or {}
                    _dl = await _gu_hp(loser_uid)  or {}
                    loser_wins  = _dl.get("duel_wins", 0)
                    loser_title = get_duel_title(loser_wins)
                    reward      = TITLE_REWARDS.get(loser_title, 0)
                    battle["reward"] = reward
                    battle["loser_title"] = loser_title
                    _dw["duel_wins"]    = _dw.get("duel_wins", 0) + 1
                    _dw["balance"]      = _dw.get("balance", 0) + reward
                    await _su_hp(winner_uid, _dw)
                    _dl["duel_losses"]  = _dl.get("duel_losses", 0) + 1
                    await _su_hp(loser_uid, _dl)
                _active_battles.pop(user.id, None)
                _active_battles.pop(foe_uid, None)
                _battle_msgs.pop(user.id, None)
                _battle_msgs.pop(foe_uid, None)
            # Обновляем message_id текущего игрока
            _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
            await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
            # Обновляем сообщение соперника (foe_msg взят ДО pop выше — см. комментарий)
            if foe_msg:
                try:
                    await bot.edit_message_text(
                        chat_id=foe_msg[0],
                        message_id=foe_msg[1],
                        text=battle_text(battle, foe_uid, await _lang_for_uid(foe_uid)),
                        parse_mode="HTML",
                        reply_markup=battle_keyboard(battle, foe_uid, await _lang_for_uid(foe_uid))
                    )
                except Exception:
                    pass
            await call.answer()
            return

        # ===== ДУЭЛИ: сдаться =====
        if cd == "duel_surrender":
            if user.id not in _active_battles:
                await call.answer(t(lang, "duel_battle_not_in_battle"), show_alert=True)
                return
            battle = _active_battles[user.id]
            if not battle.get("finished"):
                foe_uid = battle["p2_uid"] if battle["p1_uid"] == user.id else battle["p1_uid"]
                me_prefix = "p1" if battle["p1_uid"] == user.id else "p2"
                battle["finished"] = True
                battle["winner_uid"] = foe_uid
                battle["log"].append({"kind": "surrender", "actor": me_prefix})
                # Считаем награду ДО рендера battle_text
                from database import aio_get_user as _gu_sr, aio_save_user as _su_sr
                _d1 = await _gu_sr(battle["p1_uid"]) or {}
                _d2 = await _gu_sr(battle["p2_uid"]) or {}
                set_player_hp(battle["p1_uid"], battle["p1_hp"], _d1)
                set_player_hp(battle["p2_uid"], battle["p2_hp"], _d2)
                loser_uid2   = battle["p2_uid"] if foe_uid == battle["p1_uid"] else battle["p1_uid"]
                _dw2 = await _gu_sr(foe_uid) or {}
                _dl2 = await _gu_sr(loser_uid2) or {}
                loser_wins2  = _dl2.get("duel_wins", 0)
                loser_title2 = get_duel_title(loser_wins2)
                reward2      = TITLE_REWARDS.get(loser_title2, 0)
                battle["reward"] = reward2
                battle["loser_title"] = loser_title2
                _dw2["duel_wins"]   = _dw2.get("duel_wins", 0) + 1
                _dw2["balance"]     = _dw2.get("balance", 0) + reward2
                await _su_sr(foe_uid, _dw2)
                _dl2["duel_losses"] = _dl2.get("duel_losses", 0) + 1
                await _su_sr(loser_uid2, _dl2)
                foe_msg = _battle_msgs.get(foe_uid)
                if foe_msg:
                    try:
                        await bot.edit_message_text(
                            chat_id=foe_msg[0],
                            message_id=foe_msg[1],
                            text=battle_text(battle, foe_uid, await _lang_for_uid(foe_uid)),
                            parse_mode="HTML",
                            reply_markup=battle_keyboard(battle, foe_uid, await _lang_for_uid(foe_uid))
                        )
                    except Exception:
                        pass
                _active_battles.pop(foe_uid, None)
                _battle_msgs.pop(foe_uid, None)
            _active_battles.pop(user.id, None)
            _battle_msgs.pop(user.id, None)
            await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
            await call.answer(t(lang, "duel_battle_you_surrendered"))
            return

        # ===== ДУЭЛИ: навыки =====
        if cd == "duel_skills":
            await call.answer()
            await edit(duel_skills_text(data, lang), duel_skills_keyboard(lang))
            return

        # ===== ДУЭЛИ: подразделы (заглушки) =====
        # ===== ДУЭЛИ: бросить вызов — экран ввода =====
        if cd == "duel_challenge_start":
            if user.id in _active_battles:
                await call.answer(t(lang, "duel_already_in_battle_toast"), show_alert=True)
                return
            if not is_player_ready(user.id, data):
                hp_now = get_player_hp(user.id, data)
                secs   = player_hp_regen_seconds(user.id, data)
                await call.answer(
                    t(lang, "duel_hp_too_low_tick").format(hp=hp_now, secs=secs),
                    show_alert=True
                )
                return
            await call.answer()
            _challenge_input_pending[user.id] = True
            await edit(duel_challenge_screen_text(lang), duel_challenge_screen_keyboard(lang))
            return

        # ===== ДУЭЛИ: отменить вызов =====
        if cd == "duel_challenge_cancel":
            cancel_challenge(user.id)
            _challenge_input_pending.pop(user.id, None)
            await call.answer(t(lang, "duel_challenge_cancelled_toast"))
            await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
            return

        # ===== ДУЭЛИ: принять вызов =====
        if cd.startswith("duel_challenge_accept:"):
            challenger_uid = int(cd.split(":")[1])
            if user.id in _active_battles:
                await call.answer(t(lang, "duel_already_in_battle_toast"), show_alert=True)
                return
            if not is_player_ready(user.id, data):
                hp_now = get_player_hp(user.id, data)
                secs   = player_hp_regen_seconds(user.id, data)
                await call.answer(
                    t(lang, "duel_hp_too_low_recover_first").format(hp=hp_now),
                    show_alert=True
                )
                return
            await call.answer()
            # Вызывающий мог за это время уйти в другой бой (поиск/другая дуэль) —
            # принятие в этом случае перетёрло бы его текущий активный battle-state.
            if challenger_uid in _active_battles:
                cancel_challenge(challenger_uid)
                await call.answer(t(lang, "duel_challenger_in_battle"), show_alert=True)
                await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
                return
            from database import aio_get_user as _gu_ch
            challenger_data = await _gu_ch(challenger_uid)
            if not challenger_data:
                await call.answer(t(lang, "duel_challenger_not_found"), show_alert=True)
                return
            # Принимаем
            result = accept_challenge(user.id)
            if not result:
                await call.answer(t(lang, "duel_challenge_expired"), show_alert=True)
                await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
                return
            # Двойная проверка под защитой лока: между предыдущей проверкой и
            # accept_challenge() вызывающий теоретически мог успеть войти в бой.
            if challenger_uid in _active_battles:
                await call.answer(t(lang, "duel_challenger_in_battle_2"), show_alert=True)
                await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
                return
            battle = start_challenge_battle(challenger_uid, challenger_data, user.id, data)
            _active_battles[challenger_uid] = battle
            _active_battles[user.id] = battle
            # Показываем бой принявшему
            await edit(battle_text(battle, user.id, lang), battle_keyboard(battle, user.id, lang))
            _battle_msgs[user.id] = (call.message.chat.id, call.message.message_id)
            # Уведомляем вызывающего
            try:
                _challenger_lang = await _lang_for_uid(challenger_uid)
                _acceptor_name = _esc(data.get("first_name") or data.get("username") or t(_challenger_lang, "duel_invite_player_default"))
                sent = await bot.send_message(
                    challenger_uid,
                    t(_challenger_lang, "duel_accepted_battle_started").format(name=_acceptor_name)
                    + battle_text(battle, challenger_uid, _challenger_lang),
                    parse_mode="HTML",
                    reply_markup=battle_keyboard(battle, challenger_uid, _challenger_lang),
                )
                _battle_msgs[challenger_uid] = (sent.chat.id, sent.message_id)
            except Exception:
                pass
            return

        # ===== ДУЭЛИ: отклонить вызов =====
        if cd.startswith("duel_challenge_decline:"):
            challenger_uid = int(cd.split(":")[1])
            decline_challenge(user.id)
            await call.answer(t(lang, "duel_challenge_declined_toast"))
            await edit(duel_main_text(data, lang), duel_main_keyboard(lang))
            # Уведомляем вызывающего
            try:
                _decline_lang = await _lang_for_uid(challenger_uid)
                target_name = _esc(data.get("first_name") or data.get("username") or t(_decline_lang, "duel_invite_player_default"))
                await bot.send_message(
                    challenger_uid,
                    t(_decline_lang, "duel_challenge_declined_notify").format(name=target_name),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return

        if cd == "duel_charstats":
            await call.answer()
            await edit(duel_charstats_text(data, uid=user.id, lang=lang), duel_charstats_keyboard(lang))
            return

        # ===== ЗАГЛУШКИ (в разработке) =====
        responses = {
            "exchange": f'<tg-emoji emoji-id="5402186569006210455">💱</tg-emoji> <b>{"БИРЖА" if lang == "ru" else "EXCHANGE"}</b>\n\n<blockquote><b>{t(lang, "in_development")}</b></blockquote>',
        }
        text = responses.get(cd, t(lang, "unknown_cmd"))
        try:
            await call.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=back_button(lang)
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                print(e)


# ===== ОПЛАТА ЧЕРЕЗ TELEGRAM STARS =====

@dp.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload

    # ===== ОПЛАТА: Кейс Артефактов =====
    if payload == "artifact_case":
        try:
            from shop import STAR
            from database import aio_get_user, aio_save_user
        except Exception as _imp_e:
            # Импорт упал ДО того, как charge_id помечен обработанным — если
            # промолчать здесь, деньги списаны, а пользователь не получит
            # вообще ничего (см. историю бага "молчит после оплаты").
            import traceback as _tb
            print(f"[artifact_case] КРИТИЧНО: ошибка импорта в обработчике оплаты: {_imp_e!r}")
            _tb.print_exc()
            try:
                await bot.send_message(
                    message.chat.id,
                    "⚠️ Оплата принята, но бот столкнулся с внутренней ошибкой. "
                    "Напиши админу /support — начислим награду вручную."
                )
            except Exception:
                pass
            return

        # Проверяем сумму оплаты — защита от подмены инвойса
        paid_amount = message.successful_payment.total_amount
        if paid_amount != ARTIFACT_CASE_COST_STARS:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return

        # Защита от replay-атаки: один charge_id обрабатывается ровно один раз
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)

        uid = message.from_user.id

        # ВАЖНО: раньше здесь бралась _get_user_lock(uid) и всё оборачивалось
        # в `async with lock:`. /giveart (админ-команда) работает по этому же
        # payload'у ("выдать артефакт") БЕЗ какого-либо лока и с ним таких
        # проблем никогда не было. Если лок для этого uid где-то в другом
        # хендлере не освобождается (баг/раннее return без release),
        # наш код мог зависать на `async with lock` НАВСЕГДА — без
        # исключения, без лога, без сообщения игроку. Именно так выглядит
        # "деньги списаны, а бот молчит". Убираю лок, выдаём напрямую —
        # ровно как /giveart.
        # ВСЁ ниже — в одном try/except, включая получение/создание юзера.
        # Деньги уже списаны Telegram'ом И charge_id уже помечен как
        # processed (см. выше), поэтому что бы ни случилось (ошибка в
        # aio_get_user/aio_get_or_create_user, в open_artifact_case, в
        # check_achievements, в верстке текста) — пользователь должен
        # получить хотя бы fallback-сообщение, а не тишину. Раньше
        # aio_get_user/aio_get_or_create_user были ВНЕ try/except: если
        # там падало исключение, оно уходило в глобальный @dp.errors(),
        # который просто логирует и глушит апдейт — юзер не получал
        # вообще ничего, а повторная доставка апдейта от Telegram сразу
        # же выходила по "charge уже processed" — тоже молча. Баг был
        # "навсегда": деньги списаны, ни артефакта, ни компенсации.
        _lang = "ru"
        chosen = None
        msg = ""
        try:
            data = await aio_get_user(uid)
            if not data:
                # Пользователь не найден в БД — создаём и пробуем снова
                data = await aio_get_or_create_user(message.from_user)
            data["id"] = uid  # подстраховка: ключ "id" должен совпадать с uid

            _lang = data.get("lang", "ru")

            ok, msg, chosen = open_artifact_case(data, _lang)

            # Сохраняем СРАЗУ, используя uid напрямую (не data["id"],
            # чтобы не зависеть от возможного отсутствия/рассинхрона ключа).
            await aio_save_user(uid, data)

            try:
                _ach_newly = check_achievements(data)
                if _ach_newly:
                    await aio_save_user(uid, data)
                    await _notify_ach(uid, data, _ach_newly)
            except Exception as _ach_e:
                import traceback as _tb
                print(f"[artifact_case] Ошибка check_achievements: {_ach_e!r}")
                _tb.print_exc()
        except Exception as _grant_e:
            import traceback as _tb
            print(f"[artifact_case] КРИТИЧНО: ошибка выдачи награды: {_grant_e!r}")
            _tb.print_exc()
            fallback = (
                "⚠️ Оплата прошла, но при выдаче награды произошла ошибка. "
                "Напиши админу /support — разберёмся и начислим вручную."
                if _lang != "en" else
                "⚠️ Payment went through, but there was an error granting the reward. "
                "Please contact support — we'll credit it manually."
            )
            try:
                await bot.send_message(message.chat.id, fallback)
            except Exception:
                pass
            return

        # 1) Обновляем старое сообщение — убираем ссылку-инвойс
        pending = _pending_artifact_msg.pop(uid, None)
        if pending:
            old_chat_id, old_msg_id = pending
            try:
                await bot.edit_message_text(
                    artifact_case_detail_text(data, _lang),
                    chat_id=old_chat_id,
                    message_id=old_msg_id,
                    reply_markup=artifact_case_keyboard(lang=_lang),
                    parse_mode="HTML"
                )
            except Exception:
                pass

        # 2) Формируем текст результата
        # ВАЖНО: chosen может быть None — это 25%-я ветка, когда вместо
        # артефакта выдаются монеты (см. open_artifact_case в shop.py).
        # Раньше здесь считалось, что chosen всегда есть, из-за чего
        # обращение к chosen["effect"] падало с TypeError и пользователь
        # не получал вообще никакого ответа от бота (хотя деньги/монеты
        # уже были начислены и сохранены выше).
        try:
            if chosen is None:
                # Монеты вместо артефакта — msg уже содержит полный текст результата
                if _lang == "en":
                    success_text = (
                        f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'{msg}'
                    )
                else:
                    success_text = (
                        f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'{msg}'
                    )
            else:
                from shop import _get_effect_label as _eff_lbl
                effect_label = _eff_lbl(chosen["effect"], _lang)
                art_name = chosen.get("name_en", chosen["name"]) if _lang == "en" else chosen["name"]
                art_emoji_id = chosen.get("emoji_id", "")
                art_emoji = f'<tg-emoji emoji-id="{art_emoji_id}">♦️</tg-emoji> ' if art_emoji_id else ""

                # msg уже содержит правильный текст (новый артефакт или дубликат+компенсация)
                if _lang == "en":
                    success_text = (
                        f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>'
                        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>Artifact Case opened!</b>\n'
                        f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>Artifact: {art_emoji}{art_name}</b>\n'
                        f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>Bonus: {chosen["multiplier"]}× {effect_label} forever</b>\n'
                        f'<tg-emoji emoji-id="5267500801240092311">🎟</tg-emoji> <b>Spent: {ARTIFACT_CASE_COST_STARS} {STAR}</b>'
                        f'</blockquote>\n\n'
                        f'{msg}'
                    )
                else:
                    success_text = (
                        f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                        f'━━━━━━━━━━━━━━━━━━━━\n\n'
                        f'<blockquote>'
                        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>Кейс Артефактов открыт!</b>\n'
                        f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>Артефакт: {art_emoji}{art_name}</b>\n'
                        f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>Бонус: {chosen["multiplier"]}× {effect_label} навсегда</b>\n'
                        f'<tg-emoji emoji-id="5267500801240092311">🎟</tg-emoji> <b>Потрачено: {ARTIFACT_CASE_COST_STARS} {STAR}</b>'
                        f'</blockquote>\n\n'
                        f'{msg}'
                    )
            await bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        except Exception as _e:
            # Деньги/артефакт уже сохранены в БД строкой выше (save_user),
            # поэтому даже если верстка сообщения упала — игрок не теряет
            # покупку. Но бот больше не должен "молчать": шлём резервное
            # уведомление и логируем причину для разбора.
            print(f"[artifact_case] Ошибка формирования success_text: {_e!r}")
            fallback = (
                "✅ Оплата прошла успешно, кейс открыт! Награда уже зачислена "
                "(проверь баланс/коллекцию артефактов). Не удалось красиво "
                "оформить сообщение — но покупка не потеряна."
                if _lang != "en" else
                "✅ Payment successful, case opened! Reward has been credited "
                "(check your balance/artifact collection). Couldn't render the "
                "fancy message, but your purchase is not lost."
            )
            try:
                await bot.send_message(message.chat.id, fallback)
            except Exception:
                pass
        return

    # ===== ОПЛАТА: Зелье =====
    if payload.startswith("potion_"):
        potion_key = payload.removeprefix("potion_")
        from database import aio_get_user, aio_save_user
        from hunt import confirm_potion_purchase as _confirm_potion

        p = POTIONS_BY_KEY.get(potion_key)
        paid_amount = message.successful_payment.total_amount
        if not p or paid_amount != p["price_stars"]:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return

        # Защита от replay-атаки
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)

        uid = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                data = await aio_get_or_create_user(message.from_user)
            _lang = data.get("lang", "ru")

            ok, msg = await asyncio.to_thread(confirm_potion_purchase, potion_key, uid, _lang)

            # Обновляем старое сообщение (экран зелий)
            pending = _pending_potion_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id = pending
                try:
                    await bot.edit_message_text(
                        potions_shop_text(_lang),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=potions_shop_keyboard(_lang),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            await bot.send_message(message.chat.id, msg, parse_mode="HTML")
        return

    if payload.startswith("premium_pickaxe:"):
        pick_key = payload.split(":", 1)[1]
        try:
            from miner import (
                grant_premium_pickaxe, pickaxe_detail_text, pickaxe_detail_keyboard,
                get_pickaxe_page, PICKAXES, TIER_LABELS, STAR
            )
            from database import aio_get_user, aio_save_user

            # Проверяем сумму: должна совпадать с ценой кирки в Stars
            from miner import PICKAXES as _PX
        except Exception as _imp_e:
            # Тот же класс бага, что и в artifact_case: импорт до marking
            # charge_id — если промолчать, деньги списаны, а пользователь
            # не получит ничего.
            import traceback as _tb
            print(f"[premium_pickaxe] КРИТИЧНО: ошибка импорта в обработчике оплаты: {_imp_e!r}")
            _tb.print_exc()
            try:
                await bot.send_message(
                    message.chat.id,
                    "⚠️ Оплата принята, но бот столкнулся с внутренней ошибкой. "
                    "Напиши админу /support — начислим награду вручную."
                )
            except Exception:
                pass
            return
        _pick_entry = _PX.get(pick_key)
        paid_amount = message.successful_payment.total_amount
        if _pick_entry and _pick_entry.get("cost_stars") and paid_amount != _pick_entry["cost_stars"]:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return

        # Защита от replay-атаки
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)

        uid = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                return
            ok, _ = grant_premium_pickaxe(data, pick_key)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            p    = PICKAXES[pick_key]
            tier = TIER_LABELS.get(p.get("tier", ""), "")
            page = get_pickaxe_page(pick_key)

            # 1) Обновляем старое сообщение (экран кирки) — теперь с кнопкой «Выбрать»
            pending = _pending_stars_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id, _ = pending
                try:
                    await bot.edit_message_text(
                        pickaxe_detail_text(data, pick_key),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=pickaxe_detail_keyboard(data, pick_key, page),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            # 2) Новое сообщение об успешной оплате
            success_text = (
                f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                f'━━━━━━━━━━━━━━━━━━━━\n\n'
                f'<blockquote>'
                f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>Кирка: {p["name"]}</b>\n'
                f'<tg-emoji emoji-id="5444856076954520455">🎟</tg-emoji> <b>Тир: {tier}</b>\n'
                f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>Ударов за кампанию: {format_amount(p["dig_min"])}–{format_amount(p["dig_max"])}</b>\n'
                f'<tg-emoji emoji-id="5267500801240092311">🎟</tg-emoji> <b>Потрачено: {format_amount(p["cost_stars"])} {STAR}</b>'
                f'</blockquote>\n\n'
                f'<tg-emoji emoji-id="5206607081334906820">🎟</tg-emoji> <b>Кирка добавлена в мастерскую!</b>'
            )
            await bot.send_message(
                message.chat.id,
                success_text,
                parse_mode="HTML"
            )

    # ===== ОПЛАТА: Статус VIP =====
    if payload == "status_vip":
        from database import aio_get_user, aio_save_user
        paid_amount = message.successful_payment.total_amount
        if paid_amount != VIP_COST_STARS:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)
        uid = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                return
            _lang = data.get("lang", "ru")
            ok, msg = activate_status(data, "vip", _lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            # Обновляем старое сообщение
            pending = _pending_status_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id, _ = pending
                try:
                    await bot.edit_message_text(
                        status_vip_text(data, _lang),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=status_vip_keyboard(data, _lang),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            if _lang == "en":
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5325547803936572038">👑</tg-emoji> <b>VIP status activated for 30 days!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.3 to mining · +15% crit · Luck in cases</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Spent: {VIP_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            else:
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5325547803936572038">👑</tg-emoji> <b>Статус VIP активирован на 30 дней!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.3 к добыче · +15% крит · Удача в кейсах</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Потрачено: {VIP_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            await bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        return

    # ===== ОПЛАТА: Статус Premium =====
    if payload == "status_premium":
        from database import aio_get_user, aio_save_user
        paid_amount = message.successful_payment.total_amount
        if paid_amount != PREMIUM_COST_STARS:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)
        uid = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                return
            _lang = data.get("lang", "ru")
            ok, msg = activate_status(data, "premium", _lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            pending = _pending_status_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id, _ = pending
                try:
                    await bot.edit_message_text(
                        status_premium_text(data, _lang),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=status_premium_keyboard(data, _lang),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            if _lang == "en":
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5427168083074628963">⭐</tg-emoji> <b>Premium status activated for 30 days!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.6 to mining · +25% crit · Max luck</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Spent: {PREMIUM_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            else:
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5427168083074628963">⭐</tg-emoji> <b>Статус Premium активирован на 30 дней!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.6 к добыче · +25% крит · Макс. удача</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Потрачено: {PREMIUM_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            await bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        return

    # ===== ОПЛАТА: Донат (пакет монет) =====
    if payload.startswith("donate:"):
        from database import aio_get_user, aio_save_user
        pkg_key    = payload.split(":", 1)[1]
        pkg        = DONATE_BY_KEY.get(pkg_key)
        if not pkg:
            await bot.send_message(message.chat.id, "❌ Пакет доната не найден.")
            return

        paid_amount = message.successful_payment.total_amount
        if paid_amount != pkg["stars"]:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return

        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)

        uid  = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                data = await aio_get_or_create_user(message.from_user)

            _lang = data.get("lang", "ru")
            ok, msg, coins = apply_donate(data, pkg_key)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)

            # Обновляем старое сообщение — убираем кнопку-инвойс
            pending = _pending_donate_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id, _pkg_key = pending
                try:
                    await bot.edit_message_text(
                        donate_package_text(_pkg_key, _lang),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=donate_package_keyboard(_pkg_key, lang=_lang),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            name = pkg["label_en"] if _lang == "en" else pkg["label"]
            from donate import _fmt_num as _d_fmt
            coins_str = _d_fmt(pkg["coins"])
            stars_str = str(pkg["stars"])

            if _lang == "en":
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'{msg}'
                )
            else:
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'{msg}'
                )
            await bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        return

    if payload == "status_upgrade_premium":
        from database import aio_get_user, aio_save_user
        paid_amount = message.successful_payment.total_amount
        if paid_amount != UPGRADE_COST_STARS:
            await bot.send_message(message.chat.id, "❌ Ошибка: сумма оплаты не совпадает.")
            return
        charge_id = message.successful_payment.telegram_payment_charge_id
        if await aio_is_charge_processed(charge_id):
            return
        await aio_mark_charge_processed(charge_id, message.from_user.id, payload)
        uid = message.from_user.id
        lock = await _get_user_lock(uid)
        async with lock:
            data = await aio_get_user(uid)
            if not data:
                return
            _lang = data.get("lang", "ru")
            ok, msg = activate_status(data, "premium", _lang)
            if ok:
                _ach_newly = check_achievements(data)
                await aio_save_user(data["id"], data)
                await _notify_ach(data["id"], data, _ach_newly)
            pending = _pending_status_msg.pop(uid, None)
            if pending:
                old_chat_id, old_msg_id, _ = pending
                try:
                    await bot.edit_message_text(
                        status_premium_text(data, _lang),
                        chat_id=old_chat_id,
                        message_id=old_msg_id,
                        reply_markup=status_premium_keyboard(data, _lang),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            if _lang == "en":
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Payment successful!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5427168083074628963">⭐</tg-emoji> <b>VIP upgraded to Premium for 30 days!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.6 to mining · +25% crit · Max luck</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Spent: {UPGRADE_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            else:
                success_text = (
                    f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji> <b>Оплата прошла успешно!</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━\n\n'
                    f'<blockquote>'
                    f'<tg-emoji emoji-id="5427168083074628963">⭐</tg-emoji> <b>VIP улучшен до Premium на 30 дней!</b>\n'
                    f'<tg-emoji emoji-id="5197371802136892976">⛏</tg-emoji> <b>×1.6 к добыче · +25% крит · Макс. удача</b>\n'
                    f'<tg-emoji emoji-id="5348570868752595928">⭐</tg-emoji> <b>Потрачено: {UPGRADE_COST_STARS} Stars</b>'
                    f'</blockquote>'
                )
            await bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        return


def _cdl_payout_apply_sync(uid: int, total_payout: int, total_profit: int, paid_count: int):
    """Синхронная часть начисления вклада — выполняется ТОЛЬКО через
    asyncio.to_thread (см. вызов ниже), никогда напрямую из event loop.
    Раньше этот sqlite3-блок выполнялся прямо в event loop и был основной
    причиной многоминутных зависаний бота для ВСЕХ пользователей сразу
    (диск-I/O в главном потоке блокирует обработку любых других апдейтов).
    """
    import sqlite3 as _sq, json as _js
    # timeout=30 + WAL/busy_timeout — как в database.py/cdl.py, чтобы
    # это соединение вело себя так же предсказуемо, как остальные.
    _conn = _sq.connect("tgstellar.db", timeout=30)
    try:
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=30000")
        _conn.row_factory = _sq.Row
        row = _conn.execute(
            "SELECT data_json FROM users WHERE uid=?", (uid,)
        ).fetchone()
        if not row:
            print(f"[cdl_payout_loop] uid={uid} не найден в users")
            return None
        udata = _js.loads(row["data_json"])
        udata["balance"] = udata.get("balance", 0) + total_payout
        udata["ref_income"] = udata.get("ref_income", 0) + total_payout
        udata["deposits_claimed"] = udata.get("deposits_claimed", 0) + paid_count
        udata["deposits_total_profit"] = udata.get("deposits_total_profit", 0) + total_profit
        _ach_newly = check_achievements(udata)
        _conn.execute(
            # balance дублируется в отдельную колонку — её читает лидерборд
            # (leaders.py) через быстрый ORDER BY без парсинга data_json.
            "UPDATE users SET data_json=?, balance=? WHERE uid=?",
            (_js.dumps(udata, ensure_ascii=False), udata["balance"], uid)
        )
        _conn.commit()
        return udata, _ach_newly
    finally:
        # `with _conn:` управляет только транзакцией, но НЕ закрывает
        # соединение — этот цикл тикает раз в минуту, поэтому забытый
        # close() здесь особенно быстро копит открытые fd на tgstellar.db.
        _conn.close()


async def _cdl_payout_loop():
    """Фоновая задача: каждую минуту проверяет созревшие вклады,
    выплачивает баланс и отправляет уведомление пользователю."""
    while True:
        await asyncio.sleep(60)
        try:
            matured = await _cdl_get_matured_all()
            if not matured:
                continue

            # Группируем по uid
            by_uid: dict[int, list] = {}
            for dep in matured:
                by_uid.setdefault(dep["uid"], []).append(dep)

            for uid, deps in by_uid.items():
                # Считаем выплаты и помечаем claimed=1
                total_payout = 0
                total_profit = 0
                paid_deps    = []
                for dep in deps:
                    payout = await _cdl_claim(dep["id"])
                    if payout is not None:
                        total_payout += payout
                        total_profit += payout - dep["amount"]
                        paid_deps.append(dep)
                if not paid_deps:
                    continue

                # Атомарное начисление баланса — в отдельном потоке, чтобы
                # не морозить event loop для всех остальных пользователей.
                try:
                    result = await asyncio.to_thread(
                        _cdl_payout_apply_sync, uid, total_payout, total_profit, len(paid_deps)
                    )
                except Exception as _db_e:
                    print(f"[cdl_payout_loop] ошибка начисления uid={uid}: {_db_e}")
                    continue
                if result is None:
                    continue
                udata, _ach_newly = result

                if _ach_newly:
                    await _notify_ach(uid, udata, _ach_newly)

                # Шлём отдельное уведомление на каждый вклад
                for dep in paid_deps:
                    cfg = _CDL_DEP_BY_KEY_REF.get(dep["dep_key"], {})
                    profit = dep["payout"] - dep["amount"]
                    notif = (
                        f'<tg-emoji emoji-id="{cfg.get("emoji_id", "5440621591387980068")}">💰</tg-emoji> '
                        f'<b>Вклад #{dep["id"]} закрыт!</b>\n\n'
                        f'<blockquote>'
                        f'<b>{cfg.get("label", dep["dep_key"])}</b> · {cfg.get("hours", "?")}ч\n'
                        f'<tg-emoji emoji-id="5447183459602669338">💰</tg-emoji> '
                        f'<b>Вложено:</b> {format_amount(dep["amount"])}\n'
                        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> '
                        f'<b>Получено:</b> +{format_amount(dep["payout"])}\n'
                        f'<tg-emoji emoji-id="5224257782013769471">💸</tg-emoji> '
                        f'<b>Прибыль:</b> +{format_amount(profit)}'
                        f'</blockquote>'
                    )
                    try:
                        await bot.send_message(uid, notif, parse_mode="HTML")
                    except Exception as _send_e:
                        print(f"[cdl_payout_loop] send_message uid={uid}: {_send_e}")
        except Exception as _e:
            print(f"[cdl_payout_loop] {_e}")


_PETS_INTERVAL_ONE  = 12 * 3600
_PETS_INTERVAL_MANY =  6 * 3600
_USERS_SCAN_INTERVAL = 30  # секунд — определяется самой частой нуждой (сад)


async def _users_scan_loop():
    """Объединённый фоновый цикл: шахта + питомцы + сад.

    РАНЬШЕ это были три (фактически четыре, считая garden_notify_loop в
    main.py) НЕЗАВИСИМЫХ цикла, каждый из которых сам делал полный скан
    таблицы users (get_all_users() -> json.loads на каждую строку) на
    своём таймере (60с / 15мин / 30с). Из-за несинхронизированных
    таймеров сканы периодически накладывались друг на друга по времени,
    и в такие моменты в памяти одновременно жили 2-3 полные копии всей
    таблицы (парсинг + промежуточные объекты в каждом потоке) — это и
    давало резкие скачки RSS процесса.

    Теперь полный скан делается ОДИН раз за тик (раз в 30 сек — под
    самую частую потребность, сад), и в рамках одного прохода по уже
    загрученным данным проверяются все три системы. Условия по времени
    (mine_last_notified_start, pet_last_group_notify) остаются внутри —
    они просто пропускают пользователя, если его час/минута ещё не
    настали, реального доп. нагрузки от более частого тика это не даёт,
    т.к. сама проверка — это дешёвое сравнение в памяти, а не поход в БД.
    """
    from database import get_all_users, save_user as _sv
    import random as _rnd
    import datetime as _dt
    import green as _green

    while True:
        try:
            for _d in await asyncio.to_thread(get_all_users):
                uid = _d.get("id")
                if not uid:
                    continue
                changed = False

                # ---------- Шахта: уведомление о завершении копки ----------
                if _d.get("mine_start") is not None and not _d.get("mine_collected"):
                    if _d.get("mine_last_notified_start") != _d["mine_start"]:
                        prog = calc_mine_progress(_d)
                        if prog["finished"]:
                            _lang = _d.get("lang", "ru")
                            msg_text = mine_finished_notify_text(_d, _lang)
                            try:
                                await bot.send_message(uid, msg_text, parse_mode="HTML")
                            except Exception:
                                pass
                            _d["mine_last_notified_start"] = _d["mine_start"]
                            changed = True

                # ---------- Питомцы: доход + уведомление ----------
                owned = _d.get("owned_pets", [])
                if owned:
                    now = int(_dt.datetime.now(_dt.timezone.utc).timestamp())
                    last_all = _d.get("pet_last_group_notify", 0)
                    interval = _PETS_INTERVAL_ONE if len(owned) == 1 else _PETS_INTERVAL_MANY

                    if now - last_all >= interval:
                        pk  = _rnd.choice(owned)
                        pet = __import__("pets").PETS_BY_KEY.get(pk)
                        if pet:
                            amount = _rnd.randint(pet["income_min"], pet["income_max"])
                            try:
                                from shop import get_artifact_pets_multiplier as _apt_mult
                                amount = int(amount * _apt_mult(_d))
                            except Exception:
                                pass
                            _d["balance"] = _d.get("balance", 0) + amount
                            _d["ref_income"] = _d.get("ref_income", 0) + amount
                            _d["pet_last_group_notify"] = now

                            msgs       = __import__("pets")._NOTIFICATIONS.get(pk, [])
                            notif_text = _rnd.choice(msgs) if msgs else ""
                            msg_text   = pet_income_text(pk, amount, notif_text)
                            try:
                                await bot.send_message(uid, msg_text, parse_mode="HTML")
                            except Exception:
                                pass
                            changed = True

                # ---------- Сад: проверка созревших грядок ----------
                # Сад защищаем персональным локом и перечитываем свежие
                # данные ПОД локом перед сохранением — снапшот из общего
                # скана мог устареть из-за параллельного действия игрока
                # (сбор урожая и т.п.). Это сохраняет ту же гарантию,
                # что была в прежнем отдельном garden_notify_loop.
                garden = _d.get("garden")
                if isinstance(garden, dict) and garden.get("plots"):
                    from database import get_user as _gu_fresh
                    async with await _get_user_lock(uid):
                        # Перечитываем свежие данные ПОД локом — снапшот из
                        # общего скана мог устареть из-за параллельного
                        # действия игрока (сбор урожая и т.п.), как и в
                        # прежнем отдельном garden_notify_loop.
                        fresh = await asyncio.to_thread(_gu_fresh, uid)
                        ready = _green.check_ready_plots(fresh) if fresh else []
                        if ready:
                            await asyncio.to_thread(_sv, uid, fresh)

                    for item in ready:
                        flower = item["flower"]
                        text = (
                            f"🌸 В твоём Мистическом саду созрело растение — "
                            f"<b>{_green.flower_label(flower)}</b>!\n"
                            f"Загляни собрать урожай 🌾"
                        )
                        try:
                            await bot.send_message(uid, text, parse_mode="HTML")
                        except Exception:
                            pass
                    # Сад сохраняется отдельной веткой выше (под локом,
                    # на свежих данных) — в общий `_d`/`changed` не мешаем.

                if changed:
                    await asyncio.to_thread(_sv, uid, _d)
        except Exception as _e:
            print(f"[users_scan_loop] {_e}")
        await asyncio.sleep(_USERS_SCAN_INTERVAL)


async def _poison_loop():
    """Фоновая задача: яд наносит урон боссу каждую минуту.
    Суммарный урон = damage, распределённый равномерно по 30 тикам (30 мин).
    Если босс умирает от яда — владелец получает награду.
    """
    from database import get_all_users, save_user as _sv
    from hunt import get_boss_state, _save_boss_state, BOSS_KILL_REWARD, _now_ts as _h_now
    from shop import get_active_poison_info

    while True:
        await asyncio.sleep(60)  # тик каждую минуту
        try:
            from database import get_all_users as _gau
            # Полный скан таблицы (json.loads на каждого юзера) выполняем в
            # отдельном потоке, чтобы на время чтения БД event loop бота не
            # замирал для всех игроков одновременно.
            for _d in await asyncio.to_thread(_gau):
                poison = get_active_poison_info(_d)
                if not poison:
                    continue

                now = _h_now()

                # Считаем сколько тиков уже прошло и сколько урона нанесено
                applied_at   = poison.get("applied_at", poison["ends_at"] - 1800)
                total_damage = poison["damage"]
                duration_sec = 30 * 60  # 30 минут = 1800 сек
                tick_damage  = round(total_damage / 30)  # урон за 1 тик (1 мин)

                last_tick = poison.get("last_tick", applied_at)
                if now - last_tick < 55:  # ещё не прошла минута
                    continue

                # Наносим тик урона боссу
                state = await asyncio.to_thread(get_boss_state)
                if not state.get("boss_alive"):
                    continue

                hp_before = state["boss_hp"]
                hp_after  = max(0, hp_before - tick_damage)
                state["boss_hp"] = hp_after

                poison["last_tick"] = now
                _d["active_poison"] = poison

                killed = hp_after == 0
                if killed:
                    from datetime import datetime, timezone as _tz
                    died_at      = now
                    spawned_at   = state.get("boss_spawned", died_at)
                    kill_duration = died_at - spawned_at
                    state["boss_alive"]         = False
                    state["boss_died_at"]        = died_at
                    state["boss_kill_duration"]  = kill_duration
                    _d["balance"] = _d.get("balance", 0) + BOSS_KILL_REWARD
                    _d["ref_income"] = _d.get("ref_income", 0) + BOSS_KILL_REWARD
                    _d["active_poison"] = None

                await asyncio.to_thread(_save_boss_state, state)
                await asyncio.to_thread(_sv, _d["id"], _d)

                if killed:
                    from hunt import BOSSES_BY_KEY
                    boss_name = BOSSES_BY_KEY.get(state.get("boss_key"), {}).get("name", "Босс")
                    reward_text = (
                        f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд добил босса!</b>\n\n'
                        f'<blockquote>'
                        f'<b>{boss_name} уничтожен ядом!</b>\n'
                        f'<tg-emoji emoji-id="5438496463044752972">💰</tg-emoji> <b>Награда: +{format_amount(BOSS_KILL_REWARD)} монет</b>'
                        f'</blockquote>'
                    )
                    try:
                        await bot.send_message(_d["id"], reward_text, parse_mode="HTML")
                    except Exception:
                        pass

        except Exception as _e:
            print(f"[poison_loop] {_e}")



async def _lang_for_uid(uid: int) -> str:
    """Возвращает язык интерфейса конкретного игрока (для рендера боя другому игроку).
    Раньше это была синхронная функция с прямым sqlite3-доступом, вызываемая
    напрямую из async-хендлеров дуэлей (в т.ч. из таймера, тикающего каждые
    3 секунды на КАЖДЫЙ активный бой) — то есть event loop блокировался на
    диск-I/O практически при каждом действии в дуэли. Теперь — через to_thread."""
    try:
        from database import get_user as _gu_lang
        d = await asyncio.to_thread(_gu_lang, uid) or {}
        return get_lang(d)
    except Exception:
        return "ru"


async def _duel_timer_loop():
    """Каждые 3 секунды обновляет боевые экраны активных дуэлей,
    чтобы кнопки отображали актуальный таймер кулдауна."""
    import time as _time
    while True:
        await asyncio.sleep(3)
        try:
            processed = set()
            for uid, battle in list(_active_battles.items()):
                if battle.get("finished"):
                    continue
                me = "p1" if battle["p1_uid"] == uid else "p2"
                now = int(_time.time())
                cooldowns = battle.get(f"{me}_cooldowns", {})
                has_active_cd = any(v > now for v in cooldowns.values())
                if not has_active_cd:
                    continue
                msg_info = _battle_msgs.get(uid)
                if not msg_info:
                    continue
                # Дедупликация — не обновляем одно и то же сообщение дважды
                msg_key = (msg_info[0], msg_info[1])
                if msg_key in processed:
                    continue
                processed.add(msg_key)
                try:
                    await bot.edit_message_text(
                        chat_id=msg_info[0],
                        message_id=msg_info[1],
                        text=battle_text(battle, uid, await _lang_for_uid(uid)),
                        parse_mode="HTML",
                        reply_markup=battle_keyboard(battle, uid, await _lang_for_uid(uid)),
                    )
                except Exception:
                    pass
        except Exception as _e:
            print(f"[duel_timer_loop] {_e}")

async def _hp_regen_notify_loop():
    """
    Каждые 10 секунд тикает регенерация HP игроков вне боя.
    Когда HP восстанавливается до 100 — шлёт уведомление.
    """
    # Просто держим словарь «уже уведомлён о полном HP»
    _notified_full: set[int] = set()

    while True:
        await asyncio.sleep(HP_REGEN_INTERVAL)
        try:
            from database import get_user as _gu_regen
            from duel import _player_hp as _phps, _calc_stats as _cs
            # Раньше здесь на каждый тик (каждые несколько секунд!) грузилась
            # и парсилась ВСЯ таблица users — это останавливало весь бот для
            # всех игроков одновременно. _player_hp — это уже готовый
            # in-memory словарь тех, кому вообще нужна регенерация, так что
            # достаточно пройтись по нему, а из БД читать по одному игроку
            # (да и то только когда реально есть тик) вместо полного скана.
            for _uid, entry in list(_phps.items()):
                if _uid in _active_battles:
                    continue
                import time as _t
                now = int(_t.time())
                elapsed = now - entry["last_regen_at"]
                ticks   = elapsed // HP_REGEN_INTERVAL
                if ticks > 0:
                    _d = await asyncio.to_thread(_gu_regen, _uid)
                    if _d is None:
                        continue
                    hp_max = _cs(_d)["hp"]
                    was_below_100 = entry["hp"] < 100
                    entry["hp"] = min(hp_max, entry["hp"] + ticks * HP_REGEN_AMOUNT)
                    entry["last_regen_at"] += ticks * HP_REGEN_INTERVAL
                    # Уведомление только один раз когда достиг 100
                    if was_below_100 and entry["hp"] >= 100 and _uid not in _notified_full:
                        _notified_full.add(_uid)
                        try:
                            await bot.send_message(
                                _uid,
                                '❤️ <b>HP восстановлено!</b>\n\n'
                                '<blockquote>Твоё здоровье полностью восстановлено.\n'
                                'Теперь можно начинать новую дуэль!</blockquote>',
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                    elif entry["hp"] < 100:
                        _notified_full.discard(_uid)
        except Exception as _e:
            print(f"[hp_regen_loop] {_e}")


async def run_bot():
    logging.basicConfig(level=logging.INFO)

    init_db()          # создаёт таблицу при первом запуске
    init_refs_db()     # создаёт таблицы рефералов и капчи
    init_hunt_db()     # создаёт таблицу боссов
    init_leaders_db()  # создаёт таблицу статистики боссов для лидерборда
    init_stats_db()    # создаёт таблицу онлайн-статистики
    init_klan_db()     # создаёт таблицы кланов
    init_checks_db()   # создаёт таблицы чеков и промокодов
    init_cdl_db()      # создаёт таблицу вкладов
    init_city_db()     # создаёт таблицы города (арбитражный трейдинг)
    init_crystal_leaders_db()  # создаёт таблицу событий баланса кристаллов для топа
    init_achievements_db()  # создаёт таблицу счётчиков "сколько игроков открыли ачивку"

    # ── Миграция: добавляем поля питомцев для старых пользователей ──
    from database import aio_get_all_users, aio_save_user as _save_mig
    for _u in await aio_get_all_users():
        _changed = False
        if "owned_pets" not in _u:
            _u["owned_pets"] = []
            _changed = True
        if "pet_last_notify" not in _u:
            _u["pet_last_notify"] = {}
            _changed = True
        if "pet_last_income" not in _u:
            _u["pet_last_income"] = {}
            _changed = True
        if "pet_income_offset" not in _u:
            _u["pet_income_offset"] = {}
            _changed = True
        if "pet_last_group_notify" not in _u:
            _u["pet_last_group_notify"] = 0
            _changed = True
        # Миграция охоты
        if "owned_swords" not in _u:
            _u["owned_swords"] = []
            _changed = True
        if "equipped_sword" not in _u:
            _u["equipped_sword"] = None
            _changed = True
        if "last_boss_hit" not in _u:
            _u["last_boss_hit"] = 0
            _changed = True
        if _changed:
            await _save_mig(_u["id"], _u)

    # ── Запускаем фоновую задачу вкладов (авто-выплаты) ──
    asyncio.create_task(_cdl_payout_loop())

    # ── Объединённый скан: шахта + питомцы + сад (один full-table scan
    #    вместо трёх/четырёх независимых) ──
    asyncio.create_task(_users_scan_loop())

    # ── Запускаем фоновую задачу яда ──
    asyncio.create_task(_poison_loop())

    # ── Запускаем таймер обновления кнопок дуэлей (каждые 3 сек) ──
    asyncio.create_task(_duel_timer_loop())

    # ── Запускаем фоновую задачу регенерации HP вне боя ──
    asyncio.create_task(_hp_regen_notify_loop())

    # ── Запускаем фоновые задачи города (цены / путешествия / новости) ──
    asyncio.create_task(city_prices_loop())
    asyncio.create_task(city_travel_loop(bot))
    asyncio.create_task(city_news_loop())
    asyncio.create_task(city_exchange_loop())

    # ── Бонус за @TGStellarr_bot в описании профиля: раз в 30 минут сверяем
    #    bio каждого игрока напрямую через Telegram API (см. bio_bonus.py) ──
    from bio_bonus import bio_bonus_scan_loop
    asyncio.create_task(bio_bonus_scan_loop(bot))

    print("🤖 Бот запущен! БД: tgstellar.db")
    await dp.start_polling(bot)


# Намеренно нет блока `if __name__ == "__main__":` — точка входа теперь в main.py,
# который импортирует bot/dp/run_bot из этого файла. Если запустить mainhelp.py
# напрямую, бот не стартует — это сделано специально, чтобы не было двух точек входа.
