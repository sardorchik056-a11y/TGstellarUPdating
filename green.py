# ============================================================
#  green.py — «Садовый Дневник»: медитативный раздел без боёв.
#
#  ВАЖНО: этот модуль НИЧЕГО не регистрирует сам (нет @dp.message
#  внутри). Все хендлеры (команды/колбэки) регистрируются в main.py —
#  так же, как это уже сделано для case.py. Здесь только данные,
#  игровая логика и тексты.
#
#  Хранение состояния: внутри d["garden"] (обычный JSON-блоб
#  пользователя, тот же самый data_json, что и всё остальное в
#  проекте) — новых таблиц в БД не требуется, migration не нужна.
# ============================================================

import asyncio
import random
import time
from datetime import datetime, date

from database import aio_get_or_create_user, aio_save_user, aio_get_all_users, format_amount

# ──────────────────────────────────────────────────────────────
#  РИТУАЛЫ
# ──────────────────────────────────────────────────────────────

# key -> (команда без "/", название для текста, эмодзи, стадия открытия,
#         глагол в прошедшем времени для дневника с плейсхолдером {f})
RITUALS = {
    "полить":         {"title": "Полить",         "emoji": "💧", "unlock_stage": 0,
                        "diary": "Я полил {f}, и мне показалось, что оно благодарно блеснуло."},
    "опрыскать":      {"title": "Опрыскать",      "emoji": "🌫", "unlock_stage": 1,
                        "diary": "Я опрыскал листья {f}, и в воздухе повис лёгкий свежий туман."},
    "укрыть":         {"title": "Укрыть",         "emoji": "🧣", "unlock_stage": 1,
                        "diary": "Я укрыл {f} от сквозняка, и оно как будто расслабилось."},
    "погладить":      {"title": "Погладить",      "emoji": "🤲", "unlock_stage": 1,
                        "diary": "Я погладил {f}, и он чуть наклонился в мою сторону."},
    "удобрить":       {"title": "Удобрить",       "emoji": "🌾", "unlock_stage": 1,
                        "diary": "Я удобрил землю у {f}, и почувствовал, как в ней зашевелилась жизнь."},
    "включить_свет":  {"title": "Дать свет",      "emoji": "☀️", "unlock_stage": 1,
                        "diary": "Я подарил {f} немного света, и оно потянулось навстречу."},
    "притемнить":     {"title": "Создать тень",   "emoji": "🌘", "unlock_stage": 1,
                        "diary": "Я укрыл {f} мягкой тенью, и оно выдохнуло спокойно."},
    "шепот":          {"title": "Прошептать",     "emoji": "🤫", "unlock_stage": 2,
                        "diary": "Бутон засветился, когда я прошептал ему своё имя."},
    "танец":          {"title": "Потанцевать",    "emoji": "💃", "unlock_stage": 3,
                        "diary": "{f} танцевал со мной в ритме ветра."},
    "поговорить":     {"title": "Поговорить",     "emoji": "🗣", "unlock_stage": 4,
                        "diary": "{f} заговорил со мной тихим шёпотом листвы."},
}
RITUAL_KEYS = list(RITUALS.keys())

# Пары ритуалов для определения характера растения на стадии 5
_CHAR_PAIRS = {
    "water":  ("полить", "опрыскать"),
    "touch":  ("погладить", "танец"),
    "word":   ("шепот", "поговорить"),
    "light":  ("включить_свет", "притемнить"),
}

CHARACTERS = {
    "water":  {"name": "Водный Лотос",       "emoji": "🪷",
               "desc": "даёт +5 к удаче каждый день в случайных событиях"},
    "touch":  {"name": "Поющий Цветок",      "emoji": "🌸",
               "desc": "открывает доступ к радужным стикерам каждый вечер"},
    "word":   {"name": "Древний Дуб-Мудрец", "emoji": "🌳",
               "desc": "предсказывает погоду на завтра"},
    "light":  {"name": "Огненный Клён",      "emoji": "🍁",
               "desc": "даёт +10% к скорости роста будущих растений"},
    "rainbow": {"name": "Радужный Кристалл", "emoji": "💎",
               "desc": "даёт +10 ко всем бонусам сразу — самый редкий характер"},
    "gray":   {"name": "Серый Черенок",      "emoji": "🥀",
               "desc": "пока без особых способностей — попробуй в следующий раз побыть внимательнее"},
}

# ──────────────────────────────────────────────────────────────
#  СТАДИИ РОСТА
# ──────────────────────────────────────────────────────────────

STAGES = [
    {"name": "Семя-Спящий",      "form": "Семя",  "days": 1, "emoji": "🌰"},
    {"name": "Росток-Нежный",    "form": "Росток","days": 7, "emoji": "🌱"},
    {"name": "Бутон-Таинственный","form": "Бутон", "days": 7, "emoji": "🌿"},
    {"name": "Цветок-Сияющий",  "form": "Цветок","days": 7, "emoji": "🌸"},
    {"name": "Плод-Мудрый",     "form": "Плод",  "days": 7, "emoji": "🍈"},
    {"name": "Древо-Предок",    "form": "Древо", "days": None, "emoji": "🌳"},
]

STAGE_COIN_REWARD = [5, 10, 15, 20, 50]  # за переход НА стадию 1..5

# ──────────────────────────────────────────────────────────────
#  80 РАСТЕНИЙ ГЕРБАРИЯ
#  каждое: id, name, emoji, category, flavor (короткая деталь для описания)
# ──────────────────────────────────────────────────────────────

def _p(pid, name, emoji, cat, flavor):
    return {"id": pid, "name": name, "emoji": emoji, "category": cat, "flavor": flavor}

PLANTS = []

# --- Базовые (5) — стадия 1 ---
for pid, name, emoji, flavor in [
    ("base_daisy",     "Ромашка",     "🌼", "простая и честная, как летнее утро"),
    ("base_cornflower","Василёк",     "💠", "синий, как небо после дождя"),
    ("base_bell",      "Колокольчик","🔔", "тихонько звенит на ветру, если прислушаться"),
    ("base_dandelion", "Одуванчик",  "🌾", "готов улететь с первым же желанием"),
    ("base_sunflower", "Подсолнух",  "🌻", "весь день поворачивается вслед за солнцем"),
]:
    PLANTS.append(_p(pid, name, emoji, "Базовые", flavor))

