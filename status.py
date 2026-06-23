# ============================================================
#  status.py  —  Система статусов TGStellar
#  Статусы: Standart / VIP / Premium
#  Покупка за Telegram Stars, срок действия 30 дней
# ============================================================

import time
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ────────────────────────────────────────────────────────────
#  КОНСТАНТЫ
# ────────────────────────────────────────────────────────────

STATUS_DURATION = 30 * 24 * 3600   # 30 дней в секундах

# Стоимость в Telegram Stars
VIP_COST_STARS        = 89
PREMIUM_COST_STARS    = 149
UPGRADE_COST_STARS    = 59   # улучшение VIP → Premium

# Ключи ядов-бонусов (берём из shop.py: poison_1 = Гадюка, poison_2 = Кобра)
VIP_BONUS_POISON_KEY     = "poison_1"   # Яд Гадюки
PREMIUM_BONUS_POISON_KEY = "poison_2"   # Яд Кобры

# ────────────────────────────────────────────────────────────
#  EMOJI IDS
# ────────────────────────────────────────────────────────────

_E = {
    "vip":        "5325547803936572038",   # корона VIP
    "premium":    "5427168083074628963",   # звезда Premium
    "standart":   "5397916757333654639",   # базовый Standart
    "cur_status": "5201691993775818138",   # текущий статус (в профиле)
    "pay_btn":    "5262643974912355126",   # эмодзи в кнопке оплаты
    "mine":       "5197371802136892976",   # шахта
    "hunt":       "5424972470023104089",   # охота
    "pets":       "5337047059180566409",   # питомцы
    "crit":       "5256047523620995497",   # крит
    "luck":       "5442939099906325301",   # удача
    "poison":     "5456584142286250164",   # яд
    "star":       "5348570868752595928",   # звезда Telegram
    "timer":      "5382194935057372936",   # таймер
    "ok":         "5206607081334906820",   # галочка
    "warn":       "5240241223632954241",   # предупреждение
    "back":       "6039539366177541657",   # назад
    "coin":       "5199552030615558774",   # монета
    "boost":      "5438571934210082705",   # молния
    "calendar":   "5440621591387980068",   # таймер/календарь
}


def _pe(key: str, fallback: str = "•") -> str:
    return f'<tg-emoji emoji-id="{_E[key]}">{fallback}</tg-emoji>'


def _btn(emoji_key: str, label: str, cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=label,
        callback_data=cb,
        icon_custom_emoji_id=_E[emoji_key]
    )


def _back_btn(cb: str, label: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=label,
        callback_data=cb,
        icon_custom_emoji_id=_E["back"]
    )


def _L(lang: str, ru: str, en: str) -> str:
    """Inline двуязычная строка без обращения к lang.py."""
    return en if lang == "en" else ru


# ────────────────────────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ────────────────────────────────────────────────────────────

def _now_ts() -> int:
    return int(time.time())


def _fmt_time_left(seconds: int, lang: str = "ru") -> str:
    if seconds <= 0:
        return "expired" if lang == "en" else "истёк"
    days    = seconds // 86400
    hours   = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if lang == "en":
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    if days > 0:
        return f"{days}д {hours}ч"
    if hours > 0:
        return f"{hours}ч {minutes}м"
    return f"{minutes}м"


def get_active_status(data: dict) -> str:
    """Возвращает текущий активный статус: 'standart', 'vip', 'premium'."""
    now = _now_ts()
    status_data = data.get("status_subscription")
    if not status_data:
        return "standart"
    if status_data.get("ends_at", 0) <= now:
        return "standart"
    return status_data.get("tier", "standart")


def get_status_ends_at(data: dict) -> int | None:
    """Возвращает timestamp окончания подписки или None."""
    sd = data.get("status_subscription")
    if not sd:
        return None
    if sd.get("ends_at", 0) <= _now_ts():
        return None
    return sd.get("ends_at")


def get_status_multiplier(data: dict) -> float:
    """Множитель добычи (шахта / охота / питомцы) для текущего статуса."""
    s = get_active_status(data)
    if s == "premium":
        return 1.6
    if s == "vip":
        return 1.3
    return 1.0


