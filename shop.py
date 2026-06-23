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
    {"key": "boost_1.2x_10min", "multiplier": 1.2, "dur_key": "10min", "chance": 80},
    {"key": "boost_1.2x_30min", "multiplier": 1.2, "dur_key": "30min", "chance": 65},
    {"key": "boost_1.2x_1h",    "multiplier": 1.2, "dur_key": "1h",    "chance": 45},
    {"key": "boost_1.2x_2h",    "multiplier": 1.2, "dur_key": "2h",    "chance": 35},
    {"key": "boost_1.2x_4h",    "multiplier": 1.2, "dur_key": "4h",    "chance": 25},
    {"key": "boost_1.2x_10h",   "multiplier": 1.2, "dur_key": "10h",   "chance": 18},
    {"key": "boost_1.2x_24h",   "multiplier": 1.2, "dur_key": "24h",   "chance": 10},
    {"key": "boost_1.5x_10min", "multiplier": 1.5, "dur_key": "10min", "chance": 60},
    {"key": "boost_1.5x_30min", "multiplier": 1.5, "dur_key": "30min", "chance": 40},
    {"key": "boost_1.5x_1h",    "multiplier": 1.5, "dur_key": "1h",    "chance": 35},
    {"key": "boost_1.5x_2h",    "multiplier": 1.5, "dur_key": "2h",    "chance": 25},
    {"key": "boost_1.5x_4h",    "multiplier": 1.5, "dur_key": "4h",    "chance": 19},
    {"key": "boost_1.5x_10h",   "multiplier": 1.5, "dur_key": "10h",   "chance": 12},
    {"key": "boost_1.5x_24h",   "multiplier": 1.5, "dur_key": "24h",   "chance":  5},
    {"key": "boost_2x_10min",   "multiplier": 2.0, "dur_key": "10min", "chance": 40},
    {"key": "boost_2x_30min",   "multiplier": 2.0, "dur_key": "30min", "chance": 30},
    {"key": "boost_2x_1h",      "multiplier": 2.0, "dur_key": "1h",    "chance": 22},
    {"key": "boost_2x_2h",      "multiplier": 2.0, "dur_key": "2h",    "chance": 12},
    {"key": "boost_2x_4h",      "multiplier": 2.0, "dur_key": "4h",    "chance":  8},
    {"key": "boost_2x_10h",     "multiplier": 2.0, "dur_key": "10h",   "chance":  3},
    {"key": "boost_2x_24h",     "multiplier": 2.0, "dur_key": "24h",   "chance":  1},
]

BOOSTERS_BY_KEY = {b["key"]: b for b in _BOOSTER_POOL}
MAX_INVENTORY = 10

_SELL_PRICES = {
    ("1.2", "10min"): 500,   ("1.2", "30min"): 1_200, ("1.2", "1h"): 2_000,
    ("1.2", "2h"):    3_500, ("1.2", "4h"):    5_500,  ("1.2", "10h"): 10_000,
    ("1.2", "24h"):   18_000,
    ("1.5", "10min"): 800,   ("1.5", "30min"): 2_000, ("1.5", "1h"): 3_500,
    ("1.5", "2h"):    6_000, ("1.5", "4h"):    9_000,  ("1.5", "10h"): 16_000,
    ("1.5", "24h"):   28_000,
    ("2.0", "10min"): 1_200, ("2.0", "30min"): 3_000, ("2.0", "1h"): 5_500,
    ("2.0", "2h"):    9_500, ("2.0", "4h"):    15_000, ("2.0", "10h"): 26_000,
    ("2.0", "24h"):   45_000,
}


def get_sell_price(item: dict) -> int:
    m = item["multiplier"]
    if m >= 2.0:   mk = "2.0"
    elif m >= 1.5: mk = "1.5"
    else:          mk = "1.2"
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
    {"key": "xpboost_1.4x_30min", "type": "xp_boost", "multiplier": 1.4, "dur_key": "30min", "chance": 60},
    {"key": "xpboost_1.4x_1h",   "type": "xp_boost", "multiplier": 1.4, "dur_key": "1h",    "chance": 45},
    {"key": "xpboost_1.4x_2h",   "type": "xp_boost", "multiplier": 1.4, "dur_key": "2h",    "chance": 30},
    {"key": "xpboost_1.4x_4h",   "type": "xp_boost", "multiplier": 1.4, "dur_key": "4h",    "chance": 20},
    {"key": "xpboost_1.4x_6h",   "type": "xp_boost", "multiplier": 1.4, "dur_key": "6h",    "chance": 12},
    {"key": "xpboost_1.4x_24h",  "type": "xp_boost", "multiplier": 1.4, "dur_key": "24h",   "chance":  5},
    {"key": "xpboost_1.4x_48h",  "type": "xp_boost", "multiplier": 1.4, "dur_key": "48h",   "chance":  2},
    {"key": "xpboost_1.8x_30min", "type": "xp_boost", "multiplier": 1.8, "dur_key": "30min", "chance": 35},
    {"key": "xpboost_1.8x_1h",   "type": "xp_boost", "multiplier": 1.8, "dur_key": "1h",    "chance": 22},
    {"key": "xpboost_1.8x_2h",   "type": "xp_boost", "multiplier": 1.8, "dur_key": "2h",    "chance": 14},
    {"key": "xpboost_1.8x_4h",   "type": "xp_boost", "multiplier": 1.8, "dur_key": "4h",    "chance":  8},
    {"key": "xpboost_1.8x_6h",   "type": "xp_boost", "multiplier": 1.8, "dur_key": "6h",    "chance":  4},
    {"key": "xpboost_1.8x_24h",  "type": "xp_boost", "multiplier": 1.8, "dur_key": "24h",   "chance":  2},
    {"key": "xpboost_1.8x_48h",  "type": "xp_boost", "multiplier": 1.8, "dur_key": "48h",   "chance":  1},
]

XP_POOL_BY_KEY = {x["key"]: x for x in _XP_POOL}
MAX_XP_INVENTORY = 10

# ============================================================
#  ПУЛ КЕЙСА УСИЛИТЕЛЕЙ
# ============================================================