# --- Цветущие (15) — стадии 2,3,4 ---
for pid, name, emoji, flavor in [
    ("bloom_rose",     "Роза",     "🌹", "бархатные лепестки пахнут мёдом и утренней росой"),
    ("bloom_lily",     "Лилия",    "🤍", "белая, торжественная, будто сошла со старой картины"),
    ("bloom_peony",    "Пион",     "🌺", "пышный и щедрый, как хорошее настроение"),
    ("bloom_tulip",    "Тюльпан",  "🌷", "стройный, весенний, обещающий тепло"),
    ("bloom_orchid",   "Орхидея",  "🪻", "загадочная гостья из тропического сна"),
]:
    PLANTS.append(_p(pid, name, emoji, "Цветущие", flavor))

for pid, name, emoji, flavor in [
    ("bloom_lavender", "Лаванда",  "💜", "пахнет спокойным вечером и чистым бельём"),
    ("bloom_jasmine",  "Жасмин",   "🤍", "раскрывается ночью и наполняет сад сладким ароматом"),
    ("bloom_lilac",    "Сирень",   "💐", "гроздья лиловых звёзд на тонких ветках"),
    ("bloom_magnolia", "Магнолия","🌸", "крупные лепестки, будто вылепленные из воска"),
    ("bloom_wisteria", "Глициния","🟣", "свисает лиловым водопадом с невидимой опоры"),
]:
    PLANTS.append(_p(pid, name, emoji, "Цветущие", flavor))

for pid, name, emoji, flavor in [
    ("bloom_lotus",     "Лотос",    "🪷", "растёт из ила, но остаётся идеально чистым"),
    ("bloom_sakura",    "Сакура",   "🌸", "цветёт всего неделю — и от этого ещё дороже"),
    ("bloom_edelweiss", "Эдельвейс","⚪", "звезда, что растёт только там, где тихо"),
    ("bloom_mimosa",    "Мимоза",   "🟡", "стесняется прикосновений и сжимает листья"),
    ("bloom_azalea",    "Азалия",   "🌺", "яркая вспышка цвета среди зелёных теней"),
]:
    PLANTS.append(_p(pid, name, emoji, "Цветущие", flavor))

# --- Экзотические (8) — из семян ---
for pid, name, emoji, flavor in [
    ("exo_ghost_orchid", "Орхидея-Призрак", "👻", "почти невидима, пока не зацветёт в темноте"),
    ("exo_strelitzia",   "Стрелиция",       "🦩", "похожа на птицу, застывшую перед взлётом"),
    ("exo_anthurium",    "Антуриум",        "❤️", "глянцевое сердце среди тропической листвы"),
    ("exo_heliconia",    "Геликония",       "🦞", "яркая, будто вырезанная из тропического заката"),
    ("exo_plumeria",     "Плюмерия",        "🌼", "цветок, из которого плетут гавайские венки"),
    ("exo_tillandsia",   "Тилландсия",      "🌫", "живёт вовсе без земли, питаясь воздухом"),
    ("exo_bromelia",     "Бромелия",        "🔴", "хранит капли росы в самом центре розетки"),
    ("exo_passiflora",   "Пассифлора",      "🟣", "цветок страсти со сложным звёздчатым узором"),
]:
    PLANTS.append(_p(pid, name, emoji, "Экзотические", flavor))

# --- Лесные (8) ---
for pid, name, emoji, flavor in [
    ("forest_fern",     "Папоротник Орляк","🌿", "разворачивается спиралью, как древний свиток"),
    ("forest_oxalis",   "Кислица",         "🍀", "складывает листья перед дождём заранее"),
    ("forest_lily",     "Ландыш",          "🤍", "маленькие колокольчики с очень стойким ароматом"),
    ("forest_blueberry", "Черника",        "🫐", "прячет сладость под скромными зелёными листьями"),
    ("forest_moss",      "Мох-Ягель",      "🌾", "хрустит под ногами и живёт веками"),
    ("forest_clubmoss",  "Плаун",          "🟢", "ровесник динозавров среди лесной подстилки"),
    ("forest_pyrola",    "Грушанка",       "⚪", "цветёт тихо в самой густой тени"),
    ("forest_asarum",    "Копытень",       "💚", "прячет цветок прямо у земли, под листьями"),
]:
    PLANTS.append(_p(pid, name, emoji, "Лесные", flavor))

# --- Горные (4) ---
for pid, name, emoji, flavor in [
    ("mount_rhodo",   "Рододендрон",  "🌺", "цветёт там, где кончается лес и начинается камень"),
    ("mount_gentian", "Горечавка",    "💙", "синева, что спорит с цветом неба на высоте"),
    ("mount_saxifrage","Камнеломка", "⚪", "буквально прорастает сквозь трещины в скале"),
    ("mount_edelweiss2","Горный Эдельвейс","🤍", "редкая награда для тех, кто поднялся выше облаков"),
]:
    PLANTS.append(_p(pid, name, emoji, "Горные", flavor))

# --- Пустынные (4) ---
for pid, name, emoji, flavor in [
    ("desert_opuntia", "Кактус Опунция", "🌵", "колючий снаружи, но полон воды внутри"),
    ("desert_aloe",    "Алоэ Вера",      "🪴", "лечит там, где обжигает солнце"),
    ("desert_agave",   "Агава",          "🌵", "терпеливо копит силы десятилетиями ради одного цветения"),
    ("desert_euphorbia","Молочай",       "🟢", "маскируется под кактус, но им не является"),
]:
    PLANTS.append(_p(pid, name, emoji, "Пустынные", flavor))

# --- Болотные (3) ---
for pid, name, emoji, flavor in [
    ("swamp_cottongrass","Пушица",        "☁️", "белые пушистые шапки над тихой топью"),
    ("swamp_sphagnum",   "Сфагнум",       "🟢", "губка болота, что копит воду веками"),
    ("swamp_cranberry",  "Клюква Болотная","🔴", "прячет кислую ягоду среди мягкого мха"),
]:
    PLANTS.append(_p(pid, name, emoji, "Болотные", flavor))

# --- Хищные (3) ---
for pid, name, emoji, flavor in [
    ("carn_flytrap",  "Венерина Мухоловка", "🪤", "захлопывается за доли секунды — и не ошибается"),
    ("carn_nepenthes","Непентес",           "🫙", "прячет кувшинчик-ловушку с сладкой приманкой"),
    ("carn_sundew",   "Росянка",            "✨", "ловит на липкие капли, похожие на росу"),
]:
    PLANTS.append(_p(pid, name, emoji, "Хищные", flavor))

