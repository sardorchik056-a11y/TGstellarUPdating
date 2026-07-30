# ============================================================
#  donate.py  —  Донаты / Пакеты Самосветов за Telegram Stars
# ============================================================

import aiohttp

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
#  КОНФИГ — КРИПТО-ПЛАТЁЖИ (@send / xRocket)
# ============================================================
#
#  @send — новое имя бота @CryptoBot, платёжный API называется "Crypto Pay"
#  и не переименовался вместе с ботом.
#    Токен: открой @send -> Crypto Pay -> Create App -> API Token
#    Докс:  https://help.send.tg/en/articles/10279948-crypto-pay-api
#
SEND_PAY_API_TOKEN = "582363:AALEf7JOugnrQyrkMHzH5UrO7pdOjjYnTQy"
SEND_PAY_BASE_URL  = "https://pay.crypt.bot/api"   # тестнет: https://testnet-pay.crypt.bot/api
SEND_PAY_ASSET     = "USDT"

#  xRocket — Rocket Pay API.
#    Токен: открой @xrocket -> Rocket Pay -> Создать кассу -> API token
#    Докс:  https://pay.ton-rocket.com/api
#
ROCKET_PAY_API_KEY  = "034cea3212dcfe762c3dc3093"
ROCKET_PAY_BASE_URL = "https://pay.ton-rocket.com"
ROCKET_PAY_CURRENCY = "USDT"

# Крипто-платёжки не примут микро-суммы — держим минимум по инвойсу
CRYPTO_MIN_USDT = 0.10

PAYMENT_PROVIDERS = {
    "stars":   {"label": "Telegram Stars", "emoji": "⭐"},
    "send":    {"label": "@send (USDT)",   "emoji": "💳"},
    "xrocket": {"label": "xRocket (USDT)", "emoji": "🚀"},
}

# ============================================================
#  УТИЛИТЫ
# ============================================================

_STAR_EMOJI_ID      = "5262643974912355126"   # ⭐ Telegram Stars
_SAMOSVET_EMOJI_ID  = "5465501598199342448"   # 💠 Самосвет (донатная валюта)
_BACK_EMOJI_ID      = "6039539366177541657"   # ← назад
_GIFT_EMOJI_ID      = "5222113468051629260"   # 🎁
_FIRE_EMOJI_ID      = "5438496463044752972"   # 🔥
_CROWN_EMOJI_ID     = "5348570868752595928"   # 👑  (иконка звёзд Telegram)

# Иконки для кнопок выбора способа оплаты
_CHOICE_EMOJI_STARS    = "5798819377088307477"
_CHOICE_EMOJI_XROCKET  = "5798534328698805312"
_CHOICE_EMOJI_CRYPTOBOT = "5798650400189980129"
_CHOICE_EMOJI_BY_PROVIDER = {
    "stars":   _CHOICE_EMOJI_STARS,
    "send":    _CHOICE_EMOJI_CRYPTOBOT,
    "xrocket": _CHOICE_EMOJI_XROCKET,
}

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


def _stars_to_usdt(stars: int) -> float:
    """
    Переводит цену пакета из Stars в USDT по курсу STAR_TO_USD.
    Округляет до 2 знаков и подтягивает к CRYPTO_MIN_USDT, если сумма
    слишком мала — иначе платёжка отклонит инвойс.
    """
    amount = round(stars * STAR_TO_USD, 2)
    return max(amount, CRYPTO_MIN_USDT)


# ============================================================
#  ТЕКСТ — ГЛАВНЫЙ ЭКРАН ДОНАТОВ
# ============================================================

def donate_main_text(lang: str = "ru", balance: int = 0) -> str:
    balance_str = _fmt_num(balance)

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
            f"{_samosvet()} <b>Your balance: {balance_str} Samosvets</b>"
            f"</blockquote>"
        )
        lines.append(
            f"\n<blockquote>"
            f"{_star()} <b>Payment via Telegram Stars.</b>\n"
            f"<i>Select a package below to proceed.</i>"
            f"</blockquote>"
        )
    else:
        lines.append(
            f"\n<blockquote>"
            f"{_samosvet()} <b>Твой баланс: {balance_str} Самосветов</b>"
            f"</blockquote>"
        )
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

