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
    COIN,
)


def _btn(emoji_id: str, label: str, cb: str, style: str = None) -> InlineKeyboardButton:
    kwargs = {"text": label, "callback_data": cb, "icon_custom_emoji_id": emoji_id}
    if style:
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def _back_btn(cb: str, label: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=EMOJI_BACK)


def _L(lang: str, ru: str, en: str) -> str:
    """Inline двуязычная строка без обращения к lang.py."""
    return en if lang == "en" else ru


# Независимая от miner.py константа для отображения цены в Stars.
# Кейсы артефактов оплачиваются Telegram Stars и не должны зависеть от
# того, что происходит с покупкой кирок в miner.py (см. баг: убрали
# кирки за звёзды из miner.py — заодно пропала общая константа STAR,
# и кейсы перестали открываться после оплаты).
STAR = '<tg-emoji emoji-id="5798819377088307477">⭐</tg-emoji>'

# Самосветы (донатная валюта, см. donate.py) — используется для покупки
# артефактов и статусов вместо прямой оплаты Stars.
SAMOSVET_EMOJI_ID = "5465501598199342448"
SAMOSVET = f'<tg-emoji emoji-id="{SAMOSVET_EMOJI_ID}">💠</tg-emoji>'


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
    "art_locked": "5296369303661067030",
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
#  МАГАЗИН АРТЕФАКТОВ (прямая покупка за Самосветы)
#  Раньше здесь был гача-кейс артефактов (случайный дроп за Stars).
#  Теперь каждый артефакт — самостоятельный товар с фиксированной
#  ценой в Самосветах: игрок открывает отдельное окно артефакта с
#  описанием и жмёт «Купить», без рандома. Ключи "key" у первых 10
#  артефактов оставлены без изменений — это сохраняет совместимость с
#  уже выданными артефактами в data["artifacts"] у существующих игроков.
# ============================================================