_ENH_BOOSTER_POOL = [
    # ── 1.2× ──────────────────────────────────────────────
    {"key": "enh_boost_1.2x_5min",  "type": "enh_boost", "multiplier": 1.2, "dur_key": "5min",  "chance": 85},
    {"key": "enh_boost_1.2x_30min", "type": "enh_boost", "multiplier": 1.2, "dur_key": "30min", "chance": 65},
    {"key": "enh_boost_1.2x_1h",    "type": "enh_boost", "multiplier": 1.2, "dur_key": "1h",    "chance": 45},
    {"key": "enh_boost_1.2x_2h",    "type": "enh_boost", "multiplier": 1.2, "dur_key": "2h",    "chance": 32},
    {"key": "enh_boost_1.2x_4h",    "type": "enh_boost", "multiplier": 1.2, "dur_key": "4h",    "chance": 22},
    {"key": "enh_boost_1.2x_10h",   "type": "enh_boost", "multiplier": 1.2, "dur_key": "10h",   "chance": 16},
    {"key": "enh_boost_1.2x_24h",   "type": "enh_boost", "multiplier": 1.2, "dur_key": "24h",   "chance":  9},
    # ── 1.5× ──────────────────────────────────────────────
    {"key": "enh_boost_1.5x_5min",  "type": "enh_boost", "multiplier": 1.5, "dur_key": "5min",  "chance": 62},
    {"key": "enh_boost_1.5x_30min", "type": "enh_boost", "multiplier": 1.5, "dur_key": "30min", "chance": 38},
    {"key": "enh_boost_1.5x_1h",    "type": "enh_boost", "multiplier": 1.5, "dur_key": "1h",    "chance": 32},
    {"key": "enh_boost_1.5x_2h",    "type": "enh_boost", "multiplier": 1.5, "dur_key": "2h",    "chance": 22},
    {"key": "enh_boost_1.5x_4h",    "type": "enh_boost", "multiplier": 1.5, "dur_key": "4h",    "chance": 16},
    {"key": "enh_boost_1.5x_10h",   "type": "enh_boost", "multiplier": 1.5, "dur_key": "10h",   "chance": 10},
    {"key": "enh_boost_1.5x_24h",   "type": "enh_boost", "multiplier": 1.5, "dur_key": "24h",   "chance":  4},
    # ── 2× ────────────────────────────────────────────────
    {"key": "enh_boost_2x_5min",    "type": "enh_boost", "multiplier": 2.0, "dur_key": "5min",  "chance": 42},
    {"key": "enh_boost_2x_30min",   "type": "enh_boost", "multiplier": 2.0, "dur_key": "30min", "chance": 28},
    {"key": "enh_boost_2x_1h",      "type": "enh_boost", "multiplier": 2.0, "dur_key": "1h",    "chance": 20},
    {"key": "enh_boost_2x_2h",      "type": "enh_boost", "multiplier": 2.0, "dur_key": "2h",    "chance": 10},
    {"key": "enh_boost_2x_4h",      "type": "enh_boost", "multiplier": 2.0, "dur_key": "4h",    "chance":  7},
    {"key": "enh_boost_2x_10h",     "type": "enh_boost", "multiplier": 2.0, "dur_key": "10h",   "chance":  2},
    {"key": "enh_boost_2x_24h",     "type": "enh_boost", "multiplier": 2.0, "dur_key": "24h",   "chance":  1},
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
    {"key": "art_kulon_iskazheniya",   "type": "artifact", "name": "Кулон Искажения",      "name_en": "Distortion Pendant",    "emoji_id": "5938541999031325561", "effect": "mine",   "multiplier": 1.3, "chance": 50},
    {"key": "art_oracle",              "type": "artifact", "name": "Оракул",               "name_en": "Oracle",                "emoji_id": "5165898384870999138", "effect": "damage", "multiplier": 1.3, "chance": 50},
    {"key": "art_amulet_hranitelya",   "type": "artifact", "name": "Амулет Хранителя",     "name_en": "Guardian Amulet",       "emoji_id": "5938082716703528871", "effect": "pets",   "multiplier": 1.3, "chance": 50},
    # ── 25% шанс — множитель 1.5× ──────────────────────────
    {"key": "art_lunnaya_relikviya",   "type": "artifact", "name": "Лунная Реликвия",      "name_en": "Lunar Relic",           "emoji_id": "5226662903569989373", "effect": "mine",   "multiplier": 1.5, "chance": 25},
    {"key": "art_sfera_zhadnosti",     "type": "artifact", "name": "Сфера Жадности",       "name_en": "Sphere of Greed",       "emoji_id": "5080262187302257610", "effect": "damage", "multiplier": 1.5, "chance": 25},
    {"key": "art_amulet_zhizni",       "type": "artifact", "name": "Амулет Жизни и Смерти","name_en": "Amulet of Life & Death","emoji_id": "6228938636428052300", "effect": "pets",   "multiplier": 1.5, "chance": 25},
    # ── 15% шанс — множитель 1.8× ──────────────────────────
    {"key": "art_sfera_illyuziy",      "type": "artifact", "name": "Сфера Иллюзий",        "name_en": "Sphere of Illusions",   "emoji_id": "5343583990815156847", "effect": "mine",   "multiplier": 1.8, "chance": 15},
    {"key": "art_serdtse_morey",       "type": "artifact", "name": "Сердце Морей",          "name_en": "Heart of the Seas",     "emoji_id": "6201647288947839133", "effect": "damage", "multiplier": 1.8, "chance": 15},
    {"key": "art_kristall_egzorcizma", "type": "artifact", "name": "Кристалл Экзорцизма",  "name_en": "Exorcism Crystal",      "emoji_id": "5451889386549425709", "effect": "pets",   "multiplier": 1.8, "chance": 15},
    # ── 1% шанс — комбо-артефакт ────────────────────────────
    {"key": "art_vsevlastniy",         "type": "artifact", "name": "Кольцо Перерождений",  "name_en": "Ring of Rebirths",      "emoji_id": "5872990619021875271", "effect": "all",    "multiplier": 1.4, "chance": 1},
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
    return f'{emoji}<b>{name}</b> — {a["multiplier"]}× {effect_label}'


def open_artifact_case(data: dict, lang: str = "ru") -> tuple:
    """Открыть кейс артефактов. Оплата Stars уже прошла — выдаём артефакт."""
    pool    = _ARTIFACT_POOL
    weights = [a["chance"] for a in pool]
    chosen  = random.choices(pool, weights=weights, k=1)[0]

    artifacts = data.setdefault("artifacts", [])
    already_have = any(entry["key"] == chosen["key"] for entry in artifacts)
    if not already_have:
        artifacts.append({"key": chosen["key"]})
        added_msg = f"{_pe('ok', '✅')} <b>{_L(lang, 'Артефакт добавлен в коллекцию!', 'Artifact added to collection!')}</b>"
    else:
        # Дубликат — выдаём монеты по множителю артефакта
        _dup_rewards = {1.3: 5_000_000, 1.5: 8_000_000, 1.8: 15_000_000, 1.4: 50_000_000}
        _dup_coins = _dup_rewards.get(chosen["multiplier"], 5_000_000)
        data["balance"] = data.get("balance", 0) + _dup_coins
        added_msg = (
            f"{_pe('warn', '⚠️')} <b>{_L(lang, 'Этот артефакт у тебя уже есть!', 'You already have this artifact!')}</b>\n"
            f"{_pe('coin', '💰')} <b>{_L(lang, 'Компенсация', 'Compensation')}: +{_fmt_num(_dup_coins)} {COIN}</b>"
        )

    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1

    msg = (
        f"<blockquote>{_pe('stats', '💎')} <b>{_L(lang, 'Кейс Артефактов открыт!', 'Artifact Case opened!')}</b>\n"
        f"{_pe('arrow', '➡️')} <b>{_L(lang, 'Выпало', 'Dropped')}: {_artifact_desc(chosen, lang)}</b></blockquote>\n"
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
    # ── 1.2× ──
    "enh_boost_1.2x_5min":  350,   "enh_boost_1.2x_30min": 1_000, "enh_boost_1.2x_1h":   1_700,
    "enh_boost_1.2x_2h":  2_900,   "enh_boost_1.2x_4h":    4_600,  "enh_boost_1.2x_10h":  8_500,
    "enh_boost_1.2x_24h": 15_000,
    # ── 1.5× ──
    "enh_boost_1.5x_5min":  550,   "enh_boost_1.5x_30min": 1_700,  "enh_boost_1.5x_1h":   3_000,
    "enh_boost_1.5x_2h":  5_200,   "enh_boost_1.5x_4h":    8_000,  "enh_boost_1.5x_10h": 14_000,
    "enh_boost_1.5x_24h": 24_000,
    # ── 2× ──
    "enh_boost_2x_5min":   800,    "enh_boost_2x_30min":   2_600,  "enh_boost_2x_1h":     4_700,
    "enh_boost_2x_2h":   8_500,    "enh_boost_2x_4h":     13_000,  "enh_boost_2x_10h":   22_000,
    "enh_boost_2x_24h":  40_000,
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
    "xpboost_1.4x_30min": 1_500, "xpboost_1.4x_1h": 2_800, "xpboost_1.4x_2h": 5_000,
    "xpboost_1.4x_4h": 8_500, "xpboost_1.4x_6h": 13_000, "xpboost_1.4x_24h": 22_000,
    "xpboost_1.4x_48h": 38_000,
    "xpboost_1.8x_30min": 3_000, "xpboost_1.8x_1h": 5_500, "xpboost_1.8x_2h": 10_000,
    "xpboost_1.8x_4h": 17_000, "xpboost_1.8x_6h": 26_000, "xpboost_1.8x_24h": 45_000,
    "xpboost_1.8x_48h": 80_000,
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
        if len(inv) >= MAX_INVENTORY:
            return False, f"❌ {_L(lang, 'Инвентарь ускорителей полон!', 'Booster inventory is full!')}\n{_L(lang, f'Максимум {MAX_INVENTORY} шт. Активируй или продай лишние.', f'Max {MAX_INVENTORY} items. Activate or sell some.')}", None
    elif case["type"] == "enhancer":
        inv = data.setdefault("enh_inventory", [])
        if len(inv) >= MAX_ENH_INVENTORY:
            return False, f"❌ {_L(lang, 'Инвентарь усилителей полон!', 'Enhancer inventory is full!')}\n{_L(lang, f'Максимум {MAX_ENH_INVENTORY} шт. Используй или продай лишние.', f'Max {MAX_ENH_INVENTORY} items. Use or sell some.')}", None
    else:
        inv = data.setdefault("xp_inventory", [])
        if len(inv) >= MAX_XP_INVENTORY:
            return False, f"❌ {_L(lang, 'XP-инвентарь полон!', 'XP inventory is full!')}\n{_L(lang, f'Максимум {MAX_XP_INVENTORY} шт. Используй или продай лишние.', f'Max {MAX_XP_INVENTORY} items. Use or sell some.')}", None
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
        inv_line = f"{_L(lang, 'В инвентаре', 'In inventory')}: {len(inv)}/{MAX_INVENTORY}"
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
        inv_line = f"{_L(lang, 'В инвентаре усилителей', 'Enhancer inventory')}: {len(inv)}/{MAX_ENH_INVENTORY}"
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
        else:
            instance["multiplier"]   = dropped["multiplier"]
            instance["dur_key"]      = dropped["dur_key"]
            instance["duration_sec"] = _DUR[dropped["dur_key"]]
            name = _xp_item_name(dropped, lang)
        inv.append(instance)
        inv_line = f"{_L(lang, 'В XP-инвентаре', 'XP inventory')}: {len(inv)}/{MAX_XP_INVENTORY}"
    data["cases_total_opened"] = data.get("cases_total_opened", 0) + 1
    data["cases_total_spent"]  = data.get("cases_total_spent",  0) + cost
    msg = (
        f"<blockquote>{_pe('case', '📦')} <b>{_L(lang, 'Кейс открыт!', 'Case opened!')}</b>\n"
        f"{_pe('arrow', '➡️')} <b>{_L(lang, 'Выпало', 'Dropped')}:</b> {name}</blockquote>\n"
        f"\n<blockquote>{_pe('spent', '💸')} <b>{_L(lang, 'Потрачено', 'Spent')}: {_fmt_num(cost)}</b> {_pe('coin', '💰')}\n"
        f"{_pe('balance', '💰')} <b>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</b> {_pe('coin', '💰')}\n"
        f"{_pe('inv', '🎒')} <b>{inv_line}</b></blockquote>"
    )
    return True, msg, instance


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
        f"<blockquote>{_pe('activate', '✅')} <b>{_L(lang, 'Ускоритель активирован!', 'Booster activated!')}</b>\n"
        f"{_pe('boost', '⚡')} <b>{_booster_name(item, lang)}</b>\n"
        f"<b>{_L(lang, 'Все показатели кирки', 'All pickaxe stats')} ×{mult} {_L(lang, 'на', 'for')} {dur}!</b></blockquote>"
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
        f"<blockquote>{_pe('sell', '💸')} <b>{_L(lang, 'Ускоритель продан!', 'Booster sold!')}</b>\n"
        f"{_pe('boost', '⚡')} <b>{_booster_name(item, lang)}</b>\n"
        f"{_pe('coin', '💰')} <b>+{_fmt_num(price)}</b>\n"
        f"{_pe('balance', '💰')} <b>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</b> {_pe('coin', '💰')}</blockquote>"
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
            f"<blockquote>{_pe('xp_boost', '🔮')} <b>{_L(lang, 'XP-ускоритель активирован!', 'XP booster activated!')}</b>\n"
            f"{_pe('xp_instant', '✨')} <b>{_L(lang, 'Множитель опыта', 'XP multiplier')} ×{mult} {_L(lang, 'на', 'for')} {dur}!</b></blockquote>"
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
        lvl_msg = f"\n🎉 <b>Level up to {level}!</b>" * min(lvl_ups, 3)
        if lvl_ups > 3:
            lvl_msg = f"\n🎉 <b>Level up to {level} (+{lvl_ups} lvl)!</b>"
    else:
        lvl_msg = f"\n🎉 <b>Уровень повышен до {level}!</b>" * min(lvl_ups, 3)
        if lvl_ups > 3:
            lvl_msg = f"\n🎉 <b>Уровень повышен до {level} (+{lvl_ups} ур.)!</b>"
    return True, (
        f"<blockquote>{_pe('xp_instant', '✨')} <b>{_L(lang, 'Опыт получен!', 'XP received!')}</b>\n"
        f"{_pe('xp_instant', '✨')} <b>+{_fmt_num(gained)} XP</b>{lvl_msg}</blockquote>\n"
        f"\n<blockquote><b>{_L(lang, 'Уровень', 'Level')}: {level}</b>\n"
        f"<b>{_L(lang, 'Опыт', 'XP')}: {_fmt_num(xp)}/{_fmt_num(xp_max)}</b></blockquote>"
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
        f"<blockquote>{_pe('sell', '💸')} <b>{_L(lang, 'Продано!', 'Sold!')}</b>\n"
        f"{_xp_item_name(item, lang)}\n"
        f"{_pe('coin', '💰')} <b>+{_fmt_num(price)}</b>\n"
        f"{_pe('balance', '💰')} <b>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</b> {_pe('coin', '💰')}</blockquote>"
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
        f'<blockquote><tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>{_L(lang, "Яд применён!", "Poison applied!")}</b>\n'
        f'<b>{pname}</b>\n'
        f'<tg-emoji emoji-id="{_E["timer"]}">⏱</tg-emoji> <b>{_L(lang, "Урон наносится 30 минут автоматически", "Damage applied automatically for 30 minutes")}</b>\n'
        f'<b>{_L(lang, "Суммарный урон боссу", "Total boss damage")}: {_fmt_num(item["damage"])}</b></blockquote>'
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
        f'{_pe("sell", "💸")} <b>{_L(lang, "Продано!", "Sold!")}</b>\n'
        f'{_enh_item_name(item, lang)}\n'
        f'{_pe("coin", "💰")} <b>+{_fmt_num(price)}</b>\n'
        f'{_pe("balance", "💰")} <b>{_L(lang, "Баланс", "Balance")}: {_fmt_num(data["balance"])}</b> {_pe("coin", "💰")}'
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
        f'{_pe("enh_boost", "⚡")} <b>{_L(lang, "Усилитель активирован!", "Enhancer activated!")}</b>\n'
        f'<b>{_L(lang, "Урон", "Damage")} ×{mult} {_L(lang, "на", "for")} {dur}!</b>'
    )


# ============================================================
#  UI — ИНВЕНТАРЬ УСИЛИТЕЛЕЙ
# ============================================================

def enh_inventory_text(data: dict, lang: str = "ru") -> str:
    inv      = data.setdefault("enh_inventory", [])
    poison   = get_active_poison_info(data)
    enh_act  = get_active_enh_booster_info(data)
    lines    = [f'<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>{_L(lang, "УСИЛИТЕЛИ И ЯДЫ", "BOOSTERS & POISONS")}</b>\n']
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        lines.append(
            f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>{_L(lang, "Активен усилитель", "Active booster")}: ×{mult}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b>\n'
        )
    else:
        lines.append(f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>{_L(lang, "Нет активного усилителя.", "No active booster.")}</b>\n')
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
            f'{_pe("ok", "✅")} <b>{_L(lang, "Яд", "Poison")}: {pname} — {dmg} {dmg_label}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b>'
        )
    else:
        lines.append(f'{_pe("cancel", "❌")} <b>{_L(lang, "Нет активного яда.", "No active poison.")}</b>')
    lines.append("</blockquote>")
    if not inv:
        lines.append(
            f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji>'
            f' <b>{_L(lang, "Инвентарь пуст. Открой Кейс усилителей!", "Inventory empty. Open an Enhancer case!")}</b></blockquote>'
        )
    else:
        lines.append(f'\n<blockquote><b>{_L(lang, "В инвентаре", "In inventory")} ({len(inv)}/{MAX_ENH_INVENTORY}):</b>')
        for i, item in enumerate(inv, 1):
            price = get_enh_sell_price(item)
            lines.append(f'\n<b>{i}. {_enh_item_name(item, lang)}</b>\n{_pe("coin", "💰")} <b>{_fmt_num(price)}</b>')
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
                f'\n\n<blockquote>{_pe("warn", "⚠️")} <b>{_L(lang, "Уже активен", "Already active")}: {aname}</b>\n'
                f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b></blockquote>'
            )
        _poison_names_en2 = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        pname = _poison_names_en2.get(item["name"], item["name"]) if lang == "en" else item["name"]
        return (
            f'<blockquote><tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji>'
            f' <b>{pname}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Длительность: 30 минут", "Duration: 30 minutes")}</b>\n'
            f'<b>{_L(lang, "Суммарный урон боссу", "Total boss damage")}: {_fmt_num(item["damage"])}</b></blockquote>\n'
            f'\n<blockquote><b>{_L(lang, "Яд действует автоматически — урон списывается равномерно каждую минуту.", "Poison works automatically — damage applied evenly each minute.")}</b>\n'
            f'<b>{_L(lang, "Работает на текущего активного босса.", "Works on the current active boss.")}</b></blockquote>\n'
            f'\n<blockquote>{_pe("coin", "💰")} <b>{_L(lang, "Цена продажи", "Sell price")}: {_fmt_num(price)}</b></blockquote>'
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
            f'\n\n<blockquote>{_pe("warn", "⚠️")} <b>{_L(lang, "Активен", "Active")}: {act_mult} {_L(lang, "на", "for")} {act_dur}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b></blockquote>'
        )
    return (
        f'<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji>'
        f' <b>{_L(lang, "Усилитель урона", "Damage booster")} {mult}</b>\n'
        f'{_pe("timer", "⏱")} <b>{_L(lang, "Длительность", "Duration")}: {dur}</b>\n'
        f'{_pe("mult", "🔢")} <b>{_L(lang, "Множитель", "Multiplier")}: {mult}</b></blockquote>\n'
        f'\n<blockquote><b>{_L(lang, f"Увеличивает весь урон по боссу в {mult} на {dur}.", f"Increases all boss damage by {mult} for {dur}.")}</b></blockquote>\n'
        f'\n<blockquote>{_pe("coin", "💰")} <b>{_L(lang, "Цена продажи", "Sell price")}: {_fmt_num(price)}</b></blockquote>'
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
            f'<blockquote>{_pe("warn", "⚠️")} <b>{_L(lang, "Замена яда", "Replace poison")}</b>\n'
            f'<b>{_L(lang, "Сейчас активен", "Currently active")}: {aname}</b>\n'
            f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b></blockquote>\n'
            f'\n<blockquote><b>{_L(lang, "Заменить на", "Replace with")}: {iname}?</b>\n'
            f'{_pe("warn", "⚠️")} <b>{_L(lang, "Текущий яд будет потерян!", "Current poison will be lost!")}</b></blockquote>'
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
        f'<blockquote>{_pe("warn", "⚠️")} <b>{_L(lang, "Замена усилителя", "Replace booster")}</b>\n'
        f'<b>{_L(lang, "Сейчас активен", "Currently active")}: {act_mult} {_L(lang, "на", "for")} {act_dur}</b>\n'
        f'{_pe("timer", "⏱")} <b>{_L(lang, "Осталось", "Left")}: {left}</b></blockquote>\n'
        f'\n<blockquote><b>{_L(lang, "Заменить на", "Replace with")}: {new_mult} {_L(lang, "на", "for")} {new_dur}?</b>\n'
        f'{_pe("warn", "⚠️")} <b>{_L(lang, "Старый усилитель будет потерян!", "Old booster will be lost!")}</b></blockquote>'
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
            f"<blockquote>{_pe('shop', '🛒')} <b>CASE SHOP</b>\n"
            f"<b>Open cases and get bonuses!</b></blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> <b>Your stats</b>\n'
            f"<b>Cases opened: {_fmt_num(total_opened)}</b>\n"
            f"{_pe('spent', '💸')} <b>Spent: {_fmt_num(total_spent)}</b> {_pe('coin', '💰')}</blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji> <b>Good luck! May something great drop</b><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji></blockquote>'
        )
    return (
        f"<blockquote>{_pe('shop', '🛒')} <b>МАГАЗИН КЕЙСОВ</b>\n"
        f"<b>Открывай кейсы и получай бонусы!</b></blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> <b>Твоя статистика</b>\n'
        f"<b>Открыто кейсов: {_fmt_num(total_opened)}</b>\n"
        f"{_pe('spent', '💸')} <b>Потрачено: {_fmt_num(total_spent)}</b> {_pe('coin', '💰')}</blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji> <b>Удачи тебе! Пусть выпадет что-то крутое</b><tg-emoji emoji-id="5269531045165816230">🎟</tg-emoji></blockquote>'
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
                f"{_pe('boost', '⚡')} <b>Booster 1.2× — 10min to 24h</b>\n"
                f"{_pe('boost', '⚡')} <b>Booster 1.5× — 10min to 24h</b>\n"
                f"{_pe('boost', '⚡')} <b>Booster 2× — 10min to 24h</b>"
            )
        else:
            loot_lines = (
                f"{_pe('boost', '⚡')} <b>Ускоритель 1.2× — 10мин до 24ч</b>\n"
                f"{_pe('boost', '⚡')} <b>Ускоритель 1.5× — 10мин до 24ч</b>\n"
                f"{_pe('boost', '⚡')} <b>Ускоритель 2× — 10мин до 24ч</b>"
            )
    elif case["type"] == "enhancer":
        if lang == "en":
            loot_lines = (
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Damage booster 1.2× — 5min to 24h</b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Damage booster 1.5× — 5min to 24h</b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Damage booster 2× — 5min to 24h</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Viper Venom — 100 000 dmg (5%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Cobra Venom — 150 000 dmg (3%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Black Mamba Venom — 225 000 dmg (2%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Basilisk Venom — 350 000 dmg (1%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Leviathan Venom — 500 000 dmg (0.5%)</b>'
            )
        else:
            loot_lines = (
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Усилитель урона 1.2× — 5мин до 24ч</b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Усилитель урона 1.5× — 5мин до 24ч</b>\n'
                f'<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Усилитель урона 2× — 5мин до 24ч</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд Гадюки — 100 000 урона (5%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд Кобры — 150 000 урона (3%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд Чёрной Мамбы — 225 000 урона (2%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд Василиска — 350 000 урона (1%)</b>\n'
                f'<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>Яд Левиафана — 500 000 урона (0.5%)</b>'
            )
    else:
        if lang == "en":
            loot_lines = (
                f"{_pe('xp_instant', '✨')} <b>Instant XP: 100 / 225 / 750 / 2 000 / 5 000</b>\n"
                f"{_pe('xp_boost', '🔮')} <b>XP booster ×1.4 — 30min to 48h</b>\n"
                f"{_pe('xp_boost', '🔮')} <b>XP booster ×1.8 — 30min to 48h</b>"
            )
        else:
            loot_lines = (
                f"{_pe('xp_instant', '✨')} <b>Моментальный опыт: 100 / 225 / 750 / 2 000 / 5 000 XP</b>\n"
                f"{_pe('xp_boost', '🔮')} <b>XP-ускоритель ×1.4 — от 30 мин до 48 ч</b>\n"
                f"{_pe('xp_boost', '🔮')} <b>XP-ускоритель ×1.8 — от 30 мин до 48 ч</b>"
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
        f"{_pe('ok', '✅')} <b>{_L(lang, 'Хватает монет', 'Enough coins')}</b>"
        if can_buy else
        f"{_pe('cancel', '❌')} <b>{_L(lang, 'Недостаточно монет', 'Not enough coins')}</b>"
    )
    return (
        f"<blockquote>{_pe(e_key, '📦')} <b>{cname} {case_label}</b>\n"
        f"{_pe('coin', '💰')} <b>{_L(lang, 'Цена', 'Price')}:</b> <b>{_fmt_num(case['cost'])}</b>\n"
        f"{_pe('balance', '💰')} <b>{_L(lang, 'Баланс', 'Balance')}:</b> <b>{bal_str}</b></blockquote>\n"
        f"\n<blockquote><b>{_L(lang, 'Возможный лут', 'Possible loot')}:</b>\n{loot_lines}</blockquote>\n"
        f"\n<blockquote>{status}</blockquote>"
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
            f'{_ae(a)} <b>{aname}</b> — '
            f'<b><i>{a["multiplier"]}× {eff_label}</i></b> <b>({pct}%)</b>\n'
        )

    loot = "".join(_row(a, a["chance"]) for a in _ARTIFACT_POOL)

    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>{_L(lang, "Кейс Артефактов", "Artifact Case")}</b>\n'
        f'<tg-emoji emoji-id="5262643974912355126">⭐</tg-emoji> <b>{_L(lang, "Цена", "Price")}: {ARTIFACT_CASE_COST_STARS} Telegram Stars</b></blockquote>\n'
        f'\n<blockquote><b>{_L(lang, "Возможный лут", "Possible loot")}:</b>\n{loot}</blockquote>\n'
        f'\n<blockquote>'
        f'<tg-emoji emoji-id="{_E_BONUS}">✨</tg-emoji> <b>{_L(lang, "Артефакты дают постоянный бонус навсегда!", "Artifacts give a permanent bonus forever!")}</b>\n'
        f'{_pe("warn", "⚠️")} <b>{_L(lang, "Дубликат — компенсация монетами.", "Duplicate — compensated with coins.")}</b></blockquote>\n'
        f'\n<blockquote><tg-emoji emoji-id="5359664288241829619">📦</tg-emoji> <b>{_L(lang, "Открыто кейсов", "Cases opened")}: {opened}</b>  |  '
        f'{_pe("stats", "💎")} <b>{_L(lang, "Коллекция", "Collection")}: {len(owned)}/10</b></blockquote>'
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
            f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>{_L(lang, "МОЯ КОЛЛЕКЦИЯ АРТЕФАКТОВ", "MY ARTIFACT COLLECTION")}</b>\n'
            f'{_pe("cancel", "❌")} <b>{_L(lang, "У тебя пока нет артефактов.", "You have no artifacts yet.")}</b>\n'
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
                f'{ae} <b>{aname}</b> — '
                f'<b><i>{a["multiplier"]}× {effect_label}</i></b>\n'
            )

    mine_icon  = f'<tg-emoji emoji-id="{_E_MINE}">⛏</tg-emoji>'
    dmg_icon   = f'<tg-emoji emoji-id="{_E_DMG}">⚔️</tg-emoji>'
    pets_icon  = f'<tg-emoji emoji-id="{_E_PETS}">🐾</tg-emoji>'
    bonus_icon = f'<tg-emoji emoji-id="{_E_BONUS}">✨</tg-emoji>'

    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> '
        f'<b>{_L(lang, "МОЯ КОЛЛЕКЦИЯ", "MY COLLECTION")} ({len(owned)}/10)</b></blockquote>\n'
        f'\n<blockquote>'
        f'{bonus_icon} <b>{_L(lang, "Итоговые бонусы", "Total bonuses")}:</b>\n'
        f'{mine_icon} <b>{_L(lang, "Руда", "Ore")}: ×{mine_mult}</b>\n'
        f'{dmg_icon} <b>{_L(lang, "Босс", "Boss")}: ×{damage_mult}</b>\n'
        f'{pets_icon} <b>{_L(lang, "Питомцы", "Pets")}: ×{pets_mult}</b>'
        f'</blockquote>\n'
        f'\n<blockquote><b>{_L(lang, "Артефакты", "Artifacts")}:</b>\n' + "".join(artifact_lines) + '</blockquote>'
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
        b_active_str = f"\n{_pe('boost', '⚡')} <b>{'Active' if lang == 'en' else 'Активен'}: {mult} — ⏱ {left}</b>"
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        xp_active_str = f"\n{_pe('xp_boost', '🔮')} <b>{'Active' if lang == 'en' else 'Активен'}: ×{mult} XP — ⏱ {left}</b>"
    if enh_act:
        left = _fmt_time_left(enh_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(enh_act["multiplier"])
        lbl = "Booster" if lang == "en" else "Усилитель"
        enh_active_str += f'\n<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>{lbl}: ×{mult} — ⏱ {left}</b>'
    if poison:
        left = _fmt_time_left(poison["ends_at"] - _now_ts(), lang)
        _poison_names_en = {
            "Яд Гадюки": "Viper Venom", "Яд Кобры": "Cobra Venom",
            "Яд Чёрной Мамбы": "Black Mamba Venom", "Яд Василиска": "Basilisk Venom",
            "Яд Левиафана": "Leviathan Venom",
        }
        pname = _poison_names_en.get(poison["name"], poison["name"]) if lang == "en" else poison["name"]
        enh_active_str += f'\n<tg-emoji emoji-id="5456584142286250164">☠️</tg-emoji> <b>{"Poison" if lang == "en" else "Яд"}: {pname} — ⏱ {left}</b>'

    if lang == "en":
        return (
            f"<blockquote>{_pe('inv', '🎒')} <b>INVENTORY</b></blockquote>\n"
            f"\n<blockquote>{_pe('boost', '⚡')} <b>Pickaxe boosters</b>  <b>[{len(b_inv)}/{MAX_INVENTORY}]</b>{b_active_str}</blockquote>\n"
            f"\n<blockquote>{_pe('xp_boost', '🔮')} <b>XP items</b>  <b>[{len(xp_inv)}/{MAX_XP_INVENTORY}]</b>{xp_active_str}</blockquote>\n"
            f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Damage boosters & poisons</b>  <b>[{len(enh_inv)}/{MAX_ENH_INVENTORY}]</b>{enh_active_str}</blockquote>'
        )
    return (
        f"<blockquote>{_pe('inv', '🎒')} <b>ИНВЕНТАРЬ</b></blockquote>\n"
        f"\n<blockquote>{_pe('boost', '⚡')} <b>Ускорители кирки</b>  <b>[{len(b_inv)}/{MAX_INVENTORY}]</b>{b_active_str}</blockquote>\n"
        f"\n<blockquote>{_pe('xp_boost', '🔮')} <b>XP-предметы</b>  <b>[{len(xp_inv)}/{MAX_XP_INVENTORY}]</b>{xp_active_str}</blockquote>\n"
        f'\n<blockquote><tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> <b>Усилители и яды</b>  <b>[{len(enh_inv)}/{MAX_ENH_INVENTORY}]</b>{enh_active_str}</blockquote>'
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
        lines = [f"<blockquote>{_pe('boost', '⚡')} <b>PICKAXE BOOSTERS</b>\n"]
        if active:
            left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
            mult = _multiplier_label(active["multiplier"])
            dur  = _dur_label(active["dur_key"], lang)
            lines.append(f"{_pe('ok', '✅')} <b>Active: {mult} for {dur}</b>\n{_pe('timer', '⏱')} <b>Left: {left}</b>")
        else:
            lines.append(f"{_pe('cancel', '❌')} <b>No active booster.</b>")
        lines.append("</blockquote>")
        if not inv:
            lines.append(f"\n<blockquote>{_pe('case', '📦')} <b>Inventory empty. Open a Booster case!</b></blockquote>")
        else:
            inv_lines = [f"\n<blockquote><b>In inventory ({len(inv)}/{MAX_INVENTORY}):</b>"]
            for i, item in enumerate(inv, 1):
                price = get_sell_price(item)
                inv_lines.append(f"\n<b>{i}. {_booster_name(item, lang)}</b>\n{_pe('coin', '💰')} <b>{_fmt_num(price)}</b>")
            inv_lines.append("</blockquote>")
            lines.extend(inv_lines)
    else:
        lines = [f"<blockquote>{_pe('boost', '⚡')} <b>УСКОРИТЕЛИ КИРКИ</b>\n"]
        if active:
            left = _fmt_time_left(active["ends_at"] - _now_ts(), lang)
            mult = _multiplier_label(active["multiplier"])
            dur  = _dur_label(active["dur_key"], lang)
            lines.append(f"{_pe('ok', '✅')} <b>Активен: {mult} на {dur}</b>\n{_pe('timer', '⏱')} <b>Осталось: {left}</b>")
        else:
            lines.append(f"{_pe('cancel', '❌')} <b>Нет активного ускорителя.</b>")
        lines.append("</blockquote>")
        if not inv:
            lines.append(f"\n<blockquote>{_pe('case', '📦')} <b>Инвентарь пуст. Открой Кейс ускорителей!</b></blockquote>")
        else:
            inv_lines = [f"\n<blockquote><b>В инвентаре ({len(inv)}/{MAX_INVENTORY}):</b>"]
            for i, item in enumerate(inv, 1):
                price = get_sell_price(item)
                inv_lines.append(f"\n<b>{i}. {_booster_name(item, lang)}</b>\n{_pe('coin', '💰')} <b>{_fmt_num(price)}</b>")
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
            f"\n\n<blockquote>{_pe('warn', '⚠️')} <b>{_L(lang, 'Активен', 'Active')}: {act_mult} {_L(lang, 'на', 'for')} {act_dur}</b>\n"
            f"{_pe('timer', '⏱')} <b>{_L(lang, 'Осталось', 'Left')}: {left}</b></blockquote>"
        )
    return (
        f"<blockquote>{_pe('boost', '⚡')} <b>{_booster_name(item, lang)}</b>\n"
        f"{_pe('timer', '⏱')} <b>{_L(lang, 'Длительность', 'Duration')}: {dur}</b>\n"
        f"{_pe('mult', '🔢')} <b>{_L(lang, 'Множитель', 'Multiplier')}: {mult}</b></blockquote>\n"
        f"\n<blockquote><b>{_L(lang, 'Эффект (все показатели кирки):', 'Effect (all pickaxe stats):')} </b>\n"
        f"<b>• {_L(lang, 'Ударов за кампанию', 'Hits per campaign')}: ×{mult}</b>\n"
        f"<b>• {_L(lang, 'Монет в час', 'Coins per hour')}: ×{mult}</b>\n"
        f"<b>• {_L(lang, 'Скорость добычи', 'Mining speed')}: ×{mult}</b></blockquote>\n"
        f"\n<blockquote>{_pe('coin', '💰')} <b>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</b></blockquote>"
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
        f"<blockquote>{_pe('warn', '⚠️')} <b>{_L(lang, 'Замена ускорителя', 'Replace booster')}</b>\n"
        f"<b>{_L(lang, 'Сейчас активен', 'Currently active')}: {act_mult} {_L(lang, 'на', 'for')} {act_dur}</b>\n"
        f"{_pe('timer', '⏱')} <b>{_L(lang, 'Осталось', 'Left')}: {left}</b></blockquote>\n"
        f"\n<blockquote><b>{_L(lang, 'Заменить на', 'Replace with')}: {new_mult} {_L(lang, 'на', 'for')} {new_dur}?</b>\n"
        f"{_pe('warn', '⚠️')} <b>{_L(lang, 'Старый ускоритель будет потерян!', 'Old booster will be lost!')}</b></blockquote>"
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
    lines = [f"<blockquote>{_pe('xp_boost', '🔮')} <b>{_L(lang, 'XP-ПРЕДМЕТЫ', 'XP ITEMS')}</b>\n"]
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        mult = _multiplier_label(xp_act["multiplier"])
        dur  = _dur_label(xp_act["dur_key"], lang)
        lines.append(
            f"{_pe('ok', '✅')} <b>{_L(lang, 'Активен XP-ускоритель', 'Active XP booster')}: ×{mult} {_L(lang, 'на', 'for')} {dur}</b>\n"
            f"{_pe('timer', '⏱')} <b>{_L(lang, 'Осталось', 'Left')}: {left}</b>"
        )
    else:
        lines.append(f"{_pe('cancel', '❌')} <b>{_L(lang, 'Нет активного XP-ускорителя.', 'No active XP booster.')}</b>")
    lines.append("</blockquote>")
    if not inv:
        lines.append(f"\n<blockquote>{_pe('xp_case', '🔮')} <b>{_L(lang, 'XP-инвентарь пуст. Открой XP-кейс!', 'XP inventory empty. Open an XP case!')}</b></blockquote>")
    else:
        inv_lines = [f"\n<blockquote><b>{_L(lang, 'В инвентаре', 'In inventory')} ({len(inv)}/{MAX_XP_INVENTORY}):</b>"]
        for i, item in enumerate(inv, 1):
            price = get_xp_sell_price(item)
            inv_lines.append(f"\n<b>{i}. {_xp_item_name(item, lang)}</b>\n{_pe('coin', '💰')} <b>{_fmt_num(price)}</b>")
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
            f"<blockquote>{_pe('xp_instant', '✨')} <b>{_L(lang, 'Моментальный опыт', 'Instant XP')}</b>\n"
            f"{_pe('xp_instant', '✨')} <b>{_L(lang, 'Опыт', 'XP')}: +{_fmt_num(item['xp'])} XP</b></blockquote>\n"
            f"\n<blockquote><b>{_L(lang, 'Применить — сразу получишь опыт.', 'Apply — you get XP immediately.')}</b>\n"
            f"<b>{_L(lang, 'Учитывает активный XP-ускоритель!', 'Counts active XP booster!')}</b></blockquote>\n"
            f"\n<blockquote>{_pe('coin', '💰')} <b>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</b></blockquote>"
        )
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    warning = ""
    if xp_act:
        left = _fmt_time_left(xp_act["ends_at"] - _now_ts(), lang)
        act_mult = _multiplier_label(xp_act["multiplier"])
        act_dur  = _dur_label(xp_act["dur_key"], lang)
        warning  = (
            f"\n\n<blockquote>{_pe('warn', '⚠️')} <b>{_L(lang, 'Активен', 'Active')}: ×{act_mult} {_L(lang, 'на', 'for')} {act_dur}</b>\n"
            f"{_pe('timer', '⏱')} <b>{_L(lang, 'Осталось', 'Left')}: {left}</b></blockquote>"
        )
    return (
        f"<blockquote>{_pe('xp_boost', '🔮')} <b>{_L(lang, 'XP-ускоритель', 'XP booster')} {mult}</b>\n"
        f"{_pe('mult', '🔢')} <b>{_L(lang, 'Множитель', 'Multiplier')}: ×{mult}</b>\n"
        f"{_pe('timer', '⏱')} <b>{_L(lang, 'Длительность', 'Duration')}: {dur}</b></blockquote>\n"
        f"\n<blockquote><b>{_L(lang, f'Умножает весь получаемый опыт на {mult} на {dur}.', f'Multiplies all XP gained by {mult} for {dur}.')}</b></blockquote>\n"
        f"\n<blockquote>{_pe('coin', '💰')} <b>{_L(lang, 'Цена продажи', 'Sell price')}: {_fmt_num(price)}</b></blockquote>"
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
        f"<blockquote>{_pe('warn', '⚠️')} <b>{_L(lang, 'Замена XP-ускорителя', 'Replace XP booster')}</b>\n"
        f"<b>{_L(lang, 'Сейчас активен', 'Currently active')}: ×{act_mult} {_L(lang, 'на', 'for')} {act_dur}</b>\n"
        f"{_pe('timer', '⏱')} <b>{_L(lang, 'Осталось', 'Left')}: {left}</b></blockquote>\n"
        f"\n<blockquote><b>{_L(lang, 'Заменить на', 'Replace with')}: ×{new_mult} {_L(lang, 'на', 'for')} {new_dur}?</b>\n"
        f"{_pe('warn', '⚠️')} <b>{_L(lang, 'Старый XP-ускоритель будет потерян!', 'Old XP booster will be lost!')}</b></blockquote>"
    )


def xp_confirm_replace_keyboard(instance_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_L(lang, "Да, заменить", "Yes, replace"), callback_data=f"xp_replace_{instance_id}",  icon_custom_emoji_id=_E["ok"]),
        InlineKeyboardButton(text=_L(lang, "Отмена", "Cancel"),             callback_data=f"xp_info_{instance_id}",     icon_custom_emoji_id=_E["cancel"]),
    )
    return builder.as_markup()
