# ============================================================
#  donate.py  —  Донаты / Пакеты Самосветов за Telegram Stars
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
#  ПАКЕТЫ САМОСВЕТОВ  (курс фиксированный: 1 ⭐ = 1 самосвет)
# ============================================================

DONATE_PACKAGES = [
    {
        "key":       "donate_1",
        "samosvety": 49,
        "stars":     49,
        "emoji":     "💠",
        "label":     "Стартовый",
        "label_en":  "Starter",
        "tier":      1,
    },
    {
        "key":       "donate_2",
        "samosvety": 100,
        "stars":     100,
        "emoji":     "💠",
        "label":     "Базовый",
        "label_en":  "Basic",
        "tier":      1,
    },
    {
        "key":       "donate_3",
        "samosvety": 250,
        "stars":     250,
        "emoji":     "🔷",
        "label":     "Стандарт",
        "label_en":  "Standard",
        "tier":      2,
    },
    {
        "key":       "donate_4",
        "samosvety": 500,
        "stars":     500,
        "emoji":     "🔷",
        "label":     "Расширенный",
        "label_en":  "Advanced",
        "tier":      2,
    },
    {
        "key":       "donate_5",
        "samosvety": 1_000,
        "stars":     1_000,
        "emoji":     "💎",
        "label":     "Премиум",
        "label_en":  "Premium",
        "tier":      3,
    },
    {
        "key":       "donate_6",
        "samosvety": 2_500,
        "stars":     2_500,
        "emoji":     "💎",
        "label":     "Элитный",
        "label_en":  "Elite",
        "tier":      3,
    },
    {
        "key":       "donate_7",
        "samosvety": 5_000,
        "stars":     5_000,
        "emoji":     "🏆",
        "label":     "Легенда",
        "label_en":  "Legend",
        "tier":      4,
    },
    {
        "key":       "donate_8",
        "samosvety": 10_000,
        "stars":     10_000,
        "emoji":     "🌌",
        "label":     "Абсолют",
        "label_en":  "Absolute",
        "tier":      5,
    },
]

DONATE_BY_KEY = {p["key"]: p for p in DONATE_PACKAGES}

# Ограничения на пакет (для валидации, если понадобится кастомная сумма)
DONATE_MIN_SAMOSVETY = 49
DONATE_MAX_SAMOSVETY = 10_000

# Курс Telegram Stars -> USD (приблизительный, официальный курс Telegram
# варьируется по региону; поправь при необходимости под актуальный курс)
STAR_TO_USD = 0.013

# ============================================================
#  УТИЛИТЫ
# ============================================================

_STAR_EMOJI_ID      = "5262643974912355126"   # ⭐ Telegram Stars
_SAMOSVET_EMOJI_ID  = "5465501598199342448"   # 💠 Самосвет (донатная валюта)
_BACK_EMOJI_ID      = "6039539366177541657"   # ← назад
_GIFT_EMOJI_ID      = "5222113468051629260"   # 🎁
_FIRE_EMOJI_ID      = "5438496463044752972"   # 🔥
_CROWN_EMOJI_ID     = "5348570868752595928"   # 👑  (иконка звёзд Telegram)

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


def _samosvet() -> str:
    return _tg(_SAMOSVET_EMOJI_ID, "💠")


def _L(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def _fmt_num(n) -> str:
    """
    Сокращает число до буквенного вида — та же короткая шкала, что в
    database.py -> format_amount() / miner.py / achieves.py, единый стиль
    чисел по всему проекту:
      999          -> "999"
      1500         -> "1.5K"
      100000       -> "100K"
      2300000      -> "2.3M"
      1500000000   -> "1.5B"
      10**12       -> "1T"
      10**15       -> "1Qa"  (quadrillion)
      10**18       -> "1Qi"  (quintillion)
      10**21       -> "1Sx"  (sextillion)
      10**24       -> "1Sp"  (septillion)
      10**27       -> "1Oc"  (octillion)
      10**30       -> "1No"  (nonillion)
      10**33       -> "1Dc"  (decillion)
    Если число ещё больше — формат не ломается: продолжаем Dc2, Dc3, ...
    Дробная часть показывается только если она не нулевая (1.5K, но не 1.0K).
    """
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n < 1000:
        return f"{sign}{int(n)}" if n == int(n) else f"{sign}{n:.1f}"

    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]
    idx = 0
    val = n
    while val >= 1000:
        val /= 1000
        idx += 1

    val = int(val * 10) / 10  # округление вниз до 1 знака после запятой

    if idx < len(suffixes):
        suffix = suffixes[idx]
    else:
        suffix = f"Dc{idx - len(suffixes) + 2}"

    if val == int(val):
        return f"{sign}{int(val)}{suffix}"
    return f"{sign}{val:.1f}{suffix}"