def donate_package_text(pkg_key: str, lang: str = "ru", show_method_hint: bool = True) -> str:
    p = DONATE_BY_KEY.get(pkg_key)
    if not p:
        return "❌ Пакет не найден." if lang == "ru" else "❌ Package not found."

    name          = p["label_en"] if lang == "en" else p["label"]
    samosvety_str = _fmt_num(p["samosvety"])
    stars_str     = _fmt_stars(p["stars"])
    hint = ""
    if show_method_hint:
        hint = (
            f"\n\n<i>Choose a payment method below</i>" if lang == "en"
            else f"\n\n<i>Выберите способ оплаты ниже</i>"
        )

    if lang == "en":
        return (
            f"<blockquote>"
            f'<tg-emoji emoji-id="5400362079783770689">🌟</tg-emoji> <b>«{name}» Package</b>\n'
            f"{_samosvet()} <b>You get:</b> {samosvety_str} Samosvets\n"
            f"{_star()} <b>Price:</b> {stars_str}"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f'<tg-emoji emoji-id="5206607081334906820">🌟</tg-emoji> Credited to your balance instantly after payment\n'
            f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> Samosvets never expire'
            f"</blockquote>"
            f"{hint}"
        )
    else:
        return (
            f"<blockquote>"
            f'<tg-emoji emoji-id="5400362079783770689">🌟</tg-emoji> <b>Пакет «{name}»</b>\n'
            f"{_samosvet()} <b>Получишь:</b> {samosvety_str} Самосветов\n"
            f"{_star()} <b>Стоимость:</b> {stars_str}"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f'<tg-emoji emoji-id="5206607081334906820">🌟</tg-emoji> Зачисляется на баланс сразу после оплаты\n'
            f'<tg-emoji emoji-id="5427168083074628963">🌟</tg-emoji> Самосветы не сгорают'
            f"</blockquote>"
            f"{hint}"
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
    """
    Экран конкретного пакета.
    Пока способ оплаты ещё не выбран (invoice_url=None) — три кнопки выбора
    без сумм: Stars / Cryptobot / xRocket.
    После того как выбран Stars и для него создана invoice_url — как раньше,
    кнопка "Купить" с суммой + "Мои звёзды" (эта кнопка нужна только тут).
    """
    builder = InlineKeyboardBuilder()
    p = DONATE_BY_KEY.get(pkg_key)
    stars_str = _fmt_stars(p["stars"]) if p else "?"

    if invoice_url:
        builder.row(InlineKeyboardButton(
            text=f"{_L(lang, 'Купить', 'Buy')} {stars_str}",
            url=invoice_url,
            icon_custom_emoji_id=_STAR_EMOJI_ID,
            style="success",
        ))
        builder.row(InlineKeyboardButton(
            text=_L(lang, "Мои звёзды", "My stars"),
            url="tg://stars/",
            icon_custom_emoji_id=_CROWN_EMOJI_ID,
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="Stars",
            callback_data=f"donate_buy_{pkg_key}",
            icon_custom_emoji_id=_CHOICE_EMOJI_STARS,
        ))
        builder.row(InlineKeyboardButton(
            text="Cryptobot",
            callback_data=f"donate_pay_send_{pkg_key}",
            icon_custom_emoji_id=_CHOICE_EMOJI_CRYPTOBOT,
        ))
        builder.row(InlineKeyboardButton(
            text="xRocket",
            callback_data=f"donate_pay_xrocket_{pkg_key}",
            icon_custom_emoji_id=_CHOICE_EMOJI_XROCKET,
        ))

    builder.row(InlineKeyboardButton(
        text=_L(lang, " Все пакеты", " All packages"),
        callback_data="donate_main",
        icon_custom_emoji_id=_BACK_EMOJI_ID,
    ))
    return builder.as_markup()


# ============================================================
#  @send (Crypto Pay API) — создание и проверка счёта
# ============================================================

async def create_send_invoice(pkg_key: str, uid: int) -> tuple[bool, str, str]:
    """
    Создаёт счёт на оплату через @send (Crypto Pay API).
    Возвращает (ok, pay_url, invoice_id).
    """
    p = DONATE_BY_KEY.get(pkg_key)
    if not p or not SEND_PAY_API_TOKEN or "PASTE_YOUR" in SEND_PAY_API_TOKEN:
        return False, "", ""

    amount = _stars_to_usdt(p["stars"])
    headers = {"Crypto-Pay-API-Token": SEND_PAY_API_TOKEN}
    body = {
        "asset": SEND_PAY_ASSET,
        "amount": f"{amount:.2f}",
        "description": f"TGStellar — пакет «{p['label']}» ({p['samosvety']} самосветов)",
        "payload": f"send_donate:{pkg_key}:{uid}",
        "expires_in": 3600,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SEND_PAY_BASE_URL}/createInvoice",
                headers=headers, json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
    except Exception as e:
        print(f"[donate] @send createInvoice error: {e}")
        return False, "", ""

    if not data.get("ok"):
        print(f"[donate] @send createInvoice failed: {data}")
        return False, "", ""

    result = data["result"]
    pay_url = (
        result.get("bot_invoice_url")
        or result.get("mini_app_invoice_url")
        or result.get("pay_url")
    )
    invoice_id = str(result.get("invoice_id", ""))
    if not pay_url or not invoice_id:
        return False, "", ""
    return True, pay_url, invoice_id


async def check_send_invoice(invoice_id: str) -> str:
    """
    Проверяет статус счёта @send.
    Возвращает "paid" / "active" / "expired" / "error".
    """
    if not SEND_PAY_API_TOKEN or "PASTE_YOUR" in SEND_PAY_API_TOKEN:
        return "error"
    headers = {"Crypto-Pay-API-Token": SEND_PAY_API_TOKEN}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SEND_PAY_BASE_URL}/getInvoices",
                headers=headers, params={"invoice_ids": invoice_id},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
    except Exception as e:
        print(f"[donate] @send getInvoices error: {e}")
        return "error"

    if not data.get("ok"):
        return "error"
    items = data["result"].get("items", [])
    if not items:
        return "error"
    return items[0].get("status", "error")