# --- Сезонные (20) — 4 сезона × 5 ---
SEASON_PLANTS = {
    "spring": [
        ("season_snowdrop", "Подснежник", "❄️", "первым пробивается сквозь тающий снег"),
        ("season_crocus",   "Крокус",     "🟣", "открывается на пару часов раньше, чем всё вокруг"),
        ("season_hyacinth", "Гиацинт",    "💜", "аромат, в котором чувствуется приход весны"),
        ("season_narcissus","Нарцисс",    "💛", "смотрится в лужи после мартовского дождя"),
        ("season_lungwort", "Медуница",   "💙", "меняет цвет лепестков за один день"),
    ],
    "summer": [
        ("season_cosmea",     "Космея",     "🌸", "лёгкая, будто состоит из воздуха и лета"),
        ("season_zinnia",     "Циния",      "🟠", "держит форму даже под самым жарким солнцем"),
        ("season_nasturtium", "Настурция",  "🧡", "яркая заплатка цвета на летней грядке"),
        ("season_calendula",  "Календула",  "🟡", "закрывается вечером и снова открывается утром"),
        ("season_purslane",   "Портулак",   "🌺", "не боится жары и растёт там, где сухо"),
    ],
    "autumn": [
        ("season_aster",       "Астра Осенняя", "💜", "цветёт назло первым холодам"),
        ("season_chrysanthemum","Хризантема",   "🟡", "держится дольше всех, даже когда сад уже пуст"),
        ("season_marigold",     "Бархатцы",     "🟠", "пахнет землёй и поздним урожаем"),
        ("season_heather",      "Вереск",       "💗", "покрывает целые холмы лиловым туманом"),
        ("season_colchicum",    "Безвременник",  "🟣", "цветёт осенью, а листья пускает лишь весной"),
    ],
    "winter": [
        ("season_hellebore", "Морозник",       "🤍", "цветёт прямо сквозь снег в самый глухой мороз"),
        ("season_holly",     "Падуб",          "🔴", "яркие ягоды среди колючих зимних листьев"),
        ("season_mistletoe", "Омела",          "💚", "живёт высоко в кронах, зеленея всю зиму"),
        ("season_wjasmine",  "Зимний Жасмин",  "💛", "распускается жёлтым огоньком в самые тёмные дни"),
        ("season_icebloom",  "Ледяной Цветок", "🩵", "будто выточен изо льда, но живой и тёплый"),
    ],
}
for _season, _lst in SEASON_PLANTS.items():
    for pid, name, emoji, flavor in _lst:
        PLANTS.append(_p(pid, name, emoji, "Сезонные", flavor))

# --- Легендарные (10) — секретные достижения ---
LEGENDARY_PLANTS = {
    "moon_flower":      _p("legend_moon",     "Лунный Цветок",     "🌙", "Легендарные", "раскрывается только тем, кто не спит в полночь"),
    "eternal_oak":      _p("legend_oak",      "Вечный Дуб",        "🌳", "Легендарные", "не пропустил ни дня — и потому не увядает"),
    "rainbow_cactus":   _p("legend_cactus",   "Радужный Кактус",   "🌈", "Легендарные", "собрал все краски заботы в один день"),
    "wisdom_tree":      _p("legend_wisdom",   "Древо Мудрости",    "📖", "Легендарные", "выросло из сотни тихих разговоров"),
    "dancing_banana":   _p("legend_banana",   "Танцующий Банан",   "🍌", "Легендарные", "нелепое и весёлое — награда за пятьдесят танцев"),
    "golden_rose":      _p("legend_golden",   "Золотая Роза",      "🏵", "Легендарные", "сияет золотом за настоящую коллекцию"),
    "immortelle":       _p("legend_immortelle","Бессмертник",      "♾", "Легендарные", "прошло полный круг роста дважды"),
    "elements_flower":  _p("legend_elements", "Цветок Стихий",     "🌪", "Легендарные", "видел дождь, солнце, снег и ветер"),
    "tree_of_life":     _p("legend_life",     "Древо Жизни",       "🌲", "Легендарные", "почти весь гербарий уместился в его тени"),
    "cosmic_lotus":     _p("legend_cosmic",   "Космический Лотос", "🌌", "Легендарные", "последний и единственный — весь гербарий собран"),
}
for _lp in LEGENDARY_PLANTS.values():
    PLANTS.append(_lp)

PLANTS_BY_ID = {p["id"]: p for p in PLANTS}
assert len(PLANTS) == 80, f"Ожидалось 80 растений, получилось {len(PLANTS)}"

CATEGORY_ORDER = ["Базовые", "Цветущие", "Экзотические", "Лесные", "Горные",
                   "Пустынные", "Болотные", "Хищные", "Сезонные", "Легендарные"]

SEED_POOL_IDS = [p["id"] for p in PLANTS if p["category"] in
                  ("Экзотические", "Лесные", "Горные", "Пустынные", "Болотные", "Хищные")]

# Сопоставление стадия -> id растений, открывающихся при переходе на неё
_bloom_ids = [p["id"] for p in PLANTS if p["category"] == "Цветущие"]
STAGE_UNLOCK_PLANTS = {
    1: [p["id"] for p in PLANTS if p["category"] == "Базовые"],
    2: _bloom_ids[0:5],
    3: _bloom_ids[5:10],
    4: _bloom_ids[10:15],
}

# ──────────────────────────────────────────────────────────────
#  ДОСТИЖЕНИЯ
# ──────────────────────────────────────────────────────────────

# Обычные достижения (spec §"Достижения (ачивки)")
ACHIEVEMENTS_G = [
    {"id": "stage1",       "name": "Первый шаг",              "coins": 5,
     "check": lambda g: g["stage"] >= 1},
    {"id": "stage2",       "name": "Нежный росток",           "coins": 10,
     "check": lambda g: g["stage"] >= 2},
    {"id": "stage3",       "name": "Таинственный бутон",      "coins": 15,
     "check": lambda g: g["stage"] >= 3},
    {"id": "stage4",       "name": "Сияющий цветок",          "coins": 20,
     "check": lambda g: g["stage"] >= 4},
    {"id": "stage5",       "name": "Мудрый плод",             "coins": 50,
     "check": lambda g: g["stage"] >= 5},
    {"id": "collect10",    "name": "Начинающий коллекционер", "coins": 10,
     "check": lambda g: len(g["collection"]) >= 10},
    {"id": "collect25",    "name": "Увлечённый садовник",     "coins": 25,
     "check": lambda g: len(g["collection"]) >= 25},
    {"id": "collect50",    "name": "Опытный коллекционер",    "coins": 50,
     "check": lambda g: len(g["collection"]) >= 50},
    {"id": "collect70",    "name": "Мастер гербария",         "coins": 100,
     "check": lambda g: len(g["collection"]) >= 70},
    {"id": "collect80",    "name": "Легенда сада",            "coins": 500,
     "check": lambda g: len(g["collection"]) >= 80},
    {"id": "streak7",      "name": "Трудоголик",              "coins": 10,
     "check": lambda g: g["streak_days"] >= 7},
    {"id": "streak14",     "name": "Железная воля",           "coins": 25,
     "check": lambda g: g["streak_days"] >= 14},
    {"id": "streak21",     "name": "Хранитель времени",       "coins": 50,
     "check": lambda g: g["streak_days"] >= 21},
    {"id": "streak30",     "name": "Душа сада",               "coins": 100,
     "check": lambda g: g["streak_days"] >= 30},
    {"id": "water100",     "name": "Водолей",                 "coins": 10,
     "check": lambda g: g["ritual_counts"].get("полить", 0) >= 100},
    {"id": "whisper50",    "name": "Нежный голос",             "coins": 10,
     "check": lambda g: g["ritual_counts"].get("шепот", 0) >= 50},
    {"id": "dance50",      "name": "Танцор",                  "coins": 10,
     "check": lambda g: g["ritual_counts"].get("танец", 0) >= 50},
    {"id": "talk100",      "name": "Мудрец",                  "coins": 15,
     "check": lambda g: g["ritual_counts"].get("поговорить", 0) >= 100},
    {"id": "all_rituals10","name": "Мастер всех стихий",       "coins": 30,
     "check": lambda g: all(g["ritual_counts"].get(k, 0) >= 10 for k in RITUAL_KEYS)},
]