def _fmt_stars(s: int) -> str:
    """Форматирует количество Stars той же буквенной шкалой, что и _fmt_num,
    чтобы не было разнобоя между «15.0к ⭐» и «1.5M» в одном файле."""
    return f"{_fmt_num(s)} ⭐"


def _fmt_usd(stars: int) -> str:
    """Приблизительная сумма в USD по курсу STAR_TO_USD."""
    return f"${stars * STAR_TO_USD:.2f}"


# ============================================================
#  ТЕКСТ — ГЛАВНЫЙ ЭКРАН ДОНАТОВ
# ============================================================

def donate_main_text(lang: str = "ru") -> str:
    if lang == "en":
        header = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>DONATE — Samosvet Packages</b>\n"
            f"Support the project and get Samosvets instantly!\n"
            f"{_tg(_FIRE_EMOJI_ID, '🔥')} <b>Samosvets are credited immediately after payment.</b>"
            f"</blockquote>\n"
        )
    else:
        header = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>ДОНАТЫ — Пакеты Самосветов</b>\n"
            f"Поддержи проект и получи Самосветы мгновенно!\n"
            f"{_tg(_FIRE_EMOJI_ID, '🔥')} <b>Самосветы зачисляются сразу после оплаты.</b>"
            f"</blockquote>\n"
        )

    lines = [header]

    if lang == "en":
        lines.append(
            f"\n<blockquote>"
            f"{_star()} <b>Payment via Telegram Stars.</b>\n"
            f"{_samosvet()} <b>Rate: 1 ⭐ = 1 Samosvet.</b>\n"
            f"<i>Select a package below to proceed.</i>"
            f"</blockquote>"
        )
    else:
        lines.append(
            f"\n<blockquote>"
            f"{_star()} <b>Оплата через Telegram Stars.</b>\n"
            f"{_samosvet()} <b>Курс: 1 ⭐ = 1 Самосвет.</b>\n"
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

    name          = p["label_en"] if lang == "en" else p["label"]
    samosvety_str = _fmt_num(p["samosvety"])
    stars_str     = _fmt_stars(p["stars"])

    if lang == "en":
        return (
            f"<blockquote>"
            f'<tg-emoji emoji-id="5400362079783770689">🌟</tg-emoji> <b>{name} Package</b>\n'
            f"{_samosvet()} <b>Samosvets: {samosvety_str}</b>\n"
            f"{_star()} <b>Price: {stars_str}</b>\n"
            f'<tg-emoji emoji-id="5429651785352501917">🌟</tg-emoji> <b>Rate: 1 ⭐ = 1 Samosvet</b>'
            f"</blockquote>\n"
            f"\n<blockquote>"
            f'<tg-emoji emoji-id="5206607081334906820">🌟</tg-emoji> <b>Samosvets are credited instantly after payment.</b>\n'
            f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> <b>No expiry — yours forever.</b>'
            f"</blockquote>"
        )
    else:
        return (
            f"<blockquote>"
            f'<tg-emoji emoji-id="5400362079783770689">🌟</tg-emoji> <b>Пакет «{name}»</b>\n'
            f"{_samosvet()} <b>Самосветы: {samosvety_str}</b>\n"
            f"{_star()} <b>Цена: {stars_str}</b>\n"
            f'<tg-emoji emoji-id="5429651785352501917">🌟</tg-emoji> <b>Курс: 1 ⭐ = 1 Самосвет</b>'
            f"</blockquote>\n"
            f"\n<blockquote>"
            f'<tg-emoji emoji-id="5206607081334906820">🌟</tg-emoji> <b>Самосветы зачисляются мгновенно после оплаты.</b>\n'
            f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> <b>Срок действия не ограничен — твои навсегда.</b>'
            f"</blockquote>"
        )


# ============================================================
#  КЛАВИАТУРЫ
# ============================================================

def donate_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Список всех пакетов — кнопка на каждый."""
    builder = InlineKeyboardBuilder()
    for p in DONATE_PACKAGES:
        samosvety_str = _fmt_num(p["samosvety"])
        stars_str     = _fmt_stars(p["stars"])
        usd_str       = _fmt_usd(p["stars"])
        builder.row(InlineKeyboardButton(
            text=f"{samosvety_str} | {stars_str} | {usd_str}",
            callback_data=f"donate_pkg_{p['key']}",
            icon_custom_emoji_id=_SAMOSVET_EMOJI_ID,
        ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My stars"),
        url="tg://stars/",
        icon_custom_emoji_id=_CROWN_EMOJI_ID,
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Назад в профиль", "Back to profile"),
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
        text=_L(lang, " Все пакеты", " All packages"),
        callback_data="donate_main",
        icon_custom_emoji_id=_BACK_EMOJI_ID,
    ))
    return builder.as_markup()


# ============================================================
#  ЛОГИКА — ЗАЧИСЛЕНИЕ САМОСВЕТОВ
# ============================================================

def apply_donate(data: dict, pkg_key: str) -> tuple[bool, str, int]:
    """
    Зачислить Самосветы за донат после успешной оплаты Stars.
    Вызывать из хендлера successful_payment.

    Самосветы — донатная валюта, отдельная от игровых монет (balance).
    Хранится в data["samosvety"].

    Возвращает (ok, msg, samosvety_added).
    Модифицирует data на месте — сохранение в БД на стороне вызывающего.
    """
    p = DONATE_BY_KEY.get(pkg_key)
    if not p:
        return False, "❌ Пакет не найден.", 0

    samosvety = p["samosvety"]
    data["samosvety"] = data.get("samosvety", 0) + samosvety
    data["total_donated_stars"] = data.get("total_donated_stars", 0) + p["stars"]
    data["total_donated_samosvety"] = data.get("total_donated_samosvety", 0) + samosvety
    data["donate_purchases"] = data.get("donate_purchases", 0) + 1
    data.setdefault("donate_purchased_keys", []).append(pkg_key)

    lang = data.get("lang", "ru")
    name = p["label_en"] if lang == "en" else p["label"]
    samosvety_str = _fmt_num(samosvety)
    bal_str       = _fmt_num(data["samosvety"])

    if lang == "en":
        msg = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>Thank you for your support!</b>\n"
            f"{p['emoji']} <b>Package «{name}» activated!</b>\n"
            f"{_samosvet()} <b>+{samosvety_str} Samosvets</b>\n"
            f"{_samosvet()} <b>Balance: {bal_str}</b>"
            f"</blockquote>"
        )
    else:
        msg = (
            f"<blockquote>"
            f"{_tg(_GIFT_EMOJI_ID, '🎁')} <b>Спасибо за поддержку!</b>\n"
            f"{p['emoji']} <b>Пакет «{name}» активирован!</b>\n"
            f"{_samosvet()} <b>+{samosvety_str} Самосветов</b>\n"
            f"{_samosvet()} <b>Баланс: {bal_str}</b>"
            f"</blockquote>"
        )
    return True, msg, samosvety


# ============================================================
#  КАК ПОДКЛЮЧИТЬ В БОТЕ (инструкция в комментарии)
# ============================================================
#
#  1. В профиле добавить кнопку:
#       InlineKeyboardButton(text="💠 Донат", callback_data="donate_main")
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
#       ok, msg, samosvety = apply_donate(user_data, pkg_key)
#       # apply_donate() уже сам проставил donate_purchases,
#       # total_donated_stars, total_donated_samosvety, donate_purchased_keys —
#       # ничего доинкрементировать вручную не нужно.
#       # Самосветы хранятся отдельно от игровых монет: user_data["samosvety"]
#       from achieves import check_achievements, notify_new_achievements
#       newly = check_achievements(user_data)
#       # сохранить user_data в БД
#       await bot.send_message(user_id, msg)
#       await notify_new_achievements(bot, user_id, newly, user_data.get("lang", "ru"))
