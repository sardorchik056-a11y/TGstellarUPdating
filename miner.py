# ============================================================
#  miner.py  —  Модуль шахты для TGStellar бота
#  Переписан для aiogram 3.x
# ============================================================

import random
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
#  PREMIUM EMOJI IDs
# ============================================================

EMOJI_NOT_BOUGHT  = "5240241223632954241"
EMOJI_SELECTED    = "5206607081334906820"
EMOJI_BACK        = "6039539366177541657"

EMOJI_COIN        = "5199552030615558774"
EMOJI_STAR        = "5267500801240092311"

EMOJI_BTN_START        = "5906891238270834298"
EMOJI_BTN_COLLECT      = "5310278924616356636"
EMOJI_BTN_COLLECT_PART = "5310278924616356636"
EMOJI_BTN_REFRESH      = "5386367538735104399"
EMOJI_BTN_SELL         = "5429518319243775957"
EMOJI_BTN_INV          = "5445221832074483553"
EMOJI_BTN_WORKSHOP     = "5278702045883292456"
EMOJI_BTN_DURATION     = "5440621591387980068"

EMOJI_BTN_BUY_COINS  = "5199552030615558774"
EMOJI_BTN_BUY_STARS  = "5267500801240092311"
EMOJI_BTN_FREE       = "5199552030615558774"
EMOJI_BTN_SELECT     = "5397916757333654639"
EMOJI_BTN_ACTIVE     = "5206607081334906820"
EMOJI_BTN_NO_COINS   = "5240241223632954241"

EMOJI_BTN_DUR_BUY    = "5199552030615558774"
EMOJI_BTN_SELL_ALL   = "5429518319243775957"

EMOJI_BTN_PAGE_PREV  = "5255703720078879038"
EMOJI_BTN_PAGE_NEXT  = "5253767677670862169"