def get_crit_chance_bonus(data: dict) -> int:
    """Дополнительный шанс критического урона (%) от статуса."""
    s = get_active_status(data)
    if s == "premium":
        return 25
    if s == "vip":
        return 15
    return 0


def get_luck_bonus(data: dict) -> bool:
    """Есть ли бонус к удаче при покупке/открытии кейсов."""
    return get_active_status(data) in ("vip", "premium")


def activate_status(data: dict, tier: str, lang: str = "ru") -> tuple[bool, str]:
    """
    Активировать / продлить / улучшить подписку.
    tier: 'vip' или 'premium'
    - Тот же тир: продление (adds STATUS_DURATION к текущему ends_at)
    - Другой тир (upgrade/downgrade): заменяет, срок с нуля
    Возвращает (ok, message_text)
    """
    now = _now_ts()
    sd  = data.get("status_subscription")
    current_tier    = sd.get("tier") if sd else None
    current_ends_at = sd.get("ends_at", 0) if sd else 0

    if current_tier == tier and current_ends_at > now:
        # Продление: добавляем 30 дней к оставшемуся сроку
        ends_at = current_ends_at + STATUS_DURATION
        action_label = _L(lang, "продлён", "renewed")
    else:
        # Новая активация или смена тира
        ends_at = now + STATUS_DURATION
        action_label = _L(lang, "активирован", "activated")

    data["status_subscription"] = {
        "tier":      tier,
        "ends_at":   ends_at,
        "bought_at": now,
    }

    # Выдаём бонусный яд в enh_inventory
    import uuid
    from shop import ENH_POOL_BY_KEY
    poison_key = VIP_BONUS_POISON_KEY if tier == "vip" else PREMIUM_BONUS_POISON_KEY
    poison     = ENH_POOL_BY_KEY.get(poison_key)
    poison_msg = ""
    if poison:
        inv = data.setdefault("enh_inventory", [])
        from shop import MAX_ENH_INVENTORY
        if len(inv) < MAX_ENH_INVENTORY:
            new_item = dict(poison)
            new_item["instance_id"] = str(uuid.uuid4())[:8]
            inv.append(new_item)
            poison_name = _L(lang, "Яд Гадюки", "Viper Poison") if poison_key == VIP_BONUS_POISON_KEY else _L(lang, "Яд Кобры", "Cobra Poison")
            poison_msg = f'\n{_pe("poison", "☠️")} <b>{_L(lang, f"Бонусный {poison_name} добавлен в инвентарь!", f"Bonus {poison_name} added to your inventory!")}</b>'
        else:
            poison_msg = f'\n{_pe("warn", "⚠️")} <b>{_L(lang, "Инвентарь усилителей полон — яд не выдан.", "Booster inventory is full — poison was not given.")}</b>'

    label = "VIP" if tier == "vip" else "Premium"
    return True, f'{_pe("ok", "✅")} <b>{_L(lang, f"Статус {label} {action_label} на 30 дней!", f"{label} status {action_label} for 30 days!")}</b>{poison_msg}'


# ────────────────────────────────────────────────────────────
#  ТЕКСТЫ
# ────────────────────────────────────────────────────────────

