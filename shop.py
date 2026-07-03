# ============================================================
#  shop.py  —  Магазин кейсов TGStellar
#  Переписан для aiogram 3.x
# ============================================================

import random
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from miner import (
    EMOJI_BACK,
    EMOJI_BTN_BUY_COINS,
    EMOJI_BTN_SELL,
    EMOJI_BTN_COLLECT,
    EMOJI_BTN_ACTIVE,
    EMOJI_BTN_SELECT,
    EMOJI_BTN_DURATION,
    EMOJI_BTN_INV,
    EMOJI_BTN_WORKSHOP,
    EMOJI_NOT_BOUGHT,
    EMOJI_SELECTED,
)


def _btn(emoji_id: str, label: str, cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=emoji_id)


def _back_btn(cb: str, label: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=EMOJI_BACK)


def _L(lang: str, ru: str, en: str) -> str:
    """Inline двуязычная строка без обращения к lang.py."""
    return en if lang == "en" else ru


_E = {
    "case":       "5438571934210082705",
    "xp_case":    "5404843113652970870",
    "enh_case":   "5256047523620995497",
    "boost":      "5438571934210082705",
    "enh_boost":  "5256047523620995497",
    "poison":     "5456584142286250164",
    "xp_boost":   "5224607267797606837",
    "xp_instant": "5404843113652970870",
    "coin":       "5199552030615558774",
    "stats":      "5442939099906325301",
    "luck":       "5442939099906325301",
    "inv":        "5445221832074483553",
    "sell":       "5429518319243775957",
    "activate":   "5206607081334906820",
    "warn":       "5240241223632954241",
    "ok":         "5206607081334906820",
    "cancel":     "5240241223632954241",
    "shop":       "5442939099906325301",
    "back":       "6039539366177541657",
    "timer":      "5440621591387980068",
    "mult":       "5397916757333654639",
    "spent":      "5447183459602669338",
    "balance":    "5278467510604160626",
    "arrow":      "5427168083074628963",
}