# ============================================================
#  xRocket (Rocket Pay API) — создание и проверка счёта
# ============================================================

async def create_xrocket_invoice(pkg_key: str, uid: int) -> tuple[bool, str, str]:
    """
    Создаёт счёт на оплату через xRocket (Rocket Pay API).
    Возвращает (ok, pay_url, invoice_id).
    """
    p = DONATE_BY_KEY.get(pkg_key)
    if not p or not ROCKET_PAY_API_KEY or "PASTE_YOUR" in ROCKET_PAY_API_KEY:
        return False, "", ""

    amount = _stars_to_usdt(p["stars"])
    headers = {"Rocket-Pay-Key": ROCKET_PAY_API_KEY}
    body = {
        "amount": amount,
        "currency": ROCKET_PAY_CURRENCY,
        "description": f"TGStellar — пакет «{p['label']}» ({p['samosvety']} самосветов)",
        "payload": f"xrocket_donate:{pkg_key}:{uid}",
        "numPayments": 1,  # сколько раз можно оплатить этот счёт — обязательное поле API
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ROCKET_PAY_BASE_URL}/invoices",
                headers=headers, json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                status_code = resp.status
                data = await resp.json()
    except Exception as e:
        print(f"[donate] xRocket create invoice error: {e}")
        return False, "", ""

    if status_code >= 400:
        print(f"[donate] xRocket create invoice HTTP {status_code}: {data}")
        return False, "", ""

    # Ответ API обёрнут в {"success": bool, "data": {...}}
    if not data.get("success"):
        print(f"[donate] xRocket create invoice failed: {data}")
        return False, "", ""

    result = data.get("data", {})
    pay_url = result.get("link") or result.get("payLink") or result.get("url")
    invoice_id = str(result.get("id", ""))
    if not pay_url or not invoice_id:
        return False, "", ""
    return True, pay_url, invoice_id