# Секретные достижения — привязаны к легендарным растениям (награда сама
# по себе — открытие растения; текст появляется только когда игрок близок).
SECRET_ACHIEVEMENTS = [
    {"id": "night_watch",  "name": "Ночной сторож",       "plant": "moon_flower",
     "check": lambda g: g.get("midnight_visits", 0) >= 10,
     "hint": lambda g: f'{g.get("midnight_visits",0)}/10 визитов после полуночи'},
    {"id": "loyal_friend",  "name": "Верный друг",         "plant": "eternal_oak",
     "check": lambda g: g.get("no_miss_streak", 0) >= 30,
     "hint": lambda g: f'{g.get("no_miss_streak",0)}/30 дней без пропуска'},
    {"id": "ritual_master", "name": "Мастер ритуалов",      "plant": "rainbow_cactus",
     "check": lambda g: len(set(g.get("today_ritual_log", []))) >= 10,
     "hint": lambda g: f'{len(set(g.get("today_ritual_log", [])))}/10 ритуалов за сегодня'},
    {"id": "philosopher",   "name": "Философ",             "plant": "wisdom_tree",
     "check": lambda g: g["ritual_counts"].get("поговорить", 0) >= 100,
     "hint": lambda g: f'{g["ritual_counts"].get("поговорить",0)}/100 разговоров'},
    {"id": "artist",        "name": "Художник",            "plant": "dancing_banana",
     "check": lambda g: g["ritual_counts"].get("танец", 0) >= 50,
     "hint": lambda g: f'{g["ritual_counts"].get("танец",0)}/50 танцев'},
    {"id": "collector",     "name": "Собиратель",           "plant": "golden_rose",
     "check": lambda g: len(g["collection"]) >= 50,
     "hint": lambda g: f'{len(g["collection"])}/50 растений'},
    {"id": "patient",       "name": "Терпеливый",           "plant": "immortelle",
     "check": lambda g: g.get("stage5_count", 0) >= 2,
     "hint": lambda g: f'{g.get("stage5_count",0)}/2 раза достигнуто Древо-Предок'},
    {"id": "weather_dependent", "name": "Метеозависимый",   "plant": "elements_flower",
     "check": lambda g: len(g.get("weather_flags", [])) >= 4,
     "hint": lambda g: f'{len(g.get("weather_flags", []))}/4 явлений природы пережито'},
    {"id": "legend_gardener", "name": "Садовник-легенда",   "plant": "tree_of_life",
     "check": lambda g: len(g["collection"]) >= 70,
     "hint": lambda g: f'{len(g["collection"])}/70 растений'},
    {"id": "the_one",       "name": "Единственный",         "plant": "cosmic_lotus",
     "check": lambda g: len(g["collection"]) >= 79,
     "hint": lambda g: f'{len(g["collection"])}/79 остальных растений'},
]

# ──────────────────────────────────────────────────────────────
#  ЕЖЕДНЕВНЫЕ ГЛОБАЛЬНЫЕ ИВЕНТЫ
# ──────────────────────────────────────────────────────────────

DAILY_EVENTS = {
    "rain":  {"name": "Дождливый день 🌧",  "desc": "все ритуалы дают +1 доп. След воспоминания"},
    "sun":   {"name": "Солнечный день ☀️",  "desc": "достаточно 2 ритуалов вместо 3 для активного дня"},
    "wind":  {"name": "Ветреный день 🌬",   "desc": "ритуал «Укрыть» даёт двойной бонус"},
    "moon":  {"name": "Лунная ночь 🌙",     "desc": "«Прошептать» открывает скрытое свойство на сегодня"},
    "bloom": {"name": "Цветущий день 🌼",   "desc": "все растения в Гербарии сегодня как будто найдены — самое время для скриншота!"},
}
_daily_event_state = {"date": None, "key": None}


def get_daily_event() -> dict:
    today = date.today().isoformat()
    if _daily_event_state["date"] != today:
        _daily_event_state["date"] = today
        _daily_event_state["key"] = random.choice(list(DAILY_EVENTS.keys()))
    key = _daily_event_state["key"]
    return {"key": key, **DAILY_EVENTS[key]}


def _current_season() -> str:
    m = date.today().month
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    if m in (9, 10, 11):
        return "autumn"
    return "winter"


SEASON_NAMES = {"spring": "Весенняя неделя 🌸", "summer": "Летняя неделя ☀️",
                "autumn": "Осенняя неделя 🍂", "winter": "Зимняя неделя ❄️"}


def _in_theme_week() -> bool:
    # Первые 7 дней месяца — тематическая неделя текущего сезона
    return date.today().day <= 7


# ──────────────────────────────────────────────────────────────
#  СОСТОЯНИЕ САДА ВНУТРИ d["garden"]
# ──────────────────────────────────────────────────────────────

def _now_ts() -> int:
    return int(time.time())


def _today_str() -> str:
    return date.today().isoformat()