def _pe(key: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{_E[key]}">{fallback}</tg-emoji>'


# ============================================================
#  ДЛИТЕЛЬНОСТИ
# ============================================================

_DUR = {
    "5min":  5  * 60,
    "10min": 10 * 60,
    "30min": 30 * 60,
    "1h":    60 * 60,
    "2h":    2  * 60 * 60,
    "4h":    4  * 60 * 60,
    "6h":    6  * 60 * 60,
    "10h":   10 * 60 * 60,
    "24h":   24 * 60 * 60,
    "48h":   48 * 60 * 60,
}

_DUR_LABELS = {
    "5min":  "5 мин",
    "10min": "10 мин",
    "30min": "30 мин",
    "1h":    "1 час",
    "2h":    "2 часа",
    "4h":    "4 часа",
    "6h":    "6 часов",
    "10h":   "10 часов",
    "24h":   "24 часа",
    "48h":   "48 часов",
}

_DUR_LABELS_EN = {
    "5min":  "5 min",
    "10min": "10 min",
    "30min": "30 min",
    "1h":    "1 hour",
    "2h":    "2 hours",
    "4h":    "4 hours",
    "6h":    "6 hours",
    "10h":   "10 hours",
    "24h":   "24 hours",
    "48h":   "48 hours",
}

def _dur_label(dur_key: str, lang: str = "ru") -> str:
    return (_DUR_LABELS_EN if lang == "en" else _DUR_LABELS).get(dur_key, dur_key)

# ============================================================
#  ПУЛ ОБЫЧНОГО КЕЙСА
# ============================================================

_BOOSTER_POOL = [
    {"key": "boost_1.4x_30min", "multiplier": 1.4, "dur_key": "30min", "chance": 55},
    {"key": "boost_1.4x_4h",    "multiplier": 1.4, "dur_key": "4h",    "chance": 25},
    {"key": "boost_1.4x_24h",   "multiplier": 1.4, "dur_key": "24h",   "chance": 10},
    {"key": "boost_1.8x_30min", "multiplier": 1.8, "dur_key": "30min", "chance": 30},
    {"key": "boost_1.8x_4h",    "multiplier": 1.8, "dur_key": "4h",    "chance": 12},
    {"key": "boost_1.8x_24h",   "multiplier": 1.8, "dur_key": "24h",   "chance":  4},
    {"key": "boost_2x_30min",   "multiplier": 2.0, "dur_key": "30min", "chance": 18},
    {"key": "boost_2x_4h",      "multiplier": 2.0, "dur_key": "4h",    "chance":  7},
    {"key": "boost_2x_24h",     "multiplier": 2.0, "dur_key": "24h",   "chance":  2},
]

BOOSTERS_BY_KEY = {b["key"]: b for b in _BOOSTER_POOL}
MAX_INVENTORY = 10

_SELL_PRICES = {
    ("1.4", "30min"): 1_500, ("1.4", "4h"): 6_500,  ("1.4", "24h"): 20_000,
    ("1.8", "30min"): 2_500, ("1.8", "4h"): 11_000, ("1.8", "24h"): 32_000,
    ("2.0", "30min"): 3_500, ("2.0", "4h"): 16_000, ("2.0", "24h"): 48_000,
}


def get_sell_price(item: dict) -> int:
    m = item["multiplier"]
    if m >= 2.0:   mk = "2.0"
    elif m >= 1.8: mk = "1.8"
    else:          mk = "1.4"
    return _SELL_PRICES.get((mk, item["dur_key"]), 1_000)


# ============================================================
#  ПУЛ XP-КЕЙСА
# ============================================================

_XP_POOL = [
    {"key": "xp_100",  "type": "xp_instant", "xp": 100,  "chance": 90},
    {"key": "xp_225",  "type": "xp_instant", "xp": 225,  "chance": 70},
    {"key": "xp_750",  "type": "xp_instant", "xp": 750,  "chance": 35},
    {"key": "xp_2000", "type": "xp_instant", "xp": 2000, "chance": 12},
    {"key": "xp_5000", "type": "xp_instant", "xp": 5000, "chance":  3},
    {"key": "xpboost_1.4x_30min", "type": "xp_boost", "multiplier": 1.4, "dur_key": "30min", "chance": 55},
    {"key": "xpboost_1.4x_4h",    "type": "xp_boost", "multiplier": 1.4, "dur_key": "4h",    "chance": 25},
    {"key": "xpboost_1.4x_24h",   "type": "xp_boost", "multiplier": 1.4, "dur_key": "24h",   "chance": 10},
    {"key": "xpboost_1.8x_30min", "type": "xp_boost", "multiplier": 1.8, "dur_key": "30min", "chance": 30},
    {"key": "xpboost_1.8x_4h",    "type": "xp_boost", "multiplier": 1.8, "dur_key": "4h",    "chance": 12},
    {"key": "xpboost_1.8x_24h",   "type": "xp_boost", "multiplier": 1.8, "dur_key": "24h",   "chance":  4},
    {"key": "xpboost_2x_30min",   "type": "xp_boost", "multiplier": 2.0, "dur_key": "30min", "chance": 18},
    {"key": "xpboost_2x_4h",      "type": "xp_boost", "multiplier": 2.0, "dur_key": "4h",    "chance":  7},
    {"key": "xpboost_2x_24h",     "type": "xp_boost", "multiplier": 2.0, "dur_key": "24h",   "chance":  2},
]

XP_POOL_BY_KEY = {x["key"]: x for x in _XP_POOL}
MAX_XP_INVENTORY = 10

# ============================================================
#  ПУЛ КЕЙСА УСИЛИТЕЛЕЙ
# ============================================================

_ENH_BOOSTER_POOL = [
    # ── 1.4× ──────────────────────────────────────────────
    {"key": "enh_boost_1.4x_30min", "type": "enh_boost", "multiplier": 1.4, "dur_key": "30min", "chance": 55},
    {"key": "enh_boost_1.4x_4h",    "type": "enh_boost", "multiplier": 1.4, "dur_key": "4h",    "chance": 25},
    {"key": "enh_boost_1.4x_24h",   "type": "enh_boost", "multiplier": 1.4, "dur_key": "24h",   "chance": 10},
    # ── 1.8× ──────────────────────────────────────────────
    {"key": "enh_boost_1.8x_30min", "type": "enh_boost", "multiplier": 1.8, "dur_key": "30min", "chance": 30},
    {"key": "enh_boost_1.8x_4h",    "type": "enh_boost", "multiplier": 1.8, "dur_key": "4h",    "chance": 12},
    {"key": "enh_boost_1.8x_24h",   "type": "enh_boost", "multiplier": 1.8, "dur_key": "24h",   "chance":  4},
    # ── 2× ────────────────────────────────────────────────
    {"key": "enh_boost_2x_30min",   "type": "enh_boost", "multiplier": 2.0, "dur_key": "30min", "chance": 18},
    {"key": "enh_boost_2x_4h",      "type": "enh_boost", "multiplier": 2.0, "dur_key": "4h",    "chance":  7},
    {"key": "enh_boost_2x_24h",     "type": "enh_boost", "multiplier": 2.0, "dur_key": "24h",   "chance":  2},
]

# 5 ядов: Гадюка / Кобра / Чёрная Мамба / Василиск / Левиафан
_POISON_POOL = [
    {"key": "poison_1", "type": "poison", "name": "Яд Гадюки",       "damage": 100_000, "dur_key": "30min", "chance": 5.0},
    {"key": "poison_2", "type": "poison", "name": "Яд Кобры",        "damage": 150_000, "dur_key": "30min", "chance": 3.0},
    {"key": "poison_3", "type": "poison", "name": "Яд Чёрной Мамбы", "damage": 225_000, "dur_key": "30min", "chance": 2.0},
    {"key": "poison_4", "type": "poison", "name": "Яд Василиска",    "damage": 350_000, "dur_key": "30min", "chance": 1.0},
    {"key": "poison_5", "type": "poison", "name": "Яд Левиафана",    "damage": 500_000, "dur_key": "30min", "chance": 0.5},
]

_ENH_POOL = _ENH_BOOSTER_POOL + _POISON_POOL
ENH_POOL_BY_KEY = {x["key"]: x for x in _ENH_POOL}
POISON_BY_KEY   = {x["key"]: x for x in _POISON_POOL}
MAX_ENH_INVENTORY = 10

# ============================================================
#  ПУЛ КЕЙСА АРТЕФАКТОВ
# ============================================================

_ARTIFACT_POOL = [
    # ── 50% шанс — множитель 1.3× ──────────────────────────
    {"key": "art_kulon_iskazheniya",   "type": "artifact", "name": "Кулон Искажения",      "name_en": "Distortion Pendant",    "emoji_id": "5938541999031325561", "effect": "mine",   "multiplier": 1.25, "chance": 50},
    {"key": "art_oracle",              "type": "artifact", "name": "Оракул",               "name_en": "Oracle",                "emoji_id": "5165898384870999138", "effect": "damage", "multiplier": 1.25, "chance": 50},
    {"key": "art_amulet_hranitelya",   "type": "artifact", "name": "Амулет Хранителя",     "name_en": "Guardian Amulet",       "emoji_id": "5938082716703528871", "effect": "pets",   "multiplier": 1.25, "chance": 50},
    # ── 25% шанс — множитель 1.5× ──────────────────────────
    {"key": "art_lunnaya_relikviya",   "type": "artifact", "name": "Лунная Реликвия",      "name_en": "Lunar Relic",           "emoji_id": "5226662903569989373", "effect": "mine",   "multiplier": 1.4, "chance": 25},
    {"key": "art_sfera_zhadnosti",     "type": "artifact", "name": "Сфера Жадности",       "name_en": "Sphere of Greed",       "emoji_id": "5080262187302257610", "effect": "damage", "multiplier": 1.4, "chance": 25},
    {"key": "art_amulet_zhizni",       "type": "artifact", "name": "Амулет Жизни и Смерти","name_en": "Amulet of Life & Death","emoji_id": "6228938636428052300", "effect": "pets",   "multiplier": 1.4, "chance": 25},
    # ── 15% шанс — множитель 1.8× ──────────────────────────
    {"key": "art_sfera_illyuziy",      "type": "artifact", "name": "Сфера Иллюзий",        "name_en": "Sphere of Illusions",   "emoji_id": "5343583990815156847", "effect": "mine",   "multiplier": 1.65, "chance": 15},
    {"key": "art_serdtse_morey",       "type": "artifact", "name": "Сердце Морей",          "name_en": "Heart of the Seas",     "emoji_id": "6201647288947839133", "effect": "damage", "multiplier": 1.65, "chance": 15},
    {"key": "art_kristall_egzorcizma", "type": "artifact", "name": "Кристалл Экзорцизма",  "name_en": "Exorcism Crystal",      "emoji_id": "5451889386549425709", "effect": "pets",   "multiplier": 1.65, "chance": 15},
    # ── 1% шанс — комбо-артефакт ────────────────────────────
    {"key": "art_vsevlastniy",         "type": "artifact", "name": "Кольцо Перерождений",  "name_en": "Ring of Rebirths",      "emoji_id": "5872990619021875271", "effect": "all",    "multiplier": 1.35, "chance": 1},
]

ARTIFACT_POOL_BY_KEY = {a["key"]: a for a in _ARTIFACT_POOL}
ARTIFACT_CASE_COST_STARS = 299

_ARTIFACT_EFFECT_LABELS = {
    "mine":   "к добыче руды",
    "damage": "к урону по боссу",
    "pets":   "к добыче питомцов",
    "all":    "ко всем трём видам добычи",
}

_ARTIFACT_EFFECT_LABELS_EN = {
    "mine":   "to ore mining",
    "damage": "to boss damage",
    "pets":   "to pet income",
    "all":    "to all three income types",
}

def _get_effect_label(effect: str, lang: str = "ru") -> str:
    return (_ARTIFACT_EFFECT_LABELS_EN if lang == "en" else _ARTIFACT_EFFECT_LABELS).get(effect, "")

def _artifact_desc(a: dict, lang: str = "ru") -> str:
    effect_label = _get_effect_label(a["effect"], lang)
    eid  = a.get("emoji_id", "")
    emoji = f'<tg-emoji emoji-id="{eid}">♦️</tg-emoji> ' if eid else ""
    name = a.get("name_en", a["name"]) if lang == "en" else a["name"]
    return f'{emoji}<b><i>{name}</i></b> — {a["multiplier"]}× {effect_label}'


_ARTIFACT_CASE_COIN_REWARD = 50_000_000  # монеты за 25%-шанс вместо артефакта

def open_artifact_case(data: dict, lang: str = "ru") -> tuple:
    """Открыть кейс артефактов. Оплата Stars уже прошла — выдаём артефакт.
    25% шанс: выдаём 50М монет вместо артефакта.
    75% шанс: выдаём артефакт из пула.
    ВСЕГДА возвращает (True, msg, chosen) — сохранение на стороне вызывающего."""

    # Счётчик инкрементируется всегда — деньги потрачены в любом случае
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1

    # ── 25% шанс: монеты вместо артефакта ──────────────────────────────
    if random.random() < 0.25:
        coins = _ARTIFACT_CASE_COIN_REWARD
        data["balance"] = data.get("balance", 0) + coins
        if lang == "en":
            msg = (
                f"<blockquote>{_pe('stats', '💎')} <b><i>Artifact Case opened!</i></b>\n"
                f"{_pe('coin', '💰')} <b><i>Lucky coins drop: +{_fmt_num(coins)} {COIN}</i></b></blockquote>"
            )
        else:
            msg = (
                f"<blockquote>{_pe('stats', '💎')} <b><i>Кейс Артефактов открыт!</i></b>\n"
                f"{_pe('coin', '💰')} <b><i>Монеты вместо артефакта: +{_fmt_num(coins)} {COIN}</i></b></blockquote>"
            )
        return True, msg, None

    # ── 75% шанс: артефакт из пула ─────────────────────────────────────
    pool    = _ARTIFACT_POOL
    weights = [a["chance"] for a in pool]
    chosen  = random.choices(pool, weights=weights, k=1)[0]

    artifacts = data.setdefault("artifacts", [])
    already_have = any(entry["key"] == chosen["key"] for entry in artifacts)
    if not already_have:
        artifacts.append({"key": chosen["key"]})
        added_msg = f"{_pe('ok', '✅')} <b><i>{_L(lang, 'Артефакт добавлен в коллекцию!', 'Artifact added to collection!')}</i></b>"
    else:
        # Дубликат — выдаём монеты по множителю артефакта
        _dup_rewards = {1.3: 5_000_000, 1.5: 8_000_000, 1.8: 15_000_000, 1.4: 50_000_000}
        _dup_coins = _dup_rewards.get(chosen["multiplier"], 5_000_000)
        data["balance"] = data.get("balance", 0) + _dup_coins
        added_msg = (
            f"{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Этот артефакт у тебя уже есть!', 'You already have this artifact!')}</i></b>\n"
            f"{_pe('coin', '💰')} <b><i>{_L(lang, 'Компенсация', 'Compensation')}: +{_fmt_num(_dup_coins)} {COIN}</i></b>"
        )

    msg = (
        f"<blockquote>{_pe('stats', '💎')} <b><i>{_L(lang, 'Кейс Артефактов открыт!', 'Artifact Case opened!')}</i></b>\n"
        f"{_pe('arrow', '➡️')} <b><i>{_L(lang, 'Выпало', 'Dropped')}: {_artifact_desc(chosen, lang)}</i></b></blockquote>\n"
        f"\n<blockquote>{added_msg}</blockquote>"
    )
    return True, msg, chosen


def get_artifact_mine_multiplier(data: dict) -> float:
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("mine", "all"):
            total *= a["multiplier"]
    return round(total, 4)


def get_artifact_damage_multiplier(data: dict) -> float:
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("damage", "all"):
            total *= a["multiplier"]
    return round(total, 4)


def get_artifact_pets_multiplier(data: dict) -> float:
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("pets", "all"):
            total *= a["multiplier"]
    return round(total, 4)


_ENH_SELL_PRICES = {
    # ── 1.4× ──
    "enh_boost_1.4x_30min": 1_500, "enh_boost_1.4x_4h": 6_500, "enh_boost_1.4x_24h": 20_000,
    # ── 1.8× ──
    "enh_boost_1.8x_30min": 2_500, "enh_boost_1.8x_4h": 11_000, "enh_boost_1.8x_24h": 32_000,
    # ── 2× ──
    "enh_boost_2x_30min":   3_500, "enh_boost_2x_4h":   16_000, "enh_boost_2x_24h":   48_000,
    # ── Яды ──
    "poison_1": 7_500,
    "poison_2": 13_000,
    "poison_3": 20_000,
    "poison_4": 35_000,
    "poison_5": 50_000,
}


def get_enh_sell_price(item: dict) -> int:
    return _ENH_SELL_PRICES.get(item["key"], 1_000)

_XP_SELL_PRICES = {
    "xpboost_1.4x_30min": 1_500, "xpboost_1.4x_4h": 6_500,  "xpboost_1.4x_24h": 20_000,
    "xpboost_1.8x_30min": 2_500, "xpboost_1.8x_4h": 11_000, "xpboost_1.8x_24h": 32_000,
    "xpboost_2x_30min":   3_500, "xpboost_2x_4h":   16_000, "xpboost_2x_24h":   48_000,
}


def get_xp_sell_price(item: dict) -> int:
    return _XP_SELL_PRICES.get(item["key"], 500)


CASES = {
    "common":   {"key": "common",   "name": "Ускорителей", "cost": 10_000, "pool": _BOOSTER_POOL, "type": "booster"},
    "xp":       {"key": "xp",       "name": "XP",          "cost": 25_000, "pool": _XP_POOL,      "type": "xp"},
    "enhancer": {"key": "enhancer", "name": "Усилителей",  "cost": 50_000, "pool": _ENH_POOL,     "type": "enhancer"},
}

# ============================================================
#  УТИЛИТЫ
# ============================================================

def _fmt_num(n) -> str:
    """
    Сокращённый формат чисел: 1500 -> "1.5к", 100000 -> "100к",
    2300000 -> "2.3м" и т.д. Единый стиль во всём боте.
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

    for div, suffix in [
        (1_000_000_000_000, "трлн"),
        (1_000_000_000,     "млрд"),
        (1_000_000,         "м"),
        (1_000,             "к"),
    ]:
        if n >= div:
            val = n / div
            val = int(val * 10) / 10
            if val == int(val):
                return f"{sign}{int(val)}{suffix}"
            return f"{sign}{val:.1f}{suffix}"

    return f"{sign}{int(n)}"


def _multiplier_label(mult: float) -> str:
    s = f"{mult}"
    if s.endswith(".0"):
        s = s[:-2]
    return f"{s}×"


def _booster_name(b: dict, lang: str = "ru") -> str:
    dur = _dur_label(b['dur_key'], lang)
    if lang == "en":
        return f"Booster {_multiplier_label(b['multiplier'])} for {dur}"
    return f"Ускоритель {_multiplier_label(b['multiplier'])} на {dur}"


def _xp_item_name(item: dict, lang: str = "ru") -> str:
    if item["type"] == "xp_instant":
        return f"{_pe('xp_instant', '✨')} {_fmt_num(item['xp'])} XP"
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f"{_pe('xp_boost', '🔮')} XP booster {mult} for {dur}"
    return f"{_pe('xp_boost', '🔮')} XP-ускоритель {mult} на {dur}"


def _enh_item_name(item: dict, lang: str = "ru") -> str:
    if item["type"] == "poison":
        dmg = _fmt_num(item["damage"])
        _poison_names_en = {
            "Яд Гадюки":       "Viper Venom",
            "Яд Кобры":        "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom",
            "Яд Василиска":    "Basilisk Venom",
            "Яд Левиафана":    "Leviathan Venom",
        }
        pname = _poison_names_en.get(item["name"], item["name"]) if lang == "en" else item["name"]
        dmg_label = "dmg" if lang == "en" else "урона"
        return f'{_pe("poison", "☠️")} {pname} — {dmg} {dmg_label}'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f'{_pe("enh_boost", "⚡")} Damage booster {mult} for {dur}'
    return f'{_pe("enh_boost", "⚡")} Усилитель {mult} на {dur}'


def _enh_item_name_plain(item: dict, lang: str = "ru") -> str:
    """Без HTML-тегов — для текста кнопок клавиатуры."""
    if item["type"] == "poison":
        dmg = _fmt_num(item["damage"])
        _poison_names_en = {
            "Яд Гадюки":       "Viper Venom",
            "Яд Кобры":        "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom",
            "Яд Василиска":    "Basilisk Venom",
            "Яд Левиафана":    "Leviathan Venom",
        }
        pname = _poison_names_en.get(item["name"], item["name"]) if lang == "en" else item["name"]
        dmg_label = "dmg" if lang == "en" else "урона"
        return f'{pname} — {dmg} {dmg_label}'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f'Damage booster {mult} for {dur}'
    return f'Усилитель {mult} на {dur}'


def _xp_item_name_plain(item: dict, lang: str = "ru") -> str:
    """Без HTML-тегов — для текста кнопок клавиатуры."""
    if item["type"] == "xp_instant":
        return f'{_fmt_num(item["xp"])} XP'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f'XP booster {mult} for {dur}'
    return f'XP-ускоритель {mult} на {dur}'


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _fmt_time_left(seconds: float, lang: str = "ru") -> str:
    seconds = int(seconds)
    if seconds <= 0:
        return "expired" if lang == "en" else "истёк"
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    if lang == "en":
        if h > 0:  return f"{h}h {m:02d}m"
        if m > 0:  return f"{m}m {s:02d}s"
        return f"{s}s"
    if h > 0:  return f"{h}ч {m:02d}м"
    if m > 0:  return f"{m}м {s:02d}с"
    return f"{s}с"


# ============================================================
#  ЛОГИКА
# ============================================================

def open_case(data: dict, case_key: str, lang: str = "ru") -> tuple:
    case = CASES.get(case_key)
    if not case:
        return False, _L(lang, "❌ Неизвестный кейс.", "❌ Unknown case."), None
    cost = case["cost"]
    if data.get("balance", 0) < cost:
        return False, f"❌ {_L(lang, 'Недостаточно монет!', 'Not enough coins!')}\n{_L(lang, 'Нужно', 'Need')}: {_fmt_num(cost)} {_pe('coin', '💰')}", None
    if case["type"] == "booster":
        inv = data.setdefault("boosters_inventory", [])
    elif case["type"] == "enhancer":
        inv = data.setdefault("enh_inventory", [])
    else:
        inv = data.setdefault("xp_inventory", [])
    pool    = case["pool"]
    weights = [b["chance"] for b in pool]
    dropped = random.choices(pool, weights=weights, k=1)[0]
    data["balance"] -= cost
    ts  = int(_now_ts())
    rnd = random.randint(1000, 9999)
    instance_id = f"{dropped['key']}_{ts}_{rnd}"
    if case["type"] == "booster":
        instance = {
            "instance_id":  instance_id,
            "key":          dropped["key"],
            "multiplier":   dropped["multiplier"],
            "dur_key":      dropped["dur_key"],
            "duration_sec": _DUR[dropped["dur_key"]],
            "chance":       dropped["chance"],
        }
        inv.append(instance)
        name     = f"{_pe('boost', '⚡')} {_booster_name(dropped, lang)}"
        inv_line = f"{_L(lang, 'В инвентаре', 'In inventory')}: {len(inv)}"
    elif case["type"] == "enhancer":
        instance = {
            "instance_id": instance_id,
            "key":         dropped["key"],
            "type":        dropped["type"],
            "chance":      dropped["chance"],
        }
        if dropped["type"] == "poison":
            instance["name"]       = dropped["name"]
            instance["damage"]     = dropped["damage"]
            instance["dur_key"]    = dropped["dur_key"]
            instance["duration_sec"] = _DUR[dropped["dur_key"]]
        else:
            instance["multiplier"]   = dropped["multiplier"]
            instance["dur_key"]      = dropped["dur_key"]
            instance["duration_sec"] = _DUR[dropped["dur_key"]]
        inv.append(instance)
        name     = _enh_item_name(instance, lang)
        inv_line = f"{_L(lang, 'В инвентаре усилителей', 'Enhancer inventory')}: {len(inv)}"
    else:
        instance = {
            "instance_id": instance_id,
            "key":         dropped["key"],
            "type":        dropped["type"],
            "chance":      dropped["chance"],
        }
        if dropped["type"] == "xp_instant":
            instance["xp"] = dropped["xp"]
            name = _xp_item_name(dropped, lang)
            # xp_instant применяется сразу — не кладём в инвентарь
            from miner import xp_for_level, MAX_LEVEL
            gained = dropped["xp"]
            level   = data.get("level", 1)
            xp      = data.get("xp", 0) + gained
            xp_max  = data.get("xp_max", xp_for_level(level))
            lvl_ups = 0
            while xp >= xp_max and level < MAX_LEVEL:
                xp    -= xp_max
                level += 1
                lvl_ups += 1
                xp_max  = xp_for_level(level)
            if level >= MAX_LEVEL:
                xp = min(xp, xp_max)
            data["level"]  = level
            data["xp"]     = xp
            data["xp_max"] = xp_max
            if lvl_ups:
                if lang == "en":
                    lvl_msg = f"\n🎉 <b><i>Level up to {level}!</i></b>" if lvl_ups <= 3 else f"\n🎉 <b><i>Level up to {level} (+{lvl_ups} lvl)!</i></b>"
                else:
                    lvl_msg = f"\n🎉 <b><i>Уровень повышен до {level}!</i></b>" * min(lvl_ups, 3) if lvl_ups <= 3 else f"\n🎉 <b><i>Уровень повышен до {level} (+{lvl_ups} ур.)!</i></b>"
            else:
                lvl_msg = ""
            data["cases_total_opened"] = data.get("cases_total_opened", 0) + 1
            data["cases_total_spent"]  = data.get("cases_total_spent",  0) + cost
            msg = (
                f"<blockquote>{_pe('case', '📦')} <b><i>{_L(lang, 'Кейс открыт!', 'Case opened!')}</i></b>\n"
                f"{_pe('arrow', '➡️')} <b><i>{_L(lang, 'Выпало', 'Dropped')}:</i></b> {name}</blockquote>\n"
                f"\n<blockquote>{_pe('xp_instant', '✨')} <b><i>+{_fmt_num(gained)} XP {_L(lang, 'начислено сразу!', 'applied instantly!')}</i></b>{lvl_msg}</blockquote>\n"
                f"\n<blockquote>{_pe('spent', '💸')} <b><i>{_L(lang, 'Потрачено', 'Spent')}: {_fmt_num(cost)}</i></b> {_pe('coin', '💰')}\n"
                f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}</blockquote>"
            )
            return True, msg, instance
        else:
            instance["multiplier"]   = dropped["multiplier"]
            instance["dur_key"]      = dropped["dur_key"]
            instance["duration_sec"] = _DUR[dropped["dur_key"]]
            name = _xp_item_name(dropped, lang)
        inv.append(instance)
        inv_line = f"{_L(lang, 'В XP-инвентаре', 'XP inventory')}: {len(inv)}"
    data["cases_total_opened"] = data.get("cases_total_opened", 0) + 1
    data["cases_total_spent"]  = data.get("cases_total_spent",  0) + cost
    msg = (
        f"<blockquote>{_pe('case', '📦')} <b><i>{_L(lang, 'Кейс открыт!', 'Case opened!')}</i></b>\n"
        f"{_pe('arrow', '➡️')} <b><i>{_L(lang, 'Выпало', 'Dropped')}:</i></b> {name}</blockquote>\n"
        f"\n<blockquote>{_pe('spent', '💸')} <b><i>{_L(lang, 'Потрачено', 'Spent')}: {_fmt_num(cost)}</i></b> {_pe('coin', '💰')}\n"
        f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}\n"
        f"{_pe('inv', '🎒')} <b><i>{inv_line}</i></b></blockquote>"
    )
    return True, msg, instance


# ============================================================
#  МАППИНГ НОМЕР КЕЙСА → КЛЮЧ
# ============================================================

CASE_NUM_TO_KEY = {1: "common", 2: "xp", 3: "enhancer"}
CASE_KEY_TO_NUM = {v: k for k, v in CASE_NUM_TO_KEY.items()}


def open_case_multi(data: dict, case_num: int, qty: int, lang: str = "ru") -> tuple:
    """
    Открывает qty кейсов с номером case_num (#1/#2/#3).
    Команды: открыть #1 5  /купить #2 10  open #1 5  /open #3 3
    Возвращает (ok, итоговое_сообщение).
    """
    case_key = CASE_NUM_TO_KEY.get(case_num)
    if not case_key:
        if lang == "en":
            err = f"Case #{case_num} not found. Available: #1 (boosters), #2 (XP), #3 (enhancers)."
        else:
            err = f"Кейс #{case_num} не найден. Доступны: #1 (ускорители), #2 (XP), #3 (усилители)."
        return False, f"❌ {err}"

    if qty < 1:
        err = "Количество должно быть ≥ 1." if lang == "ru" else "Quantity must be ≥ 1."
        return False, f"❌ {err}"
    if qty > 100:
        err = "Максимум 100 кейсов за раз." if lang == "ru" else "Maximum 100 cases at once."
        return False, f"❌ {err}"

    case       = CASES[case_key]
    total_cost = case["cost"] * qty

    if data.get("balance", 0) < total_cost:
        can_open = data.get("balance", 0) // case["cost"]
        if lang == "en":
            err = (
                f"Not enough coins for {qty} cases!\n"
                f"Need: {_fmt_num(total_cost)} | Balance: {_fmt_num(data.get('balance', 0))}\n"
                f"Can open: {can_open}"
            )
        else:
            err = (
                f"Недостаточно монет для {qty} кейсов!\n"
                f"Нужно: {_fmt_num(total_cost)} | Баланс: {_fmt_num(data.get('balance', 0))}\n"
                f"Можно открыть: {can_open}"
            )
        return False, f"❌ {err}"

    # Открываем qty кейсов подряд
    results: dict = {}  # item_key -> count
    opened_count  = 0
    for _ in range(qty):
        ok, _msg, instance = open_case(data, case_key, lang=lang)
        if not ok:
            break  # прерываем если закончились монеты в процессе
        if instance:
            k = instance.get("key", "?")
            results[k] = results.get(k, 0) + 1
            opened_count += 1

    if opened_count == 0:
        err = "Не удалось открыть ни одного кейса." if lang == "ru" else "Failed to open any cases."
        return False, f"❌ {err}"

    spent = case["cost"] * opened_count

    _CASE_NAMES_SHORT    = {"common": "Ускорителей", "xp": "XP", "enhancer": "Усилителей"}
    _CASE_NAMES_SHORT_EN = {"common": "Booster",     "xp": "XP", "enhancer": "Enhancer"}
    cname = _CASE_NAMES_SHORT_EN.get(case_key, case_key) if lang == "en" else _CASE_NAMES_SHORT.get(case_key, case_key)

    # Формируем список дропа
    result_lines = []
    for item_key, count in sorted(results.items(), key=lambda x: -x[1]):
        if case_key == "common":
            b = BOOSTERS_BY_KEY.get(item_key)
            name = _booster_name(b, lang) if b else item_key
        elif case_key == "xp":
            x = XP_POOL_BY_KEY.get(item_key)
            name = _xp_item_name_plain(x, lang) if x else item_key
        else:
            e = ENH_POOL_BY_KEY.get(item_key)
            name = _enh_item_name_plain(e, lang) if e else item_key
        qty_str = f" ×{count}" if count > 1 else ""
        result_lines.append(f"<b><i>{name}</i></b>{qty_str}")

    loot_text = "\n".join(f"  • {l}" for l in result_lines)

    if lang == "en":
        msg = (
            f"<blockquote>{_pe('case', '📦')} <b><i>Opened {opened_count}× {cname} case{'s' if opened_count != 1 else ''}!</i></b></blockquote>\n"
            f"\n<blockquote><b><i>Loot:</i></b>\n{loot_text}</blockquote>\n"
            f"\n<blockquote>{_pe('spent', '💸')} <b><i>Spent: {_fmt_num(spent)}</i></b> {_pe('coin', '💰')}\n"
            f"{_pe('balance', '💰')} <b><i>Balance: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}</blockquote>"
        )
    else:
        msg = (
            f"<blockquote>{_pe('case', '📦')} <b><i>Открыто {opened_count}× кейс {cname}!</i></b></blockquote>\n"
            f"\n<blockquote><b><i>Лут:</i></b>\n{loot_text}</blockquote>\n"
            f"\n<blockquote>{_pe('spent', '💸')} <b><i>Потрачено: {_fmt_num(spent)}</i></b> {_pe('coin', '💰')}\n"
            f"{_pe('balance', '💰')} <b><i>Баланс: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}</blockquote>"
        )
    return True, msg


def activate_booster(data: dict, instance_id: str, force: bool = False, lang: str = "ru") -> tuple:
    inv  = data.get("boosters_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return False, _L(lang, "❌ Ускоритель не найден.", "❌ Booster not found.")
    active     = data.get("active_booster")
    has_active = active and active.get("ends_at", 0) > _now_ts()
    if has_active and not force:
        return False, f"CONFIRM_REPLACE:{instance_id}"
    data["boosters_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    ends_at = _now_ts() + item["duration_sec"]
    data["active_booster"] = {
        "key": item["key"], "multiplier": item["multiplier"],
        "dur_key": item["dur_key"], "ends_at": ends_at,
    }
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    return True, (
        f"<blockquote>{_pe('activate', '✅')} <b><i>{_L(lang, 'Ускоритель активирован!', 'Booster activated!')}</i></b>\n"
        f"{_pe('boost', '⚡')} <b><i>{_booster_name(item, lang)}</i></b>\n"
        f"<b><i>{_L(lang, 'Все показатели кирки', 'All pickaxe stats')} ×{mult} {_L(lang, 'на', 'for')} {dur}!</i></b></blockquote>"
    )


def sell_booster(data: dict, instance_id: str, lang: str = "ru") -> tuple:
    inv  = data.get("boosters_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return False, _L(lang, "❌ Ускоритель не найден.", "❌ Booster not found."), 0
    price = get_sell_price(item)
    data["boosters_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    data["balance"] = data.get("balance", 0) + price
    return True, (
        f"<blockquote>{_pe('sell', '💸')} <b><i>{_L(lang, 'Ускоритель продан!', 'Booster sold!')}</i></b>\n"
        f"{_pe('boost', '⚡')} <b><i>{_booster_name(item, lang)}</i></b>\n"
        f"{_pe('coin', '💰')} <b><i>+{_fmt_num(price)}</i></b>\n"
        f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}</blockquote>"
    ), price


def use_xp_item(data: dict, instance_id: str, force: bool = False, lang: str = "ru") -> tuple:
    inv  = data.setdefault("xp_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return False, _L(lang, "❌ Предмет не найден.", "❌ Item not found.")
    if item["type"] == "xp_boost":
        active     = data.get("active_xp_booster")
        has_active = active and active.get("ends_at", 0) > _now_ts()
        if has_active and not force:
            return False, f"CONFIRM_REPLACE_XP:{instance_id}"
        data["xp_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
        ends_at = _now_ts() + item["duration_sec"]
        data["active_xp_booster"] = {
            "key": item["key"], "multiplier": item["multiplier"],
            "dur_key": item["dur_key"], "ends_at": ends_at,
        }
        mult = _multiplier_label(item["multiplier"])
        dur  = _dur_label(item["dur_key"], lang)
        return True, (
            f"<blockquote>{_pe('xp_boost', '🔮')} <b><i>{_L(lang, 'XP-ускоритель активирован!', 'XP booster activated!')}</i></b>\n"
            f"{_pe('xp_instant', '✨')} <b><i>{_L(lang, 'Множитель опыта', 'XP multiplier')} ×{mult} {_L(lang, 'на', 'for')} {dur}!</i></b></blockquote>"
        )
    from miner import xp_for_level, MAX_LEVEL
    gained = item["xp"]
    data["xp_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    level   = data.get("level", 1)
    xp      = data.get("xp", 0) + gained
    xp_max  = data.get("xp_max", xp_for_level(level))
    lvl_ups = 0
    while xp >= xp_max and level < MAX_LEVEL:
        xp    -= xp_max
        level += 1
        lvl_ups += 1
        xp_max  = xp_for_level(level)
    if level >= MAX_LEVEL:
        xp = min(xp, xp_max)
    data["level"]  = level
    data["xp"]     = xp
    data["xp_max"] = xp_max
    if lang == "en":
        lvl_msg = f"\n🎉 <b><i>Level up to {level}!</i></b>" * min(lvl_ups, 3)
        if lvl_ups > 3:
            lvl_msg = f"\n🎉 <b><i>Level up to {level} (+{lvl_ups} lvl)!</i></b>"
    else:
        lvl_msg = f"\n🎉 <b><i>Уровень повышен до {level}!</i></b>" * min(lvl_ups, 3)
        if lvl_ups > 3:
            lvl_msg = f"\n🎉 <b><i>Уровень повышен до {level} (+{lvl_ups} ур.)!</i></b>"
    return True, (
        f"<blockquote>{_pe('xp_instant', '✨')} <b><i>{_L(lang, 'Опыт получен!', 'XP received!')}</i></b>\n"
        f"{_pe('xp_instant', '✨')} <b><i>+{_fmt_num(gained)} XP</i></b>{lvl_msg}</blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, 'Уровень', 'Level')}: {level}</i></b>\n"
        f"<b><i>{_L(lang, 'Опыт', 'XP')}: {_fmt_num(xp)}/{_fmt_num(xp_max)}</i></b></blockquote>"
    )


def sell_xp_item(data: dict, instance_id: str, lang: str = "ru") -> tuple:
    inv  = data.setdefault("xp_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return False, _L(lang, "❌ Предмет не найден.", "❌ Item not found."), 0
    price = get_xp_sell_price(item)
    data["xp_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    data["balance"] = data.get("balance", 0) + price
    return True, (
        f"<blockquote>{_pe('sell', '💸')} <b><i>{_L(lang, 'Продано!', 'Sold!')}</i></b>\n"
        f"{_xp_item_name(item, lang)}\n"
        f"{_pe('coin', '💰')} <b><i>+{_fmt_num(price)}</i></b>\n"
        f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}</blockquote>"
    ), price


# ============================================================
#  ГЕТТЕРЫ активных бустеров
# ============================================================

def get_active_booster_multiplier(data: dict) -> float:
    active = data.get("active_booster")
    if not active:
        return 1.0
    if active.get("ends_at", 0) > _now_ts():
        return active["multiplier"]
    data["active_booster"] = None
    return 1.0


def get_active_booster_info(data: dict) -> dict | None:
    active = data.get("active_booster")
    if not active:
        return None
    if active.get("ends_at", 0) > _now_ts():
        return active
    data["active_booster"] = None
    return None


def get_active_xp_booster_multiplier(data: dict) -> float:
    active = data.get("active_xp_booster")
    if not active:
        return 1.0
    if active.get("ends_at", 0) > _now_ts():
        return active["multiplier"]
    data["active_xp_booster"] = None
    return 1.0


def get_active_xp_booster_info(data: dict) -> dict | None:
    active = data.get("active_xp_booster")
    if not active:
        return None
    if active.get("ends_at", 0) > _now_ts():
        return active
    data["active_xp_booster"] = None
    return None


# ============================================================
#  UI
# ============================================================

# ============================================================
#  АКТИВНЫЙ ЯД (геттеры)
# ============================================================

def get_active_enh_booster_info(data: dict) -> dict | None:
    active = data.get("active_enh_booster")
    if not active:
        return None
    if active.get("ends_at", 0) > _now_ts():
        return active
    data["active_enh_booster"] = None
    return None


def get_active_poison_info(data: dict) -> dict | None:
    active = data.get("active_poison")
    if not active:
        return None
    if active.get("ends_at", 0) > _now_ts():
        return active
    data["active_poison"] = None
    return None


# ============================================================
#  ПРИМЕНЕНИЕ ЯДА
# ============================================================

def use_poison(data: dict, instance_id: str, force: bool = False, lang: str = "ru") -> tuple:
    inv  = data.setdefault("enh_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item or item["type"] != "poison":
        return False, _L(lang, "❌ Яд не найден.", "❌ Poison not found.")
    active     = get_active_poison_info(data)
    has_active = active is not None
    if has_active and not force:
        return False, f"CONFIRM_REPLACE_POISON:{instance_id}"
    data["enh_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    duration = item.get("duration_sec") or _DUR.get(item.get("dur_key", ""), 30 * 60)
    ends_at = _now_ts() + duration
    data["active_poison"] = {
        "key":      item["key"],
        "name":     item["name"],
        "damage":   item["damage"],
        "dur_key":  item["dur_key"],
        "ends_at":  ends_at,
        "applied_at": _now_ts(),
    }
    _poison_names_en = {
        "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
        "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
        "Яд Левиафана": "Leviathan Venom",
    }
    pname = _poison_names_en.get(item["name"], item["name"]) if lang == "en" else item["name"]
    return True, (
        f'<blockquote><tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>{_L(lang, "Яд применён!", "Poison applied!")}</i></b>\n'
        f'<b><i>{pname}</i></b>\n'
        f'<tg-emoji emoji-id="{_E["timer"]}">⏱</tg-emoji> <b><i>{_L(lang, "Урон наносится 30 минут автоматически", "Damage applied automatically for 30 minutes")}</i></b>\n'
        f'<b><i>{_L(lang, "Суммарный урон боссу", "Total boss damage")}: {_fmt_num(item["damage"])}</i></b></blockquote>'
    )


# ============================================================
#  ПРОДАЖА предмета из инвентаря усилителей
# ============================================================

def sell_enh_item(data: dict, instance_id: str, lang: str = "ru") -> tuple:
    inv  = data.setdefault("enh_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return False, _L(lang, "❌ Предмет не найден.", "❌ Item not found."), 0
    price = get_enh_sell_price(item)
    data["enh_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    data["balance"] = data.get("balance", 0) + price
    return True, (
        f'{_pe("sell", "💸")} <b><i>{_L(lang, "Продано!", "Sold!")}</i></b>\n'
        f'{_enh_item_name(item, lang)}\n'
        f'{_pe("coin", "💰")} <b><i>+{_fmt_num(price)}</i></b>\n'
        f'{_pe("balance", "💰")} <b><i>{_L(lang, "Баланс", "Balance")}: {_fmt_num(data["balance"])}</i></b> {_pe("coin", "💰")}'
    ), price


# ============================================================
#  АКТИВАЦИЯ ускорителя из кейса усилителей
# ============================================================

def activate_enh_boost(data: dict, instance_id: str, force: bool = False, lang: str = "ru") -> tuple:
    inv  = data.setdefault("enh_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item or item["type"] != "enh_boost":
        return False, _L(lang, "❌ Усилитель не найден.", "❌ Enhancer not found.")
    active     = data.get("active_enh_booster")
    has_active = active and active.get("ends_at", 0) > _now_ts()
    if has_active and not force:
        return False, f"CONFIRM_REPLACE_ENH:{instance_id}"
    data["enh_inventory"] = [x for x in inv if x["instance_id"] != instance_id]
    duration = item.get("duration_sec") or _DUR.get(item.get("dur_key", ""), 30 * 60)
    ends_at = _now_ts() + duration
    data["active_enh_booster"] = {
        "key":        item["key"],
        "multiplier": item["multiplier"],
        "dur_key":    item["dur_key"],
        "ends_at":    ends_at,
    }
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    return True, (
        f'{_pe("enh_boost", "⚡")} <b><i>{_L(lang, "Усилитель активирован!", "Enhancer activated!")}</i></b>\n'
        f'<b><i>{_L(lang, "Урон", "Damage")} ×{mult} {_L(lang, "на", "for")} {dur}!</i></b>'
    )


# ============================================================
#  UI — ИНВЕНТАРЬ УСИЛИТЕЛЕЙ
# ============================================================

def enh_inventory_text(data: dict, lang: str = "ru") -> str:
    inv      = data.setdefault("enh_inventory", [])
    poison   = get_active_poison_info(data)
    enh_act  = get_active_enh_booster_info(data)
    lines    = [f'<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{_L(lang, "УСИЛИТЕЛИ И ЯДЫ", "BOOSTERS & POISONS")}</i></b>\n']
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        lines.append(
            f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{_L(lang, "Активен усилитель", "Active booster")}: ×{mult}</i></b>\n'
            f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b>\n'
        )
    else:
        lines.append(f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{_L(lang, "Нет активного усилителя.", "No active booster.")}</i></b>\n')
    if poison:
        left = _fmt_time_left(poison["ends_at"] - _now_ts(), lang)
        dmg  = _fmt_num(poison["damage"])
        _poison_names_en = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        pname = _poison_names_en.get(poison["name"], poison["name"]) if lang == "en" else poison["name"]
        dmg_label = "dmg" if lang == "en" else "урона"
        lines.append(
            f'{_pe("ok", "✅")} <b><i>{_L(lang, "Яд", "Poison")}: {pname} — {dmg} {dmg_label}</i></b>\n'
            f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b>'
        )
    else:
        lines.append(f'{_pe("cancel", "❌")} <b><i>{_L(lang, "Нет активного яда.", "No active poison.")}</i></b>')
    lines.append("</blockquote>")
    if not inv:
        lines.append(
            f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji>'
            f' <b><i>{_L(lang, "Инвентарь пуст. Открой Кейс усилителей!", "Inventory empty. Open an Enhancer case!")}</i></b></blockquote>'
        )
    else:
        lines.append(f'\n<blockquote><b><i>{_L(lang, "В инвентаре", "In inventory")} ({len(inv)}/{MAX_ENH_INVENTORY}):</i></b>')
        for i, item in enumerate(inv, 1):
            price = get_enh_sell_price(item)
            lines.append(f'\n<b><i>{i}. {_enh_item_name(item, lang)}</i></b>\n{_pe("coin", "💰")} <b><i>{_fmt_num(price)}</i></b>')
        lines.append('</blockquote>')
    return "".join(lines)


def enh_inventory_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    inv = data.get("enh_inventory", [])
    for item in inv[:MAX_ENH_INVENTORY]:
        e_key = "poison" if item["type"] == "poison" else "enh_boost"
        builder.row(_btn(_E[e_key], _enh_item_name_plain(item, lang), f'enh_info_{item["instance_id"]}'))
    builder.row(_back_btn("profile_boosters", _L(lang, "Инвентарь", "Inventory")))
    return builder.as_markup()


def enh_item_detail_text(data: dict, instance_id: str, lang: str = "ru") -> str:
    inv  = data.get("enh_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return _L(lang, "❌ Предмет не найден.", "❌ Item not found.")
    price = get_enh_sell_price(item)
    if item["type"] == "poison":
        poison_act = get_active_poison_info(data)
        warning    = ""
        if poison_act:
            left = _fmt_time_left(poison_act["ends_at"] - _now_ts(), lang)
            _poison_names_en = {
                "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
                "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
                "Яд Левиафана": "Leviathan Venom",
            }
            aname = _poison_names_en.get(poison_act["name"], poison_act["name"]) if lang == "en" else poison_act["name"]
            warning = (
                f'\n\n<blockquote>{_pe("warn", "⚠️")} <b><i>{_L(lang, "Уже активен", "Already active")}: {aname}</i></b>\n'
                f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b></blockquote>'
            )
        _poison_names_en2 = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        pname = _poison_names_en2.get(item["name"], item["name"]) if lang == "en" else item["name"]
        return (
            f'<blockquote><tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji>'
            f' <b><i>{pname}</i></b>\n'
            f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Длительность: 30 минут", "Duration: 30 minutes")}</i></b>\n'
            f'<b><i>{_L(lang, "Суммарный урон боссу", "Total boss damage")}: {_fmt_num(item["damage"])}</i></b></blockquote>\n'
            f'\n<blockquote><b><i>{_L(lang, "Яд действует автоматически — урон списывается равномерно каждую минуту.", "Poison works automatically — damage applied evenly each minute.")}</i></b>\n'
            f'<b><i>{_L(lang, "Работает на текущего активного босса.", "Works on the current active boss.")}</i></b></blockquote>\n'
            f'\n<blockquote>{_pe("coin", "💰")} <b><i>{_L(lang, "Цена продажи", "Sell price")}: {_fmt_num(price)}</i></b></blockquote>'
            f'{warning}'
        )
    # enh_boost
    mult     = _multiplier_label(item["multiplier"])
    dur      = _dur_label(item["dur_key"], lang)
    active   = data.get("active_enh_booster")
    warning  = ""
    if active and active.get("ends_at", 0) > _now_ts():
        left     = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        act_mult = _multiplier_label(active["multiplier"])
        act_dur  = _dur_label(active["dur_key"], lang)
        warning  = (
            f'\n\n<blockquote>{_pe("warn", "⚠️")} <b><i>{_L(lang, "Активен", "Active")}: {act_mult} {_L(lang, "на", "for")} {act_dur}</i></b>\n'
            f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b></blockquote>'
        )
    return (
        f'<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji>'
        f' <b><i>{_L(lang, "Усилитель урона", "Damage booster")} {mult}</i></b>\n'
        f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Длительность", "Duration")}: {dur}</i></b>\n'
        f'{_pe("mult", "🔢")} <b><i>{_L(lang, "Множитель", "Multiplier")}: {mult}</i></b></blockquote>\n'
        f'\n<blockquote><b><i>{_L(lang, f"Увеличивает весь урон по боссу в {mult} на {dur}.", f"Increases all boss damage by {mult} for {dur}.")}</i></b></blockquote>\n'
        f'\n<blockquote>{_pe("coin", "💰")} <b><i>{_L(lang, "Цена продажи", "Sell price")}: {_fmt_num(price)}</i></b></blockquote>'
        f'{warning}'
    )


def enh_item_detail_keyboard(item_type: str, instance_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if item_type == "poison":
        builder.row(_btn(_E["poison"], _L(lang, "Применить яд", "Apply poison"), f"enh_use_{instance_id}"))
    else:
        builder.row(_btn(_E["enh_boost"], _L(lang, "Активировать", "Activate"), f"enh_activate_{instance_id}"))
    builder.row(_btn(_E["sell"], _L(lang, "Продать", "Sell"), f"enh_sell_{instance_id}"))
    builder.row(_back_btn("inv_enh", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def enh_confirm_replace_text(data: dict, instance_id: str, replace_type: str, lang: str = "ru") -> str:
    inv  = data.get("enh_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return "❌ Ошибка." if lang == "ru" else "❌ Error."
    if replace_type == "poison":
        active = get_active_poison_info(data)
        if not active:
            return "❌ Ошибка." if lang == "ru" else "❌ Error."
        left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        _poison_names_en = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        aname = _poison_names_en.get(active["name"], active["name"]) if lang == "en" else active["name"]
        iname = _poison_names_en.get(item["name"], item["name"]) if lang == "en" else item["name"]
        return (
            f'<blockquote>{_pe("warn", "⚠️")} <b><i>{_L(lang, "Замена яда", "Replace poison")}</i></b>\n'
            f'<b><i>{_L(lang, "Сейчас активен", "Currently active")}: {aname}</i></b>\n'
            f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b></blockquote>\n'
            f'\n<blockquote><b><i>{_L(lang, "Заменить на", "Replace with")}: {iname}?</i></b>\n'
            f'{_pe("warn", "⚠️")} <b><i>{_L(lang, "Текущий яд будет потерян!", "Current poison will be lost!")}</i></b></blockquote>'
        )
    active = data.get("active_enh_booster")
    if not active:
        return "❌ Ошибка." if lang == "ru" else "❌ Error."
    left     = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
    act_mult = _multiplier_label(active["multiplier"])
    act_dur  = _dur_label(active["dur_key"], lang)
    new_mult = _multiplier_label(item["multiplier"])
    new_dur  = _dur_label(item["dur_key"], lang)
    return (
        f'<blockquote>{_pe("warn", "⚠️")} <b><i>{_L(lang, "Замена усилителя", "Replace booster")}</i></b>\n'
        f'<b><i>{_L(lang, "Сейчас активен", "Currently active")}: {act_mult} {_L(lang, "на", "for")} {act_dur}</i></b>\n'
        f'{_pe("timer", "⏱")} <b><i>{_L(lang, "Осталось", "Left")}: {left}</i></b></blockquote>\n'
        f'\n<blockquote><b><i>{_L(lang, "Заменить на", "Replace with")}: {new_mult} {_L(lang, "на", "for")} {new_dur}?</i></b>\n'
        f'{_pe("warn", "⚠️")} <b><i>{_L(lang, "Старый усилитель будет потерян!", "Old booster will be lost!")}</i></b></blockquote>'
    )


def enh_confirm_replace_keyboard(instance_id: str, replace_type: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if replace_type == "poison":
        yes_cb = f"enh_poison_replace_{instance_id}"
        no_cb  = f"enh_info_{instance_id}"
    else:
        yes_cb = f"enh_boost_replace_{instance_id}"
        no_cb  = f"enh_info_{instance_id}"
    builder.row(
        InlineKeyboardButton(text=_L(lang, "Да, заменить", "Yes, replace"), callback_data=yes_cb, icon_custom_emoji_id=_E["ok"]),
        InlineKeyboardButton(text=_L(lang, "Отмена", "Cancel"),             callback_data=no_cb,  icon_custom_emoji_id=_E["cancel"]),
    )
    return builder.as_markup()


# ============================================================
def cases_shop_text(data: dict = None, lang: str = "ru") -> str:
    total_opened = (data or {}).get("cases_total_opened", 0)
    total_spent  = (data or {}).get("cases_total_spent",  0)
    if lang == "en":
        return (
            f"<blockquote>{_pe('shop', '🛒')} <b><i>CASE SHOP</i></b>\n"
            f"<b><i>Open cases and get bonuses!</i></b></blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> <b><i>Your stats</i></b>\n'
            f"<b><i>Cases opened: {_fmt_num(total_opened)}</i></b>\n"
            f"{_pe('spent', '💸')} <b><i>Spent: {_fmt_num(total_spent)}</i></b> {_pe('coin', '💰')}</blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji> <b><i>Good luck! May something great drop</i></b><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji></blockquote>'
        )
    return (
        f"<blockquote>{_pe('shop', '🛒')} <b><i>МАГАЗИН КЕЙСОВ</i></b>\n"
        f"<b><i>Открывай кейсы и получай бонусы!</i></b></blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> <b><i>Твоя статистика</i></b>\n'
        f"<b><i>Открыто кейсов: {_fmt_num(total_opened)}</i></b>\n"
        f"{_pe('spent', '💸')} <b><i>Потрачено: {_fmt_num(total_spent)}</i></b> {_pe('coin', '💰')}</blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji> <b><i>Удачи тебе! Пусть выпадет что-то крутое</i></b><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji></blockquote>'
    )


def cases_shop_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _CASE_NAMES = {
        "common":   ("Ускорителей", "Booster"),
        "xp":       ("XP",          "XP"),
        "enhancer": ("Усилителей",  "Enhancer"),
    }
    for c in CASES.values():
        if c["type"] == "booster":
            e_key = "case"
        elif c["type"] == "xp":
            e_key = "xp_case"
        else:
            e_key = "enh_case"
        names = _CASE_NAMES.get(c["key"], (c["name"], c["name"]))
        cname = names[1] if lang == "en" else names[0]
        builder.row(_btn(_E[e_key], f'{cname} {"case" if lang == "en" else "кейс"}', f'case_info_{c["key"]}'))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Кейс Артефактов", "Artifact Case"),
        callback_data="artifact_case_info",
        icon_custom_emoji_id="5229011542011299168"
    ))
    builder.row(_back_btn("back_to_menu", _L(lang, "Назад в меню", "Back to menu")))
    return builder.as_markup()


def case_detail_text(data: dict, case_key: str, lang: str = "ru") -> str:
    case    = CASES[case_key]
    balance = data.get("balance", 0)
    can_buy = balance >= case["cost"]
    bal_str = f"{_fmt_num(balance)} {_pe('coin', '💰')}"
    if case["type"] == "booster":
        if lang == "en":
            loot_lines = (
                f"{_pe('boost', '⚡')} <b><i>Booster 1.4× — 30min to 24h</i></b>\n"
                f"{_pe('boost', '⚡')} <b><i>Booster 1.8× — 30min to 24h</i></b>\n"
                f"{_pe('boost', '⚡')} <b><i>Booster 2× — 30min to 24h</i></b>"
            )
        else:
            loot_lines = (
                f"{_pe('boost', '⚡')} <b><i>Ускоритель 1.4× — 30мин до 24ч</i></b>\n"
                f"{_pe('boost', '⚡')} <b><i>Ускоритель 1.8× — 30мин до 24ч</i></b>\n"
                f"{_pe('boost', '⚡')} <b><i>Ускоритель 2× — 30мин до 24ч</i></b>"
            )
    elif case["type"] == "enhancer":
        if lang == "en":
            loot_lines = (
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Damage booster 1.4× — 30min to 24h</i></b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Damage booster 1.8× — 30min to 24h</i></b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Damage booster 2× — 30min to 24h</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Viper Venom — 100 000 dmg (5%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Cobra Venom — 150 000 dmg (3%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Black Mamba Venom — 225 000 dmg (2%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Basilisk Venom — 350 000 dmg (1%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Leviathan Venom — 500 000 dmg (0.5%)</i></b>'
            )
        else:
            loot_lines = (
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Усилитель урона 1.4× — 30мин до 24ч</i></b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Усилитель урона 1.8× — 30мин до 24ч</i></b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Усилитель урона 2× — 30мин до 24ч</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Яд Гадюки — 100 000 урона (5%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Яд Кобры — 150 000 урона (3%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Яд Чёрной Мамбы — 225 000 урона (2%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Яд Василиска — 350 000 урона (1%)</i></b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>Яд Левиафана — 500 000 урона (0.5%)</i></b>'
            )
    else:
        if lang == "en":
            loot_lines = (
                f"{_pe('xp_instant', '✨')} <b><i>Instant XP: 100 / 225 / 750 / 2 000 / 5 000</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP booster ×1.4 — 30min to 24h</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP booster ×1.8 — 30min to 24h</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP booster ×2 — 30min to 24h</i></b>"
            )
        else:
            loot_lines = (
                f"{_pe('xp_instant', '✨')} <b><i>Моментальный опыт: 100 / 225 / 750 / 2 000 / 5 000 XP</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP-ускоритель ×1.4 — от 30 мин до 24 ч</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP-ускоритель ×1.8 — от 30 мин до 24 ч</i></b>\n"
                f"{_pe('xp_boost', '🔮')} <b><i>XP-ускоритель ×2 — от 30 мин до 24 ч</i></b>"
            )
    if case["type"] == "booster":
        e_key = "case"
    elif case["type"] == "enhancer":
        e_key = "enh_case"
    else:
        e_key = "xp_case"
    _CASE_NAMES_EN = {"common": "Booster", "xp": "XP", "enhancer": "Enhancer"}
    cname = _CASE_NAMES_EN.get(case["key"], case["name"]) if lang == "en" else case["name"]
    case_label = "case" if lang == "en" else "кейс"
    status = (
        f"{_pe('ok', '✅')} <b><i>{_L(lang, 'Хватает монет', 'Enough coins')}</i></b>"
        if can_buy else
        f"{_pe('cancel', '❌')} <b><i>{_L(lang, 'Недостаточно монет', 'Not enough coins')}</i></b>"
    )
    # Номера кейсов для команды открытия
    _CASE_NUM = {"common": 1, "xp": 2, "enhancer": 3}
    case_num = _CASE_NUM.get(case_key, 1)
    if lang == "en":
        cmd_hint = (
            f"\n\n<blockquote><i>"
            f"Quick open: <code>open #{case_num} 5</code> or <code>/open #{case_num} 5</code>"
            f"</i></blockquote>"
        )
    else:
        cmd_hint = (
            f"\n\n<blockquote><i>"
            f"Быстрое открытие: <code>открыть #{case_num} 5</code> или <code>/купить #{case_num} 5</code>"
            f"</i></blockquote>"
        )
    return (
        f"<blockquote>{_pe(e_key, '📦')} <b><i>{cname} {case_label}</i></b>\n"
        f"{_pe('coin', '💰')} <b><i>{_L(lang, 'Цена', 'Price')}:</i></b> <b><i>{_fmt_num(case['cost'])}</i></b>\n"
        f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}:</i></b> <b><i>{bal_str}</i></b></blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, 'Возможный лут', 'Possible loot')}:</i></b>\n{loot_lines}</blockquote>\n"
        f"\n<blockquote>{status}</blockquote>"
        f"{cmd_hint}"
    )


def case_detail_keyboard(case_key: str, can_buy: bool, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_buy:
        builder.row(_btn(_E["shop"], _L(lang, "Купить и открыть", "Buy and open"), f"case_open_{case_key}"))
    else:
        builder.row(_btn(_E["cancel"], _L(lang, "Недостаточно монет", "Not enough coins"), "noop"))
    builder.row(_back_btn("shop_cases", _L(lang, "Назад", "Back")))
    return builder.as_markup()


# ============================================================
#  UI — КЕЙС АРТЕФАКТОВ
# ============================================================

def artifact_case_detail_text(data: dict, lang: str = "ru") -> str:
    opened = data.get("artifact_cases_opened", 0)
    owned  = data.get("artifacts", [])

    _E_MINE   = "5201914481671682382"
    _E_DMG    = "5373173798633752502"
    _E_PETS   = "5208535779348864977"
    _E_BONUS  = "5438496463044752972"

    def _ae(a):
        eid = a.get("emoji_id", "")
        return f'<tg-emoji emoji-id="{eid}">💎</tg-emoji>' if eid else "💎"

    def _row(a, pct):
        eff_label = _get_effect_label(a["effect"], lang)
        aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
        return (
            f'{_ae(a)} <b><i>{aname}</i></b> — '
            f'<b><i><i>{a["multiplier"]}× {eff_label}</i></i></b> <b><i>({pct}%)</i></b>\n'
        )

    loot = "".join(_row(a, a["chance"]) for a in _ARTIFACT_POOL)

    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b><i>{_L(lang, "Кейс Артефактов", "Artifact Case")}</i></b>\n'
        f'<tg-emoji emoji-id="5262643974912355126">⭐</tg-emoji> <b><i>{_L(lang, "Цена", "Price")}: {ARTIFACT_CASE_COST_STARS} Telegram Stars</i></b></blockquote>\n'
        f'\n<blockquote><b><i>{_L(lang, "Возможный лут", "Possible loot")}:</i></b>\n{loot}</blockquote>\n'
        f'\n<blockquote>'
        f'<tg-emoji emoji-id="{_E_BONUS}">✨</tg-emoji> <b><i>{_L(lang, "Артефакты дают постоянный бонус навсегда!", "Artifacts give a permanent bonus forever!")}</i></b>\n'
        f'{_pe("warn", "⚠️")} <b><i>{_L(lang, "Дубликат — компенсация монетами.", "Duplicate — compensated with coins.")}</i></b></blockquote>\n'
        f'\n<blockquote><tg-emoji emoji-id="5359664288241829619">📦</tg-emoji> <b><i>{_L(lang, "Открыто кейсов", "Cases opened")}: {opened}</i></b>  |  '
        f'{_pe("stats", "💎")} <b><i>{_L(lang, "Коллекция", "Collection")}: {len(owned)}/10</i></b></blockquote>'
    )


def artifact_case_keyboard(invoice_url: str = None, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if invoice_url:
        builder.row(InlineKeyboardButton(
            text=f"{'Open' if lang == 'en' else 'Открыть'} {ARTIFACT_CASE_COST_STARS} ⭐",
            url=invoice_url,
            icon_custom_emoji_id="5999336376342940892",
            style="success"
        ))
    else:
        builder.row(_btn(_E["stats"], f"{'Open' if lang == 'en' else 'Открыть'} {ARTIFACT_CASE_COST_STARS} ⭐", "artifact_case_buy"))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Мои звёзды", "My stars"),
        url="tg://stars/",
        icon_custom_emoji_id="5348570868752595928"
    ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Моя коллекция", "My collection"),
        callback_data="artifact_collection",
        icon_custom_emoji_id="5222113468051629260"
    ))
    builder.row(_back_btn("shop_cases", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def artifact_collection_text(data: dict, lang: str = "ru") -> str:
    owned = data.get("artifacts", [])
    if not owned:
        return (
            f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b><i>{_L(lang, "МОЯ КОЛЛЕКЦИЯ АРТЕФАКТОВ", "MY ARTIFACT COLLECTION")}</i></b>\n'
            f'{_pe("cancel", "❌")} <b><i>{_L(lang, "У тебя пока нет артефактов.", "You have no artifacts yet.")}</i></b>\n'
            f'{_L(lang, "Открой Кейс Артефактов, чтобы получить первый!", "Open an Artifact Case to get your first one!")}</blockquote>'
        )

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    _E_MINE  = "5201914481671682382"
    _E_DMG   = "5373173798633752502"
    _E_PETS  = "5208535779348864977"
    _E_BONUS = "5438496463044752972"

    artifact_lines = []
    for entry in owned:
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a:
            eid  = a.get("emoji_id", "")
            ae   = f'<tg-emoji emoji-id="{eid}">💎</tg-emoji>' if eid else "💎"
            effect_label = _get_effect_label(a["effect"], lang)
            aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
            artifact_lines.append(
                f'{ae} <b><i>{aname}</i></b> — '
                f'<b><i><i>{a["multiplier"]}× {effect_label}</i></i></b>\n'
            )

    mine_icon  = f'<tg-emoji emoji-id="{_E_MINE}">⛏</tg-emoji>'
    dmg_icon   = f'<tg-emoji emoji-id="{_E_DMG}">⚔️</tg-emoji>'
    pets_icon  = f'<tg-emoji emoji-id="{_E_PETS}">🐾</tg-emoji>'
    bonus_icon = f'<tg-emoji emoji-id="{_E_BONUS}">✨</tg-emoji>'

    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> '
        f'<b><i>{_L(lang, "МОЯ КОЛЛЕКЦИЯ", "MY COLLECTION")} ({len(owned)}/10)</i></b></blockquote>\n'
        f'\n<blockquote>'
        f'{bonus_icon} <b><i>{_L(lang, "Итоговые бонусы", "Total bonuses")}:</i></b>\n'
        f'{mine_icon} <b><i>{_L(lang, "Руда", "Ore")}: ×{mine_mult}</i></b>\n'
        f'{dmg_icon} <b><i>{_L(lang, "Босс", "Boss")}: ×{damage_mult}</i></b>\n'
        f'{pets_icon} <b><i>{_L(lang, "Питомцы", "Pets")}: ×{pets_mult}</i></b>'
        f'</blockquote>\n'
        f'\n<blockquote><b><i>{_L(lang, "Артефакты", "Artifacts")}:</i></b>\n' + "".join(artifact_lines) + '</blockquote>'
    )


def artifact_collection_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_back_btn("artifact_case_info", _L(lang, "К кейсу", "To case")))
    return builder.as_markup()


def inventory_main_text(data: dict, lang: str = "ru") -> str:
    b_inv    = data.get("boosters_inventory", [])
    xp_inv   = data.get("xp_inventory", [])
    enh_inv  = data.get("enh_inventory", [])
    active   = get_active_booster_info(data)
    xp_act   = get_active_xp_booster_info(data)
    poison   = get_active_poison_info(data)
    enh_act  = get_active_enh_booster_info(data)
    b_active_str   = ""
    xp_active_str  = ""
    enh_active_str = ""
    if active:
        left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(active["multiplier"])
        b_active_str = f"\n{_pe('boost', '⚡')} <b><i>{'Active' if lang == 'en' else 'Активен'}: {mult} — ⏱ {left}</i></b>"
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        xp_active_str = f"\n{_pe('xp_boost', '🔮')} <b><i>{'Active' if lang == 'en' else 'Активен'}: ×{mult} XP — ⏱ {left}</i></b>"
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        lbl = "Booster" if lang == "en" else "Усилитель"
        enh_active_str += f'\n<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{lbl}: ×{mult} — ⏱ {left}</i></b>'
    if poison:
        left = _fmt_time_left(poison["ends_at"] - _now_ts(), lang)
        _poison_names_en = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        pname = _poison_names_en.get(poison["name"], poison["name"]) if lang == "en" else poison["name"]
        enh_active_str += f'\n<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>{"Poison" if lang == "en" else "Яд"}: {pname} — ⏱ {left}</i></b>'

    if lang == "en":
        return (
            f"<blockquote>{_pe('inv', '🎒')} <b><i>INVENTORY</i></b></blockquote>\n"
            f"\n<blockquote>{_pe('boost', '⚡')} <b><i>Pickaxe boosters</i></b>  <b><i>[{len(b_inv)}/{MAX_INVENTORY}]</i></b>{b_active_str}</blockquote>\n"
            f"\n<blockquote>{_pe('xp_boost', '🔮')} <b><i>XP items</i></b>  <b><i>[{len(xp_inv)}/{MAX_XP_INVENTORY}]</i></b>{xp_active_str}</blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Damage boosters & poisons</i></b>  <b><i>[{len(enh_inv)}/{MAX_ENH_INVENTORY}]</i></b>{enh_active_str}</blockquote>'
        )
    return (
        f"<blockquote>{_pe('inv', '🎒')} <b><i>ИНВЕНТАРЬ</i></b></blockquote>\n"
        f"\n<blockquote>{_pe('boost', '⚡')} <b><i>Ускорители кирки</i></b>  <b><i>[{len(b_inv)}/{MAX_INVENTORY}]</i></b>{b_active_str}</blockquote>\n"
        f"\n<blockquote>{_pe('xp_boost', '🔮')} <b><i>XP-предметы</i></b>  <b><i>[{len(xp_inv)}/{MAX_XP_INVENTORY}]</i></b>{xp_active_str}</blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>Усилители и яды</i></b>  <b><i>[{len(enh_inv)}/{MAX_ENH_INVENTORY}]</i></b>{enh_active_str}</blockquote>'
    )


def inventory_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if lang == "en":
        builder.row(_btn(_E["boost"],    "Pickaxe boosters", "inv_boosters"))
        builder.row(_btn(_E["xp_boost"], "XP items",         "inv_xp"))
        builder.row(_btn(_E["enh_case"], "Boosters & poisons","inv_enh"))
        builder.row(_back_btn("profile", "Back to profile"))
    else:
        builder.row(_btn(_E["boost"],    "Ускорители кирки", "inv_boosters"))
        builder.row(_btn(_E["xp_boost"], "XP-предметы",      "inv_xp"))
        builder.row(_btn(_E["enh_case"], "Усилители и яды",  "inv_enh"))
        builder.row(_back_btn("profile", "Назад в профиль"))
    return builder.as_markup()


def boosters_inventory_text(data: dict, lang: str = "ru") -> str:
    inv    = data.get("boosters_inventory", [])
    active = get_active_booster_info(data)
    if lang == "en":
        lines = [f"<blockquote>{_pe('boost', '⚡')} <b><i>PICKAXE BOOSTERS</i></b>\n"]
        if active:
            left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
            mult = _multiplier_label(active["multiplier"])
            dur  = _dur_label(active["dur_key"], lang)
            lines.append(f"{_pe('ok', '✅')} <b><i>Active: {mult} for {dur}</i></b>\n{_pe('timer', '⏱')} <b><i>Left: {left}</i></b>")
        else:
            lines.append(f"{_pe('cancel', '❌')} <b><i>No active booster.</i></b>")
        lines.append("</blockquote>")
        if not inv:
            lines.append(f"\n<blockquote>{_pe('case', '📦')} <b><i>Inventory empty. Open a Booster case!</i></b></blockquote>")
        else:
            inv_lines = [f"\n<blockquote><b><i>In inventory ({len(inv)}/{MAX_INVENTORY}):</i></b>"]
            for i, item in enumerate(inv, 1):
                price = get_sell_price(item)
                inv_lines.append(f"\n<b><i>{i}. {_booster_name(item, lang)}</i></b>\n{_pe('coin', '💰')} <b><i>{_fmt_num(price)}</i></b>")
            inv_lines.append("</blockquote>")
            lines.extend(inv_lines)
    else:
        lines = [f"<blockquote>{_pe('boost', '⚡')} <b><i>УСКОРИТЕЛИ КИРКИ</i></b>\n"]
        if active:
            left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
            mult = _multiplier_label(active["multiplier"])
            dur  = _dur_label(active["dur_key"], lang)
            lines.append(f"{_pe('ok', '✅')} <b><i>Активен: {mult} на {dur}</i></b>\n{_pe('timer', '⏱')} <b><i>Осталось: {left}</i></b>")
        else:
            lines.append(f"{_pe('cancel', '❌')} <b><i>Нет активного ускорителя.</i></b>")
        lines.append("</blockquote>")
        if not inv:
            lines.append(f"\n<blockquote>{_pe('case', '📦')} <b><i>Инвентарь пуст. Открой Кейс ускорителей!</i></b></blockquote>")
        else:
            inv_lines = [f"\n<blockquote><b><i>В инвентаре ({len(inv)}/{MAX_INVENTORY}):</i></b>"]
            for i, item in enumerate(inv, 1):
                price = get_sell_price(item)
                inv_lines.append(f"\n<b><i>{i}. {_booster_name(item, lang)}</i></b>\n{_pe('coin', '💰')} <b><i>{_fmt_num(price)}</i></b>")
            inv_lines.append("</blockquote>")
            lines.extend(inv_lines)
    return "".join(lines)


def boosters_inventory_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    inv = data.get("boosters_inventory", [])
    for item in inv[:MAX_INVENTORY]:
        builder.row(_btn(_E["boost"], _booster_name(item, lang), f'boost_info_{item["instance_id"]}'))
    builder.row(_back_btn("profile_boosters", "Inventory" if lang == "en" else "Инвентарь"))
    return builder.as_markup()


def booster_detail_text(data: dict, instance_id: str, lang: str = "ru") -> str:
    inv  = data.get("boosters_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return _L(lang, "❌ Ускоритель не найден.", "❌ Booster not found.")
    mult   = _multiplier_label(item["multiplier"])
    dur    = _dur_label(item["dur_key"], lang)
    price  = get_sell_price(item)
    active = get_active_booster_info(data)
    warning = ""
    if active:
        left     = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        act_mult = _multiplier_label(active["multiplier"])
        act_dur  = _dur_label(active["dur_key"], lang)
        warning  = (
            f"\n\n<blockquote>{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Активен', 'Active')}: {act_mult} {_L(lang, 'на', 'for')} {act_dur}</i></b>\n"
            f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Осталось', 'Left')}: {left}</i></b></blockquote>"
        )
    return (
        f"<blockquote>{_pe('boost', '⚡')} <b><i>{_booster_name(item, lang)}</i></b>\n"
        f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Длительность', 'Duration')}: {dur}</i></b>\n"
        f"{_pe('mult', '🔢')} <b><i>{_L(lang, 'Множитель', 'Multiplier')}: {mult}</i></b></blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, 'Эффект (все показатели кирки):', 'Effect (all pickaxe stats):')} </i></b>\n"
        f"<b><i>• {_L(lang, 'Ударов за кампанию', 'Hits per campaign')}: ×{mult}</i></b>\n"
        f"<b><i>• {_L(lang, 'Монет в час', 'Coins per hour')}: ×{mult}</i></b>\n"
        f"<b><i>• {_L(lang, 'Скорость добычи', 'Mining speed')}: ×{mult}</i></b></blockquote>\n"
        f"\n<blockquote>{_pe('coin', '💰')} <b><i>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</i></b></blockquote>"
        f"{warning}"
    )


def booster_detail_keyboard(data: dict, instance_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_btn(_E["activate"], _L(lang, "Активировать", "Activate"), f"boost_activate_{instance_id}"))
    builder.row(_btn(_E["sell"],     _L(lang, "Продать", "Sell"),          f"boost_sell_{instance_id}"))
    builder.row(_back_btn("inv_boosters", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def booster_confirm_replace_text(data: dict, instance_id: str, lang: str = "ru") -> str:
    inv    = data.get("boosters_inventory", [])
    item   = next((x for x in inv if x["instance_id"] == instance_id), None)
    active = get_active_booster_info(data)
    if not item or not active:
        return "❌ Ошибка." if lang == "ru" else "❌ Error."
    left     = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
    act_mult = _multiplier_label(active["multiplier"])
    act_dur  = _dur_label(active["dur_key"], lang)
    new_mult = _multiplier_label(item["multiplier"])
    new_dur  = _dur_label(item["dur_key"], lang)
    return (
        f"<blockquote>{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Замена ускорителя', 'Replace booster')}</i></b>\n"
        f"<b><i>{_L(lang, 'Сейчас активен', 'Currently active')}: {act_mult} {_L(lang, 'на', 'for')} {act_dur}</i></b>\n"
        f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Осталось', 'Left')}: {left}</i></b></blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, 'Заменить на', 'Replace with')}: {new_mult} {_L(lang, 'на', 'for')} {new_dur}?</i></b>\n"
        f"{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Старый ускоритель будет потерян!', 'Old booster will be lost!')}</i></b></blockquote>"
    )


def booster_confirm_replace_keyboard(instance_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_L(lang, "Да, заменить", "Yes, replace"), callback_data=f"boost_replace_{instance_id}", icon_custom_emoji_id=_E["ok"]),
        InlineKeyboardButton(text=_L(lang, "Отмена", "Cancel"),             callback_data=f"boost_info_{instance_id}",    icon_custom_emoji_id=_E["cancel"]),
    )
    return builder.as_markup()


def xp_inventory_text(data: dict, lang: str = "ru") -> str:
    inv    = data.setdefault("xp_inventory", [])
    xp_act = get_active_xp_booster_info(data)
    lines = [f"<blockquote>{_pe('xp_boost', '🔮')} <b><i>{_L(lang, 'XP-ПРЕДМЕТЫ', 'XP ITEMS')}</i></b>\n"]
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        dur  = _dur_label(xp_act["dur_key"], lang)
        lines.append(
            f"{_pe('ok', '✅')} <b><i>{_L(lang, 'Активен XP-ускоритель', 'Active XP booster')}: ×{mult} {_L(lang, 'на', 'for')} {dur}</i></b>\n"
            f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Осталось', 'Left')}: {left}</i></b>"
        )
    else:
        lines.append(f"{_pe('cancel', '❌')} <b><i>{_L(lang, 'Нет активного XP-ускорителя.', 'No active XP booster.')}</i></b>")
    lines.append("</blockquote>")
    if not inv:
        lines.append(f"\n<blockquote>{_pe('xp_case', '🔮')} <b><i>{_L(lang, 'XP-инвентарь пуст. Открой XP-кейс!', 'XP inventory empty. Open an XP case!')}</i></b></blockquote>")
    else:
        inv_lines = [f"\n<blockquote><b><i>{_L(lang, 'В инвентаре', 'In inventory')} ({len(inv)}/{MAX_XP_INVENTORY}):</i></b>"]
        for i, item in enumerate(inv, 1):
            price = get_xp_sell_price(item)
            inv_lines.append(f"\n<b><i>{i}. {_xp_item_name(item, lang)}</i></b>\n{_pe('coin', '💰')} <b><i>{_fmt_num(price)}</i></b>")
        inv_lines.append("</blockquote>")
        lines.extend(inv_lines)
    return "".join(lines)


def xp_inventory_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    inv = data.get("xp_inventory", [])
    for item in inv[:MAX_XP_INVENTORY]:
        builder.row(_btn(_E["xp_boost"], _xp_item_name_plain(item, lang), f'xp_info_{item["instance_id"]}'))
    builder.row(_back_btn("profile_boosters", _L(lang, "Инвентарь", "Inventory")))
    return builder.as_markup()


def xp_item_detail_text(data: dict, instance_id: str, lang: str = "ru") -> str:
    inv  = data.get("xp_inventory", [])
    item = next((x for x in inv if x["instance_id"] == instance_id), None)
    if not item:
        return _L(lang, "❌ Предмет не найден.", "❌ Item not found.")
    price  = get_xp_sell_price(item)
    xp_act = get_active_xp_booster_info(data)
    if item["type"] == "xp_instant":
        return (
            f"<blockquote>{_pe('xp_instant', '✨')} <b><i>{_L(lang, 'Моментальный опыт', 'Instant XP')}</i></b>\n"
            f"{_pe('xp_instant', '✨')} <b><i>{_L(lang, 'Опыт', 'XP')}: +{_fmt_num(item['xp'])} XP</i></b></blockquote>\n"
            f"\n<blockquote><b><i>{_L(lang, 'Применить — сразу получишь опыт.', 'Apply — you get XP immediately.')}</i></b>\n"
            f"<b><i>{_L(lang, 'Учитывает активный XP-ускоритель!', 'Counts active XP booster!')}</i></b></blockquote>\n"
            f"\n<blockquote>{_pe('coin', '💰')} <b><i>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</i></b></blockquote>"
        )
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    warning = ""
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        act_mult = _multiplier_label(xp_act["multiplier"])
        act_dur  = _dur_label(xp_act["dur_key"], lang)
        warning  = (
            f"\n\n<blockquote>{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Активен', 'Active')}: ×{act_mult} {_L(lang, 'на', 'for')} {act_dur}</i></b>\n"
            f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Осталось', 'Left')}: {left}</i></b></blockquote>"
        )
    return (
        f"<blockquote>{_pe('xp_boost', '🔮')} <b><i>{_L(lang, 'XP-ускоритель', 'XP booster')} {mult}</i></b>\n"
        f"{_pe('mult', '🔢')} <b><i>{_L(lang, 'Множитель', 'Multiplier')}: ×{mult}</i></b>\n"
        f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Длительность', 'Duration')}: {dur}</i></b></blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, f'Умножает весь получаемый опыт на {mult} на {dur}.', f'Multiplies all XP gained by {mult} for {dur}.')}</i></b></blockquote>\n"
        f"\n<blockquote>{_pe('coin', '💰')} <b><i>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</i></b></blockquote>"
        f"{warning}"
    )


def xp_item_detail_keyboard(instance_id: str, is_boost: bool, lang: str = "ru") -> InlineKeyboardMarkup:
    builder  = InlineKeyboardBuilder()
    label    = _L(lang, "Активировать", "Activate") if is_boost else _L(lang, "Применить", "Apply")
    e_key    = "xp_boost" if is_boost else "xp_instant"
    builder.row(_btn(_E[e_key],  label,                      f"xp_use_{instance_id}"))
    builder.row(_btn(_E["sell"], _L(lang, "Продать", "Sell"), f"xp_sell_{instance_id}"))
    builder.row(_back_btn("inv_xp", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def xp_confirm_replace_text(data: dict, instance_id: str, lang: str = "ru") -> str:
    inv    = data.get("xp_inventory", [])
    item   = next((x for x in inv if x["instance_id"] == instance_id), None)
    xp_act = get_active_xp_booster_info(data)
    if not item or not xp_act:
        return "❌ Ошибка." if lang == "ru" else "❌ Error."
    left     = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
    act_mult = _multiplier_label(xp_act["multiplier"])
    act_dur  = _dur_label(xp_act["dur_key"], lang)
    new_mult = _multiplier_label(item["multiplier"])
    new_dur  = _dur_label(item["dur_key"], lang)
    return (
        f"<blockquote>{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Замена XP-ускорителя', 'Replace XP booster')}</i></b>\n"
        f"<b><i>{_L(lang, 'Сейчас активен', 'Currently active')}: ×{act_mult} {_L(lang, 'на', 'for')} {act_dur}</i></b>\n"
        f"{_pe('timer', '⏱')} <b><i>{_L(lang, 'Осталось', 'Left')}: {left}</i></b></blockquote>\n"
        f"\n<blockquote><b><i>{_L(lang, 'Заменить на', 'Replace with')}: ×{new_mult} {_L(lang, 'на', 'for')} {new_dur}?</i></b>\n"
        f"{_pe('warn', '⚠️')} <b><i>{_L(lang, 'Старый XP-ускоритель будет потерян!', 'Old XP booster will be lost!')}</i></b></blockquote>"
    )


def xp_confirm_replace_keyboard(instance_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_L(lang, "Да, заменить", "Yes, replace"), callback_data=f"xp_replace_{instance_id}",  icon_custom_emoji_id=_E["ok"]),
        InlineKeyboardButton(text=_L(lang, "Отмена", "Cancel"),             callback_data=f"xp_info_{instance_id}",     icon_custom_emoji_id=_E["cancel"]),
    )
    return builder.as_markup()


# ============================================================
#  ЕДИНЫЙ ИНВЕНТАРЬ — СТАКИНГ И ИСПОЛЬЗОВАНИЕ ПО ID
#  Все три инвентаря (boosters, xp, enh) объединены в одно
#  представление. Одинаковые предметы складываются в стопки.
#  Каждой стопке присваивается slot_id (#1, #2, ...).
# ============================================================

def _get_or_assign_slot_ids(data: dict) -> dict:
    """
    Возвращает dict: key -> slot_id (int).
    Если slot_id для какого-то key ещё нет — назначает новый.
    Slot_ids хранятся в data['inv_slot_ids'].
    """
    slot_map: dict = data.setdefault("inv_slot_ids", {})
    used = set(slot_map.values())

    # Собираем все ключи из всех трёх инвентарей
    all_keys = set()
    for item in data.get("boosters_inventory", []):
        all_keys.add(item["key"])
    for item in data.get("xp_inventory", []):
        all_keys.add(item["key"])
    for item in data.get("enh_inventory", []):
        all_keys.add(item["key"])

    # Назначаем slot_id новым ключам
    counter = 1
    for key in sorted(all_keys):
        if key not in slot_map:
            while counter in used:
                counter += 1
            slot_map[key] = counter
            used.add(counter)
            counter += 1

    # Убираем slot_ids для ключей которых больше нет
    orphan_keys = [k for k in list(slot_map.keys()) if k not in all_keys]
    for k in orphan_keys:
        del slot_map[k]

    return slot_map


def get_unified_inventory(data: dict) -> list:
    """
    Возвращает список стопок:
    {
      "slot_id": int,
      "key": str,
      "type": str,         # boost / xp_boost / xp_instant / enh_boost / poison
      "count": int,
      "display": str,      # HTML-название
      "display_plain": str,# без HTML
      "item_sample": dict, # один пример предмета (для отображения характеристик)
    }
    Сортировка: по типу, потом по slot_id.
    """
    slot_map = _get_or_assign_slot_ids(data)

    stacks: dict = {}  # key -> {"count": int, "items": list, "type": str}

    for item in data.get("boosters_inventory", []):
        k = item["key"]
        if k not in stacks:
            stacks[k] = {"count": 0, "item_sample": item, "type": "boost"}
        stacks[k]["count"] += 1

    for item in data.get("xp_inventory", []):
        k = item["key"]
        if k not in stacks:
            stacks[k] = {"count": 0, "item_sample": item, "type": item.get("type", "xp_boost")}
        stacks[k]["count"] += 1

    for item in data.get("enh_inventory", []):
        k = item["key"]
        if k not in stacks:
            stacks[k] = {"count": 0, "item_sample": item, "type": item.get("type", "enh_boost")}
        stacks[k]["count"] += 1

    result = []
    for key, stack in stacks.items():
        sid = slot_map.get(key, 0)
        sample = stack["item_sample"]
        itype  = stack["type"]
        if itype == "boost":
            disp       = f"{_pe('boost', '⚡')} {_booster_name(sample)}"
            disp_plain = _booster_name(sample)
        elif itype in ("xp_boost", "xp_instant"):
            disp       = _xp_item_name(sample)
            disp_plain = _xp_item_name_plain(sample)
        else:
            disp       = _enh_item_name(sample)
            disp_plain = _enh_item_name_plain(sample)
        result.append({
            "slot_id":      sid,
            "key":          key,
            "type":         itype,
            "count":        stack["count"],
            "display":      disp,
            "display_plain": disp_plain,
            "item_sample":  sample,
        })

    # Сортируем: яды отдельно в конце, остальное по slot_id
    TYPE_ORDER = {"boost": 0, "xp_instant": 1, "xp_boost": 2, "enh_boost": 3, "poison": 4}
    result.sort(key=lambda x: (TYPE_ORDER.get(x["type"], 9), x["slot_id"]))
    return result


def unified_inventory_text(data: dict, lang: str = "ru") -> str:
    """Единый экран инвентаря со стакингом и slot_id."""
    stacks = get_unified_inventory(data)
    active   = get_active_booster_info(data)
    xp_act   = get_active_xp_booster_info(data)
    enh_act  = get_active_enh_booster_info(data)
    poison   = get_active_poison_info(data)

    lines = [f"<blockquote>{_pe('inv', '🎒')} <b><i>{'INVENTORY' if lang == 'en' else 'ИНВЕНТАРЬ'}</i></b></blockquote>\n"]

    # Активные бусты
    active_lines = []
    if active:
        left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(active["multiplier"])
        active_lines.append(f"{_pe('boost','⚡')} <b><i>{'Pickaxe' if lang=='en' else 'Кирка'}: {mult} — ⏱ {left}</i></b>")
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        active_lines.append(f"{_pe('xp_boost','🔮')} <b><i>XP: ×{mult} — ⏱ {left}</i></b>")
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        active_lines.append(f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{"Damage" if lang=="en" else "Урон"}: ×{mult} — ⏱ {left}</i></b>')
    if poison:
        left = _fmt_time_left(poison["ends_at"] - _now_ts(), lang)
        _pn_en = {"Яд Гадюки":"Viper","Яд Кобры":"Cobra","Яд Чёрной Мамбы":"Black Mamba","Яд Василиска":"Basilisk","Яд Левиафана":"Leviathan"}
        pname = _pn_en.get(poison["name"], poison["name"]) if lang == "en" else poison["name"]
        active_lines.append(f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>{"Poison" if lang=="en" else "Яд"}: {pname} — ⏱ {left}</i></b>')

    if active_lines:
        lbl = "Active" if lang == "en" else "Активно"
        lines.append(f"\n<blockquote>{_pe('ok','✅')} <b><i>{lbl}:</i></b>\n" + "\n".join(active_lines) + "</blockquote>\n")

    if not stacks:
        lbl = "Inventory is empty. Open cases!" if lang == "en" else "Инвентарь пуст. Открой кейсы!"
        lines.append(f"\n<blockquote>{_pe('case','📦')} <b><i>{lbl}</i></b></blockquote>")
    else:
        total = sum(s["count"] for s in stacks)
        lbl_inv = "In inventory" if lang == "en" else "В инвентаре"
        lines.append(f"\n<blockquote expandable><b><i>{lbl_inv} ({total} шт.):</i></b>\n")
        for s in stacks:
            cnt_str = f" <i>({s['count']} шт.)</i>" if s["count"] > 1 else ""
            lines.append(f"<b><i>#{s['slot_id']}</i></b> <i>{s['display']}</i>{cnt_str}\n")
        lines.append("</blockquote>")

    lbl_hint = (
        "\n<blockquote><i>"
        "Use: <code>use #N</code> or <code>-use #N</code>\n"
        "Cancel: <code>/stop #N</code>\n"
        "Sell: <code>/sell #N</code> or <code>/sell #N 5</code>\n"
        "Transfer: <code>отп #N</code> or <code>отп #N 3 @username</code>\n"
        "Open cases: <code>open #1 5</code> or <code>/open #2 10</code>"
        "</i></blockquote>"
        if lang == "en" else
        "\n<blockquote><i>"
        "Использовать: <code>исп #N</code> или <code>-use #N</code>\n"
        "Отменить: <code>/стоп #N</code>\n"
        "Продать: <code>/sell #N</code> или <code>/sell #N 5</code>\n"
        "Передать: <code>отп #N</code> или <code>отп #N 3 @username</code>\n"
        "Открыть кейсы: <code>открыть #1 5</code> или <code>/купить #2 10</code>"
        "</i></blockquote>"
    )
    lines.append(lbl_hint)
    return "".join(lines)


def use_item_by_slot_id(data: dict, slot_id: int, lang: str = "ru") -> tuple:
    """
    Активирует один предмет из стопки по slot_id.
    Если уже активен бустер того же типа — возвращает ошибку с подсказкой.
    Возвращает (ok: bool, msg: str).
    """
    slot_map = _get_or_assign_slot_ids(data)
    key = next((k for k, sid in slot_map.items() if sid == slot_id), None)
    if not key:
        return False, f"❌ {'Slot #' if lang=='en' else 'Слот #'}{slot_id} {'not found.' if lang=='en' else 'не найден.'}"

    # Ищем один экземпляр в нужном инвентаре
    for inv_key in ("boosters_inventory", "xp_inventory", "enh_inventory"):
        inv = data.get(inv_key, [])
        item = next((x for x in inv if x["key"] == key), None)
        if item:
            itype = item.get("type") or ("boost" if inv_key == "boosters_inventory" else "xp_boost")
            instance_id = item["instance_id"]
            if inv_key == "boosters_inventory":
                # Проверяем активный
                active = get_active_booster_info(data)
                if active:
                    left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
                    mult = _multiplier_label(active["multiplier"])
                    return False, (
                        f"❌ <b><i>{'Already active' if lang=='en' else 'Уже активен'}: {mult} ⏱ {left}</i></b>\n"
                        f"{'Cancel with' if lang=='en' else 'Отменить через'} <code>{'stop' if lang=='en' else 'стоп'} #N</code>"
                    )
                return activate_booster(data, instance_id, force=False, lang=lang)
            elif inv_key == "xp_inventory":
                if itype == "xp_boost":
                    xp_act = get_active_xp_booster_info(data)
                    if xp_act:
                        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
                        mult = _multiplier_label(xp_act["multiplier"])
                        return False, (
                            f"❌ <b><i>{'XP booster already active' if lang=='en' else 'XP-ускоритель уже активен'}: ×{mult} ⏱ {left}</i></b>\n"
                            f"{'Cancel with' if lang=='en' else 'Отменить через'} <code>{'stop' if lang=='en' else 'стоп'} #N</code>"
                        )
                return use_xp_item(data, instance_id, force=False, lang=lang)
            else:
                if itype == "enh_boost":
                    enh_act = get_active_enh_booster_info(data)
                    if enh_act:
                        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
                        mult = _multiplier_label(enh_act["multiplier"])
                        return False, (
                            f"❌ <b><i>{'Damage booster already active' if lang=='en' else 'Усилитель урона уже активен'}: ×{mult} ⏱ {left}</i></b>\n"
                            f"{'Cancel with' if lang=='en' else 'Отменить через'} <code>{'stop' if lang=='en' else 'стоп'} #N</code>"
                        )
                    return activate_enh_boost(data, instance_id, force=False, lang=lang)
                elif itype == "poison":
                    poison_act = get_active_poison_info(data)
                    if poison_act:
                        left = _fmt_time_left(poison_act["ends_at"] - _now_ts(), lang)
                        return False, (
                            f"❌ <b><i>{'Poison already active' if lang=='en' else 'Яд уже активен'} ⏱ {left}</i></b>\n"
                            f"{'Cancel with' if lang=='en' else 'Отменить через'} <code>{'stop' if lang=='en' else 'стоп'} #N</code>"
                        )
                    return use_poison(data, instance_id, force=False, lang=lang)

    return False, f"❌ {'Item not found.' if lang=='en' else 'Предмет не найден.'}"


def cancel_active_by_type(data: dict, boost_type: str, lang: str = "ru") -> tuple:
    """
    Отменяет активный буст указанного типа.
    boost_type: 'boost' | 'xp' | 'enh' | 'poison'
    Возвращает (ok, msg).
    """
    if boost_type == "boost":
        active = get_active_booster_info(data)
        if not active:
            return False, "❌ " + ("No active pickaxe booster." if lang=="en" else "Нет активного ускорителя кирки.")
        data["active_booster"] = None
        mult = _multiplier_label(active["multiplier"])
        return True, f"{'Pickaxe booster' if lang=='en' else 'Ускоритель кирки'} {mult} {'cancelled.' if lang=='en' else 'отменён.'}"
    if boost_type == "xp":
        active = get_active_xp_booster_info(data)
        if not active:
            return False, "❌ " + ("No active XP booster." if lang=="en" else "Нет активного XP-ускорителя.")
        data["active_xp_booster"] = None
        mult = _multiplier_label(active["multiplier"])
        return True, f"XP-{'booster' if lang=='en' else 'ускоритель'} ×{mult} {'cancelled.' if lang=='en' else 'отменён.'}"
    if boost_type == "enh":
        active = get_active_enh_booster_info(data)
        if not active:
            return False, "❌ " + ("No active damage booster." if lang=="en" else "Нет активного усилителя урона.")
        data["active_enh_booster"] = None
        mult = _multiplier_label(active["multiplier"])
        return True, f"{'Damage booster' if lang=='en' else 'Усилитель урона'} ×{mult} {'cancelled.' if lang=='en' else 'отменён.'}"
    if boost_type == "poison":
        active = get_active_poison_info(data)
        if not active:
            return False, "❌ " + ("No active poison." if lang=="en" else "Нет активного яда.")
        data["active_poison"] = None
        _pn_en = {"Яд Гадюки":"Viper","Яд Кобры":"Cobra","Яд Чёрной Мамбы":"Black Mamba","Яд Василиска":"Basilisk","Яд Левиафана":"Leviathan"}
        pname = _pn_en.get(active["name"], active["name"]) if lang == "en" else active["name"]
        return True, f"{'Poison' if lang=='en' else 'Яд'} {pname} {'cancelled.' if lang=='en' else 'отменён.'}"
    return False, "❌ Unknown type."


def get_all_active_boosters_text(data: dict, lang: str = "ru") -> str:
    """
    Текст для команды /boost — показывает все активные бусты
    и подсказку как отменить.
    """
    active   = get_active_booster_info(data)
    xp_act   = get_active_xp_booster_info(data)
    enh_act  = get_active_enh_booster_info(data)
    poison   = get_active_poison_info(data)

    lines = []
    if active:
        left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(active["multiplier"])
        dur  = _dur_label(active["dur_key"], lang)
        lines.append(
            f"{_pe('boost','⚡')} <b><i>{'Pickaxe booster' if lang=='en' else 'Ускоритель кирки'}: {mult} {'for' if lang=='en' else 'на'} <i>{dur}</i></i></b>\n"
            f"   ⏱ <i>{'Left' if lang=='en' else 'Осталось'}: {left}</i> — <code>{'/stop boost' if lang=='en' else '/стоп буст'}</code>"
        )
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        dur  = _dur_label(xp_act["dur_key"], lang)
        lines.append(
            f"{_pe('xp_boost','🔮')} <b><i>XP-{'booster' if lang=='en' else 'ускоритель'}: ×{mult} {'for' if lang=='en' else 'на'} <i>{dur}</i></i></b>\n"
            f"   ⏱ <i>{'Left' if lang=='en' else 'Осталось'}: {left}</i> — <code>{'/stop xp' if lang=='en' else '/стоп xp'}</code>"
        )
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        dur  = _dur_label(enh_act["dur_key"], lang)
        lines.append(
            f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b><i>{"Damage booster" if lang=="en" else "Усилитель урона"}: ×{mult} {"for" if lang=="en" else "на"} <i>{dur}</i></i></b>\n'
            f'   ⏱ <i>{"Left" if lang=="en" else "Осталось"}: {left}</i> — <code>{"/stop dmg" if lang=="en" else "/стоп урон"}</code>'
        )
    if poison:
        left = _fmt_time_left(poison["ends_at"] - _now_ts(), lang)
        _pn_en = {"Яд Гадюки":"Viper Venom","Яд Кобры":"Cobra Venom","Яд Чёрной Мамбы":"Black Mamba Venom","Яд Василиска":"Basilisk Venom","Яд Левиафана":"Leviathan Venom"}
        pname = _pn_en.get(poison["name"], poison["name"]) if lang == "en" else poison["name"]
        lines.append(
            f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b><i>{"Poison" if lang=="en" else "Яд"}: {pname}</i></b>\n'
            f'   ⏱ <i>{"Left" if lang=="en" else "Осталось"}: {left}</i> — <code>{"/stop poison" if lang=="en" else "/стоп яд"}</code>'
        )

    if not lines:
        empty = "No active boosters." if lang == "en" else "Нет активных ускорителей."
        return f"<blockquote>{_pe('cancel','❌')} <b><i>{empty}</i></b></blockquote>"

    title = "ACTIVE BOOSTERS" if lang == "en" else "АКТИВНЫЕ УСКОРИТЕЛИ"
    body  = "\n\n".join(lines)
    hint_ru = (
        "\n\n<blockquote><i>Команды отмены:\n"
        "<code>/стоп буст</code> — кирка\n"
        "<code>/стоп xp</code> — XP\n"
        "<code>/стоп урон</code> — урон\n"
        "<code>/стоп яд</code> — яд</i></blockquote>"
    )
    hint_en = (
        "\n\n<blockquote><i>Cancel commands:\n"
        "<code>/stop boost</code> — pickaxe\n"
        "<code>/stop xp</code> — XP\n"
        "<code>/stop dmg</code> — damage\n"
        "<code>/stop poison</code> — poison</i></blockquote>"
    )
    return f"<blockquote>{_pe('boost','⚡')} <b><i>{title}</i></b>\n\n{body}</blockquote>" + (hint_en if lang == "en" else hint_ru)


def sell_item_by_slot_id(data: dict, slot_id: int, qty: int = 1, lang: str = "ru") -> tuple[bool, str]:
    """
    Продаёт qty предметов из стопки по slot_id.
    Возвращает (ok, сообщение).
    """
    from database import format_amount as _fa

    slot_map = _get_or_assign_slot_ids(data)
    key = next((k for k, sid in slot_map.items() if sid == slot_id), None)
    if key is None:
        err = f"Слот #{slot_id} не найден." if lang == "ru" else f"Slot #{slot_id} not found."
        return False, f"❌ {err}"

    # Определяем тип и инвентарь
    inv_key = None
    item_sample = None
    sell_price_fn = None

    boost_inv = data.get("boosters_inventory", [])
    if any(i["key"] == key for i in boost_inv):
        inv_key = "boosters_inventory"
        item_sample = next(i for i in boost_inv if i["key"] == key)
        sell_price_fn = get_sell_price

    if inv_key is None:
        xp_inv = data.get("xp_inventory", [])
        if any(i["key"] == key for i in xp_inv):
            inv_key = "xp_inventory"
            item_sample = next(i for i in xp_inv if i["key"] == key)
            sell_price_fn = get_xp_sell_price

    if inv_key is None:
        enh_inv = data.get("enh_inventory", [])
        if any(i["key"] == key for i in enh_inv):
            inv_key = "enh_inventory"
            item_sample = next(i for i in enh_inv if i["key"] == key)
            sell_price_fn = get_enh_sell_price

    if inv_key is None:
        err = f"Слот #{slot_id} не найден." if lang == "ru" else f"Slot #{slot_id} not found."
        return False, f"❌ {err}"

    inv = data[inv_key]
    available = sum(1 for i in inv if i["key"] == key)

    if qty < 1:
        err = "Количество должно быть ≥ 1." if lang == "ru" else "Quantity must be ≥ 1."
        return False, f"❌ {err}"
    if qty > available:
        err = (
            f"В стопке только {available} шт." if lang == "ru"
            else f"Only {available} in stack."
        )
        return False, f"❌ {err}"

    price_each = sell_price_fn(item_sample)
    total_earn = price_each * qty

    # Убираем qty предметов из инвентаря
    removed = 0
    new_inv = []
    for i in inv:
        if i["key"] == key and removed < qty:
            removed += 1
        else:
            new_inv.append(i)
    data[inv_key] = new_inv

    # Если стопка полностью продана — убираем slot_id
    remaining = available - qty
    if remaining == 0:
        slot_map.pop(key, None)
        data["inv_slot_ids"] = slot_map

    data["balance"] = data.get("balance", 0) + total_earn

    # Название предмета
    itype = item_sample.get("type", "boost")
    if itype == "boost":
        name = _booster_name(item_sample)
    elif itype in ("xp_boost", "xp_instant"):
        name = _xp_item_name_plain(item_sample)
    else:
        name = _enh_item_name_plain(item_sample)

    if lang == "en":
        qty_str = f"{qty} шт. " if qty > 1 else ""
        msg = (
            f"<blockquote>💰 <b><i>Sold {qty_str}{name}</i></b>\n"
            f"+ {_fa(total_earn)} {'(× ' + str(qty) + ')' if qty > 1 else ''}\n"
            f"Balance: <b><i>{_fa(data['balance'])}</i></b></blockquote>"
        )
    else:
        qty_str = f"{qty} шт. " if qty > 1 else ""
        msg = (
            f"<blockquote>💰 <b><i>Продано: {qty_str}{name}</i></b>\n"
            f"+ {_fa(total_earn)}{' (× ' + str(qty) + ')' if qty > 1 else ''}\n"
            f"Баланс: <b><i>{_fa(data['balance'])}</i></b></blockquote>"
        )
    return True, msg


def transfer_item_by_slot_id(
    sender_data: dict,
    recipient_data: dict,
    slot_id: int,
    qty: int = 1,
    lang: str = "ru",
) -> tuple[bool, str, str]:
    """
    Передаёт qty предметов из инвентаря sender_data → recipient_data по slot_id.
    Возвращает (ok, sender_msg, recipient_msg).
    Модифицирует оба словаря на месте — сохранение в БД на стороне вызывающего.
    """

    # ── Найти ключ стопки по slot_id ──────────────────────────────────
    slot_map = _get_or_assign_slot_ids(sender_data)
    key = next((k for k, sid in slot_map.items() if sid == slot_id), None)
    if key is None:
        err = f"Слот #{slot_id} не найден." if lang == "ru" else f"Slot #{slot_id} not found."
        return False, f"❌ {err}", ""

    # ── Определяем инвентарь и тип предмета ───────────────────────────
    inv_key       = None
    item_sample   = None
    item_name_fn  = None

    boost_inv = sender_data.get("boosters_inventory", [])
    if any(i["key"] == key for i in boost_inv):
        inv_key      = "boosters_inventory"
        item_sample  = next(i for i in boost_inv if i["key"] == key)
        item_name_fn = lambda it: _booster_name(it)

    if inv_key is None:
        xp_inv = sender_data.get("xp_inventory", [])
        if any(i["key"] == key for i in xp_inv):
            inv_key      = "xp_inventory"
            item_sample  = next(i for i in xp_inv if i["key"] == key)
            item_name_fn = lambda it: _xp_item_name_plain(it)

    if inv_key is None:
        enh_inv = sender_data.get("enh_inventory", [])
        if any(i["key"] == key for i in enh_inv):
            inv_key      = "enh_inventory"
            item_sample  = next(i for i in enh_inv if i["key"] == key)
            item_name_fn = lambda it: _enh_item_name_plain(it)

    if inv_key is None:
        err = f"Слот #{slot_id} не найден." if lang == "ru" else f"Slot #{slot_id} not found."
        return False, f"❌ {err}", ""

    # ── Проверяем наличие ──────────────────────────────────────────────
    sender_inv = sender_data[inv_key]
    available  = sum(1 for i in sender_inv if i["key"] == key)

    if qty < 1:
        err = "Количество должно быть ≥ 1." if lang == "ru" else "Quantity must be ≥ 1."
        return False, f"❌ {err}", ""
    if qty > available:
        err = (
            f"В стопке только {available} шт." if lang == "ru"
            else f"Only {available} in stack."
        )
        return False, f"❌ {err}", ""

    # ── Перемещаем предметы ────────────────────────────────────────────
    transferred = []
    remaining   = []
    for item in sender_inv:
        if item["key"] == key and len(transferred) < qty:
            transferred.append(item)
        else:
            remaining.append(item)

    sender_data[inv_key] = remaining

    # Если стопка опустела — убираем slot_id
    if available - qty == 0:
        slot_map.pop(key, None)
        sender_data["inv_slot_ids"] = slot_map

    # Добавляем получателю
    recipient_inv = recipient_data.setdefault(inv_key, [])
    recipient_inv.extend(transferred)

    # ── Формируем имя предмета ─────────────────────────────────────────
    name = item_name_fn(item_sample)

    qty_str = f"{qty} шт. " if qty > 1 else ""

    recip_name  = recipient_data.get("first_name") or recipient_data.get("username") or str(recipient_data["id"])
    sender_name = sender_data.get("first_name") or sender_data.get("username") or str(sender_data["id"])

    if lang == "en":
        sender_msg = (
            f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> '
            f'<b><i>You successfully sent {qty_str}{name} to player {recip_name}!</i></b>'
        )
        recip_msg = (
            f'<tg-emoji emoji-id="5222113468051629260">🎁</tg-emoji> '
            f'<b><i>You received {qty_str}{name} from {sender_name}!</i></b>'
        )
    else:
        sender_msg = (
            f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> '
            f'<b><i>Вы успешно передали {qty_str}{name} игроку {recip_name}!</i></b>'
        )
        recip_msg = (
            f'<tg-emoji emoji-id="5222113468051629260">🎁</tg-emoji> '
            f'<b><i>Вы получили {qty_str}{name} от {sender_name}!</i></b>'
        )

    return True, sender_msg, recip_msg