ARTIFACT_SHOP_POOL = [
    # ── Tier 1: 1.25× — 169⭐ ────────────────────────────────
    {"key": "art_kulon_iskazheniya",        "type": "artifact", "name": "Кулон Искажения",             "name_en": "Distortion Pendant",       "emoji_id": "5938541999031325561", "effect": "mine",   "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},
    {"key": "art_oracle",                   "type": "artifact", "name": "Оракул",                      "name_en": "Oracle",                   "emoji_id": "5165898384870999138", "effect": "damage", "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},
    {"key": "art_amulet_hranitelya",        "type": "artifact", "name": "Амулет Хранителя",            "name_en": "Guardian Amulet",           "emoji_id": "5938082716703528871", "effect": "pets",   "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},
    {"key": "art_oskolok_zvezdnoy_pyli",    "type": "artifact", "name": "Осколок Звёздной Пыли",       "name_en": "Shard of Stardust",         "emoji_id": "5399955939086314661",                     "effect": "mine",   "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},
    {"key": "art_klinok_nemezidy",          "type": "artifact", "name": "Клинок Немезиды",             "name_en": "Blade of Nemesis",          "emoji_id": "5467879180425252211",                     "effect": "damage", "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},
    {"key": "art_osheynik_vernosti",        "type": "artifact", "name": "Ошейник Верности",            "name_en": "Collar of Loyalty",         "emoji_id": "5296313099719043752",                     "effect": "pets",   "multiplier": 1.25, "price_samosvety": 169, "tier": "t125"},

    # ── Tier 2: 1.4× — 249⭐ ─────────────────────────────────
    {"key": "art_lunnaya_relikviya",        "type": "artifact", "name": "Лунная Реликвия",             "name_en": "Lunar Relic",               "emoji_id": "5226662903569989373", "effect": "mine",   "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},
    {"key": "art_sfera_zhadnosti",          "type": "artifact", "name": "Сфера Жадности",              "name_en": "Sphere of Greed",           "emoji_id": "5080262187302257610", "effect": "damage", "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},
    {"key": "art_amulet_zhizni",            "type": "artifact", "name": "Амулет Жизни и Смерти",       "name_en": "Amulet of Life & Death",    "emoji_id": "6228938636428052300", "effect": "pets",   "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},
    {"key": "art_zhezl_glubin",             "type": "artifact", "name": "Жезл Глубин",                 "name_en": "Rod of the Depths",         "emoji_id": "5170593338176308141",                     "effect": "mine",   "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},
    {"key": "art_pechat_vozmezdiya",        "type": "artifact", "name": "Печать Возмездия",            "name_en": "Seal of Retribution",       "emoji_id": "5298737505678407110",                     "effect": "damage", "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},
    {"key": "art_svistok_povelitelya_zverey","type": "artifact", "name": "Свисток Повелителя Зверей",  "name_en": "Beastmaster's Whistle",     "emoji_id": "5397797168264260168",                     "effect": "pets",   "multiplier": 1.4, "price_samosvety": 249, "tier": "t140"},

    # ── Tier 3: 1.65× — 359⭐ ────────────────────────────────
    {"key": "art_sfera_illyuziy",           "type": "artifact", "name": "Сфера Иллюзий",               "name_en": "Sphere of Illusions",       "emoji_id": "5343583990815156847", "effect": "mine",   "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},
    {"key": "art_serdtse_morey",            "type": "artifact", "name": "Сердце Морей",                "name_en": "Heart of the Seas",         "emoji_id": "6201647288947839133", "effect": "damage", "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},
    {"key": "art_kristall_egzorcizma",      "type": "artifact", "name": "Кристалл Экзорцизма",         "name_en": "Exorcism Crystal",          "emoji_id": "5451889386549425709", "effect": "pets",   "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},
    {"key": "art_korona_podzemnogo_korolya","type": "artifact", "name": "Корона Подземного Короля",    "name_en": "Crown of the Underground King", "emoji_id": "5433758796289685818",                  "effect": "mine",   "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},
    {"key": "art_sekira_titana",            "type": "artifact", "name": "Секира Титана",               "name_en": "Titan's Axe",               "emoji_id": "4978927175597032385",                     "effect": "damage", "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},
    {"key": "art_totem_drevnego_lesa",      "type": "artifact", "name": "Тотем Древнего Леса",         "name_en": "Totem of the Ancient Forest","emoji_id": "5323638849887290800",                    "effect": "pets",   "multiplier": 1.65, "price_samosvety": 359, "tier": "t165"},

    # ── Tier 4: 1.8× — 489⭐ (новый) ─────────────────────────
    {"key": "art_serdtse_gory",             "type": "artifact", "name": "Сердце Горы",                 "name_en": "Heart of the Mountain",     "emoji_id": "5087371165630989886",                     "effect": "mine",   "multiplier": 1.8, "price_samosvety": 489, "tier": "t180"},
    {"key": "art_kogot_drakona",            "type": "artifact", "name": "Коготь Дракона",              "name_en": "Dragon's Claw",             "emoji_id": "5364278388787786116",                     "effect": "damage", "multiplier": 1.8, "price_samosvety": 489, "tier": "t180"},
    {"key": "art_svitok_prirucheniya",      "type": "artifact", "name": "Свиток Приручения",           "name_en": "Scroll of Taming",          "emoji_id": "5240116609451842590",                     "effect": "pets",   "multiplier": 1.8, "price_samosvety": 489, "tier": "t180"},

    # ── Легендарные — множат ВСЕ три вида добычи сразу ──────
    {"key": "art_vsevlastniy",              "type": "artifact", "name": "Кольцо Перерождений",         "name_en": "Ring of Rebirths",          "emoji_id": "5872990619021875271", "effect": "all", "multiplier": 1.35, "price_samosvety": 699,  "tier": "tall"},
    {"key": "art_korona_vechnosti",         "type": "artifact", "name": "Корона Вечности",             "name_en": "Crown of Eternity",         "emoji_id": "5474515531962795294",                     "effect": "all", "multiplier": 1.6,  "price_samosvety": 999,  "tier": "tall"},
    {"key": "art_serdtse_vselennoy",        "type": "artifact", "name": "Сердце Вселенной",            "name_en": "Heart of the Universe",     "emoji_id": "5453997820354771233",                     "effect": "all", "multiplier": 1.95, "price_samosvety": 1399, "tier": "tall"},
    {"key": "art_tron_bogov",               "type": "artifact", "name": "Трон Гибели",                 "name_en": "Throne of Doom",        "emoji_id": "5249396161172757849",                     "effect": "all", "multiplier": 2.25, "price_samosvety": 1899, "tier": "tall"},
]

# Обратная совместимость: часть кода (и, возможно, внешние модули)
# может ссылаться на старое имя _ARTIFACT_POOL.
_ARTIFACT_POOL = ARTIFACT_SHOP_POOL
ARTIFACT_POOL_BY_KEY = {a["key"]: a for a in ARTIFACT_SHOP_POOL}
MAX_ARTIFACTS = len(ARTIFACT_SHOP_POOL)

# Обычные и редкие артефакты можно купить и за монеты (без Stars).
# Эпические/мифические/легендарные — только за Stars.
ARTIFACT_COIN_PRICE_BY_TIER = {"t125": 280_000_000_000_000, "t140": 550_000_000_000_000}
for _a in ARTIFACT_SHOP_POOL:
    _cp = ARTIFACT_COIN_PRICE_BY_TIER.get(_a["tier"])
    if _cp:
        _a["price_coins"] = _cp
del _a, _cp

ARTIFACT_TIERS = [
    {"tier": "t125", "multiplier": 1.25, "price_samosvety": 169,  "price_coins": 280_000_000_000_000, "name": "Обычные",     "name_en": "Common",    "icon": "🔹"},
    {"tier": "t140", "multiplier": 1.4,  "price_samosvety": 249,  "price_coins": 550_000_000_000_000, "name": "Редкие",      "name_en": "Rare",      "icon": "🔷"},
    {"tier": "t165", "multiplier": 1.65, "price_samosvety": 359,  "name": "Эпические",   "name_en": "Epic",      "icon": "💠"},
    {"tier": "t180", "multiplier": 1.8,  "price_samosvety": 489,  "name": "Мифические",  "name_en": "Mythic",    "icon": "🔶"},
    {"tier": "tall", "multiplier": None, "price_samosvety": None, "name": "Легендарные (× ко всей добыче)", "name_en": "Legendary (× to all income)", "icon": "👑"},
]
ARTIFACT_TIERS_BY_KEY = {t["tier"]: t for t in ARTIFACT_TIERS}

# 5 эмодзи "редкости" — все подходят одинаково, поэтому раздаём их по
# тирам случайно (порядок не важен, тиров и айди поровну — по 5).
_ARTIFACT_TIER_ICON_IDS = [
    "5251280754167539397",
    "5251575062506531550",
    "5251553162468284915",
    "5251661382759243996",
    "5251329454801710673",
]
_shuffled_tier_icon_ids = _ARTIFACT_TIER_ICON_IDS[:]
random.shuffle(_shuffled_tier_icon_ids)
for _t, _icon_id in zip(ARTIFACT_TIERS, _shuffled_tier_icon_ids):
    _t["icon_id"] = _icon_id
del _t, _icon_id


def _tier_icon(t: dict) -> str:
    icon_id = t.get("icon_id") if t else None
    if icon_id:
        return f'<tg-emoji emoji-id="{icon_id}">{t["icon"]}</tg-emoji>'
    return t["icon"] if t else "💎"


def artifacts_in_tier(tier_key: str) -> list:
    return [a for a in ARTIFACT_SHOP_POOL if a["tier"] == tier_key]


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

_ARTIFACT_EFFECT_ICONS = {
    "mine":   "⛏️",
    "damage": "⚔️",
    "pets":   "🐾",
    "all":    "✨",
}

def _get_effect_label(effect: str, lang: str = "ru") -> str:
    return (_ARTIFACT_EFFECT_LABELS_EN if lang == "en" else _ARTIFACT_EFFECT_LABELS).get(effect, "")

def _artifact_icon(a: dict) -> str:
    eid = a.get("emoji_id", "")
    if eid:
        return f'<tg-emoji emoji-id="{eid}">💎</tg-emoji>'
    return _ARTIFACT_EFFECT_ICONS.get(a.get("effect"), "💎")

def _artifact_desc(a: dict, lang: str = "ru") -> str:
    effect_label = _get_effect_label(a["effect"], lang)
    name = a.get("name_en", a["name"]) if lang == "en" else a["name"]
    return f'{_artifact_icon(a)} <b><i>{name}</i></b> — {a["multiplier"]}× {effect_label}'


def is_artifact_owned(data: dict, artifact_key: str) -> bool:
    return any(entry["key"] == artifact_key for entry in data.get("artifacts", []))


def buy_artifact(data: dict, artifact_key: str, lang: str = "ru") -> tuple:
    """
    Выдаёт артефакт покупателю. Вызывается ПОСЛЕ того, как оплата (списание
    Самосветов) уже произведена — эта функция только добавляет артефакт
    в коллекцию, без рандома.
    Возвращает (ok, сообщение).
    """
    art = ARTIFACT_POOL_BY_KEY.get(artifact_key)
    if not art:
        err = "Неизвестный артефакт." if lang == "ru" else "Unknown artifact."
        return False, f"❌ {err}"

    if is_artifact_owned(data, artifact_key):
        err = (
            "Этот артефакт у тебя уже есть — покупать второй раз не нужно."
            if lang == "ru"
            else "You already own this artifact — no need to buy it again."
        )
        return False, f"⚠️ {err}"

    artifacts = data.setdefault("artifacts", [])
    artifacts.append({"key": artifact_key})
    data["artifacts_bought"] = data.get("artifacts_bought", 0) + 1

    name = art.get("name_en", art["name"]) if lang == "en" else art["name"]
    msg = (
        f"<blockquote>{_pe('ok', '✅')} <b><i>{_L(lang, 'Артефакт куплен!', 'Artifact purchased!')}</i></b>\n"
        f"{_artifact_desc(art, lang)}</blockquote>\n"
        f"\n<blockquote>{_pe('stats', '💎')} <b><i>{_L(lang, 'Коллекция', 'Collection')}: {len(artifacts)}/{MAX_ARTIFACTS}</i></b></blockquote>"
    )
    return True, msg


def get_samosvety(data: dict) -> int:
    """Текущий баланс Самосветов пользователя (донатная валюта, см. donate.py)."""
    return data.get("samosvety", 0)


def _artifact_insufficient_samosvety_text(cost: int, balance: int, lang: str = "ru") -> str:
    """Текст-инструкция при нехватке Самосветов для покупки артефакта."""
    missing = cost - balance
    return (
        f'<blockquote>'
        f'{_pe("warn", "⚠️")} <b><i>{_L(lang, "Недостаточно Самосветов", "Not enough Samosvety")}</i></b>\n'
        f'{SAMOSVET} <b><i>{_L(lang, f"Нужно: {cost} · У тебя: {balance}", f"Needed: {cost} · You have: {balance}")}</i></b>\n'
        f'{SAMOSVET} <b><i>{_L(lang, f"Не хватает: {missing}", f"Missing: {missing}")}</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_pe("ok", "🎁")} <b><i>{_L(lang, "Пополни баланс в разделе «Донат» — Самосветы можно купить за Telegram Stars или крипту.", "Top up your balance in the “Donate” section — you can buy Samosvety with Telegram Stars or crypto.")}</i></b>'
        f'</blockquote>'
    )


def artifact_insufficient_keyboard(artifact_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура при нехватке Самосветов на артефакт — ведёт в раздел Донат."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Пополнить Самосветы (Донат)", "Top up Samosvety (Donate)"),
        callback_data="donate_main",
        icon_custom_emoji_id=SAMOSVET_EMOJI_ID,
    ))
    builder.row(_back_btn(f"artifact_info_{artifact_key}", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def buy_artifact_with_samosvety(data: dict, artifact_key: str, lang: str = "ru") -> tuple:
    """
    Покупка артефакта за Самосветы. Списывает Самосветы с data["samosvety"]
    и сразу выдаёт артефакт через buy_artifact() — без инвойса.
    Возвращает (ok, сообщение). Если Самосветов не хватает — ok=False и
    текст с инструкцией, как пополнить баланс (раздел «Донат»).
    """
    art = ARTIFACT_POOL_BY_KEY.get(artifact_key)
    if not art:
        err = "Неизвестный артефакт." if lang == "ru" else "Unknown artifact."
        return False, f"❌ {err}"

    if is_artifact_owned(data, artifact_key):
        err = (
            "Этот артефакт у тебя уже есть — покупать второй раз не нужно."
            if lang == "ru"
            else "You already own this artifact — no need to buy it again."
        )
        return False, f"⚠️ {err}"

    cost = art["price_samosvety"]
    balance = get_samosvety(data)
    if balance < cost:
        return False, _artifact_insufficient_samosvety_text(cost, balance, lang)

    data["samosvety"] = balance - cost
    ok, msg = buy_artifact(data, artifact_key, lang)
    if not ok:
        # откатываем списание, если выдача неожиданно не удалась
        data["samosvety"] = balance
        return ok, msg

    new_balance = data["samosvety"]
    spent_line = f'\n{SAMOSVET} <b><i>{_L(lang, f"Потрачено: {cost} Самосветов · Остаток: {new_balance}", f"Spent: {cost} Samosvety · Balance: {new_balance}")}</i></b>'
    return ok, msg + spent_line


def buy_artifact_with_coins(data: dict, artifact_key: str, lang: str = "ru") -> tuple:
    """
    Покупка артефакта за монеты вместо Самосветов. Доступно только для
    артефактов с заданным "price_coins" (тиры t125/t140 — обычные и
    редкие). Списывает баланс сразу же, без инвойса.
    Возвращает (ok, сообщение).
    """
    art = ARTIFACT_POOL_BY_KEY.get(artifact_key)
    if not art:
        err = "Неизвестный артефакт." if lang == "ru" else "Unknown artifact."
        return False, f"❌ {err}"

    if is_artifact_owned(data, artifact_key):
        err = (
            "Этот артефакт у тебя уже есть — покупать второй раз не нужно."
            if lang == "ru"
            else "You already own this artifact — no need to buy it again."
        )
        return False, f"⚠️ {err}"

    cost = art.get("price_coins")
    if not cost:
        err = (
            "Этот артефакт нельзя купить за монеты — только за Самосветы."
            if lang == "ru"
            else "This artifact can't be bought with coins — Samosvety only."
        )
        return False, f"❌ {err}"

    if data.get("balance", 0) < cost:
        err = f"❌ {_L(lang, 'Недостаточно монет!', 'Not enough coins!')}\n{_L(lang, 'Нужно', 'Need')}: {_fmt_num(cost)} {_pe('coin', '💰')}"
        return False, err

    data["balance"] -= cost
    artifacts = data.setdefault("artifacts", [])
    artifacts.append({"key": artifact_key})
    data["artifacts_bought"] = data.get("artifacts_bought", 0) + 1

    msg = (
        f"<blockquote>{_pe('ok', '✅')} <b><i>{_L(lang, 'Артефакт куплен!', 'Artifact purchased!')}</i></b>\n"
        f"{_artifact_desc(art, lang)}</blockquote>\n"
        f"\n<blockquote>{_pe('spent', '💰')} <b><i>{_L(lang, 'Потрачено', 'Spent')}: {_fmt_num(cost)}</i></b> {_pe('coin', '💰')}\n"
        f"{_pe('stats', '💎')} <b><i>{_L(lang, 'Коллекция', 'Collection')}: {len(artifacts)}/{MAX_ARTIFACTS}</i></b></blockquote>"
    )
    return True, msg


def get_artifact_mine_multiplier(data: dict) -> float:
    """
    Бонусы артефактов складываются, а не перемножаются: два артефакта
    по +25% (multiplier=1.25) дают в сумме +50% (1.5), а не +56.25% (1.25*1.25).
    """
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("mine", "all"):
            total += a["multiplier"] - 1
    return round(total, 4)


def get_artifact_damage_multiplier(data: dict) -> float:
    """См. комментарий в get_artifact_mine_multiplier — бонусы складываются."""
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("damage", "all"):
            total += a["multiplier"] - 1
    return round(total, 4)


def get_artifact_pets_multiplier(data: dict) -> float:
    """См. комментарий в get_artifact_mine_multiplier — бонусы складываются."""
    total = 1.0
    for entry in data.get("artifacts", []):
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a and a["effect"] in ("pets", "all"):
            total += a["multiplier"] - 1
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
    Сокращённый формат чисел: 1500 -> "1.5K", 100000 -> "100K",
    2300000 -> "2.3M", 1_500_000_000 -> "1.5B" и т.д.
    Единый стиль со всем ботом (см. database.py -> format_amount).
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


def _multiplier_label(mult: float) -> str:
    s = f"{mult}"
    if s.endswith(".0"):
        s = s[:-2]
    return f"{s}×"


def _booster_name(b: dict, lang: str = "ru") -> str:
    dur = _dur_label(b['dur_key'], lang)
    cnt = b.get("count", 1)
    suffix = f" ×{cnt}" if cnt > 1 else ""
    if lang == "en":
        return f"Booster {_multiplier_label(b['multiplier'])} for {dur}{suffix}"
    return f"Ускоритель {_multiplier_label(b['multiplier'])} на {dur}{suffix}"


def _xp_item_name(item: dict, lang: str = "ru") -> str:
    cnt = item.get("count", 1)
    suffix = f" ×{cnt}" if cnt > 1 else ""
    if item["type"] == "xp_instant":
        return f"{_pe('xp_instant', '✨')} {_fmt_num(item['xp'])} XP{suffix}"
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f"{_pe('xp_boost', '🔮')} XP booster {mult} for {dur}{suffix}"
    return f"{_pe('xp_boost', '🔮')} XP-ускоритель {mult} на {dur}{suffix}"


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
        cnt = item.get("count", 1)
        suffix = f" ×{cnt}" if cnt > 1 else ""
        return f'{_pe("poison", "☠️")} {pname} — {dmg} {dmg_label}{suffix}'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    cnt = item.get("count", 1)
    suffix = f" ×{cnt}" if cnt > 1 else ""
    if lang == "en":
        return f'{_pe("enh_boost", "⚡")} Damage booster {mult} for {dur}{suffix}'
    return f'{_pe("enh_boost", "⚡")} Усилитель {mult} на {dur}{suffix}'


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
        cnt = item.get("count", 1)
        suffix = f" ×{cnt}" if cnt > 1 else ""
        return f'{pname} — {dmg} {dmg_label}{suffix}'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    cnt = item.get("count", 1)
    suffix = f" ×{cnt}" if cnt > 1 else ""
    if lang == "en":
        return f'Damage booster {mult} for {dur}{suffix}'
    return f'Усилитель {mult} на {dur}{suffix}'


def _xp_item_name_plain(item: dict, lang: str = "ru") -> str:
    """Без HTML-тегов — для текста кнопок клавиатуры."""
    cnt = item.get("count", 1)
    suffix = f" ×{cnt}" if cnt > 1 else ""
    if item["type"] == "xp_instant":
        return f'{_fmt_num(item["xp"])} XP{suffix}'
    mult = _multiplier_label(item["multiplier"])
    dur  = _dur_label(item["dur_key"], lang)
    if lang == "en":
        return f'XP booster {mult} for {dur}{suffix}'
    return f'XP-ускоритель {mult} на {dur}{suffix}'


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


# ============================================================
#  УВЕДОМЛЕНИЯ ОБ ОКОНЧАНИИ УСКОРИТЕЛЕЙ / ЯДОВ
# ============================================================
#  Вызывается фоновым циклом _boosters_expiry_loop в mainhelp.py.
#  Флаг "notified_expired" хранится ВНУТРИ самого объекта активного
#  бустера (active_booster / active_xp_booster / active_enh_booster /
#  active_poison) — переживает рестарт бота и не требует отдельной
#  таблицы или доп. похода в БД.
#
#  Сами объекты здесь НЕ удаляются и не обнуляются — их по-прежнему
#  лениво чистят get_active_*_multiplier/_info при первом реальном
#  обращении (mine.py/hunt.py/pets.py), чтобы не было двух разных
#  мест, которые могут разойтись в логике "когда именно бустер
#  считается закончившимся".
# ============================================================

_BOOST_FIELDS = ("active_booster", "active_xp_booster", "active_enh_booster", "active_poison")

_POISON_NAMES_EN = {
    "Яд Гадюки":       "Viper Venom",
    "Яд Кобры":        "Cobra Venom",
    "Яд Чёрной Мамбы": "Black Mamba Venom",
    "Яд Василиска":    "Basilisk Venom",
    "Яд Левиафана":    "Leviathan Venom",
}


def _boost_expired_text(field: str, b: dict, lang: str = "ru") -> str:
    if field == "active_booster":
        mult = _multiplier_label(b.get("multiplier", 1))
        if lang == "en":
            return (
                f'{_pe("boost", "⚡")} <b><i>Your pickaxe booster {mult} has ended.</i></b>\n'
                f'<i>Pickaxe stats are back to normal.</i>'
            )
        return (
            f'{_pe("boost", "⚡")} <b><i>Ускоритель кирки {mult} закончился.</i></b>\n'
            f'<i>Показатели кирки вернулись к обычным.</i>'
        )
    if field == "active_xp_booster":
        mult = _multiplier_label(b.get("multiplier", 1))
        if lang == "en":
            return (
                f'{_pe("xp_boost", "🔮")} <b><i>Your XP booster {mult} has ended.</i></b>\n'
                f'<i>XP gain is back to normal.</i>'
            )
        return (
            f'{_pe("xp_boost", "🔮")} <b><i>XP-ускоритель {mult} закончился.</i></b>\n'
            f'<i>Получение опыта вернулось к обычному.</i>'
        )
    if field == "active_enh_booster":
        mult = _multiplier_label(b.get("multiplier", 1))
        if lang == "en":
            return (
                f'{_pe("enh_boost", "⚡")} <b><i>Your damage booster {mult} has ended.</i></b>\n'
                f'<i>Boss damage is back to normal.</i>'
            )
        return (
            f'{_pe("enh_boost", "⚡")} <b><i>Усилитель урона {mult} закончился.</i></b>\n'
            f'<i>Урон по боссу вернулся к обычному.</i>'
        )
    if field == "active_poison":
        name  = b.get("name", "")
        pname = _POISON_NAMES_EN.get(name, name) if lang == "en" else name
        if lang == "en":
            return f'{_pe("poison", "☠️")} <b><i>{pname} has stopped applying damage.</i></b>'
        return f'{_pe("poison", "☠️")} <b><i>{pname} перестал наносить урон.</i></b>'
    return ""


def collect_expired_boost_notifications(data: dict, lang: str = "ru", now: float | None = None) -> list:
    """
    Проходит по всем активным ускорителям/ядам игрока. Для каждого, что
    только что истёк (ends_at <= now) и ещё НЕ уведомлён (нет флага
    notified_expired) — ставит notified_expired=True (мутирует data на
    месте) и добавляет готовый HTML-текст уведомления в результат.

    Ничего не пишет в БД и не шлёт сообщений сама — только готовит
    тексты и мутирует переданный data. Вызывающий код (фоновый цикл в
    mainhelp.py) должен сам сохранить data, если список непустой, и
    сам отправить тексты через bot.send_message.
    """
    if now is None:
        now = _now_ts()
    out = []
    for field in _BOOST_FIELDS:
        b = data.get(field)
        if b and b.get("ends_at", 0) <= now and not b.get("notified_expired"):
            b["notified_expired"] = True
            out.append(_boost_expired_text(field, b, lang))
    return out


# ============================================================
#  АНТИСПАМ: ЛИМИТ НА ОТКРЫТИЕ КЕЙСОВ
# ============================================================

CASE_OPEN_COOLDOWN_BUTTON_SEC  = 1   # открытие кнопкой (одиночный кейс)
CASE_OPEN_COOLDOWN_COMMAND_SEC = 1   # открытие текстовой командой (в т.ч. массовое)


def _check_case_cooldown(data: dict, lang: str = "ru", via_command: bool = False) -> tuple[bool, str]:
    """
    Проверяет, прошло ли достаточно времени с последнего открытия кейса.
    via_command=True — открытие через текстовую команду (1 сек),
    via_command=False — открытие кнопкой (1 сек).
    Возвращает (ok, сообщение_об_ошибке).
    Метку времени ставит _mark_case_opened() ПОСЛЕ успешного открытия —
    сама проверка data не меняет.
    """
    cooldown = CASE_OPEN_COOLDOWN_COMMAND_SEC if via_command else CASE_OPEN_COOLDOWN_BUTTON_SEC
    last_ts = data.get("last_case_open_ts", 0)
    elapsed = _now_ts() - last_ts
    if elapsed < cooldown:
        wait = int(cooldown - elapsed) + 1
        err = (
            f"Слишком быстро! Подожди ещё {wait} сек. перед открытием кейса."
            if lang == "ru"
            else f"Too fast! Wait {wait} more sec. before opening a case."
        )
        return False, f"⏳ {err}"
    return True, ""


def _mark_case_opened(data: dict) -> None:
    data["last_case_open_ts"] = _now_ts()


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
#  СТЕКИНГ ПРЕДМЕТОВ ИНВЕНТАРЯ
#  Одинаковые предметы (одинаковый key) хранятся ОДНОЙ записью
#  с полем "count", а не отдельной записью на каждый дроп.
#  Это предотвращает бесконечный рост data_json у активных игроков
#  (раньше каждый кейс добавлял новую запись — за месяцы игры
#  набирались тысячи записей и JSON разрастался до мегабайт).
# ============================================================

def _add_or_stack(inv: list, key: str, build_instance, qty: int = 1) -> dict:
    """
    Добавляет qty предметов в инвентарь со стекингом по key.
    Если предмет с таким key уже есть — увеличивает его count.
    Иначе создаёт новую запись через build_instance() (dict без
    instance_id/count) с count=qty.
    Возвращает актуальный объект стопки.
    """
    existing = next((x for x in inv if x.get("key") == key), None)
    if existing is not None:
        existing["count"] = existing.get("count", 1) + qty
        return existing
    instance = build_instance()
    instance["instance_id"] = f"stack_{key}"
    instance["count"] = qty
    inv.append(instance)
    return instance


def _remove_qty_by_key(inv: list, key: str, qty: int = 1) -> list:
    """
    Убирает qty штук предметов с данным key из инвентаря.
    Совместимо и со старыми (не застекованными, по одной записи на
    предмет) данными, и с новыми (с полем count) — считает их
    эквивалентно, работает по общему количеству.
    """
    new_inv = []
    left = qty
    for item in inv:
        if item.get("key") == key and left > 0:
            cnt = item.get("count", 1)
            if cnt <= left:
                left -= cnt
                continue
            item["count"] = cnt - left
            left = 0
            new_inv.append(item)
        else:
            new_inv.append(item)
    return new_inv


# ============================================================
#  ЛОГИКА
# ============================================================

def open_case(data: dict, case_key: str, lang: str = "ru", _check_cooldown: bool = True, via_command: bool = False) -> tuple:
    case = CASES.get(case_key)
    if not case:
        return False, _L(lang, "❌ Неизвестный кейс.", "❌ Unknown case."), None
    if _check_cooldown:
        ok_cd, err_cd = _check_case_cooldown(data, lang, via_command=via_command)
        if not ok_cd:
            return False, err_cd, None
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
        instance = _add_or_stack(inv, dropped["key"], lambda: {
            "key":          dropped["key"],
            "multiplier":   dropped["multiplier"],
            "dur_key":      dropped["dur_key"],
            "duration_sec": _DUR[dropped["dur_key"]],
            "chance":       dropped["chance"],
        })
        name     = f"{_pe('boost', '⚡')} {_booster_name(dropped, lang)}"
        inv_line = f"{_L(lang, 'В инвентаре', 'In inventory')}: {sum(x.get('count', 1) for x in inv)}"
    elif case["type"] == "enhancer":
        def _build_enh():
            inst = {
                "key":    dropped["key"],
                "type":   dropped["type"],
                "chance": dropped["chance"],
            }
            if dropped["type"] == "poison":
                inst["name"]         = dropped["name"]
                inst["damage"]       = dropped["damage"]
                inst["dur_key"]      = dropped["dur_key"]
                inst["duration_sec"] = _DUR[dropped["dur_key"]]
            else:
                inst["multiplier"]   = dropped["multiplier"]
                inst["dur_key"]      = dropped["dur_key"]
                inst["duration_sec"] = _DUR[dropped["dur_key"]]
            return inst
        instance = _add_or_stack(inv, dropped["key"], _build_enh)
        name     = _enh_item_name(instance, lang)
        inv_line = f"{_L(lang, 'В инвентаре усилителей', 'Enhancer inventory')}: {sum(x.get('count', 1) for x in inv)}"
    else:
        if dropped["type"] == "xp_instant":
            instance = {
                "instance_id": instance_id,
                "key":         dropped["key"],
                "type":        dropped["type"],
                "chance":      dropped["chance"],
                "xp":          dropped["xp"],
            }
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
            _mark_case_opened(data)
            return True, msg, instance
        else:
            def _build_xp():
                return {
                    "key":          dropped["key"],
                    "type":         dropped["type"],
                    "chance":       dropped["chance"],
                    "multiplier":   dropped["multiplier"],
                    "dur_key":      dropped["dur_key"],
                    "duration_sec": _DUR[dropped["dur_key"]],
                }
            instance = _add_or_stack(inv, dropped["key"], _build_xp)
            name = _xp_item_name(dropped, lang)
        inv_line = f"{_L(lang, 'В XP-инвентаре', 'XP inventory')}: {sum(x.get('count', 1) for x in inv)}"
    data["cases_total_opened"] = data.get("cases_total_opened", 0) + 1
    data["cases_total_spent"]  = data.get("cases_total_spent",  0) + cost
    msg = (
        f"<blockquote>{_pe('case', '📦')} <b><i>{_L(lang, 'Кейс открыт!', 'Case opened!')}</i></b>\n"
        f"{_pe('arrow', '➡️')} <b><i>{_L(lang, 'Выпало', 'Dropped')}:</i></b> {name}</blockquote>\n"
        f"\n<blockquote>{_pe('spent', '💸')} <b><i>{_L(lang, 'Потрачено', 'Spent')}: {_fmt_num(cost)}</i></b> {_pe('coin', '💰')}\n"
        f"{_pe('balance', '💰')} <b><i>{_L(lang, 'Баланс', 'Balance')}: {_fmt_num(data['balance'])}</i></b> {_pe('coin', '💰')}\n"
        f"{_pe('inv', '🎒')} <b><i>{inv_line}</i></b></blockquote>"
    )
    _mark_case_opened(data)
    return True, msg, instance


# ============================================================
#  МАППИНГ НОМЕР КЕЙСА → КЛЮЧ
# ============================================================

CASE_NUM_TO_KEY = {1: "common", 2: "xp", 3: "enhancer"}
CASE_KEY_TO_NUM = {v: k for k, v in CASE_NUM_TO_KEY.items()}


def open_case_multi(data: dict, case_num: int, qty: int, lang: str = "ru", via_command: bool = True, chat_type: str = "private") -> tuple:
    """
    Открывает qty кейсов с номером case_num (#1/#2/#3).
    Команды: открыть #1 5  /купить #2 10  open #1 5  /open #3 3
    via_command: True — вызов текстовой командой (кулдаун 1 сек, по умолчанию),
                 False — вызов кнопкой (кулдаун 1 сек).
    chat_type: тип чата, откуда пришла команда ("private", "group", "supergroup", "channel").
               Текстовые команды (via_command=True) работают только в личных сообщениях —
               в группах/супергруппах открытие кейсов доступно только через меню (кнопки),
               т.е. с via_command=False.
    Возвращает (ok, итоговое_сообщение).
    """
    if via_command and chat_type != "private":
        err = (
            "Эта команда доступна только в личных сообщениях с ботом. "
            "В чате открывайте кейсы через меню (кнопки)."
            if lang == "ru"
            else "This command only works in private messages with the bot. "
                 "In group chats, open cases via the menu buttons."
        )
        return False, f"❌ {err}"

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

    ok_cd, err_cd = _check_case_cooldown(data, lang, via_command=via_command)
    if not ok_cd:
        return False, err_cd

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
        ok, _msg, instance = open_case(data, case_key, lang=lang, _check_cooldown=False)
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
    data["boosters_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["boosters_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
        data["xp_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["xp_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["xp_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["enh_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["enh_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
    data["enh_inventory"] = _remove_qty_by_key(inv, item["key"], 1)
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
        text=_L(lang, "Магазин Артефактов", "Artifact Shop"),
        callback_data="artifact_shop_list",
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
#  UI — МАГАЗИН АРТЕФАКТОВ (прямая покупка, без рандома)
#  Навигация: список тиров → артефакты тира → окно артефакта (купить)
# ============================================================

_E_MINE  = "5201914481671682382"
_E_DMG   = "5373173798633752502"
_E_PETS  = "5208535779348864977"
_E_BONUS = "5438496463044752972"


def artifact_shop_list_text(data: dict, lang: str = "ru") -> str:
    owned = data.get("artifacts", [])
    owned_keys = {e["key"] for e in owned}

    lines = []
    for t in ARTIFACT_TIERS:
        items = artifacts_in_tier(t["tier"])
        have  = sum(1 for a in items if a["key"] in owned_keys)
        tname = t["name_en"] if lang == "en" else t["name"]
        if t["tier"] == "tall":
            price_str = f"699–1899 {SAMOSVET}"
            mult_str  = _L(lang, "1.35×–2.25× ко ВСЕЙ добыче сразу", "1.35×–2.25× to ALL income at once")
        else:
            price_str = f'{t["price_samosvety"]} {SAMOSVET}'
            mult_str  = _L(lang, f'{t["multiplier"]}× к руде / урону / питомцам', f'{t["multiplier"]}× to ore / damage / pets')
        lines.append(
            f'{_tier_icon(t)} <b><i>{tname}</i></b> — <b><i>{mult_str}</i></b>\n'
            f'<b><i>{price_str}</i></b>  |  '
            f'{_pe("stats","💎")} <b><i>{have}/{len(items)}</i></b>\n'
        )

    balance = get_samosvety(data)
    total_owned = len(owned)
    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> '
        f'<b><i>{_L(lang, "МАГАЗИН АРТЕФАКТОВ", "ARTIFACT SHOP")}</i></b>\n'
        f'{_pe("stats","💎")} <b><i>{_L(lang, "Собрано", "Collected")}: {total_owned}/{MAX_ARTIFACTS}</i></b>\n'
        f'{SAMOSVET} <b><i>{_L(lang, f"Баланс Самосветов: {balance}", f"Samosvety balance: {balance}")}</i></b></blockquote>\n'
        f'\n<blockquote>{"".join(lines)}</blockquote>\n'
        f'\n<blockquote>{_pe("ok","✨")} <b><i>{_L(lang, "Каждый артефакт — постоянный бонус навсегда, без рандома. Выбери тир, затем артефакт, и купи его за Самосветы.", "Every artifact is a permanent bonus forever, no randomness. Pick a tier, then an artifact, and buy it with Samosvety.")}</i></b></blockquote>'
    )


def artifact_shop_list_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in ARTIFACT_TIERS:
        tname = t["name_en"] if lang == "en" else t["name"]
        label = tname
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f'artifact_tier_{t["tier"]}',
            icon_custom_emoji_id=t.get("icon_id", ""),
        ))
    builder.row(InlineKeyboardButton(
        text=_L(lang, "Моя коллекция", "My collection"),
        callback_data="artifact_collection",
        icon_custom_emoji_id="5222113468051629260"
    ))
    balance = get_samosvety(data)
    builder.row(InlineKeyboardButton(
        text=_L(lang, f"Мои Самосветы: {balance} (Донат)", f"My Samosvety: {balance} (Donate)"),
        callback_data="donate_main",
        icon_custom_emoji_id=SAMOSVET_EMOJI_ID
    ))
    builder.row(_back_btn("shop_cases", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def artifact_tier_text(data: dict, tier_key: str, lang: str = "ru") -> str:
    t = ARTIFACT_TIERS_BY_KEY.get(tier_key)
    items = artifacts_in_tier(tier_key)
    owned_keys = {e["key"] for e in data.get("artifacts", [])}
    tname = (t["name_en"] if lang == "en" else t["name"]) if t else tier_key

    rows = []
    for a in items:
        aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
        eff   = _get_effect_label(a["effect"], lang)
        status = _pe("ok", "✅") if a["key"] in owned_keys else _pe("art_locked", "🔒")
        coin_part = f' / {_fmt_num(a["price_coins"])} {_pe("coin", "💰")}' if a.get("price_coins") else ""
        rows.append(
            f'{status} {_artifact_icon(a)} <b><i>{aname}</i></b> — '
            f'<b><i>{a["multiplier"]}× {eff}</i></b> · <b><i>{a["price_samosvety"]} {SAMOSVET}{coin_part}</i></b>\n'
        )

    return (
        f'<blockquote>{_tier_icon(t)} <b><i>{tname}</i></b></blockquote>\n'
        f'\n<blockquote>{"".join(rows)}</blockquote>\n'
        f'\n<blockquote>{_pe("stats","💎")} <b><i>{_L(lang, "Выбери артефакт, чтобы открыть окно покупки.", "Pick an artifact to open the purchase window.")}</i></b></blockquote>'
    )


def artifact_tier_keyboard(data: dict, tier_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    owned_keys = {e["key"] for e in data.get("artifacts", [])}
    for a in artifacts_in_tier(tier_key):
        aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
        owned = a["key"] in owned_keys
        if owned:
            label = f'{aname} — {_L(lang, "куплено", "owned")}'
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f'artifact_info_{a["key"]}',
                icon_custom_emoji_id=a["emoji_id"] or _E["ok"],
                style="success",
            ))
        else:
            coin_part = f' / {_fmt_num(a["price_coins"])}' if a.get("price_coins") else ""
            label = f'{aname} — {a["price_samosvety"]}{coin_part}'
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f'artifact_info_{a["key"]}',
                icon_custom_emoji_id=a["emoji_id"] or _E["art_locked"],
            ))
    builder.row(_back_btn("artifact_shop_list", _L(lang, "К тирам", "To tiers")))
    return builder.as_markup()


def artifact_info_text(data: dict, artifact_key: str, lang: str = "ru") -> str:
    """Отдельное окно одного артефакта: полное описание + цена + статус."""
    a = ARTIFACT_POOL_BY_KEY.get(artifact_key)
    if not a:
        return f'❌ {_L(lang, "Артефакт не найден.", "Artifact not found.")}'

    aname  = a.get("name_en", a["name"]) if lang == "en" else a["name"]
    eff    = _get_effect_label(a["effect"], lang)
    owned  = is_artifact_owned(data, artifact_key)
    icon   = _artifact_icon(a)

    if owned:
        status_line = f'{_pe("ok","✅")} <b><i>{_L(lang, "Уже в твоей коллекции", "Already in your collection")}</i></b>'
    else:
        status_line = f'{_pe("art_locked","🔒")} <b><i>{_L(lang, "Цена", "Price")}: {a["price_samosvety"]} {_L(lang, "Самосветов", "Samosvety")}</i></b>'
        if a.get("price_coins"):
            status_line += f'\n{_pe("coin","💰")} <b><i>{_L(lang, "или", "or")}: {_fmt_num(a["price_coins"])} {_L(lang, "монет", "coins")}</i></b>'

    effect_full = (
        _L(lang, "Даёт постоянный множитель ко ВСЕМ трём видам добычи (руда, урон по боссу, питомцы).",
                  "Gives a permanent multiplier to ALL three income types (ore, boss damage, pets).")
        if a["effect"] == "all" else
        _L(lang, f"Даёт постоянный множитель {a['multiplier']}× {eff}.",
                  f"Gives a permanent {a['multiplier']}× multiplier {eff}.")
    )

    return (
        f'<blockquote>{icon} <b><i>{aname}</i></b>\n'
        f'{_pe("stats","💎")} <b><i>{a["multiplier"]}× {eff}</i></b></blockquote>\n'
        f'\n<blockquote>{effect_full}</blockquote>\n'
        f'\n<blockquote>{status_line}</blockquote>\n'
        f'\n<blockquote>{_pe("warn","⚠️")} <b><i>{_L(lang, "Бонус действует всегда и не расходуется.", "The bonus is permanent and never consumed.")}</i></b></blockquote>'
    )


def artifact_info_keyboard(data: dict, artifact_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    a = ARTIFACT_POOL_BY_KEY.get(artifact_key)
    owned = is_artifact_owned(data, artifact_key)

    if owned:
        builder.row(InlineKeyboardButton(
            text=_L(lang, "Уже куплено", "Already owned"),
            callback_data="noop",
            icon_custom_emoji_id=(a["emoji_id"] if a else "") or _E["ok"],
            style="success",
        ))
    else:
        builder.row(_btn(
            SAMOSVET_EMOJI_ID,
            _L(lang, f'Купить за {a["price_samosvety"]}', f'Buy for {a["price_samosvety"]}'),
            f"artifact_buy_{artifact_key}",
            style="success",
        ))
        if a and a.get("price_coins"):
            builder.row(_btn(
                a["emoji_id"] or _E["coin"],
                _L(lang, f'Купить за {_fmt_num(a["price_coins"])} монет', f'Buy for {_fmt_num(a["price_coins"])} coins'),
                f"artifact_buy_coins_{artifact_key}",
            ))

    builder.row(InlineKeyboardButton(
        text=_L(lang, "Моя коллекция", "My collection"),
        callback_data="artifact_collection",
        icon_custom_emoji_id="5222113468051629260"
    ))
    tier_key = a["tier"] if a else "t125"
    builder.row(_back_btn(f"artifact_tier_{tier_key}", _L(lang, "Назад", "Back")))
    return builder.as_markup()


def artifact_collection_text(data: dict, lang: str = "ru") -> str:
    owned = data.get("artifacts", [])
    if not owned:
        return (
            f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b><i>{_L(lang, "МОЯ КОЛЛЕКЦИЯ АРТЕФАКТОВ", "MY ARTIFACT COLLECTION")}</i></b>\n'
            f'{_pe("cancel", "❌")} <b><i>{_L(lang, "У тебя пока нет артефактов.", "You have no artifacts yet.")}</i></b>\n'
            f'{_L(lang, "Загляни в Магазин Артефактов, чтобы купить первый!", "Check out the Artifact Shop to buy your first one!")}</blockquote>'
        )

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    artifact_lines = []
    for entry in owned:
        a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
        if a:
            effect_label = _get_effect_label(a["effect"], lang)
            aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
            artifact_lines.append(
                f'{_artifact_icon(a)} <b><i>{aname}</i></b> — '
                f'<b><i><i>{a["multiplier"]}× {effect_label}</i></i></b>\n'
            )

    mine_icon  = f'<tg-emoji emoji-id="{_E_MINE}">⛏</tg-emoji>'
    dmg_icon   = f'<tg-emoji emoji-id="{_E_DMG}">⚔️</tg-emoji>'
    pets_icon  = f'<tg-emoji emoji-id="{_E_PETS}">🐾</tg-emoji>'
    bonus_icon = f'<tg-emoji emoji-id="{_E_BONUS}">✨</tg-emoji>'

    return (
        f'<blockquote><tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> '
        f'<b><i>{_L(lang, "МОЯ КОЛЛЕКЦИЯ", "MY COLLECTION")} ({len(owned)}/{MAX_ARTIFACTS})</i></b></blockquote>\n'
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
    builder.row(_back_btn("artifact_shop_list", _L(lang, "В магазин", "To shop")))
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
        stacks[k]["count"] += item.get("count", 1)

    for item in data.get("xp_inventory", []):
        k = item["key"]
        if k not in stacks:
            stacks[k] = {"count": 0, "item_sample": item, "type": item.get("type", "xp_boost")}
        stacks[k]["count"] += item.get("count", 1)

    for item in data.get("enh_inventory", []):
        k = item["key"]
        if k not in stacks:
            stacks[k] = {"count": 0, "item_sample": item, "type": item.get("type", "enh_boost")}
        stacks[k]["count"] += item.get("count", 1)

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
            cnt_str = f" <b><i>({s['count']} шт.)</i></b>" if s["count"] > 1 else ""
            lines.append(f"<b><i>#{s['slot_id']} {s['display']}</i></b>{cnt_str}\n")
        lines.append("</blockquote>")

    # Артефакты — не стакаются (у игрока либо есть, либо нет), поэтому
    # отдельным блоком под обычным инвентарём, тем же стилем, что и на
    # экране коллекции (artifact_collection_text): своя иконка у каждого
    # артефакта (emoji_id из _ARTIFACT_POOL, если задан) + название и
    # множитель/эффект жирным курсивом.
    owned_artifacts = data.get("artifacts", [])
    if owned_artifacts:
        lbl_art = "Artifacts" if lang == "en" else "Артефакты"
        artifact_lines = []
        for entry in owned_artifacts:
            a = ARTIFACT_POOL_BY_KEY.get(entry["key"])
            if not a:
                continue
            eid   = a.get("emoji_id", "")
            aicon = f'<tg-emoji emoji-id="{eid}">♦️</tg-emoji>' if eid else "♦️"
            aname = a.get("name_en", a["name"]) if lang == "en" else a["name"]
            effect_label = _get_effect_label(a["effect"], lang)
            artifact_lines.append(
                f'{aicon} <b><i>{aname} — {a["multiplier"]}× {effect_label}</i></b>\n'
            )
        if artifact_lines:
            lines.append(
                f"\n<blockquote><b><i>{lbl_art} ({len(artifact_lines)}):</i></b>\n"
                + "".join(artifact_lines) + "</blockquote>"
            )

    lbl_hint = (
        "\n<blockquote><b><i>"
        "Use: <code>use #N</code> or <code>-use #N</code>\n"
        "Cancel: <code>/boost</code>\n"
        "Sell: <code>/sell #N</code> or <code>/sell #N 5</code>\n"
        "Transfer: <code>отп #N</code> or <code>отп #N 3 @username</code>\n"
        "Open cases: <code>open #1 5</code> or <code>/open #2 10</code>"
        "</i></b></blockquote>"
        if lang == "en" else
        "\n<blockquote><b><i>"
        "Использовать: <code>исп #N</code> или <code>-use #N</code>\n"
        "Отменить: <code>/буст </code>\n"
        "Продать: <code>/sell #N</code> или <code>/sell #N 5</code>\n"
        "Передать: <code>отп #N</code> или <code>отп #N 3 @username</code>\n"
        "Открыть кейсы: <code>открыть #1 5</code> или <code>/купить #2 10</code>"
        "</i></b></blockquote>"
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
    available = sum(i.get("count", 1) for i in inv if i["key"] == key)

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

    # Убираем qty предметов из инвентаря (учитывает стекинг через "count")
    data[inv_key] = _remove_qty_by_key(inv, key, qty)

    # Если стопка полностью продана — убираем slot_id
    remaining = available - qty
    if remaining == 0:
        slot_map.pop(key, None)
        data["inv_slot_ids"] = slot_map

    data["balance"] = data.get("balance", 0) + total_earn

    # Название предмета
    itype = item_sample.get("type", "boost")
    item_sample = {k2: v2 for k2, v2 in item_sample.items() if k2 != "count"}
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
    available  = sum(i.get("count", 1) for i in sender_inv if i["key"] == key)

    if qty < 1:
        err = "Количество должно быть ≥ 1." if lang == "ru" else "Quantity must be ≥ 1."
        return False, f"❌ {err}", ""
    if qty > available:
        err = (
            f"В стопке только {available} шт." if lang == "ru"
            else f"Only {available} in stack."
        )
        return False, f"❌ {err}", ""

    # ── Перемещаем предметы (учитывает стекинг через "count") ──────────
    sender_data[inv_key] = _remove_qty_by_key(sender_inv, key, qty)

    # Если стопка опустела — убираем slot_id
    if available - qty == 0:
        slot_map.pop(key, None)
        sender_data["inv_slot_ids"] = slot_map

    # Добавляем получателю: если у него уже есть такой предмет — просто
    # увеличиваем count существующей стопки, иначе создаём новую.
    recipient_inv = recipient_data.setdefault(inv_key, [])
    _sample = {k2: v2 for k2, v2 in item_sample.items() if k2 not in ("instance_id", "count")}
    _add_or_stack(recipient_inv, key, lambda: dict(_sample), qty=qty)

    # ── Формируем имя предмета (без count — qty уже показан отдельно) ──
    _sample_for_name = {k2: v2 for k2, v2 in item_sample.items() if k2 != "count"}
    name = item_name_fn(_sample_for_name)

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