def _default_garden() -> dict:
    return {
        "stage": 0,
        "stage_day": 0,
        "days_total": 0,
        "day_date": _today_str(),
        "day_ritual_count": 0,
        "today_ritual_log": [],
        "ritual_counts": {k: 0 for k in RITUAL_KEYS},
        "streak_days": 0,
        "no_miss_streak": 0,
        "missed_streak": 0,
        "last_active_ts": _now_ts(),
        "character": None,
        "stage5_count": 0,
        "coins": 0,
        "collection": [],
        "diary": [],
        "achievements_g": [],
        "seeds": [],
        "seeds_collected_total": 0,
        "last_seed_collect_ts": 0,
        "midnight_visits": 0,
        "weather_flags": [],
        "season_progress": {"spring": 0, "summer": 0, "autumn": 0, "winter": 0},
        "lonely_notified": False,
        "day_summary_sent_date": None,
        "pending_ritual": None,       # {"ritual": key, "deadline": ts}
        "today_schedule": [],         # [ts, ts, ts, ts] — время подсказок на сегодня
        "today_notified_idx": [],     # индексы schedule, по которым уже уведомили
    }


def get_garden(d: dict) -> dict:
    """Возвращает d['garden'], создавая/докатывая структуру при необходимости.
    Вызывать в начале КАЖДОГО обращения к саду — сам разруливает смену дня."""
    g = d.get("garden")
    if g is None:
        g = _default_garden()
        d["garden"] = g
    else:
        # мягкая миграция недостающих полей (на случай будущих обновлений)
        for k, v in _default_garden().items():
            if k not in g:
                g[k] = v
    _rollover_if_new_day(g)
    return g


def unlocked_rituals(g: dict) -> list[str]:
    return [k for k in RITUAL_KEYS if RITUALS[k]["unlock_stage"] <= g["stage"]]


# ──────────────────────────────────────────────────────────────
#  СМЕНА ДНЯ / ПРОГРЕСС СТАДИЙ
# ──────────────────────────────────────────────────────────────

def _gen_today_schedule() -> list[int]:
    """4 случайных момента времени сегодня между 08:00 и 22:00 (по времени сервера)."""
    today = date.today()
    start = datetime(today.year, today.month, today.day, 8, 0)
    end   = datetime(today.year, today.month, today.day, 22, 0)
    span  = int(end.timestamp() - start.timestamp())
    pts = sorted(random.sample(range(0, span), 4))
    return [int(start.timestamp()) + p for p in pts]


def _rollover_if_new_day(g: dict) -> list[str]:
    """Если наступил новый день — обрабатывает вчерашний прогресс.
    Возвращает список текстовых уведомлений, которые стоит показать/послать
    игроку (переход стадии, откат и т.п.) — используется фоновым циклом."""
    today = _today_str()
    if g["day_date"] == today:
        return []

    notices = []
    was_active = g["day_ritual_count"] >= (2 if get_daily_event()["key"] == "sun" else 3)
    stage_req_days = STAGES[g["stage"]]["days"]

    if g["stage"] == 0:
        # На семени достаточно любого 1 ритуала (доступен только /полить)
        was_active = g["day_ritual_count"] >= 1

    if g["day_ritual_count"] > 0:
        g["no_miss_streak"] = g.get("no_miss_streak", 0) + 1
        g["missed_streak"] = 0
    else:
        g["no_miss_streak"] = 0
        g["missed_streak"] = g.get("missed_streak", 0) + 1

    if was_active and stage_req_days is not None:
        g["streak_days"] += 1
        g["stage_day"] += 1
        if g["stage_day"] >= stage_req_days:
            g["stage"] += 1
            g["stage_day"] = 0
            reward = STAGE_COIN_REWARD[g["stage"] - 1] if g["stage"] - 1 < len(STAGE_COIN_REWARD) else 0
            g["coins"] += reward
            for pid in STAGE_UNLOCK_PLANTS.get(g["stage"], []):
                _unlock_plant(g, pid, silent=True)
            notices.append(f'stage_up:{g["stage"]}')
            if g["stage"] == 5:
                g["stage5_count"] = g.get("stage5_count", 0) + 1
                if g["character"] is None:
                    g["character"] = _assign_character(g)
                    notices.append(f'character:{g["character"]}')
    elif not was_active:
        g["streak_days"] = 0

    # Откат при 7 подряд полностью пропущенных днях (0 ритуалов)
    if g.get("missed_streak", 0) >= 7:
        g["stage_day"] = max(0, g["stage_day"] - 2)
        g["missed_streak"] = 0
        notices.append("rollback")

    # Еженедельный сбор семени, если на стадии 5 — доступность отмечается
    # отдельной проверкой в can_collect_seed(), тут ничего не делаем.

    g["days_total"] += 1
    g["day_date"] = today
    g["day_ritual_count"] = 0
    g["today_ritual_log"] = []
    g["today_schedule"] = _gen_today_schedule()
    g["today_notified_idx"] = []
    g["pending_ritual"] = None
    g["lonely_notified"] = False
    g["day_summary_sent_date"] = None

    newly = check_achievements(g)
    for a in newly:
        notices.append(f'ach:{a}')

    return notices


def _assign_character(g: dict) -> str:
    total = sum(g["ritual_counts"].values())
    if total < 20:
        return "gray"
    pair_sums = {k: g["ritual_counts"].get(a, 0) + g["ritual_counts"].get(b, 0)
                 for k, (a, b) in _CHAR_PAIRS.items()}
    values = list(pair_sums.values())
    avg = sum(values) / len(values) if values else 0
    if avg > 0 and max(values) - min(values) <= max(2, int(avg * 0.15)):
        return "rainbow"
    best_key = max(pair_sums, key=pair_sums.get)
    if pair_sums[best_key] == 0:
        return "gray"
    return best_key


# ──────────────────────────────────────────────────────────────
#  РАСТЕНИЯ / КОЛЛЕКЦИЯ
# ──────────────────────────────────────────────────────────────

def _unlock_plant(g: dict, plant_id: str, silent: bool = False) -> bool:
    if plant_id in g["collection"]:
        return False
    g["collection"].append(plant_id)
    g["coins"] += 2
    return True


def plant_full_description(plant: dict) -> str:
    cat = plant["category"]
    ambience = {
        "Базовые": "Скромное и родное растение, каких много вокруг — но именно поэтому в нём столько уюта.",
        "Цветущие": "Оно раскрылось перед тобой во всей своей красоте, наполняя сад цветом и ароматом.",
        "Экзотические": "Гостья из дальних тёплых широт — необычная, яркая, будто из другого мира.",
        "Лесные": "Тихое дитя леса, привыкшее к тени и шелесту листвы над головой.",
        "Горные": "Выросло там, где воздух разрежен, а тишина — абсолютна.",
        "Пустынные": "Училось выживать там, где воды почти нет, и научилось этому в совершенстве.",
        "Болотные": "Родом из вязкой, тихой топи — но неожиданно нежное на вид.",
        "Хищные": "Не такое безобидное, каким кажется на первый взгляд.",
        "Сезонные": "Появляется лишь в своё время года — и потому особенно ценно.",
        "Легендарные": "Такое растение встречается раз в жизни — и то не у каждого садовника.",
    }.get(cat, "")
    return (
        f'{plant["emoji"]} <b>{plant["name"]}</b> раскрылся(-ась) перед тобой. '
        f'{ambience} Оно {plant["flavor"]}. '
        f'Ты чувствуешь, как мир вокруг становится чуточку добрее. 🌿'
    )