async def check_xrocket_invoice(invoice_id: str) -> str:
    """
    Проверяет статус счёта xRocket.
    Возвращает "paid" / "active" / "expired" / "error".
    """
    if not ROCKET_PAY_API_KEY or "PASTE_YOUR" in ROCKET_PAY_API_KEY:
        return "error"
    headers = {"Rocket-Pay-Key": ROCKET_PAY_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ROCKET_PAY_BASE_URL}/invoices/{invoice_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                status_code = resp.status
                data = await resp.json()
    except Exception as e:
        print(f"[donate] xRocket check invoice error: {e}")
        return "error"

    if status_code >= 400:
        print(f"[donate] xRocket check invoice HTTP {status_code}: {data}")
        return "error"

    if not data.get("success"):
        print(f"[donate] xRocket check invoice failed: {data}")
        return "error"
    result = data.get("data", {})
    # В разных версиях API поле может называться по-разному — подстраховываемся
    status = result.get("status") or ("paid" if result.get("paid") else "active")
    return status


# ============================================================
#  ТЕКСТ И КЛАВИАТУРА — КРИПТО-СЧЁТ (@send / xRocket)
# ============================================================

def donate_crypto_invoice_text(pkg_key: str, provider: str, lang: str = "ru") -> str:
    p = DONATE_BY_KEY.get(pkg_key)
    if not p:
        return "❌ Пакет не найден." if lang == "ru" else "❌ Package not found."

    prov = PAYMENT_PROVIDERS.get(provider, {"label": provider, "emoji": "💳"})
    name = p["label_en"] if lang == "en" else p["label"]
    samosvety_str = _fmt_num(p["samosvety"])
    usdt_str = f"{_stars_to_usdt(p['stars']):.2f} USDT"

    if lang == "en":
        return (
            f"<blockquote>"
            f"{prov['emoji']} <b>Payment via {prov['label']}</b>\n"
            f"{_samosvet()} <b>Package:</b> «{name}» — {samosvety_str} Samosvets\n"
            f"{prov['emoji']} <b>Amount:</b> {usdt_str}"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f"<i>Tap “Pay”, complete the payment in the opened app, "
            f"then come back and tap “Check payment”.</i>"
            f"</blockquote>"
        )
    else:
        return (
            f"<blockquote>"
            f"{prov['emoji']} <b>Оплата через {prov['label']}</b>\n"
            f"{_samosvet()} <b>Пакет:</b> «{name}» — {samosvety_str} Самосветов\n"
            f"{prov['emoji']} <b>Сумма:</b> {usdt_str}"
            f"</blockquote>\n"
            f"\n<blockquote>"
            f"<i>Нажми «Оплатить», заверши платёж в открывшемся приложении, "
            f"затем вернись сюда и нажми «Проверить оплату».</i>"
            f"</blockquote>"
        )


def donate_crypto_invoice_keyboard(
    pkg_key: str, provider: str, pay_url: str, invoice_id: str, lang: str = "ru"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Оплатить", "Pay"),
        url=pay_url,
        icon_custom_emoji_id=_CHOICE_EMOJI_BY_PROVIDER.get(provider, _STAR_EMOJI_ID),
        style="success",
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Проверить оплату", "Check payment"),
        callback_data=f"donate_check_{provider}:{invoice_id}:{pkg_key}",
        icon_custom_emoji_id=_FIRE_EMOJI_ID,
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
#
#  6. Способы оплаты @send и xRocket работают иначе, чем Stars: у них нет
#     pre_checkout_query/successful_payment — это внешние платёжки со своим
#     REST API, поэтому оплата подтверждается через кнопку "Проверить оплату":
#
#       Хендлер callback "donate_pay_send_{pkg_key}" / "donate_pay_xrocket_{pkg_key}":
#           ok, pay_url, invoice_id = await create_send_invoice(pkg_key, uid)      # или create_xrocket_invoice
#           await call.message.edit_text(
#               donate_crypto_invoice_text(pkg_key, "send", lang),                 # или "xrocket"
#               reply_markup=donate_crypto_invoice_keyboard(pkg_key, "send", pay_url, invoice_id, lang),
#           )
#
#       Хендлер callback "donate_check_send:{invoice_id}:{pkg_key}" (аналогично для xrocket):
#           status = await check_send_invoice(invoice_id)                          # или check_xrocket_invoice
#           if status != "paid":
#               await call.answer("Оплата ещё не поступила", show_alert=True)
#               return
#           # защита от повторного зачисления по одному и тому же invoice_id —
#           # тем же charge-processed механизмом, что и для Stars
#           ok, msg, samosvety = apply_donate(user_data, pkg_key)
#           # сохранить user_data, показать achievements, отредактировать сообщение
#
#     Для продакшена лучше не только на "Проверить оплату" полагаться, а ещё
#     поднять вебхук-эндпоинт (callbackUrl у xRocket / Webhooks у @send Crypto Pay),
#     чтобы зачисление происходило мгновенно даже если пользователь не нажал кнопку.
