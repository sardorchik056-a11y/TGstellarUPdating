# ============================================================
#  donate.py  —  Донаты / Пакеты монет за Telegram Stars
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
#  ПАКЕТЫ МОНЕТ
# ============================================================

DONATE_PACKAGES = [
    {
        "key":    "donate_1",
        "coins":  100_000,
        "stars":  49,
        "emoji":  "🪙",
        "label":  "Стартовый",
        "label_en": "Starter",
        "tier":   1,
    },
    {
        "key":    "donate_2",
        "coins":  350_000,
        "stars":  89,
        "emoji":  "💰",
        "label":  "Базовый",
        "label_en": "Basic",
        "tier":   1,
    },
    {
        "key":    "donate_3",
        "coins":  1_000_000,
        "stars":  149,
        "emoji":  "💎",
        "label":  "Стандарт",
        "label_en": "Standard",
        "tier":   2,
    },
    {
        "key":    "donate_4",
        "coins":  5_000_000,
        "stars":  299,
        "emoji":  "💎",
        "label":  "Расширенный",
        "label_en": "Advanced",
        "tier":   2,
    },
    {
        "key":    "donate_5",
        "coins":  15_000_000,
        "stars":  599,
        "emoji":  "🔷",
        "label":  "Премиум",
        "label_en": "Premium",
        "tier":   3,
    },
    {
        "key":    "donate_6",
        "coins":  50_000_000,
        "stars":  1_299,
        "emoji":  "🔷",
        "label":  "Элитный",
        "label_en": "Elite",
        "tier":   3,
    },
    {
        "key":    "donate_7",
        "coins":  250_000_000,
        "stars":  2_499,
        "emoji":  "🏆",
        "label":  "Легенда",
        "label_en": "Legend",
        "tier":   4,
    },
    {
        "key":    "donate_8",
        "coins":  1_000_000_000,
        "stars":  5_000,
        "emoji":  "👑",
        "label":  "Король",
        "label_en": "King",
        "tier":   4,
    },
    {
        "key":    "donate_9",
        "coins":  5_000_000_000,
        "stars":  9_999,
        "emoji":  "👑",
        "label":  "Император",
        "label_en": "Emperor",
        "tier":   5,
    },
    {
        "key":    "donate_10",
        "coins":  25_000_000_000,
        "stars":  24_999,
        "emoji":  "🌌",
        "label":  "Абсолют",
        "label_en": "Absolute",
        "tier":   5,
    },
]

DONATE_BY_KEY = {p["key"]: p for p in DONATE_PACKAGES}

# ============================================================
#  УТИЛИТЫ
# ============================================================

_STAR_EMOJI_ID  = "5262643974912355126"   # ⭐ Telegram Stars
_COIN_EMOJI_ID  = "5199552030615558774"   # 💰 монеты
_BACK_EMOJI_ID  = "6039539366177541657"   # ← назад
_GIFT_EMOJI_ID  = "5222113468051629260"   # 🎁
_FIRE_EMOJI_ID  = "5438496463044752972"   # 🔥
_CROWN_EMOJI_ID = "5348570868752595928"   # 👑  (иконка звёзд Telegram)

_TIER_DIVIDERS = {
    1: None,
    2: ("💎", "Популярные пакеты", "Popular packages"),
    3: ("🔷", "Премиум пакеты", "Premium packages"),
    4: ("🏆", "VIP пакеты", "VIP packages"),
    5: ("🌌", "Легендарные пакеты", "Legendary packages"),
}