# ──────────────────────────────────────────────────────────────
#  СЕМЕНА-НАСЛЕДНИКИ (стадия 5)
# ──────────────────────────────────────────────────────────────

SEED_GROW_SECONDS = 3 * 24 * 3600  # 3 дня
SEED_COLLECT_INTERVAL = 7 * 24 * 3600  # раз в неделю


def can_collect_seed(g: dict) -> bool:
    if g["stage"] < 5:
        return False
    return _now_ts() - g.get("last_seed_collect_ts", 0) >= SEED_COLLECT_INTERVAL


def collect_seed(g: dict) -> bool:
    if not can_collect_seed(g):
        return False
    g["last_seed_collect_ts"] = _now_ts()
    g["seeds"].append({"planted_at": _now_ts(), "grow_seconds": SEED_GROW_SECONDS, "ready": False})
    g["seeds_collected_total"] += 1
    return True


def process_ready_seeds(g: dict) -> list[dict]:
    """Проверяет проросшие семена, превращает их в случайное непополученное
    растение из пула, возвращает список полученных растений."""
    grown = []
    still = []
    owned_seed_plants = set(pid for pid in g["collection"] if pid in SEED_POOL_IDS)
    available_pool = [pid for pid in SEED_POOL_IDS if pid not in owned_seed_plants]
    for s in g["seeds"]:
        if s.get("ready"):
            still.append(s)
            continue
        if _now_ts() - s["planted_at"] >= s["grow_seconds"]:
            if available_pool:
                pid = random.choice(available_pool)
                available_pool.remove(pid)
                owned_seed_plants.add(pid)
                _unlock_plant(g, pid)
                grown.append(PLANTS_BY_ID[pid])
            # семя использовано (даже если пул уже пуст) — убираем из очереди
        else:
            still.append(s)
    g["seeds"] = still
    return grown


def speed_up_seed(g: dict) -> bool:
    """Тратит 10 монет сада, чтобы ускорить рост первого незрелого семени."""
    pending = [s for s in g["seeds"] if not s.get("ready")]
    if not pending or g["coins"] < 10:
        return False
    g["coins"] -= 10
    s = min(pending, key=lambda s: s["planted_at"])
    s["planted_at"] = _now_ts() - s["grow_seconds"]  # сразу готово
    return True


# ──────────────────────────────────────────────────────────────
#  ДОСТИЖЕНИЯ
# ──────────────────────────────────────────────────────────────

def check_achievements(g: dict) -> list[str]:
    newly = []
    for a in ACHIEVEMENTS_G:
        if a["id"] in g["achievements_g"]:
            continue
        try:
            if a["check"](g):
                g["achievements_g"].append(a["id"])
                g["coins"] += a["coins"]
                newly.append(a["id"])
        except Exception:
            pass
    for a in SECRET_ACHIEVEMENTS:
        if a["id"] in g["achievements_g"]:
            continue
        try:
            if a["check"](g):
                g["achievements_g"].append(a["id"])
                _unlock_plant(g, LEGENDARY_PLANTS[a["plant"]]["id"])
                newly.append(a["id"])
        except Exception:
            pass
    return newly


# ──────────────────────────────────────────────────────────────
#  ВЫПОЛНЕНИЕ РИТУАЛА
# ──────────────────────────────────────────────────────────────

def do_ritual(d: dict, ritual_key: str) -> dict:
    """Основная логика выполнения ритуала. Возвращает:
    {"ok": bool, "reason": str|None, "text": str, "achievements": [...], "seeds_grown": [...]}
    Мутирует d — вызывающий код обязан сохранить пользователя после вызова."""
    g = get_garden(d)

    if ritual_key not in RITUALS:
        return {"ok": False, "reason": "unknown"}

    if RITUALS[ritual_key]["unlock_stage"] > g["stage"]:
        return {"ok": False, "reason": "locked"}

    already_today = ritual_key in g["today_ritual_log"]

    now = _now_ts()
    g["last_active_ts"] = now
    hour = datetime.now().hour
    if 0 <= hour < 5:
        g["midnight_visits"] = g.get("midnight_visits", 0) + 1

    bonus = 0
    event = get_daily_event()
    if event["key"] == "rain":
        bonus += 1
    if event["key"] == "wind" and ritual_key == "укрыть":
        bonus += 1
    if event["key"] in ("rain", "sun", "wind"):
        flags = set(g.get("weather_flags", []))
        flags.add(event["key"])
        if _current_season() == "winter":
            flags.add("snow")
        g["weather_flags"] = list(flags)

    coin_gain = 1 + bonus

    if not already_today:
        g["today_ritual_log"].append(ritual_key)
        g["day_ritual_count"] += 1
        g["ritual_counts"][ritual_key] = g["ritual_counts"].get(ritual_key, 0) + 1
        g["coins"] += coin_gain

    # Была ли это как раз запланированная подсказка? — если да, закрываем её
    bonus_hit = False
    pending = g.get("pending_ritual")
    if pending and pending["ritual"] == ritual_key and now <= pending["deadline"]:
        bonus_hit = True
        g["coins"] += 2
        g["pending_ritual"] = None

    # Дневник
    form = STAGES[g["stage"]]["form"]
    diary_line = RITUALS[ritual_key]["diary"].format(f=form)
    g["diary"].append({"day": g["days_total"] + 1, "date": _today_str(), "text": f'День {g["days_total"] + 1}. {diary_line}'})
    if len(g["diary"]) > 500:
        g["diary"] = g["diary"][-500:]

    seeds_grown = process_ready_seeds(g)
    for p in seeds_grown:
        pass  # уже добавлено в коллекцию внутри process_ready_seeds

    newly_ach = check_achievements(g)

    return {
        "ok": True,
        "already_today": already_today,
        "bonus_hit": bonus_hit,
        "diary_line": diary_line,
        "coin_gain": coin_gain if not already_today else 0,
        "day_ritual_count": g["day_ritual_count"],
        "achievements": newly_ach,
        "seeds_grown": seeds_grown,
    }


# ──────────────────────────────────────────────────────────────
#  ТЕКСТЫ
# ──────────────────────────────────────────────────────────────