def status_main_text(data: dict, lang: str = "ru") -> str:
    active  = get_active_status(data)
    ends_at = get_status_ends_at(data)

    # Шапка с текущим статусом
    if active == "premium":
        current_line = (
            f'{_pe("cur_status", "✅")} <b>{_L(lang, "Текущий статус: Premium", "Current status: Premium")}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {_fmt_time_left(ends_at - _now_ts(), lang)}</b>'
        )
    elif active == "vip":
        current_line = (
            f'{_pe("cur_status", "✅")} <b>{_L(lang, "Текущий статус: VIP", "Current status: VIP")}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {_fmt_time_left(ends_at - _now_ts(), lang)}</b>'
        )
    else:
        current_line = (
            f'{_pe("cur_status", "✅")} <b>{_L(lang, "Текущий статус: Standart", "Current status: Standart")}</b>\n'
            f'<b>{_L(lang, "Подпишись, чтобы получить привилегии", "Subscribe to unlock privileges")}</b>'
        )

    return (
        f'<blockquote>{_pe("vip", "👑")} <b>{_L(lang, "СТАТУСЫ TGStellar", "TGStellar STATUSES")}</b>\n\n'
        f'{current_line}</blockquote>\n\n'

        f'<blockquote>'
        f'{_pe("standart", "🎟")} <b>Standart</b> — {_L(lang, "базовый статус", "basic status")}\n'
        f'<b>{_L(lang, "Доступен всем игрокам бесплатно", "Available to all players for free")}</b>\n'
        f'<b>• {_L(lang, "Без бонусов к добыче", "No mining bonuses")}</b>\n'
        f'<b>• {_L(lang, "Без бонуса к критическому урону", "No critical damage bonus")}</b>\n'
        f'<b>• {_L(lang, "Без удачи в кейсах", "No luck bonus in cases")}</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'{_pe("vip", "👑")} <b>VIP</b> — {VIP_COST_STARS} {_pe("star", "⭐")} / {_L(lang, "30 дней", "30 days")}\n'
        f'{_pe("mine", "⛏")} <b>{_L(lang, "+1.3× ко всем видам добычи", "+1.3× to all types of mining/farming")}</b>\n'
        f'{_pe("crit", "⚡")} <b>{_L(lang, "Шанс крита", "Crit chance")}: +15%</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Повышенная удача в кейсах", "Increased luck in cases")}</b>\n'
        f'{_pe("poison", "☠️")} <b>{_L(lang, "Бонус: Яд Гадюки при активации", "Bonus: Viper Poison on activation")}</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'{_pe("premium", "⭐")} <b>Premium</b> — {PREMIUM_COST_STARS} {_pe("star", "⭐")} / {_L(lang, "30 дней", "30 days")}\n'
        f'{_pe("mine", "⛏")} <b>{_L(lang, "+1.6× ко всем видам добычи", "+1.6× to all types of mining/farming")}</b>\n'
        f'{_pe("crit", "⚡")} <b>{_L(lang, "Шанс крита", "Crit chance")}: +25%</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Максимальная удача в кейсах", "Maximum luck in cases")}</b>\n'
        f'{_pe("poison", "☠️")} <b>{_L(lang, "Бонус: Яд Кобры при активации", "Bonus: Cobra Poison on activation")}</b>'
        f'</blockquote>'
    )