def _emoji_btn(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


COIN = f'<tg-emoji emoji-id="{EMOJI_COIN}">🪙</tg-emoji>'
STAR = f'<tg-emoji emoji-id="5267500801240092311">⭐</tg-emoji>'

MAX_LEVEL = 150

# ---------- РУДЫ ----------
ORES = [
    # ── Common ───────────────────────────────────────────────────────────
    {"name": "🪨 Камень",  "name_en": "🪨 Stone",    "key": "stone",    "chance": 75.000, "weight": 500, "price":         50},
    {"name": '<tg-emoji emoji-id="5773638078321135255">🖤</tg-emoji> Уголь',    "name_en": '<tg-emoji emoji-id="5773638078321135255">🖤</tg-emoji> Coal',      "key": "coal",     "chance": 30.000, "weight": 200, "price":         85},
    {"name": '<tg-emoji emoji-id="5431869843903102028">🪨</tg-emoji> Кремень', "name_en": '<tg-emoji emoji-id="5431869843903102028">🪨</tg-emoji> Flint',    "key": "flint",    "chance": 22.000, "weight": 160, "price":        105},
    {"name": '<tg-emoji emoji-id="5339390195768774311">🟤</tg-emoji> Медь',     "name_en": '<tg-emoji emoji-id="5339390195768774311">🟤</tg-emoji> Copper',    "key": "copper",   "chance": 20.000, "weight": 120, "price":        125},
    # ── Rare ─────────────────────────────────────────────────────────────
    {"name": '<tg-emoji emoji-id="5206502799528976649">⚙️</tg-emoji> Железо',  "name_en": '<tg-emoji emoji-id="5206502799528976649">⚙️</tg-emoji> Iron',      "key": "iron",     "chance":  8.000, "weight":  60, "price":        280},
    {"name": '<tg-emoji emoji-id="6005900138638218214">🩶</tg-emoji> Серебро', "name_en": '<tg-emoji emoji-id="6005900138638218214">🩶</tg-emoji> Silver',   "key": "silver",   "chance":  5.500, "weight":  45, "price":        420},
    {"name": '<tg-emoji emoji-id="5773878407511150045">🔵</tg-emoji> Лазурит', "name_en": '<tg-emoji emoji-id="5773878407511150045">🔵</tg-emoji> Lazurite', "key": "lazurite", "chance":  5.000, "weight":  40, "price":        450},
    {"name": '<tg-emoji emoji-id="5445256208992718797">🌕</tg-emoji> Золото',   "name_en": '<tg-emoji emoji-id="5445256208992718797">🌕</tg-emoji> Gold',      "key": "gold",     "chance":  3.000, "weight":  20, "price":        800},
    {"name": '<tg-emoji emoji-id="5219909303720233242">🧱</tg-emoji> Гранит',  "name_en": '<tg-emoji emoji-id="5219909303720233242">🧱</tg-emoji> Granite',  "key": "granite",  "chance":  2.000, "weight":  14, "price":      2_500},
    # ── Epic ─────────────────────────────────────────────────────────────
    {"name": '<tg-emoji emoji-id="5201914481671682382">💎</tg-emoji> Алмаз',    "name_en": '<tg-emoji emoji-id="5201914481671682382">💎</tg-emoji> Diamond',   "key": "diamond",  "chance":  1.000, "weight":   8, "price":      5_000},
    # ── Legendary ────────────────────────────────────────────────────────
    {"name": '<tg-emoji emoji-id="5217620305194800391">🔮</tg-emoji> Мифрил',   "name_en": '<tg-emoji emoji-id="5217620305194800391">🔮</tg-emoji> Mithril',   "key": "mithril",  "chance":  0.100, "weight":   3, "price":     45_000},
    {"name": '<tg-emoji emoji-id="5447225730670813734">☢️</tg-emoji> Уран',     "name_en": '<tg-emoji emoji-id="5447225730670813734">☢️</tg-emoji> Uranium',   "key": "uranium",  "chance":  0.040, "weight":   2, "price":    150_000},
    {"name": '<tg-emoji emoji-id="5314686299796427450">💜</tg-emoji> Аметист',  "name_en": '<tg-emoji emoji-id="5314686299796427450">💜</tg-emoji> Amethyst',  "key": "amethyst", "chance":  0.010, "weight":   1, "price":    500_000},
    # ── Mythic ───────────────────────────────────────────────────────────
    {"name": '<tg-emoji emoji-id="5850500039956239502">🟢</tg-emoji> Нефрит',  "name_en": '<tg-emoji emoji-id="5850500039956239502">🟢</tg-emoji> Jade',     "key": "jade",     "chance":  0.005, "weight":   1, "price":  2_000_000},
    {"name": '<tg-emoji emoji-id="5470105163190515289">🌿</tg-emoji> Изумруд', "name_en": '<tg-emoji emoji-id="5470105163190515289">🌿</tg-emoji> Emerald',  "key": "emerald",  "chance":  0.002, "weight":   1, "price":  5_000_000},
    {"name": '<tg-emoji emoji-id="6138471781767319985">💀</tg-emoji> Обсидиан',"name_en": '<tg-emoji emoji-id="6138471781767319985">💀</tg-emoji> Obsidian', "key": "obsidian", "chance":  0.001, "weight":   1, "price":  8_000_000},
    {"name": '<tg-emoji emoji-id="5465283645788937267">🔷</tg-emoji> Сапфир',  "name_en": '<tg-emoji emoji-id="5465283645788937267">🔷</tg-emoji> Sapphire', "key": "sapphire", "chance":  0.0005,"weight":   1, "price": 15_000_000},
]
ORES_BY_KEY = {o["key"]: o for o in ORES}

# ============================================================
#  КИРКИ
# ============================================================

PICKAXES = {
    "wood_1": {"name": "Wood-1lvl", "dig_min": 1, "dig_max": 2, "cost": 0, "currency": "coins", "required_level": 1, "tier": "wood", "cost_stars": 0},
    "wood_2": {"name": "Wood-2lvl", "dig_min": 2, "dig_max": 4, "cost": 1_500, "currency": "coins", "required_level": 1, "tier": "wood", "cost_stars": 10},
    "wood_3": {"name": "Wood-3lvl", "dig_min": 2, "dig_max": 5, "cost": 2_500, "currency": "coins", "required_level": 1, "tier": "wood", "cost_stars": 15},
    "wood_4": {"name": "Wood-4lvl", "dig_min": 3, "dig_max": 5, "cost": 4_000, "currency": "coins", "required_level": 1, "tier": "wood", "cost_stars": 20},
    "wood_5": {"name": "Wood-5lvl", "dig_min": 3, "dig_max": 6, "cost": 6_000, "currency": "coins", "required_level": 1, "tier": "wood", "cost_stars": 25},
    "rock_1": {"name": "Rock-1lvl", "dig_min": 3, "dig_max": 7, "cost": 10_000, "currency": "coins", "required_level": 1, "tier": "rock", "cost_stars": 35},
    "rock_2": {"name": "Rock-2lvl", "dig_min": 4, "dig_max": 8, "cost": 16_000, "currency": "coins", "required_level": 1, "tier": "rock", "cost_stars": 45},
    "rock_3": {"name": "Rock-3lvl", "dig_min": 5, "dig_max": 9, "cost": 25_000, "currency": "coins", "required_level": 1, "tier": "rock", "cost_stars": 60},
    "rock_4": {"name": "Rock-4lvl", "dig_min": 5, "dig_max": 11, "cost": 40_000, "currency": "coins", "required_level": 1, "tier": "rock", "cost_stars": 80},
    "rock_5": {"name": "Rock-5lvl", "dig_min": 6, "dig_max": 12, "cost": 64_000, "currency": "coins", "required_level": 1, "tier": "rock", "cost_stars": 100},
    "iron_1": {"name": "Iron-1lvl", "dig_min": 7, "dig_max": 14, "cost": 100_000, "currency": "coins", "required_level": 1, "tier": "iron", "cost_stars": 150},
    "iron_2": {"name": "Iron-2lvl", "dig_min": 8, "dig_max": 16, "cost": 160_000, "currency": "coins", "required_level": 1, "tier": "iron", "cost_stars": 200},
    "iron_3": {"name": "Iron-3lvl", "dig_min": 9, "dig_max": 19, "cost": 260_000, "currency": "coins", "required_level": 1, "tier": "iron", "cost_stars": 250},
    "iron_4": {"name": "Iron-4lvl", "dig_min": 11, "dig_max": 21, "cost": 420_000, "currency": "coins", "required_level": 1, "tier": "iron", "cost_stars": 300},
    "iron_5": {"name": "Iron-5lvl", "dig_min": 12, "dig_max": 25, "cost": 680_000, "currency": "coins", "required_level": 1, "tier": "iron", "cost_stars": 350},
    "gold_1": {"name": "Gold-1lvl", "dig_min": 14, "dig_max": 28, "cost": 1_100_000, "currency": "coins", "required_level": 1, "tier": "gold", "cost_stars": 400},
    "gold_2": {"name": "Gold-2lvl", "dig_min": 16, "dig_max": 33, "cost": 1_700_000, "currency": "coins", "required_level": 1, "tier": "gold", "cost_stars": 450},
    "gold_3": {"name": "Gold-3lvl", "dig_min": 19, "dig_max": 37, "cost": 2_800_000, "currency": "coins", "required_level": 1, "tier": "gold", "cost_stars": 500},
    "gold_4": {"name": "Gold-4lvl", "dig_min": 22, "dig_max": 43, "cost": 4_400_000, "currency": "coins", "required_level": 1, "tier": "gold", "cost_stars": 550},
    "gold_5": {"name": "Gold-5lvl", "dig_min": 25, "dig_max": 50, "cost": 7_100_000, "currency": "coins", "required_level": 1, "tier": "gold", "cost_stars": 600},
    "diamond_1": {"name": "Diamond-1lvl", "dig_min": 28, "dig_max": 57, "cost": 11_000_000, "currency": "coins", "required_level": 1, "tier": "diamond", "cost_stars": 650},
    "diamond_2": {"name": "Diamond-2lvl", "dig_min": 33, "dig_max": 65, "cost": 18_000_000, "currency": "coins", "required_level": 1, "tier": "diamond", "cost_stars": 700},
    "diamond_3": {"name": "Diamond-3lvl", "dig_min": 38, "dig_max": 75, "cost": 29_000_000, "currency": "coins", "required_level": 1, "tier": "diamond", "cost_stars": 800},
    "diamond_4": {"name": "Diamond-4lvl", "dig_min": 43, "dig_max": 87, "cost": 46_000_000, "currency": "coins", "required_level": 1, "tier": "diamond", "cost_stars": 900},
    "diamond_5": {"name": "Diamond-5lvl", "dig_min": 50, "dig_max": 100, "cost": 74_000_000, "currency": "coins", "required_level": 1, "tier": "diamond", "cost_stars": 1100},
    "uranium_1": {"name": "Uranium-1lvl", "dig_min": 57, "dig_max": 115, "cost": 120_000_000, "currency": "coins", "required_level": 1, "tier": "uranium", "cost_stars": 1200},
    "uranium_2": {"name": "Uranium-2lvl", "dig_min": 66, "dig_max": 132, "cost": 190_000_000, "currency": "coins", "required_level": 1, "tier": "uranium", "cost_stars": 1400},
    "uranium_3": {"name": "Uranium-3lvl", "dig_min": 76, "dig_max": 151, "cost": 300_000_000, "currency": "coins", "required_level": 1, "tier": "uranium", "cost_stars": 1600},
    "uranium_4": {"name": "Uranium-4lvl", "dig_min": 87, "dig_max": 174, "cost": 490_000_000, "currency": "coins", "required_level": 1, "tier": "uranium", "cost_stars": 1800},
    "uranium_5": {"name": "Uranium-5lvl", "dig_min": 100, "dig_max": 200, "cost": 780_000_000, "currency": "coins", "required_level": 1, "tier": "uranium", "cost_stars": 2100},
    "amethyst_1": {"name": "Amethyst-1lvl", "dig_min": 115, "dig_max": 230, "cost": 1_200_000_000, "currency": "coins", "required_level": 1, "tier": "amethyst", "cost_stars": 2400},
    "amethyst_2": {"name": "Amethyst-2lvl", "dig_min": 132, "dig_max": 265, "cost": 2_000_000_000, "currency": "coins", "required_level": 1, "tier": "amethyst", "cost_stars": 2800},
    "amethyst_3": {"name": "Amethyst-3lvl", "dig_min": 152, "dig_max": 305, "cost": 3_200_000_000, "currency": "coins", "required_level": 1, "tier": "amethyst", "cost_stars": 3200},
    "amethyst_4": {"name": "Amethyst-4lvl", "dig_min": 175, "dig_max": 350, "cost": 5_100_000_000, "currency": "coins", "required_level": 1, "tier": "amethyst", "cost_stars": 3700},
    "amethyst_5": {"name": "Amethyst-5lvl", "dig_min": 201, "dig_max": 403, "cost": 8_200_000_000, "currency": "coins", "required_level": 1, "tier": "amethyst", "cost_stars": 4300},
    "vip_1": {"name": "VIP-1lvl", "dig_min": 232, "dig_max": 463, "cost": 13_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip", "cost_stars": 4900},
    "vip_2": {"name": "VIP-2lvl", "dig_min": 266, "dig_max": 533, "cost": 21_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip", "cost_stars": 5600},
    "vip_3": {"name": "VIP-3lvl", "dig_min": 306, "dig_max": 613, "cost": 33_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip", "cost_stars": 6500},
    "vip_4": {"name": "VIP-4lvl", "dig_min": 352, "dig_max": 704, "cost": 54_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip", "cost_stars": 7500},
    "vip_5": {"name": "VIP-5lvl", "dig_min": 405, "dig_max": 810, "cost": 86_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip", "cost_stars": 8600},
    "vip_plus_1": {"name": "VIP+-1lvl", "dig_min": 466, "dig_max": 932, "cost": 140_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip_plus", "cost_stars": 9900},
    "vip_plus_2": {"name": "VIP+-2lvl", "dig_min": 536, "dig_max": 1_071, "cost": 220_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip_plus", "cost_stars": 11000},
    "vip_plus_3": {"name": "VIP+-3lvl", "dig_min": 616, "dig_max": 1_232, "cost": 350_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip_plus", "cost_stars": 13000},
    "vip_plus_4": {"name": "VIP+-4lvl", "dig_min": 708, "dig_max": 1_417, "cost": 560_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip_plus", "cost_stars": 15000},
    "vip_plus_5": {"name": "VIP+-5lvl", "dig_min": 815, "dig_max": 1_630, "cost": 900_000_000_000, "currency": "coins", "required_level": 1, "tier": "vip_plus", "cost_stars": 17000},
    "premium_1": {"name": "Premium-1lvl", "dig_min": 937, "dig_max": 1_874, "cost": 0, "currency": "stars", "cost_stars": 20000, "required_level": 1, "tier": "premium"},
    "premium_2": {"name": "Premium-2lvl", "dig_min": 1_078, "dig_max": 2_155, "cost": 0, "currency": "stars", "cost_stars": 23000, "required_level": 1, "tier": "premium"},
    "premium_3": {"name": "Premium-3lvl", "dig_min": 1_239, "dig_max": 2_478, "cost": 0, "currency": "stars", "cost_stars": 26000, "required_level": 1, "tier": "premium"},
    "premium_4": {"name": "Premium-4lvl", "dig_min": 1_425, "dig_max": 2_850, "cost": 0, "currency": "stars", "cost_stars": 30000, "required_level": 1, "tier": "premium"},
    "premium_5": {"name": "Premium-5lvl", "dig_min": 1_639, "dig_max": 3_278, "cost": 0, "currency": "stars", "cost_stars": 35000, "required_level": 1, "tier": "premium"},
}

PICKAXES_ORDER = [
    "wood_1", "wood_2", "wood_3", "wood_4", "wood_5",
    "rock_1", "rock_2", "rock_3", "rock_4", "rock_5",
    "iron_1", "iron_2", "iron_3", "iron_4", "iron_5",
    "gold_1", "gold_2", "gold_3", "gold_4", "gold_5",
    "diamond_1", "diamond_2", "diamond_3", "diamond_4", "diamond_5",
    "uranium_1", "uranium_2", "uranium_3", "uranium_4", "uranium_5",
    "amethyst_1", "amethyst_2", "amethyst_3", "amethyst_4", "amethyst_5",
    "vip_1", "vip_2", "vip_3", "vip_4", "vip_5",
    "vip_plus_1", "vip_plus_2", "vip_plus_3", "vip_plus_4", "vip_plus_5",
    "premium_1", "premium_2", "premium_3", "premium_4", "premium_5",
]

WORKSHOP_PAGE_SIZE   = 10
WORKSHOP_PAGES       = [PICKAXES_ORDER[i:i + WORKSHOP_PAGE_SIZE] for i in range(0, len(PICKAXES_ORDER), WORKSHOP_PAGE_SIZE)]
WORKSHOP_TOTAL_PAGES = len(WORKSHOP_PAGES)

WORKSHOP_PAGE_LABELS = [
    "🪓 Wood / ⛏️ Rock",
    "🔩 Iron / 🌕 Gold",
    "💎 Diamond / ☢️ Uranium",
    "💜 Amethyst / 👑 VIP",
    "💠 VIP+ / 💫 Premium",
]

TIER_LABELS = {
    "wood": "Wood", "rock": "Rock", "iron": "Iron", "gold": "Gold",
    "diamond": "Diamond", "uranium": "Uranium", "amethyst": "Amethyst",
    "vip": "VIP", "vip_plus": "VIP+", "premium": "Premium",
}

DURATIONS = {
    "5min":  {"label": "5 мин",    "label_en": "5 min",    "campaigns": 1,   "cost": 0},
    "10min": {"label": "10 мин",   "label_en": "10 min",   "campaigns": 2,   "cost": 25_000},
    "15min": {"label": "15 мин",   "label_en": "15 min",   "campaigns": 3,   "cost": 75_000},
    "30min": {"label": "30 мин",   "label_en": "30 min",   "campaigns": 6,   "cost": 500_000},
    "45min": {"label": "45 мин",   "label_en": "45 min",   "campaigns": 9,   "cost": 1_000_000},
    "1h":    {"label": "1 час",    "label_en": "1 hour",   "campaigns": 12,  "cost": 1_500_000},
    "2h":    {"label": "2 часа",   "label_en": "2 hours",  "campaigns": 24,  "cost": 5_000_000},
    "4h":    {"label": "4 часа",   "label_en": "4 hours",  "campaigns": 48,  "cost": 50_000_000},
    "12h":   {"label": "12 часов", "label_en": "12 hours", "campaigns": 144, "cost": 350_000_000},
    "24h":   {"label": "24 часа",  "label_en": "24 hours", "campaigns": 288, "cost": 950_000_000},
}
DURATIONS_ORDER = ["5min", "10min", "15min", "30min", "45min", "1h", "2h", "4h", "12h", "24h"]

CAMPAIGN_SECONDS = 5 * 60
XP_PER_ORE      = 20


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _ore_name(ore: dict, lang: str = "ru") -> str:
    """Return ore display name in the requested language."""
    if lang == "en":
        return ore.get("name_en", ore["name"])
    return ore["name"]


def _dur_label(dur: dict, lang: str = "ru") -> str:
    """Return duration label in the requested language."""
    if lang == "en":
        return dur.get("label_en", dur["label"])
    return dur["label"]


def fmt_time(seconds: int, lang: str = "ru") -> str:
    if seconds <= 0:
        return "0s" if lang == "en" else "0с"
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        if lang == "en":
            return f"{h}h {m}m {s}s"
        return f"{h}ч {m}м {s}с"
    if lang == "en":
        return f"{m}m {s}s"
    return f"{m}м {s}с"


def progress_bar(percent: int, length: int = 10) -> str:
    _E_EMPTY   = "5992142065603974345"
    _E_QUARTER = "5992256170000127661"
    _E_HALF    = "5992488673759729434"
    _E_FULL    = "5992459287593489418"
    cells = []
    for i in range(length):
        cell_start = i * (100 / length)
        cell_fill  = percent - cell_start
        cell_pct   = max(0.0, min(cell_fill, (100 / length))) / (100 / length) * 100
        if cell_pct >= 75:
            eid = _E_FULL
        elif cell_pct >= 50:
            eid = _E_HALF
        elif cell_pct >= 25:
            eid = _E_QUARTER
        else:
            eid = _E_EMPTY
        cells.append(f'<tg-emoji emoji-id="{eid}">⬜</tg-emoji>')
    return "".join(cells) + f" {percent}%"


def xp_for_level(level: int) -> int:
    _manual = {1: 100, 2: 150, 3: 300, 4: 500, 5: 750, 6: 1250, 7: 1600, 8: 2200, 9: 3000, 10: 4500}
    if level in _manual:
        return _manual[level]
    raw = 4500 * (1.07 ** (level - 10))
    if raw < 1000:       return max(100, round(raw / 50) * 50)
    elif raw < 10000:    return round(raw / 100) * 100
    elif raw < 100000:   return round(raw / 500) * 500
    elif raw < 1000000:  return round(raw / 1000) * 1000
    else:                return round(raw / 5000) * 5000


def add_xp(data: dict, amount: int):
    if data.get("level", 1) >= MAX_LEVEL:
        data["xp"]     = data.get("xp_max", xp_for_level(MAX_LEVEL))
        data["xp_max"] = data.get("xp_max", xp_for_level(MAX_LEVEL))
        return
    data["xp"] = data.get("xp", 0) + amount
    while True:
        current_level = data.get("level", 1)
        if current_level >= MAX_LEVEL:
            data["level"]  = MAX_LEVEL
            data["xp_max"] = xp_for_level(MAX_LEVEL)
            data["xp"]     = data["xp_max"]
            break
        needed = xp_for_level(current_level)
        data["xp_max"] = needed
        if data["xp"] >= needed:
            data["xp"]    -= needed
            data["level"]  = current_level + 1
        else:
            break


def _fmt_cost(pick_key: str, lang: str = "ru") -> str:
    p = PICKAXES[pick_key]
    if p["currency"] == "stars":
        return f"{p['cost_stars']} {STAR} " + ("stars" if lang == "en" else "звёзд")
    if p["cost"] == 0:
        return "Free" if lang == "en" else "Бесплатно"
    return f"{_fmt_num(p['cost'])} {COIN}"


def _fmt_num(n) -> str:
    """
    Сокращённый формат чисел: 1500 -> "1.5к", 100000 -> "100к",
    2300000 -> "2.3м", 100000000 -> "100м", 1500000000 -> "1.5млрд".
    Логика идентична database.format_amount (единый стиль во всём боте).
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


def roll_ore(pick_key: str, multiplier: float = 1.0) -> list:
    pick    = PICKAXES[pick_key]
    dig_min = max(1, int(pick["dig_min"] * multiplier))
    dig_max = max(1, int(pick["dig_max"] * multiplier))
    n_digs  = random.randint(dig_min, dig_max)
    found   = {}
    weights = [o["weight"] for o in ORES]
    for _ in range(n_digs):
        ore = random.choices(ORES, weights=weights, k=1)[0]
        found[ore["key"]] = found.get(ore["key"], 0) + 1
        for o in ORES:
            if random.random() * 100 < o["chance"] * 0.3:
                found[o["key"]] = found.get(o["key"], 0) + 1
    return [(ORES_BY_KEY[k], v) for k, v in found.items()]


def get_session_params(data: dict) -> tuple:
    dur   = DURATIONS[data.get("mine_duration_key", "5min")]
    camps = dur["campaigns"]
    return camps, camps * CAMPAIGN_SECONDS


def calc_mine_progress(data: dict) -> dict:
    total_campaigns, total_seconds = get_session_params(data)
    start          = float(data["mine_start"])
    elapsed        = min(now_ts() - start, total_seconds)
    campaigns_done = min(int(elapsed / CAMPAIGN_SECONDS), total_campaigns)
    new_campaigns  = campaigns_done - data["mine_campaigns_done"]
    time_left      = max(0, total_seconds - elapsed)
    finished       = elapsed >= total_seconds
    percent        = min(100, int(elapsed / total_seconds * 100))
    return {
        "campaigns_done":  campaigns_done,
        "new_campaigns":   new_campaigns,
        "time_left":       int(time_left),
        "finished":        finished,
        "percent":         percent,
        "total_campaigns": total_campaigns,
        "total_seconds":   total_seconds,
    }


def ore_inventory_text(data: dict, short: bool = False, lang: str = "ru") -> str:
    lines = []
    for ore in ORES:
        qty = data["ores"].get(ore["key"], 0)
        if qty > 0:
            worth = qty * ore["price"]
            lines.append(f"<b>{_ore_name(ore, lang)}: {qty}</b> <b>(≈ {_fmt_num(worth)} {COIN})</b>")
    if not lines:
        return "<b>Inventory empty</b>" if lang == "en" else "<b>Инвентарь пуст</b>"
    if short and len(lines) > 3:
        more = "...and more" if lang == "en" else "...и ещё"
        return "\n".join(lines[:3]) + f"\n<b><i>{more}</i></b>"
    return "\n".join(lines)


def inventory_screen_text(data: dict, lang: str = "ru") -> str:
    title   = "Inventory" if lang == "en" else "Инвентарь"
    lines = [f'<tg-emoji emoji-id="5445221832074483553">🎟</tg-emoji> <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━\n']
    has_ores = False
    total_value = 0
    for ore in ORES:
        qty = data["ores"].get(ore["key"], 0)
        if qty > 0:
            has_ores = True
            worth = qty * ore["price"]
            total_value += worth
            lines.append(f"<blockquote><b>{_ore_name(ore, lang)}: {qty} (≈ {_fmt_num(worth)} {COIN})</b></blockquote>")
    if not has_ores:
        lines.append("<b>Inventory empty</b>" if lang == "en" else "<b>Инвентарь пуст</b>")
    else:
        total_lbl = "Total" if lang == "en" else "Итого"
        lines.append(f'\n<tg-emoji emoji-id="5303214794336125778">🎟</tg-emoji> <b>{total_lbl}: {_fmt_num(total_value)} {COIN}</b>')
    return "\n".join(lines)


# ============================================================
#  ТЕКСТЫ ЭКРАНОВ
# ============================================================

def mine_text(data: dict, lang: str = "ru") -> str:
    from lang import t
    pick_key = data.get("pickaxe", "wood_1")
    pick     = PICKAXES[pick_key]
    dur_key  = data.get("mine_duration_key", "5min")
    dur      = DURATIONS[dur_key]
    dur_lbl  = _dur_label(dur, lang)

    if data["mine_start"] is None or data["mine_collected"]:
        return (
            f'<tg-emoji emoji-id="5197371802136892976">🎟</tg-emoji> <b>{t(lang, "mine_title")}</b>\n'
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>{t(lang, "mine_selected")}: {pick["name"]}</b>\n'
            f'<tg-emoji emoji-id="5440621591387980068">🎟</tg-emoji> <b>{t(lang, "mine_duration")}: {dur_lbl}</b>\n\n'
            f'<blockquote><tg-emoji emoji-id="5445221832074483553">🎟</tg-emoji> <b>{t(lang, "mine_inventory_lbl")}:</b>\n{ore_inventory_text(data, short=True, lang=lang)}</blockquote>\n\n'
            f'{t(lang, "mine_press_start")}'
        )
    prog   = calc_mine_progress(data)
    bar    = progress_bar(prog["percent"])
    status = t(lang, "mine_finished") if prog["finished"] else t(lang, "mine_running")
    return (
        f'<tg-emoji emoji-id="5197371802136892976">🎟</tg-emoji> <b>{t(lang, "mine_title")}</b>\n'
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>{t(lang, "mine_selected")}: {pick["name"]}</b>\n'
        f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>{t(lang, "mine_campaigns")}: {prog["campaigns_done"]}/{prog["total_campaigns"]}</b>\n\n'
        f'<tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> <b>{t(lang, "mine_progress")}:</b>\n{bar}\n\n'
        f"{status}\n\n"
        f'<blockquote><tg-emoji emoji-id="5445221832074483553">🎟</tg-emoji> <b>{t(lang, "mine_inventory_lbl")}:</b>\n{ore_inventory_text(data, short=True, lang=lang)}</blockquote>'
    )


def workshop_text(data: dict, page: int = 0, lang: str = "ru") -> str:
    from lang import t
    current = data.get("pickaxe", "wood_1")
    return (
        f'<tg-emoji emoji-id="5278702045883292456">🎟</tg-emoji> <b>{t(lang, "mine_workshop_title")}</b>\n'
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<blockquote><tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_workshop_balance")}: {_fmt_num(data["balance"])}{COIN}</b>\n'
        f'<tg-emoji emoji-id="5397782960512444700">🎟</tg-emoji> <b>{t(lang, "mine_workshop_selected")}: {current}lvl</b>\n'
        f'<tg-emoji emoji-id="5444856076954520455">🎟</tg-emoji> <b>{t(lang, "mine_workshop_page")}: {page + 1}/{WORKSHOP_TOTAL_PAGES}</b></blockquote>\n\n'
        f'<b>{t(lang, "mine_workshop_choose")}</b>'
    )


def pickaxe_detail_text(data: dict, pick_key: str, lang: str = "ru") -> str:
    from lang import t
    p     = PICKAXES[pick_key]
    owned = data.get("owned_pickaxes", ["wood_1"])
    tier  = TIER_LABELS.get(p.get("tier", ""), "")
    stars_unit = t(lang, "mine_pick_stars_unit")
    if pick_key == data.get("pickaxe", "wood_1"):
        status = t(lang, "mine_pick_selected")
    elif pick_key in owned:
        status = t(lang, "mine_pick_not_active")
    elif p["currency"] == "stars":
        status = f'{t(lang, "mine_pick_for_stars_st")} — {p["cost_stars"]} {STAR}'
    else:
        status = t(lang, "mine_pick_not_bought")
    if p["currency"] == "stars":
        coins_line = f'  {COIN} {t(lang, "mine_pick_for_coins")}: <b>{t(lang, "mine_pick_unavail")}</b>\n'
        stars_line = f'  {STAR} {t(lang, "mine_pick_for_stars")}: <b>{_fmt_num(p["cost_stars"])} {stars_unit}</b>\n'
    elif p["cost"] == 0:
        free = t(lang, "mine_pick_free")
        coins_line = f'  {COIN} {t(lang, "mine_pick_for_coins")}: <b>{free}</b>\n'
        stars_line = f'  {STAR} {t(lang, "mine_pick_for_stars")}: <b>{free}</b>\n'
    else:
        cost_stars = p.get("cost_stars", 0)
        coins_line = f'  {COIN} {t(lang, "mine_pick_for_coins")}: <b>{_fmt_num(p["cost"])}</b>\n'
        stars_line = f'  {STAR} {t(lang, "mine_pick_for_stars")}: <b>{_fmt_num(cost_stars)} {stars_unit}</b>\n'
    return (
        f"<b>{p['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<blockquote><tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_workshop_balance")}: {_fmt_num(data["balance"])}</b>\n'
        f'<b>{t(lang, "mine_pick_name")}: {p["name"]}</b>\n'
        f'<b>{t(lang, "mine_pick_tier")}: {tier}</b>\n'
        f'<b>{t(lang, "mine_pick_per5")}: {_fmt_num(p["dig_min"])}–{_fmt_num(p["dig_max"])}</b></blockquote>\n\n'
        f'<blockquote><tg-emoji emoji-id="5287231198098117669">🎟</tg-emoji> <b>{t(lang, "mine_pick_prices")}:</b>\n'
        f"{coins_line}"
        f"{stars_line}\n</blockquote>"
        f'<b>{t(lang, "mine_pick_status")}: {status}</b>'
    )


def duration_shop_text(data: dict, lang: str = "ru") -> str:
    from lang import t
    cur_key    = data.get("mine_duration_key", "5min")
    cur_label  = _dur_label(DURATIONS[cur_key], lang)
    owned_durs = data.get("owned_durations", ["5min"])
    owned_cnt  = len([k for k in DURATIONS_ORDER if k in owned_durs])
    return (
        f'<tg-emoji emoji-id="5440621591387980068">🎟</tg-emoji> <b>{t(lang, "mine_dur_title")}</b>\n'
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<blockquote><tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_sell_balance")}: {_fmt_num(data["balance"])}{COIN}</b>\n'
        f'<tg-emoji emoji-id="5456140674028019486">🎟</tg-emoji> <b>{t(lang, "mine_dur_active")}: {cur_label}</b>\n'
        f'<tg-emoji emoji-id="5296369303661067030">🎟</tg-emoji> <b>{t(lang, "mine_dur_unlocked")}: {owned_cnt}/{len(DURATIONS_ORDER)}</b></blockquote>\n\n'
        f'<b>{t(lang, "mine_dur_choose")}</b>'
    )


def duration_detail_text(data: dict, dur_key: str, lang: str = "ru") -> str:
    from lang import t
    d          = DURATIONS[dur_key]
    dur_lbl    = _dur_label(d, lang)
    owned_durs = data.get("owned_durations", ["5min"])
    if dur_key == data.get("mine_duration_key", "5min"):
        status = t(lang, "mine_dur_status_active")
    elif dur_key in owned_durs:
        status = t(lang, "mine_dur_status_owned")
    else:
        status = t(lang, "mine_dur_status_none")
    price_str = _fmt_num(d["cost"]) if d["cost"] else t(lang, "mine_dur_free")
    return (
        f'<tg-emoji emoji-id="5440621591387980068">🎟</tg-emoji> <b>{t(lang, "mine_dur_card_title")} {dur_lbl}</b>\n'
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f'<tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_sell_balance")}: {_fmt_num(data["balance"])}{COIN}</b>\n\n'
        f'<tg-emoji emoji-id="5382194935057372936">🎟</tg-emoji> <b>{t(lang, "mine_dur_session")}: {dur_lbl}</b>\n'
        f'<tg-emoji emoji-id="5330320040883411678">🎟</tg-emoji> <b>{t(lang, "mine_dur_price")}: {price_str}{COIN}</b>\n'
        f'<tg-emoji emoji-id="5438496463044752972">🎟</tg-emoji> <b>{t(lang, "mine_dur_status")}: {status}</b>'
    )


def sell_screen_text(data: dict, lang: str = "ru") -> str:
    from lang import t
    has_ores = any(data["ores"].get(o["key"], 0) > 0 for o in ORES)
    title = t(lang, "mine_sell_title")
    if not has_ores:
        return (
            f'<tg-emoji emoji-id="5429518319243775957">🎟</tg-emoji> <b>{title}</b>\n'
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f'<tg-emoji emoji-id="5445221832074483553">🎟</tg-emoji> <b>{t(lang, "mine_sell_empty")}</b>\n\n'
            f'<b>{t(lang, "mine_sell_prompt")}</b>'
        )
    lines = [
        f'<tg-emoji emoji-id="5429518319243775957">🎟</tg-emoji> <b>{title}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<tg-emoji emoji-id="5305699699204837855">🎟</tg-emoji> <b>{t(lang, "mine_sell_prices")}</b>\n'
    ]
    total_value = 0
    for ore in ORES:
        qty = data["ores"].get(ore["key"], 0)
        if qty > 0:
            worth = qty * ore["price"]
            total_value += worth
            lines.append(f"<blockquote><b>{_ore_name(ore, lang)}: {qty} (≈ {_fmt_num(worth)} {COIN})</b></blockquote>")
    lines.append(f'\n<tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "mine_sell_balance")}: {_fmt_num(data["balance"])}</b>')
    lines.append(f'\n<b>{t(lang, "mine_sell_total")}: {_fmt_num(total_value)} {COIN}</b>')
    return "\n".join(lines)


# ============================================================
#  КЛАВИАТУРЫ — aiogram 3.x стиль
# ============================================================

def _prem_btn(emoji_id: str, text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback, icon_custom_emoji_id=emoji_id)


def _back_btn(callback: str, label: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback, icon_custom_emoji_id=EMOJI_BACK)


def mine_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    builder = InlineKeyboardBuilder()
    is_running  = data["mine_start"] is not None and not data["mine_collected"]
    is_finished = False
    if is_running:
        prog        = calc_mine_progress(data)
        is_finished = prog["finished"]
    if not is_running:
        builder.row(_prem_btn(EMOJI_BTN_START, t(lang, "mine_btn_start"), "mine_start"))
    elif is_finished:
        builder.row(_prem_btn(EMOJI_BTN_COLLECT, t(lang, "mine_btn_collect"), "mine_collect"))
    else:
        builder.row(
            _prem_btn(EMOJI_BTN_REFRESH, t(lang, "mine_btn_refresh"), "mine_refresh"),
            _prem_btn(EMOJI_BTN_COLLECT_PART, t(lang, "mine_btn_partial"), "mine_collect"),
        )
    has_ores = any(data["ores"].get(o["key"], 0) > 0 for o in ORES)
    if has_ores:
        builder.row(
            _prem_btn(EMOJI_BTN_SELL, t(lang, "mine_btn_sell"),  "mine_sell_screen"),
            _prem_btn(EMOJI_BTN_INV,  t(lang, "mine_btn_inv"),   "mine_inventory"),
        )
    else:
        builder.row(_prem_btn(EMOJI_BTN_INV, t(lang, "mine_btn_inv"), "mine_inventory"))
    builder.row(
        _prem_btn(EMOJI_BTN_WORKSHOP, t(lang, "mine_btn_workshop"), "mine_workshop_0"),
        _prem_btn(EMOJI_BTN_DURATION, t(lang, "mine_btn_duration"), "mine_duration_shop"),
    )
    builder.row(_back_btn("back_to_menu", t(lang, "btn_back")))
    return builder.as_markup()


def inventory_keyboard(data: dict = None, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(_back_btn("mine", "Back" if lang == "en" else "Назад"))
    return builder.as_markup()


def sell_keyboard(data: dict = None, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    label = "Sell all" if lang == "en" else "Продать всё"
    builder.row(_prem_btn(EMOJI_BTN_SELL_ALL, label, "mine_sell_all"))
    builder.row(_back_btn("mine", "Back" if lang == "en" else "Назад"))
    return builder.as_markup()


def workshop_keyboard(data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    current = data.get("pickaxe", "wood_1")
    owned   = data.get("owned_pickaxes", ["wood_1"])
    page    = max(0, min(page, WORKSHOP_TOTAL_PAGES - 1))
    page_keys = WORKSHOP_PAGES[page]
    buttons = []
    for key in page_keys:
        p     = PICKAXES[key]
        label = p["name"]
        if key == current:
            btn = InlineKeyboardButton(text=label, callback_data=f"pick_info_{key}", icon_custom_emoji_id=EMOJI_SELECTED)
        elif key in owned:
            btn = InlineKeyboardButton(text=label, callback_data=f"pick_info_{key}", style="success")
        else:
            btn = InlineKeyboardButton(text=label, callback_data=f"pick_info_{key}", icon_custom_emoji_id=EMOJI_NOT_BOUGHT)
        buttons.append(btn)
    for i in range(0, len(buttons), 2):
        row = buttons[i:i + 2]
        builder.row(*row)
    nav_row = []
    if page > 0:
        nav_row.append(_prem_btn(EMOJI_BTN_PAGE_PREV, f"{page}", f"mine_workshop_{page - 1}"))
    if page < WORKSHOP_TOTAL_PAGES - 1:
        nav_row.append(_prem_btn(EMOJI_BTN_PAGE_NEXT, f"{page + 2}", f"mine_workshop_{page + 1}"))
    if nav_row:
        builder.row(*nav_row)
    builder.row(_back_btn("mine", "Back" if lang == "en" else "Назад"))
    return builder.as_markup()


def pickaxe_detail_keyboard(data: dict, pick_key: str, page: int = -1, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    p     = PICKAXES[pick_key]
    owned = data.get("owned_pickaxes", ["wood_1"])
    if page < 0:
        page = get_pickaxe_page(pick_key)
    if lang == "en":
        _already_active = "Already active"
        _select         = "Select"
        _coins_unavail  = "Coins unavailable"
        _free           = "Free"
        _back_lbl       = "Back"
    else:
        _already_active = "Уже активна"
        _select         = "Выбрать"
        _coins_unavail  = "Монеты недоступны"
        _free           = "Бесплатно"
        _back_lbl       = "Назад"
    balance = data.get("balance", 0)
    if pick_key == data.get("pickaxe", "wood_1"):
        builder.row(_prem_btn(EMOJI_BTN_ACTIVE, _already_active, "noop"))
    elif pick_key in owned:
        builder.row(InlineKeyboardButton(text=_select, callback_data=f"pick_select_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_SELECT, style="success"))
    elif p["currency"] == "stars":
        builder.row(_prem_btn(EMOJI_BTN_NO_COINS, _coins_unavail, "noop"))
        builder.row(InlineKeyboardButton(text=f"{_fmt_num(p['cost_stars'])} ", callback_data=f"pick_buy_stars_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_BUY_STARS, style="success"))
    elif p["cost"] == 0:
        builder.row(InlineKeyboardButton(text=_free, callback_data=f"pick_buy_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_FREE, style="success"))
        builder.row(InlineKeyboardButton(text=_free, callback_data=f"pick_buy_stars_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_FREE, style="success"))
    else:
        cost_stars = p.get("cost_stars", 0)
        can_afford = balance >= p["cost"]
        if can_afford:
            builder.row(InlineKeyboardButton(text=f"{_fmt_num(p['cost'])} ", callback_data=f"pick_buy_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_BUY_COINS, style="success"))
        else:
            builder.row(InlineKeyboardButton(text=f"{_fmt_num(p['cost'])} ", callback_data=f"pick_buy_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_BUY_COINS, style="danger"))
        builder.row(InlineKeyboardButton(text=f"{_fmt_num(cost_stars)} ", callback_data=f"pick_buy_stars_{pick_key}", icon_custom_emoji_id=EMOJI_BTN_BUY_STARS, style="success"))
    builder.row(_back_btn(f"mine_workshop_{page}", f" {_back_lbl}"))
    return builder.as_markup()


def duration_shop_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder    = InlineKeyboardBuilder()
    current    = data.get("mine_duration_key", "5min")
    owned_durs = data.get("owned_durations", ["5min"])
    buttons    = []
    for key in DURATIONS_ORDER:
        d     = DURATIONS[key]
        label = _dur_label(d, lang)
        if key == current:
            buttons.append(InlineKeyboardButton(text=label, callback_data=f"dur_info_{key}", icon_custom_emoji_id=EMOJI_SELECTED))
        elif key in owned_durs:
            buttons.append(InlineKeyboardButton(text=label, callback_data=f"dur_info_{key}", style="success"))
        else:
            buttons.append(InlineKeyboardButton(text=label, callback_data=f"dur_info_{key}", icon_custom_emoji_id=EMOJI_NOT_BOUGHT))
    builder.add(*buttons)
    builder.adjust(3)
    builder.row(_back_btn("mine", "Back" if lang == "en" else "Назад"))
    return builder.as_markup()


def duration_detail_keyboard(data: dict, dur_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder    = InlineKeyboardBuilder()
    d          = DURATIONS[dur_key]
    owned_durs = data.get("owned_durations", ["5min"])
    if lang == "en":
        _already_active = "Already active"
        _select         = "Select"
        _back_lbl       = "Back"
    else:
        _already_active = "Уже активна"
        _select         = "Выбрать"
        _back_lbl       = "Назад"
    balance = data.get("balance", 0)
    if dur_key == data.get("mine_duration_key", "5min"):
        builder.row(_prem_btn(EMOJI_BTN_ACTIVE, _already_active, "noop"))
    elif dur_key in owned_durs:
        builder.row(InlineKeyboardButton(text=_select, callback_data=f"dur_select_{dur_key}", icon_custom_emoji_id=EMOJI_BTN_SELECT, style="success"))
    else:
        can_afford = balance >= d["cost"]
        if can_afford:
            builder.row(InlineKeyboardButton(text=f"{_fmt_num(d['cost'])} ", callback_data=f"dur_buy_{dur_key}", icon_custom_emoji_id=EMOJI_BTN_DUR_BUY, style="success"))
        else:
            builder.row(InlineKeyboardButton(text=f"{_fmt_num(d['cost'])} ", callback_data=f"dur_buy_{dur_key}", icon_custom_emoji_id=EMOJI_BTN_DUR_BUY, style="danger"))
    builder.row(_back_btn("mine_duration_shop", _back_lbl))
    return builder.as_markup()


# ============================================================
#  ЛОГИКА
# ============================================================

def sell_all_ores(data: dict, lang: str = "ru") -> tuple:
    from lang import t
    total = 0
    lines = []
    for ore in ORES:
        qty = data["ores"].get(ore["key"], 0)
        if qty > 0:
            earned = qty * ore["price"]
            total += earned
            lines.append(f"<blockquote><b>{_ore_name(ore, lang)}: {qty} (≈ {_fmt_num(earned)} {COIN})</b></blockquote>")
            data["ores"][ore["key"]] = 0
    data["balance"] = data.get("balance", 0) + total
    report = "\n".join(lines) if lines else f"  {t(lang, 'mine_sell_nothing')}"
    return total, report


def buy_pickaxe(data: dict, pick_key: str, lang: str = "ru") -> tuple:
    from lang import t
    if pick_key not in PICKAXES:
        return False, t(lang, "pick_unknown")
    p = PICKAXES[pick_key]
    if p["currency"] == "stars":
        return False, t(lang, "pick_stars_only")
    owned = data.setdefault("owned_pickaxes", ["wood_1"])
    if pick_key in owned:
        return False, t(lang, "pick_already_owned")
    if p["cost"] == 0:
        owned.append(pick_key)
        return True, t(lang, "pick_free_ok").format(name=p["name"])
    if data["balance"] < p["cost"]:
        return False, t(lang, "pick_no_coins").format(cost=f"{_fmt_num(p['cost'])} {COIN}")
    data["balance"] -= p["cost"]
    owned.append(pick_key)
    return True, t(lang, "pick_bought").format(name=p["name"], cost=f"{_fmt_num(p['cost'])} {COIN}")


def grant_premium_pickaxe(data: dict, pick_key: str, lang: str = "ru") -> tuple:
    from lang import t
    if pick_key not in PICKAXES:
        return False, t(lang, "pick_unknown")
    p     = PICKAXES[pick_key]
    owned = data.setdefault("owned_pickaxes", ["wood_1"])
    if pick_key in owned:
        return False, t(lang, "pick_already_owned")
    owned.append(pick_key)
    stars = p.get("cost_stars", 0)
    msg = (
        f"{t(lang, 'pick_premium_thanks')}\n"
        f"{t(lang, 'pick_premium_got').format(name=p['name'], stars=f'{_fmt_num(stars)}')}\n"
        f"({_fmt_num(p['dig_min'])}–{_fmt_num(p['dig_max'])} {t(lang, 'pick_premium_hits')})!"
    )
    return True, msg


def select_pickaxe(data: dict, pick_key: str, lang: str = "ru") -> tuple:
    from lang import t
    owned = data.get("owned_pickaxes", ["wood_1"])
    if pick_key not in owned:
        return False, t(lang, "pick_not_owned")
    if data["mine_start"] is not None and not data["mine_collected"]:
        return False, t(lang, "pick_no_change_mining")
    data["pickaxe"] = pick_key
    return True, t(lang, "pick_selected").format(name=PICKAXES[pick_key]["name"])


def buy_duration(data: dict, dur_key: str, lang: str = "ru") -> tuple:
    from lang import t
    if dur_key not in DURATIONS:
        return False, t(lang, "dur_unknown")
    d     = DURATIONS[dur_key]
    owned = data.setdefault("owned_durations", ["5min"])
    if dur_key in owned:
        return False, t(lang, "dur_already_owned")
    if data["balance"] < d["cost"]:
        return False, t(lang, "dur_no_coins").format(cost=f"{_fmt_num(d['cost'])} {COIN}")
    data["balance"] -= d["cost"]
    owned.append(dur_key)
    dur_lbl = _dur_label(d, lang)
    return True, t(lang, "dur_bought").format(label=dur_lbl, cost=f"{_fmt_num(d['cost'])} {COIN}")


def select_duration(data: dict, dur_key: str, lang: str = "ru") -> tuple:
    from lang import t
    owned = data.get("owned_durations", ["5min"])
    if dur_key not in owned and DURATIONS.get(dur_key, {}).get("cost", 1) != 0:
        return False, t(lang, "dur_not_owned")
    if data["mine_start"] is not None and not data["mine_collected"]:
        return False, t(lang, "dur_no_change_mining")
    data["mine_duration_key"] = dur_key
    dur_lbl = _dur_label(DURATIONS[dur_key], lang)
    return True, t(lang, "dur_selected").format(label=dur_lbl)


def collect_mine(data: dict, lang: str = "ru") -> tuple:
    from lang import t
    prog          = calc_mine_progress(data)
    new_campaigns = prog["new_campaigns"]
    if new_campaigns == 0:
        return prog, ""
    from shop import get_active_booster_multiplier, get_active_booster_info, _multiplier_label, get_artifact_mine_multiplier
    from status import get_status_multiplier as _status_mine_mult
    multiplier = get_active_booster_multiplier(data) * get_artifact_mine_multiplier(data) * _status_mine_mult(data)
    pick_key = data.get("pickaxe", "wood_1")
    results  = {}
    for _ in range(new_campaigns):
        for ore, qty in roll_ore(pick_key, multiplier):
            results[ore["key"]] = results.get(ore["key"], 0) + qty
            data["ores"][ore["key"]] = data["ores"].get(ore["key"], 0) + qty
    data["mine_campaigns_done"] = prog["campaigns_done"]
    if prog["finished"]:
        data["mine_collected"] = True
    total_ore_count = sum(results.values())
    add_xp(data, total_ore_count * XP_PER_ORE)
    if results:
        loot_lines = []
        for key, qty in results.items():
            ore   = ORES_BY_KEY[key]
            worth = qty * ore["price"]
            ore_name = _ore_name(ore, lang)
            loot_lines.append(f"<blockquote><b>{ore_name}: {qty} (≈ {_fmt_num(worth)} {COIN})</b></blockquote>")
        loot = "\n".join(loot_lines)
    else:
        loot = f"<b>{t(lang, 'mine_collect_nothing')}</b>"
    bar = progress_bar(prog["percent"])
    booster_line = ""
    active = get_active_booster_info(data)
    if active:
        mult_label = _multiplier_label(active["multiplier"])
        booster_label = f"{t(lang, 'mine_booster_active')} {mult_label} {t(lang, 'mine_booster_active_sfx')}"
        booster_line = f'<tg-emoji emoji-id="5438571934210082705">⚡</tg-emoji> <b>{booster_label}</b>\n'
    _result_title   = t(lang, "mine_collect_title")
    _campaigns_lbl  = t(lang, "mine_collect_campaigns")
    _session_done   = f"<b>{t(lang, 'mine_collect_done')}</b>"
    _still_running  = f"<b>⏳ {t(lang, 'mine_collect_running')} {fmt_time(prog['time_left'], lang)}</b>"
    result_text = (
        f'<tg-emoji emoji-id="5197371802136892976">🎟</tg-emoji> <b>{_result_title}</b>\n'
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>{_campaigns_lbl}: {new_campaigns}</b>\n'
        f'<tg-emoji emoji-id="5231200819986047254">🎟</tg-emoji> {bar}\n'
        f"{booster_line}\n"
        f"{loot}\n\n"
    )
    if prog["finished"]:
        result_text += _session_done
    else:
        result_text += _still_running
    return prog, result_text


def get_pickaxe_page(pick_key: str) -> int:
    if pick_key not in PICKAXES_ORDER:
        return 0
    idx = PICKAXES_ORDER.index(pick_key)
    return idx // WORKSHOP_PAGE_SIZE


def init_mine_data() -> dict:
    return {
        "ores":                {o["key"]: 0 for o in ORES},
        "pickaxe":             "wood_1",
        "owned_pickaxes":      ["wood_1"],
        "mine_duration_key":   "5min",
        "owned_durations":     ["5min"],
        "mine_start":          None,
        "mine_campaigns_done": 0,
        "mine_collected":      False,
    }


def shop_pickaxes_text(lang: str = "ru") -> str:
    title = "SHOP — PICKAXES" if lang == "en" else "МАГАЗИН — КИРКИ"
    hits  = "Hits" if lang == "en" else "Ударов"
    price = "Price" if lang == "en" else "Цена"
    per   = "per campaign" if lang == "en" else "за кампанию"
    lines = [f"🛒 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for key in PICKAXES_ORDER:
        p    = PICKAXES[key]
        cost = _fmt_cost(key, lang)
        lines.append(
            f"<b>{p['name']}</b>\n"
            f"  ⛏ {hits}: <b>{_fmt_num(p['dig_min'])}–{_fmt_num(p['dig_max'])}</b> {per}\n"
            f"  💵 {price}: <b>{cost}</b>\n"
        )
    return "\n".join(lines)


def shop_pickaxes_keyboard(data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    return workshop_keyboard(data, page, lang)