def ritual_result_text(d: dict, ritual_key: str, res: dict) -> str:
    r = RITUALS[ritual_key]
    if not res["ok"]:
        if res["reason"] == "locked":
            need = STAGES[r["unlock_stage"]]["name"]
            return (f'🔒 Этот ритуал ещё спит. Он откроется на стадии «{need}».\n'
                     f'Загляни в /сад, чтобы увидеть свой текущий прогресс.')
        return "Что-то пошло не так, попробуй ещё раз."

    g = get_garden(d)
    lines = [f'{r["emoji"]} {res["diary_line"]}']
    if res["already_today"]:
        lines.append("<i>Этот ритуал ты уже выполнял сегодня — сад запомнил, но новый След не начислен.</i>")
    else:
        lines.append(f'<i>+{res["coin_gain"]} 🍃 Монета Сада · Следов сегодня: {res["day_ritual_count"]}</i>')
    if res["bonus_hit"]:
        lines.append("✨ Ты успел ровно вовремя на подсказку сада — бонус +2 монеты!")
    for p in res["seeds_grown"]:
        lines.append(f'\n🌰 Семя-Наследник проросло! {plant_full_description(p)}')
    for aid in res["achievements"]:
        lines.append(f'\n🏆 Новое достижение: <b>{_achievement_name(aid)}</b>!')
    return "\n".join(lines)


def _achievement_name(aid: str) -> str:
    for a in ACHIEVEMENTS_G:
        if a["id"] == aid:
            return a["name"]
    for a in SECRET_ACHIEVEMENTS:
        if a["id"] == aid:
            return a["name"]
    return aid


def garden_status_text(d: dict) -> str:
    g = get_garden(d)
    stage = STAGES[g["stage"]]
    req = stage["days"]
    progress = f'{g["stage_day"]}/{req}' if req is not None else "∞"
    event = get_daily_event()

    lines = [
        f'{stage["emoji"]} <b>{stage["name"]}</b>',
        f'<blockquote>Прогресс стадии: <b>{progress}</b> дней\n'
        f'Следов воспоминания сегодня: <b>{g["day_ritual_count"]}</b>\n'
        f'Дней подряд активен: <b>{g["streak_days"]}</b>\n'
        f'Монет Сада: <b>{g["coins"]}</b> 🍃</blockquote>',
        f'\n🌤 <b>Сегодня в саду:</b> {event["name"]}\n<i>{event["desc"]}</i>',
        f'\n🌿 Открыто растений: <b>{len(g["collection"])}/80</b>',
    ]
    if g["character"]:
        ch = CHARACTERS[g["character"]]
        lines.append(f'\n{ch["emoji"]} Характер растения: <b>{ch["name"]}</b>\n<i>{ch["desc"]}</i>')
    if g["stage"] == 5:
        if can_collect_seed(g):
            lines.append('\n🌰 Готово новое Семя-Наследник! Собери его: /собрать_семя')
        pending_seeds = len([s for s in g["seeds"] if not s.get("ready")])
        if pending_seeds:
            lines.append(f'<i>Прорастает семян: {pending_seeds}</i>')

    unlocked = unlocked_rituals(g)
    ritual_lines = " ".join(f'/{k}' for k in unlocked)
    lines.append(f'\n<b>Доступные ритуалы:</b>\n{ritual_lines}')
    return "\n".join(lines)


def herbarium_overview_text(d: dict) -> str:
    g = get_garden(d)
    owned = set(g["collection"])
    lines = [f'📖 <b>Гербарий</b> — открыто {len(owned)}/80\n']
    for cat in CATEGORY_ORDER:
        cat_plants = [p for p in PLANTS if p["category"] == cat]
        have = sum(1 for p in cat_plants if p["id"] in owned)
        lines.append(f'· {cat}: {have}/{len(cat_plants)}')
    lines.append('\nПодробнее: <code>/гербарий категория</code> (например «/гербарий Цветущие»)')
    lines.append('Описание конкретного растения: <code>/растение Роза</code>')
    return "\n".join(lines)


def herbarium_category_text(d: dict, category: str) -> str:
    g = get_garden(d)
    owned = set(g["collection"])
    match = None
    for cat in CATEGORY_ORDER:
        if cat.lower() == category.strip().lower():
            match = cat
            break
    if not match:
        return f'Такой категории нет. Доступные: {", ".join(CATEGORY_ORDER)}'
    cat_plants = [p for p in PLANTS if p["category"] == match]
    lines = [f'📖 <b>{match}</b> ({sum(1 for p in cat_plants if p["id"] in owned)}/{len(cat_plants)})\n']
    for p in cat_plants:
        if p["id"] in owned:
            lines.append(f'{p["emoji"]} {p["name"]}')
        else:
            lines.append(f'❔ <i>???</i>')
    return "\n".join(lines)


def plant_info_text(d: dict, name: str) -> str:
    g = get_garden(d)
    owned = set(g["collection"])
    name_norm = name.strip().lower()
    for p in PLANTS:
        if p["name"].lower() == name_norm:
            if p["id"] not in owned:
                return "🌑 Это растение ещё не встретилось в твоём саду."
            return plant_full_description(p)
    return "Не нашёл растение с таким названием. Проверь /гербарий."


def achievements_text(d: dict) -> str:
    g = get_garden(d)
    lines = ["🏆 <b>Достижения сада</b>\n"]
    for a in ACHIEVEMENTS_G:
        mark = "✅" if a["id"] in g["achievements_g"] else "▫️"
        lines.append(f'{mark} {a["name"]} — {a["coins"]} 🍃')
    lines.append("\n<b>Секретные достижения:</b>")
    for a in SECRET_ACHIEVEMENTS:
        if a["id"] in g["achievements_g"]:
            plant_name = PLANTS_BY_ID[LEGENDARY_PLANTS[a["plant"]]["id"]]["name"]
            lines.append(f'✅ {a["name"]} → {plant_name}')
        else:
            try:
                hint = a["hint"](g)
            except Exception:
                hint = ""
            # Показываем подсказку только если игрок уже близко
            lines.append(f'▫️ ??? ({hint})' if hint else "▫️ ???")
    return "\n".join(lines)


def diary_text(d: dict, full: bool = False) -> str:
    g = get_garden(d)
    entries = g["diary"] if full else g["diary"][-5:]
    if not entries:
        return "📔 Дневник пока пуст. Начни с /полить."
    header = "📔 <b>Полная лента воспоминаний</b>\n\n" if full else "📔 <b>Последние воспоминания</b>\n\n"
    return header + "\n".join(f'<i>{e["text"]}</i>' for e in entries)