def _tg(eid: str, fb: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


def _star() -> str:
    return _tg(_STAR_EMOJI_ID, "⭐")


def _coin() -> str:
    return _tg(_COIN_EMOJI_ID, "💰")


def _L(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def _fmt_num(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n < 1000:
        return f"{sign}{int(n)}" if n == int(n) else f"{sign}{n:.1f}"
    for div, suffix in [
        (1_000_000_000_000, "трлн"),
        (1_000_000_000,     "млрд"),
        (1_000_000,         "м"),
        (1_000,             "к"),
    ]:
        if n >= div:
            val = int(n / div * 10) / 10
            return f"{sign}{int(val)}{suffix}" if val == int(val) else f"{sign}{val:.1f}{suffix}"
    return f"{sign}{int(n)}"


def _fmt_stars(s: int) -> str:
    if s >= 1000:
        val = s / 1000
        return f"{int(val)}к ⭐" if val == int(val) else f"{val:.1f}к ⭐"
    return f"{s} ⭐"


# ============================================================
#  ТЕКСТ — ГЛАВНЫЙ ЭКРАН ДОНАТОВ
# ============================================================

def donate_main_text(lang: str = "ru") -> str:
    if lang == "en":
        header = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>DONATE — Coin Packages</b>\n"
            f"Support the project and get coins instantly!\n"
            f"{_tg(_FIRE_EMOJI_ID, '🔥')} <b>Coins are credited immediately after payment.</b>"
            f"</blockquote>\n"
        )
        packages_title = "📦 Available packages:"
        coin_label = "coins"
    else:
        header = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>ДОНАТЫ — Пакеты монет</b>\n"
            f"Поддержи проект и получи монеты мгновенно!\n"
            f"{_tg(_FIRE_EMOJI_ID, '🔥')} <b>Монеты зачисляются сразу после оплаты.</b>"
            f"</blockquote>\n"
        )
        packages_title = "📦 Доступные пакеты:"
        coin_label = "монет"

    lines = [header]

    if lang == "en":
        lines.append(
            f"\n<blockquote>"
            f"{_star()} <b>Payment via Telegram Stars.</b>\n"
            f"<i>Select a package below to proceed.</i>"
            f"</blockquote>"
        )
    else:
        lines.append(
            f"\n<blockquote>"
            f"{_star()} <b>Оплата через Telegram Stars.</b>\n"
            f"<i>Выбери пакет ниже для оплаты.</i>"
            f"</blockquote>"
        )

    return "".join(lines)


# ============================================================
#  ТЕКСТ — ДЕТАЛЬНЫЙ ЭКРАН ПАКЕТА
# ============================================================

def donate_package_text(pkg_key: str, lang: str = "ru") -> str:
    p = DONATE_BY_KEY.get(pkg_key)
    if not p:
        return "❌ Пакет не найден." if lang == "ru" else "❌ Package not found."

    name       = p["label_en"] if lang == "en" else p["label"]
    coins_str  = _fmt_num(p["coins"])
    stars_str  = _fmt_stars(p["stars"])
    coin_label = "coins" if lang == "en" else "монет"

    # Подсчёт "выгоды" (монет за 1 звезду)
    per_star = int(p["coins"] / p["stars"])
    per_star_str = _fmt_num(per_star)

    if lang == "en":
        return (
            f"<blockquote>"
            f"{p['emoji']} <b>{name} Package</b>\n"
            f"{_coin()} <b>Coins: {coins_str}</b>\n"
            f"{_star()} <b>Price: {stars_str}</b>\n"
            f"📈 <b>Value: {per_star_str} coins / ⭐</b>"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f"✅ <b>Coins are credited instantly after payment.</b>\n"
            f"⚡ <b>No expiry — yours forever.</b>"
            f"</blockquote>"
        )
    else:
        return (
            f"<blockquote>"
            f"{p['emoji']} <b>Пакет «{name}»</b>\n"
            f"{_coin()} <b>Монеты: {coins_str}</b>\n"
            f"{_star()} <b>Цена: {stars_str}</b>\n"
            f"📈 <b>Выгода: {per_star_str} монет / ⭐</b>"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f"✅ <b>Монеты зачисляются мгновенно после оплаты.</b>\n"
            f"⚡ <b>Срок действия не ограничен — твои навсегда.</b>"
            f"</blockquote>"
        )


# ============================================================
#  КЛАВИАТУРЫ
# ============================================================

def donate_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Список всех пакетов — кнопка на каждый."""
    builder = InlineKeyboardBuilder()
    for p in DONATE_PACKAGES:
        name      = p["label_en"] if lang == "en" else p["label"]
        coins_str = _fmt_num(p["coins"])
        stars_str = _fmt_stars(p["stars"])
        builder.row(InlineKeyboardButton(
            text=f"{name} — {coins_str} | {stars_str}",
            callback_data=f"donate_pkg_{p['key']}",
            icon_custom_emoji_id=_STAR_EMOJI_ID,
        ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_CROWN_EMOJI_ID,
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "← Назад в профиль", "← Back to profile"),
        callback_data="profile",
        icon_custom_emoji_id=_BACK_EMOJI_ID,
    ))
    return builder.as_markup()


def donate_package_keyboard(pkg_key: str, invoice_url: str = None, lang: str = "ru") -> InlineKeyboardMarkup:
    """Экран конкретного пакета — кнопка купить + назад."""
    builder = InlineKeyboardBuilder()
    p = DONATE_BY_KEY.get(pkg_key)
    stars_str = _fmt_stars(p["stars"]) if p else "?"
    buy_label = f"{_L(lang, 'Купить', 'Buy')} {stars_str}"

    if invoice_url:
        builder.row(InlineKeyboardButton(
            text=buy_label,
            url=invoice_url,
            icon_custom_emoji_id=_STAR_EMOJI_ID,
            style="success",
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=buy_label,
            callback_data=f"donate_buy_{pkg_key}",
            icon_custom_emoji_id=_STAR_EMOJI_ID,
        ))

    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_CROWN_EMOJI_ID,
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "← Все пакеты", "← All packages"),
        callback_data="donate_main",
        icon_custom_emoji_id=_BACK_EMOJI_ID,
    ))
    return builder.as_markup()


# ============================================================
#  ЛОГИКА — ЗАЧИСЛЕНИЕ МОНЕТ
# ============================================================

def apply_donate(data: dict, pkg_key: str) -> tuple[bool, str, int]:
    """
    Зачислить монеты за донат после успешной оплаты Stars.
    Вызывать из хендлера successful_payment.

    Возвращает (ok, msg, coins_added).
    Модифицирует data на месте — сохранение в БД на стороне вызывающего.
    """
    p = DONATE_BY_KEY.get(pkg_key)
    if not p:
        return False, "❌ Пакет не найден.", 0

    coins = p["coins"]
    data["balance"] = data.get("balance", 0) + coins
    data["total_donated_stars"] = data.get("total_donated_stars", 0) + p["stars"]
    data["total_donated_coins"] = data.get("total_donated_coins", 0) + coins

    lang = data.get("lang", "ru")
    name = p["label_en"] if lang == "en" else p["label"]
    coins_str = _fmt_num(coins)
    bal_str   = _fmt_num(data["balance"])

    if lang == "en":
        msg = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>Thank you for your support!</b>\n"
            f"{p['emoji']} <b>Package «{name}» activated!</b>\n"
            f"{_coin()} <b>+{coins_str} coins</b>\n"
            f"{_coin()} <b>Balance: {bal_str}</b>"
            f"</blockquote>"
        )
    else:
        msg = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>Спасибо за поддержку!</b>\n"
            f"{p['emoji']} <b>Пакет «{name}» активирован!</b>\n"
            f"{_coin()} <b>+{coins_str} монет</b>\n"
            f"{_coin()} <b>Баланс: {bal_str}</b>"
            f"</blockquote>"
        )
    return True, msg, coins


# ============================================================
#  КАК ПОДКЛЮЧИТЬ В БОТЕ (инструкция в комментарии)
# ============================================================
#
#  1. В профиле добавить кнопку:
#       InlineKeyboardButton(text="💝 Донат", callback_data="donate_main")
#
#  2. Хендлер callback "donate_main":
#       await callback.message.edit_text(
#           donate_main_text(lang),
#           reply_markup=donate_main_keyboard(lang),
#       )
#
#  3. Хендлер callback "donate_pkg_{key}":
#       pkg_key = callback.data.removeprefix("donate_pkg_")
#       invoice_url = await bot.create_invoice_link(
#           title=..., description=..., payload=pkg_key,
#           currency="XTR", prices=[LabeledPrice(label="⭐", amount=pkg["stars"])]
#       )
#       await callback.message.edit_text(
#           donate_package_text(pkg_key, lang),
#           reply_markup=donate_package_keyboard(pkg_key, invoice_url, lang),
#       )
#
#  4. Хендлер pre_checkout_query:
#       await bot.answer_pre_checkout_query(query.id, ok=True)
#
#  5. Хендлер successful_payment:
#       pkg_key = event.successful_payment.invoice_payload
#       ok, msg, coins = apply_donate(user_data, pkg_key)
#       # сохранить user_data в БД
#       await bot.send_message(user_id, msg)