def status_main_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    active = get_active_status(data)
    builder = InlineKeyboardBuilder()
    builder.row(_btn("vip",     _L(lang, "VIP — подробнее", "VIP — details"),         "status_vip_info"))
    builder.row(_btn("premium", _L(lang, "Premium — подробнее", "Premium — details"), "status_premium_info"))
    builder.row(_back_btn("back_to_menu", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def status_vip_text(data: dict, lang: str = "ru") -> str:
    active = get_active_status(data)
    active_line = ""
    if active == "vip":
        ends_at = get_status_ends_at(data)
        active_line = (
            f'\n\n<blockquote>{_pe("ok", "✅")} <b>{_L(lang, "VIP активен!", "VIP is active!")}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {_fmt_time_left(ends_at - _now_ts(), lang)}</b>\n'
            f'<b>{_L(lang, "Покупка продлит срок ещё на 30 дней", "Purchase will extend it by another 30 days")}</b></blockquote>'
        )
    elif active == "premium":
        active_line = (
            f'\n\n<blockquote>{_pe("warn", "⚠️")} <b>{_L(lang, "У тебя активен Premium — VIP недоступен.", "You have an active Premium — VIP is unavailable.")}</b>\n'
            f'<b>{_L(lang, "Более высокий статус нельзя заменить на низкий.", "A higher status cannot be downgraded to a lower one.")}</b></blockquote>'
        )

    return (
        f'<blockquote>'
        f'{_pe("vip", "👑")} <b>{_L(lang, "Статус VIP", "VIP Status")}</b>\n\n'
        f'{_pe("calendar", "📅")} <b>{_L(lang, "Срок: 30 дней", "Duration: 30 days")}</b>\n'
        f'{_pe("star", "⭐")} <b>{_L(lang, "Стоимость", "Cost")}: {VIP_COST_STARS} Stars</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'<b>{_L(lang, "Преимущества VIP:", "VIP benefits:")}</b>\n\n'
        f'{_pe("mine", "⛏")} <b>{_L(lang, "×1.3 к добыче руды в шахте", "×1.3 to ore mining in the mine")}</b>\n'
        f'{_pe("hunt", "⚔️")} <b>{_L(lang, "×1.3 к урону в охоте", "×1.3 to hunting damage")}</b>\n'
        f'{_pe("pets", "🐾")} <b>{_L(lang, "×1.3 к доходу питомцев", "×1.3 to pets income")}</b>\n\n'
        f'{_pe("crit", "⚡")} <b>{_L(lang, "Шанс критического удара +15%", "Critical hit chance +15%")}</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Повышенная удача при открытии кейсов", "Increased luck when opening cases")}</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Удача при покупке в магазине", "Luck bonus on shop purchases")}</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'{_pe("poison", "☠️")} <b>{_L(lang, "Бонус при активации:", "Activation bonus:")}</b>\n'
        f'<b>{_L(lang, "Яд Гадюки — 100 000 урона за 30 мин", "Viper Poison — 100,000 damage over 30 min")}</b>\n'
        f'<b>{_L(lang, "(добавляется в инвентарь сразу)", "(added to inventory immediately)")}</b>'
        f'</blockquote>'
        f'{active_line}'
    )


def status_vip_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    active = get_active_status(data)
    builder = InlineKeyboardBuilder()
    if active == "premium":
        # VIP заблокирован — кнопка неактивна
        builder.row(InlineKeyboardButton(
            text=_L(lang, "🚫 Недоступно (активен Premium)", "🚫 Unavailable (Premium active)"),
            callback_data="noop",
        ))
    elif active == "vip":
        # Продление VIP + улучшение до Premium
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Продлить VIP — {VIP_COST_STARS} Stars", f"Renew VIP — {VIP_COST_STARS} Stars"),
            callback_data="status_buy_vip",
            icon_custom_emoji_id=_E["vip"]
        ))
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Улучшить до Premium — {UPGRADE_COST_STARS} ⭐", f"Upgrade to Premium — {UPGRADE_COST_STARS} ⭐"),
            callback_data="status_upgrade_premium",
            icon_custom_emoji_id=_E["premium"]
        ))
    else:
        # Standart — обычная покупка
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Купить VIP — {VIP_COST_STARS} Stars", f"Buy VIP — {VIP_COST_STARS} Stars"),
            callback_data="status_buy_vip",
            icon_custom_emoji_id=_E["vip"]
        ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My Stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_E["star"]
    ))
    builder.row(_back_btn("status", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def status_premium_text(data: dict, lang: str = "ru") -> str:
    active = get_active_status(data)
    active_line = ""
    if active == "premium":
        ends_at = get_status_ends_at(data)
        active_line = (
            f'\n\n<blockquote>{_pe("ok", "✅")} <b>{_L(lang, "Premium активен!", "Premium is active!")}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {_fmt_time_left(ends_at - _now_ts(), lang)}</b>\n'
            f'<b>{_L(lang, "Покупка продлит срок ещё на 30 дней", "Purchase will extend it by another 30 days")}</b></blockquote>'
        )
    elif active == "vip":
        active_line = (
            f'\n\n<blockquote>{_pe("ok", "✅")} <b>{_L(lang, "У тебя активен VIP.", "You have an active VIP.")}</b>\n'
            f'<b>{_L(lang, f"Можешь улучшить до Premium за {UPGRADE_COST_STARS} ⭐", f"You can upgrade to Premium for {UPGRADE_COST_STARS} ⭐")}</b></blockquote>'
        )

    return (
        f'<blockquote>'
        f'{_pe("premium", "⭐")} <b>{_L(lang, "Статус Premium", "Premium Status")}</b>\n\n'
        f'{_pe("calendar", "📅")} <b>{_L(lang, "Срок: 30 дней", "Duration: 30 days")}</b>\n'
        f'{_pe("star", "⭐")} <b>{_L(lang, "Стоимость", "Cost")}: {PREMIUM_COST_STARS} Stars</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'<b>{_L(lang, "Преимущества Premium:", "Premium benefits:")}</b>\n\n'
        f'{_pe("mine", "⛏")} <b>{_L(lang, "×1.6 к добыче руды в шахте", "×1.6 to ore mining in the mine")}</b>\n'
        f'{_pe("hunt", "⚔️")} <b>{_L(lang, "×1.6 к урону в охоте", "×1.6 to hunting damage")}</b>\n'
        f'{_pe("pets", "🐾")} <b>{_L(lang, "×1.6 к доходу питомцев", "×1.6 to pets income")}</b>\n\n'
        f'{_pe("crit", "⚡")} <b>{_L(lang, "Шанс критического удара +25%", "Critical hit chance +25%")}</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Максимальная удача в кейсах", "Maximum luck in cases")}</b>\n'
        f'{_pe("luck", "🍀")} <b>{_L(lang, "Максимальная удача при покупках", "Maximum luck on purchases")}</b>'
        f'</blockquote>\n\n'

        f'<blockquote>'
        f'{_pe("poison", "☠️")} <b>{_L(lang, "Бонус при активации:", "Activation bonus:")}</b>\n'
        f'<b>{_L(lang, "Яд Кобры — 150 000 урона за 30 мин", "Cobra Poison — 150,000 damage over 30 min")}</b>\n'
        f'<b>{_L(lang, "(добавляется в инвентарь сразу)", "(added to inventory immediately)")}</b>'
        f'</blockquote>'
        f'{active_line}'
    )


def status_premium_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    active = get_active_status(data)
    builder = InlineKeyboardBuilder()
    if active == "vip":
        # Улучшение VIP → Premium за 59 звёзд
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Улучшить до Premium — {UPGRADE_COST_STARS} ⭐", f"Upgrade to Premium — {UPGRADE_COST_STARS} ⭐"),
            callback_data="status_upgrade_premium",
            icon_custom_emoji_id=_E["premium"]
        ))
    elif active == "premium":
        # Продление Premium
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Продлить Premium — {PREMIUM_COST_STARS} Stars", f"Renew Premium — {PREMIUM_COST_STARS} Stars"),
            callback_data="status_buy_premium",
            icon_custom_emoji_id=_E["premium"]
        ))
    else:
        # Standart — обычная покупка
        builder.row(InlineKeyboardButton(
            text=_L(lang, f"Купить Premium — {PREMIUM_COST_STARS} Stars", f"Buy Premium — {PREMIUM_COST_STARS} Stars"),
            callback_data="status_buy_premium",
            icon_custom_emoji_id=_E["premium"]
        ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My Stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_E["star"]
    ))
    builder.row(_back_btn("status", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def status_vip_keyboard_invoice(invoice_url: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_L(lang, f"Купить VIP — {VIP_COST_STARS} ⭐", f"Buy VIP — {VIP_COST_STARS} ⭐"),
        url=invoice_url,
        icon_custom_emoji_id=_E["pay_btn"],
        style="success"
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My Stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_E["star"]
    ))
    builder.row(_back_btn("status_vip_info", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def status_premium_keyboard_invoice(invoice_url: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_L(lang, f"Купить Premium — {PREMIUM_COST_STARS} ⭐", f"Buy Premium — {PREMIUM_COST_STARS} ⭐"),
        url=invoice_url,
        icon_custom_emoji_id=_E["pay_btn"],
        style="success"
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My Stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_E["star"]
    ))
    builder.row(_back_btn("status_premium_info", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def status_upgrade_keyboard_invoice(invoice_url: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для апгрейда VIP → Premium за 59 звёзд."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_L(lang, f"Улучшить до Premium — {UPGRADE_COST_STARS} ⭐", f"Upgrade to Premium — {UPGRADE_COST_STARS} ⭐"),
        url=invoice_url,
        icon_custom_emoji_id=_E["pay_btn"],
        style="success"
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My Stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_E["star"]
    ))
    builder.row(_back_btn("status_premium_info", _L(lang, "Назад", "Back")))
    return builder.as_markup()