def garden_profile_text(d: dict) -> str:
    g = get_garden(d)
    stage = STAGES[g["stage"]]
    ch = CHARACTERS[g["character"]]["name"] if g["character"] else "ещё не определён"
    return (
        f'🌿 <b>Профиль садовника</b>\n'
        f'<blockquote>'
        f'Стадия: <b>{stage["name"]}</b>\n'
        f'Дней подряд: <b>{g["streak_days"]}</b>\n'
        f'Открыто растений: <b>{len(g["collection"])}/80</b>\n'
        f'Достижений: <b>{len(g["achievements_g"])}/{len(ACHIEVEMENTS_G) + len(SECRET_ACHIEVEMENTS)}</b>\n'
        f'Характер растения: <b>{ch}</b>\n'
        f'Монет Сада: <b>{g["coins"]}</b> 🍃'
        f'</blockquote>'
    )


def daily_summary_text(g: dict) -> str:
    stage = STAGES[g["stage"]]
    req = stage["days"]
    left = (req - g["stage_day"]) if req is not None else None
    left_str = f'{left}' if left is not None else "—"
    return (
        f'🌙 <b>Итог дня</b>\n'
        f'Сегодня ты сделал <b>{g["day_ritual_count"]}</b> ритуалов.\n'
        f'До новой стадии осталось <b>{left_str}</b> дн.\n'
        f'Открыто растений: <b>{len(g["collection"])}/80</b>.'
    )


LONELY_TEXT = ("🌱 Я заскучал... Листья начали опадать. Приди, пожалуйста, "
               "всего одно действие — и я снова улыбнусь!")

MISSED_RITUAL_TEXT_TMPL = "🕯 Ты не успел выполнить «{title}» в этот раз... Ничего страшного, следующая подсказка будет позже."

STAGE_UP_TEXTS = {
    1: "🌱 Семя проснулось и стало <b>Ростком-Нежным</b>! Теперь тебе доступно /погладить.",
    2: "🌿 Росток раскрылся в <b>Бутон-Таинственный</b>! Теперь тебе доступен /шепот.",
    3: "🌸 Бутон расцвёл в <b>Цветок-Сияющий</b>! Теперь тебе доступен /танец.",
    4: "🍈 Цветок налился и стал <b>Плодом-Мудрым</b>! Теперь тебе доступен /поговорить.",
    5: ("🌳 <b>Древо-Предок</b> возвышается перед тобой, могучее и мудрое. Его корни уходят глубоко "
        "в землю, а ветви тянутся к небу. Оно помнит все твои прикосновения, все слова и песни. "
        "Ты не просто садовник — ты часть этого сада. С этого дня Древо будет давать тебе "
        "Семена-Наследники (раз в неделю, /собрать_семя), чтобы твоя коллекция росла вечно."),
}


def character_text(char_key: str) -> str:
    ch = CHARACTERS[char_key]
    return f'{ch["emoji"]} Твоё Древо обрело характер: <b>{ch["name"]}</b>.\n<i>{ch["desc"]}.</i>'


# ──────────────────────────────────────────────────────────────
#  ФОНОВЫЙ ЦИКЛ (уведомления, анти-АФК, итог дня)
# ──────────────────────────────────────────────────────────────

async def green_loop(bot) -> None:
    """Раз в минуту: рассылает подсказки-ритуалы, анти-АФК сообщения,
    итог дня в 23:00. Полный скан пользователей уводится в поток
    (asyncio.to_thread внутри aio_get_all_users), как и остальные фоновые
    циклы проекта — event loop не блокируется."""
    while True:
        try:
            users = await aio_get_all_users()
            now = _now_ts()
            now_dt = datetime.now()
            for d in users:
                if "garden" not in d:
                    continue
                g = d["garden"]
                changed = False

                notices = _rollover_if_new_day(g)
                if notices:
                    changed = True
                    for n in notices:
                        try:
                            if n.startswith("stage_up:"):
                                stg = int(n.split(":")[1])
                                await bot.send_message(d["id"], STAGE_UP_TEXTS.get(stg, ""), parse_mode="HTML")
                            elif n.startswith("character:"):
                                await bot.send_message(d["id"], character_text(n.split(":")[1]), parse_mode="HTML")
                            elif n == "rollback":
                                await bot.send_message(
                                    d["id"],
                                    "🥀 Ты долго не заходил — сад немного увял и откатился на 2 дня "
                                    "прогресса. Но не переживай, растение живо и ждёт тебя!",
                                    parse_mode="HTML",
                                )
                            elif n.startswith("ach:"):
                                await bot.send_message(
                                    d["id"], f'🏆 Новое достижение: <b>{_achievement_name(n.split(":")[1])}</b>!',
                                    parse_mode="HTML",
                                )
                        except Exception:
                            pass

                # Плановые подсказки-ритуалы
                unlocked = unlocked_rituals(g)
                if g.get("pending_ritual") is None and g.get("today_schedule"):
                    for idx, ts in enumerate(g["today_schedule"]):
                        if idx in g.get("today_notified_idx", []):
                            continue
                        if now >= ts:
                            candidates = [k for k in unlocked]
                            if candidates:
                                key = random.choice(candidates)
                                g["pending_ritual"] = {"ritual": key, "deadline": now + 3600}
                                g["today_notified_idx"].append(idx)
                                changed = True
                                try:
                                    r = RITUALS[key]
                                    await bot.send_message(
                                        d["id"],
                                        f'{r["emoji"]} Сад просит внимания! Выполни <code>/{key}</code> '
                                        f'в течение часа, чтобы порадовать растение.',
                                        parse_mode="HTML",
                                    )
                                except Exception:
                                    pass
                            break

                # Просроченная подсказка
                pending = g.get("pending_ritual")
                if pending and now > pending["deadline"]:
                    try:
                        title = RITUALS[pending["ritual"]]["title"]
                        await bot.send_message(d["id"], MISSED_RITUAL_TEXT_TMPL.format(title=title), parse_mode="HTML")
                    except Exception:
                        pass
                    g["pending_ritual"] = None
                    changed = True

                # Анти-АФК: 3 дня без визита
                last_active = g.get("last_active_ts", now)
                days_inactive = (now - last_active) / 86400
                if days_inactive >= 3 and not g.get("lonely_notified"):
                    g["lonely_notified"] = True
                    changed = True
                    try:
                        await bot.send_message(d["id"], LONELY_TEXT, parse_mode="HTML")
                    except Exception:
                        pass

                # Итог дня в 23:00
                if now_dt.hour == 23 and g.get("day_summary_sent_date") != _today_str():
                    g["day_summary_sent_date"] = _today_str()
                    changed = True
                    try:
                        await bot.send_message(d["id"], daily_summary_text(g), parse_mode="HTML")
                    except Exception:
                        pass

                if changed:
                    await aio_save_user(d["id"], d)
        except Exception as e:
            print(f"[green_loop] {e}")
        await asyncio.sleep(60)
