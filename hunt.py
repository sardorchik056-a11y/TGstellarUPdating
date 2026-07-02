# ============================================================
#  hunt.py  —  Охота / Боссы TGStellar
#  Боссы: 10 уникальных, HP общие для всех игроков
#  3 босса в день; после смерти следующий через 2 часа
#  5 мечей с нарастающим уроном
#  Переписан для aiogram 3.x
# ============================================================

import random
import re
import sqlite3
import json
import threading
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from miner import COIN

DB_PATH = "tgstellar.db"

# ─────────────────────────────────────────
#  ЭМОДЗИ
# ─────────────────────────────────────────
_E = {
    "sword":        "5258203794772085854",  # активный меч
    "skull":        "5228962845672096235",  # все боссы
    "fire":         "5438571934210082705",  # fire booster
    "coin":         "5199552030615558774",  # монета
    "reward_coin":  "5438496463044752972",  # монета награды за босса
    "lock":         "5240241223632954241",  # замок
    "ok":           "5206607081334906820",  # галочка
    "back":         "6039539366177541657",  # назад (в меню/раздел)
    "back_page":    "5255703720078879038",  # назад (по страницам)
    "forward":      "5253767677670862169",  # вперёд (по страницам)
    "alert":        "5258203794772085854",  # alert/молния
    "timer":        "5440621591387980068",  # таймер
    "crit":         "5373342608028352831",  # крит
    "dmg":          "5373173798633752502",  # урон
    "shop":         "5465154440287757794",  # оружейная
    "my_swords":    "5454014806950429357",  # мои мечи
    "hp":           "5354905713585975489",  # hp
    "trophy":       "5449683594425410231",  # доход/трофей
    "hunt":         "5228962845672096235",  # охота на боссов
    "dead":         "5228962845672096235",  # для смерти босса
    "spawn":        "5197371802136892976",  # шахта
    "price":        "5397782960512444700",  # ценник
    "bag":          "5443038326535759644",  # инвентарь
    "boss":         "5438571934210082705",  # текущий босс
    "potion":       "5206523956537865948",  # зелье возрождения — TODO: заменить на свой премиум-эмодзи
    "star":         "5262643974912355126",  # звезда (валюта Telegram Stars) — TODO: заменить
}

# ─────────────────────────────────────────
#  ЭМОДЗИ МЕЧЕЙ (замени ID на свои премиум-эмодзи)
# ─────────────────────────────────────────
SWORD_EMOJIS = {
    "blade_of_despair":    "5321022334335724730",
    "kings_bane":          "5229011542011299168",
    "frozen_doom":         "5278728331083149050",
    "void_herald":         "5449883370534238228",
    "fate_cleaver":        "5449841584797413927",
    "deaths_whisper":      "5253539825360843975",
    "ash_oath":            "6311852434616489836",
    "desecrated_blade":    "5454172148782359440",
    "last_verdict":        "5805204653427660834",
    "shadow_of_oblivion":  "5316641691032104151",
    "soul_harvest":        "5219714655802381430",
    "blade_of_hopelessness":"5336812863203853480", # 🗡 Клинок Безысходности  — TODO: заменить
    "seal_of_doom":        "5463250708918711044",
    "rift_of_eternity":    "5463277406435422003",
    "star_devourer":       "5357173434843413977",
}

_DIGIT_EMOJIS = {
    '0': '5217946323277330300',
    '1': '5217834838811227319',
    '2': '5217455082097882931',
    '3': '5217897558218648996',
    '4': '5217549433939438318',
    '5': '5215460404796339401',
    '6': '5217653758695060428',
    '7': '5217861347349413496',
    '8': '5217965650630161714',
    '9': '5217442991764942337',
}

def _tg(eid, fb=""):
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

def _fmt(n) -> str:
    """
    Сокращённый формат чисел: 1500 -> "1.5к", 100000 -> "100к",
    2300000 -> "2.3м" и т.д. Используется для урона, цен, наград.
    HP босса не затрагивается — для него отдельная _fmt_digits().
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

def _now_ts():
    return int(datetime.now(timezone.utc).timestamp())

def _fmt_digits(n: int) -> str:
    """Форматирует число эмодзи-цифрами."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    s = f"{n:,}".replace(",", " ")
    parts = []
    for ch in s:
        if ch.isdigit():
            parts.append(_tg(_DIGIT_EMOJIS[ch], "🔢"))
        else:
            parts.append(ch)
    return ''.join(parts)

# ─────────────────────────────────────────
#  МЕЧИ
# ─────────────────────────────────────────
SWORDS = [
    {
        "key": "blade_of_despair",
        "name": "Клинок Отчаяния", "name_en": "Blade of Despair",
        "emoji_id": SWORD_EMOJIS["blade_of_despair"],
        "desc": "<b><i>Выкован из слёз тех, кто не вернулся из глубин.</i></b>\n<b><i>Каждый удар — последний крик отчаявшейся души.</i></b>",
        "desc_en": "<b><i>Forged from the tears of those who never returned from the depths.</i></b>\n<b><i>Every strike is the last cry of a despairing soul.</i></b>",
        "dmg_min": 50, "dmg_max": 150,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 125_000,
    },
    {
        "key": "kings_bane",
        "name": "Погибель Королей", "name_en": "King's Bane",
        "emoji_id": SWORD_EMOJIS["kings_bane"],
        "desc": "<b><i>Им пали семь правителей подземных царств.</i></b>\n<b><i>Лезвие помнит каждую корону. И жаждет следующей.</i></b>",
        "desc_en": "<b><i>Seven rulers of underground kingdoms fell to this blade.</i></b>\n<b><i>The edge remembers every crown. And craves the next.</i></b>",
        "dmg_min": 80, "dmg_max": 250,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 250_000,
    },
    {
        "key": "frozen_doom",
        "name": "Ледяная Погибель", "name_en": "Frozen Doom",
        "emoji_id": SWORD_EMOJIS["frozen_doom"],
        "desc": "<b><i>Закалён в вечном льду самого холодного яруса.</i></b>\n<b><i>Прикосновение к рукояти оставляет ожог холодом.</i></b>",
        "desc_en": "<b><i>Tempered in the eternal ice of the coldest tier.</i></b>\n<b><i>Touching the hilt leaves a burn of cold.</i></b>",
        "dmg_min": 200, "dmg_max": 500,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 400_000,
    },
    {
        "key": "void_herald",
        "name": "Вестник Бездны", "name_en": "Void Herald",
        "emoji_id": SWORD_EMOJIS["void_herald"],
        "desc": "<b><i>Он появляется раньше, чем бездна открывается.</i></b>\n<b><i>Шёпот клинка слышат только обречённые.</i></b>",
        "desc_en": "<b><i>It arrives before the void even opens.</i></b>\n<b><i>Only the doomed can hear the blade's whisper.</i></b>",
        "dmg_min": 350, "dmg_max": 700,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 750_000,
    },
    {
        "key": "fate_cleaver",
        "name": "Рассекатель Судеб", "name_en": "Fate Cleaver",
        "emoji_id": SWORD_EMOJIS["fate_cleaver"],
        "desc": "<b><i>Разрезает не только плоть — но и нити судьбы.</i></b>\n<b><i>Те, кого он касался, больше не принадлежат этому миру.</i></b>",
        "desc_en": "<b><i>Cuts not just flesh — but the threads of fate itself.</i></b>\n<b><i>Those it has touched no longer belong to this world.</i></b>",
        "dmg_min": 500, "dmg_max": 1_250,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 1_250_000,
    },
    {
        "key": "deaths_whisper",
        "name": "Шепот Смерти", "name_en": "Death's Whisper",
        "emoji_id": SWORD_EMOJIS["deaths_whisper"],
        "desc": "<b><i>Не издаёт звука при ударе. Жертва слышит лишь тишину.</i></b>\n<b><i>Говорят, смерть сама подсказывает ему цель.</i></b>",
        "desc_en": "<b><i>It makes no sound on impact. The victim hears only silence.</i></b>\n<b><i>They say death itself guides it to its mark.</i></b>",
        "dmg_min": 700, "dmg_max": 1_800,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 3_500_000,
    },
    {
        "key": "ash_oath",
        "name": "Клятва Пепла", "name_en": "Ash Oath",
        "emoji_id": SWORD_EMOJIS["ash_oath"],
        "desc": "<b><i>Выкован из пепла сгоревших шахт и павших воинов.</i></b>\n<b><i>Клятва вложена в каждый удар: не остановиться.</i></b>",
        "desc_en": "<b><i>Forged from the ash of burned mines and fallen warriors.</i></b>\n<b><i>An oath sealed in every strike: never stop.</i></b>",
        "dmg_min": 900, "dmg_max": 2_400,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 7_000_000,
    },
    {
        "key": "desecrated_blade",
        "name": "Осквернённый Клинок", "name_en": "Desecrated Blade",
        "emoji_id": SWORD_EMOJIS["desecrated_blade"],
        "desc": "<b><i>Освящённый клинок, погружённый в чёрную магию глубин.</i></b>\n<b><i>Святость обернулась проклятием — и стала страшнее.</i></b>",
        "desc_en": "<b><i>A consecrated blade dipped into the dark magic of the depths.</i></b>\n<b><i>Holiness turned to a curse — and became far worse.</i></b>",
        "dmg_min": 1_200, "dmg_max": 3_200,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 15_000_000,
    },
    {
        "key": "last_verdict",
        "name": "Последний Приговор", "name_en": "Last Verdict",
        "emoji_id": SWORD_EMOJIS["last_verdict"],
        "desc": "<b><i>Вынесен миром, который устал ждать.</i></b>\n<b><i>Приговор окончателен. Обжалование невозможно.</i></b>",
        "desc_en": "<b><i>Passed by a world that grew tired of waiting.</i></b>\n<b><i>The verdict is final. No appeals.</i></b>",
        "dmg_min": 1_600, "dmg_max": 4_200,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 30_000_000,
    },
    {
        "key": "shadow_of_oblivion",
        "name": "Тень Забвения", "name_en": "Shadow of Oblivion",
        "emoji_id": SWORD_EMOJIS["shadow_of_oblivion"],
        "desc": "<b><i>Из него вышли все тени. В него они и вернутся.</i></b>\n<b><i>Забвение — не конец. Это начало чего-то хуже.</i></b>",
        "desc_en": "<b><i>All shadows came from it. To it they shall return.</i></b>\n<b><i>Oblivion is not the end. It is the beginning of something worse.</i></b>",
        "dmg_min": 2_000, "dmg_max": 5_500,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 60_000_000,
    },
    {
        "key": "soul_harvest",
        "name": "Жатва Душ", "name_en": "Soul Harvest",
        "emoji_id": SWORD_EMOJIS["soul_harvest"],
        "desc": "<b><i>Каждая убитая им душа остаётся внутри клинка.</i></b>\n<b><i>Их вопли — его боевой клич.</i></b>",
        "desc_en": "<b><i>Every soul it slays stays trapped within the blade.</i></b>\n<b><i>Their screams are its battle cry.</i></b>",
        "dmg_min": 2_600, "dmg_max": 7_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 120_000_000,
    },
    {
        "key": "blade_of_hopelessness",
        "name": "Клинок Безысходности", "name_en": "Blade of Hopelessness",
        "emoji_id": SWORD_EMOJIS["blade_of_hopelessness"],
        "desc": "<b><i>Тем, кто его видит, кажется — выхода нет.</i></b>\n<b><i>Они правы. Выхода нет.</i></b>",
        "desc_en": "<b><i>Those who see it feel there is no way out.</i></b>\n<b><i>They are right. There is none.</i></b>",
        "dmg_min": 3_500, "dmg_max": 9_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 250_000_000,
    },
    {
        "key": "seal_of_doom",
        "name": "Печать Гибели", "name_en": "Seal of Doom",
        "emoji_id": SWORD_EMOJIS["seal_of_doom"],
        "desc": "<b><i>Поставить печать — значит вынести приговор вечности.</i></b>\n<b><i>Никто не снял её ни разу. Никто и не снимет.</i></b>",
        "desc_en": "<b><i>To set the seal is to pass judgment upon eternity.</i></b>\n<b><i>No one has ever removed it. No one ever will.</i></b>",
        "dmg_min": 4_500, "dmg_max": 12_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 500_000_000,
    },
    {
        "key": "rift_of_eternity",
        "name": "Разлом Вечности", "name_en": "Rift of Eternity",
        "emoji_id": SWORD_EMOJIS["rift_of_eternity"],
        "desc": "<b><i>Разрезает ткань времени. Каждый удар — в прошлое и будущее одновременно.</i></b>\n<b><i>Вечность не бесконечна. Он это доказал.</i></b>",
        "desc_en": "<b><i>It tears the fabric of time. Every strike lands in the past and future at once.</i></b>\n<b><i>Eternity is not infinite. It proved that.</i></b>",
        "dmg_min": 6_000, "dmg_max": 16_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 1_000_000_000,
    },
    {
        "key": "star_devourer",
        "name": "Пожиратель Звёзд", "name_en": "Star Devourer",
        "emoji_id": SWORD_EMOJIS["star_devourer"],
        "desc": "<b><i>Им была погашена первая звезда. Им будет погашена последняя.</i></b>\n<b><i>Вселенная боится его. И правильно делает.</i></b>",
        "desc_en": "<b><i>The first star was extinguished by it. So will the last.</i></b>\n<b><i>The universe fears it. And rightly so.</i></b>",
        "dmg_min": 8_000, "dmg_max": 22_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 5_000_000_000,
    },
]

SWORDS_BY_KEY = {s["key"]: s for s in SWORDS}

# ─────────────────────────────────────────
#  ЗЕЛЬЯ
# ─────────────────────────────────────────
POTIONS = [
    {
        "key": "revival",
        "name": "Зелье Возрождения", "name_en": "Revival Potion",
        "emoji_id": _E["potion"],
        "desc": "<b><i>Сваренное из крови самого босса — оно возвращает его к жизни раньше срока.</i></b>",
        "desc_en": "<b><i>Brewed from the boss's own blood — it brings him back to life ahead of time.</i></b>",
        "effect": "<b><i>Мгновенно возрождает босса, минуя время отката после смерти.</i></b>",
        "effect_en": "<b><i>Instantly revives the boss, skipping the respawn cooldown after death.</i></b>",
        "price_stars": 19,
    },
]

POTIONS_BY_KEY = {p["key"]: p for p in POTIONS}

# Рандомные цитаты для каждого меча в магазине
_SWORD_QUOTES_EN = {
    "blade_of_despair":     "<b><i>They say the first strike with this blade haunts your sleep every night.</i></b>",
    "kings_bane":           "<b><i>Seven crowns. Seven strikes. The eighth one is yours.</i></b>",
    "frozen_doom":          "<b><i>Even the hilt burns with cold. Imagine what the blade feels like.</i></b>",
    "void_herald":          "<b><i>The void stares back at you through it. Stare back.</i></b>",
    "fate_cleaver":         "<b><i>Fate's threads are thin. This blade knows exactly where to find them.</i></b>",
    "deaths_whisper":       "<b><i>The silence after the strike is more terrifying than any scream.</i></b>",
    "ash_oath":             "<b><i>The oath is never broken. Never. Under any circumstances.</i></b>",
    "desecrated_blade":     "<b><i>Consecration requires faith. Desecration requires only desire.</i></b>",
    "last_verdict":         "<b><i>No appeals. The judge has already ruled.</i></b>",
    "shadow_of_oblivion":   "<b><i>Oblivion is not death. It is worse. Much worse.</i></b>",
    "soul_harvest":         "<b><i>Thousands of voices inside. Soon there will be more.</i></b>",
    "blade_of_hopelessness":"<b><i>Those who see it stop looking for a way out. They are right.</i></b>",
    "seal_of_doom":         "<b><i>The seal cannot be removed. You can only receive the next one.</i></b>",
    "rift_of_eternity":     "<b><i>The past and the future are equally vulnerable to it.</i></b>",
    "star_devourer":        "<b><i>The first star went dark at its blow. The last one will too.</i></b>",
}

_SWORD_QUOTES = {
    "blade_of_despair":     "<b><i>Говорят, первый удар этим клинком снится тебе каждую ночь.</i></b>",
    "kings_bane":           "<b><i>Семь корон. Семь ударов. Восьмая твоя.</i></b>",
    "frozen_doom":          "<b><i>Даже рукоять обжигает холодом. Представь, каково лезвие.</i></b>",
    "void_herald":          "<b><i>Бездна смотрит в тебя сквозь него. Смотри в ответ.</i></b>",
    "fate_cleaver":         "<b><i>Нити судьбы тонкие. Этот клинок знает, как их найти.</i></b>",
    "deaths_whisper":       "<b><i>Тишина после удара — страшнее любого крика.</i></b>",
    "ash_oath":             "<b><i>Клятва не нарушается. Никогда. Ни при каких условиях.</i></b>",
    "desecrated_blade":     "<b><i>Освящение требует веры. Осквернение — только желания.</i></b>",
    "last_verdict":         "<b><i>Апелляций нет. Судья уже вынес решение.</i></b>",
    "shadow_of_oblivion":   "<b><i>Забвение — это не смерть. Это хуже. Гораздо хуже.</i></b>",
    "soul_harvest":         "<b><i>Внутри — тысячи голосов. Скоро станет больше.</i></b>",
    "blade_of_hopelessness":"<b><i>Те, кто его видит, перестают искать выход. Они правы.</i></b>",
    "seal_of_doom":         "<b><i>Печать нельзя снять. Можно только получить следующую.</i></b>",
    "rift_of_eternity":     "<b><i>Прошлое и будущее — одинаково уязвимы для него.</i></b>",
    "star_devourer":        "<b><i>Первая звезда погасла от его удара. Последняя — тоже его.</i></b>",
}

# Рандомные цитаты для каждого босса на главном экране охоты
_BOSS_HUNT_QUOTES_EN = {
    "ash_lord":         "<b><i>Ash does not lie. It shows what was. Soon it will show what you will be.</i></b>",
    "rift_lord":        "<b><i>The rift did not open by chance. It was waiting for you specifically.</i></b>",
    "ruin_warden":      "<b><i>Ruins hold secrets. He holds the ruins. You should not be here.</i></b>",
    "storm_king":       "<b><i>The storm in the tunnel is not a force of nature. It is his mood.</i></b>",
    "wasteland_master": "<b><i>The wasteland was once a forest. Before him. Keep that in mind.</i></b>",
    "volcano_lord":     "<b><i>The lava is not hot. That is just his blood, slightly cooled.</i></b>",
    "ice_overlord":     "<b><i>Cold is not a temperature. It is the way he looks at you.</i></b>",
    "abyss_titan":      "<b><i>The abyss stares into you. But he goes first.</i></b>",
    "chasm_keeper":     "<b><i>The chasm has no bottom. He checked. Personally. Many times.</i></b>",
    "storm_overlord":   "<b><i>Lightning strikes twice. If he missed the first time.</i></b>",
    "stone_monarch":    "<b><i>The mountain is his throne. You just walked into the palace.</i></b>",
    "ash_lands_lord":   "<b><i>The ashen lands remember those who came. For a long time. Very long.</i></b>",
    "ice_sovereign":    "<b><i>Ice does not melt. It waits. More patiently than you think.</i></b>",
    "dark_viceroy":     "<b><i>He already knows everything about you. Has for a while. He was just waiting.</i></b>",
    "ruin_overlord":    "<b><i>Every civilization built. He destroyed. The score is not in civilization's favor.</i></b>",
    "depths_master":    "<b><i>The depths are not silent. He is silent. For now.</i></b>",
    "mountain_lord":    "<b><i>You thought you were going up the mountain. You are going to him.</i></b>",
    "cursed_monarch":   "<b><i>The curse kills the weak. It only makes him angrier.</i></b>",
    "void_king":        "<b><i>The void is not nothing. It is his kingdom. Welcome.</i></b>",
    "last_keeper":      "<b><i>He outlived everyone. Every single one. He will outlive you too — unless you try.</i></b>",
}

_BOSS_HUNT_QUOTES = {
    "ash_lord":         "<b><i>Пепел не лжёт. Он показывает, что было. Скоро покажет, что будешь ты.</i></b>",
    "rift_lord":        "<b><i>Разлом открылся не случайно. Он ждал именно тебя.</i></b>",
    "ruin_warden":      "<b><i>Руины хранят тайны. Он хранит руины. Тебе сюда не надо.</i></b>",
    "storm_king":       "<b><i>Буря в тоннеле — это не стихия. Это его настроение.</i></b>",
    "wasteland_master": "<b><i>Пустошь была лесом. До него. Учти это.</i></b>",
    "volcano_lord":     "<b><i>Лава не горячая. Это просто его кровь остыла немного.</i></b>",
    "ice_overlord":     "<b><i>Холод — это не температура. Это его взгляд на тебя.</i></b>",
    "abyss_titan":      "<b><i>Бездна смотрит в тебя. Но сначала — он.</i></b>",
    "chasm_keeper":     "<b><i>Пропасть бездонная. Он проверял. Лично. Много раз.</i></b>",
    "storm_overlord":   "<b><i>Молния бьёт дважды. Если он промахнулся с первого раза.</i></b>",
    "stone_monarch":    "<b><i>Гора — это его трон. Ты только что вошёл во дворец.</i></b>",
    "ash_lands_lord":   "<b><i>Пепельные земли помнят тех, кто приходил. Долго. Очень долго.</i></b>",
    "ice_sovereign":    "<b><i>Лёд не тает. Он ждёт. Терпеливее, чем ты думаешь.</i></b>",
    "dark_viceroy":     "<b><i>Он уже знает о тебе всё. Ты о нём — почти ничего.</i></b>",
    "ruin_overlord":    "<b><i>Каждая цивилизация строила. Он разрушал. Счёт не в пользу цивилизаций.</i></b>",
    "depths_master":    "<b><i>Глубины не молчат. Это он молчит. Пока.</i></b>",
    "mountain_lord":    "<b><i>Ты думал, что идёшь в гору. Ты идёшь к нему.</i></b>",
    "cursed_monarch":   "<b><i>Проклятие убивает слабых. Его оно только злит.</i></b>",
    "void_king":        "<b><i>Пустота — это не ничто. Это его королевство. Добро пожаловать.</i></b>",
    "last_keeper":      "<b><i>Он пережил всех. Каждого. Он переживёт и тебя — если не постараешься.</i></b>",
}

# Запасные цитаты если босс/меч не найден в словаре
_SHOP_QUOTES_EN = [
    "<b><i>Every blade here is a story. Not all of them ended well.</i></b>",
    "<b><i>Weapons don't kill. Hands do. But a good weapon helps a great deal.</i></b>",
    "<b><i>They say the best sword is the one not yet tested in battle. Liars.</i></b>",
    "<b><i>Bosses don't fear you. Yet. Get the right blade — then we'll see.</i></b>",
    "<b><i>Iron remembers strikes. The best blades remember victories.</i></b>",
    "<b><i>The price of a sword is nothing compared to the price of defeat.</i></b>",
    "<b><i>A miner without a sword is just a miner. A miner with a sword is a hunter.</i></b>",
    "<b><i>Choose your weapon with your heart. But let your wallet think too.</i></b>",
    "<b><i>Some bosses have seen a thousand blades. They will remember yours.</i></b>",
    "<b><i>A good sword is not a purchase. It is an investment in someone else's end.</i></b>",
]

_HUNT_QUOTES_EN = [
    "<b><i>Every boss is a wall. Every strike is a crack in it.</i></b>",
    "<b><i>They don't die on their own. Someone has to help them. That someone is you.</i></b>",
    "<b><i>The hunt is not cruelty. It is economics.</i></b>",
    "<b><i>The boss is waiting. He is patient. But not eternal.</i></b>",
    "<b><i>Five million coins for one death. Not a bad deal.</i></b>",
    "<b><i>The depths are full of monsters. Good thing you have a sword.</i></b>",
    "<b><i>They say bosses can sense a hunter's fear. Don't give them that pleasure.</i></b>",
    "<b><i>Every strike brings you closer to the reward. Don't stop.</i></b>",
    "<b><i>The mine is not just ore. Sometimes it is blood too.</i></b>",
    "<b><i>Legendary hunters started with an iron blade. You have already begun.</i></b>",
]

_SHOP_QUOTES = [
    "<b><i>Каждый клинок здесь — это история. Не все из них хорошо закончились.</i></b>",
    "<b><i>Оружие не убивает. Убивают руки. Но хорошее оружие очень помогает.</i></b>",
    "<b><i>Говорят, лучший меч тот, который ещё не пробовали на деле. Лжецы.</i></b>",
    "<b><i>Боссы не боятся тебя. Пока. Купи правильный клинок — и посмотрим.</i></b>",
    "<b><i>Железо помнит удары. Лучшие клинки помнят победы.</i></b>",
    "<b><i>Цена меча — ничто по сравнению с ценой поражения.</i></b>",
    "<b><i>Шахтёр без меча — просто шахтёр. Шахтёр с мечом — охотник.</i></b>",
    "<b><i>Выбирай оружие сердцем. Но кошельком тоже думай.</i></b>",
    "<b><i>Некоторые боссы видели тысячи клинков. Твой они запомнят.</i></b>",
    "<b><i>Хороший меч — это не покупка. Это инвестиция в чужую гибель.</i></b>",
]

_HUNT_QUOTES = [
    "<b><i>Каждый босс — это стена. Каждый удар — трещина в ней.</i></b>",
    "<b><i>Они не умирают сами. Кто-то должен им помочь. Этот кто-то — ты.</i></b>",
    "<b><i>Охота — это не жестокость. Это экономика.</i></b>",
    "<b><i>Босс ждёт. Он терпеливый. Но не вечный.</i></b>",
    "<b><i>Пять миллионов монет за одну смерть. Неплохая ставка.</i></b>",
    "<b><i>Глубины полны чудовищ. Хорошо, что у тебя есть меч.</i></b>",
    "<b><i>Говорят, боссы чувствуют страх охотника. Не давай им эту радость.</i></b>",
    "<b><i>Каждый удар приближает награду. Не останавливайся.</i></b>",
    "<b><i>Шахта — это не только руда. Иногда это ещё и кровь.</i></b>",
    "<b><i>Легендарные охотники начинали с железного клинка. Ты уже начал.</i></b>",
]

# ─────────────────────────────────────────
#  БОССЫ
# ─────────────────────────────────────────
BOSS_MAX_HP       = 10_000_000
BOSS_RESPAWN_SEC  = 30 * 60    # 30 минут после смерти — следующий босс в слоте
ACTIVE_BOSS_SLOTS = 5          # одновременно активных боссов

# Блокировки на слот (защита от гонок при параллельных ударах/спавнах
# в рамках одного процесса; на уровне БД та же атаку дополнительно
# защищает транзакция BEGIN IMMEDIATE в _atomic_slot_update).
_SLOT_LOCKS_GUARD = threading.Lock()
_SLOT_LOCKS: dict[int, threading.Lock] = {}

def _get_slot_lock(slot: int) -> threading.Lock:
    with _SLOT_LOCKS_GUARD:
        lock = _SLOT_LOCKS.get(slot)
        if lock is None:
            lock = threading.Lock()
            _SLOT_LOCKS[slot] = lock
        return lock

# HP следующего босса в зависимости от скорости убийства предыдущего
BOSS_HP_FAST   = 150_000_000  # убит за <= 5 минут
BOSS_HP_MEDIUM =  50_000_000  # убит за 5-30 минут
BOSS_HP_SLOW   =  10_000_000  # убит за > 30 минут (обычный)

# Опыт за участие в убийстве
BOSS_XP_KILLER           = 25_000
BOSS_XP_PARTICIPANT_MAX  =  5_000
BOSS_XP_PARTICIPANT_MIN  =    100

def _reward_for_hp(max_hp: int) -> int:
    """Полная награда пула за босса (делится пропорционально урону)."""
    if max_hp >= 100_000_000:
        return 25_000_000
    if max_hp >= 50_000_000:
        return 15_000_000
    return 5_000_000

BOSS_KILL_REWARD = 5_000_000   # дефолт для отображения в UI

# ─────────────────────────────────────────
#  МЕХАНИКИ БОССА: ЗАГЛУШКА И ПОДАВЛЕНИЕ
# ─────────────────────────────────────────
# Заглушка (stun): каждый раз, когда босс теряет ещё STUN_HP_LOSS_STEP
# (30%) своего максимального HP (считая от точки последнего срабатывания),
# он "оглушает" STUN_TARGET_SHARE (50%) игроков, ударивших его не позже
# STUN_ATTACK_WINDOW_SEC (8) секунд назад. Оглушённые не могут атаковать
# босса STUN_DURATION_MIN..STUN_DURATION_MAX (60-180) секунд.
STUN_HP_LOSS_STEP        = 0.30
STUN_ATTACK_WINDOW_SEC   = 8
STUN_TARGET_SHARE        = 0.50
STUN_DURATION_MIN        = 60
STUN_DURATION_MAX        = 180

# Подавление (suppression): как только HP босса падает ниже
# SUPPRESSION_HP_THRESHOLD (50%), он активирует ауру подавления —
# каждый удар игрока, который бил босса не позже
# SUPPRESSION_ATTACK_WINDOW_SEC (60) секунд назад, получает случайное
# снижение урона в диапазоне SUPPRESSION_DMG_MIN..SUPPRESSION_DMG_MAX (20-50%).
SUPPRESSION_HP_THRESHOLD      = 0.50
SUPPRESSION_ATTACK_WINDOW_SEC = 60
SUPPRESSION_DMG_MIN           = 0.20
SUPPRESSION_DMG_MAX           = 0.50

def _fmt_stun_duration(secs: int) -> str:
    """Компактный формат для оставшегося времени оглушения: '2м 05с' / '48с'."""
    secs = max(0, int(secs))
    m, s = divmod(secs, 60)
    if m:
        return f"{m}м {s:02d}с"
    return f"{s}с"

BOSSES = [
    {
        "key": "ash_lord",
        "name": "Повелитель Пепла", "name_en": "Ash Lord",
        "desc": "Дух сожжённых шахт, принявший облик воина из пепла и дыма.",
        "desc_en": "The spirit of burned mines, taking the form of a warrior made of ash and smoke.",
        "lore": "Там, где он проходит, остаётся только пепел. Даже камень не выдерживает.",
        "lore_en": "Where he passes, only ash remains. Even stone cannot withstand it.",
    },
    {
        "key": "rift_lord",
        "name": "Владыка Разлома", "name_en": "Rift Lord",
        "desc": "Существо из межпространственного разлома. Его тело — чистая энергия.",
        "desc_en": "A creature from an inter-dimensional rift. Its body is pure energy.",
        "lore": "Разлом открылся сам. Он вышел первым. И закрыл его за собой.",
        "lore_en": "The rift opened on its own. He came out first. And closed it behind him.",
    },
    {
        "key": "ruin_warden",
        "name": "Страж Руин", "name_en": "Ruin Warden",
        "desc": "Хранитель забытых подземных городов. Не подпускает никого к тайнам глубин.",
        "desc_en": "Guardian of forgotten underground cities. Lets no one near the secrets of the depths.",
        "lore": "Руины помнят тех, кто пытался пройти. Страж помнит лучше.",
        "lore_en": "The ruins remember those who tried to pass. The warden remembers better.",
    },
    {
        "key": "storm_king",
        "name": "Король Бури", "name_en": "Storm King",
        "desc": "Повелитель подземных вихрей. Его гнев — это буря в замкнутом тоннеле.",
        "desc_en": "Lord of underground vortexes. His rage is a storm in a sealed tunnel.",
        "lore": "Шахтёры слышат его приближение за километр. Это их последний шанс бежать.",
        "lore_en": "Miners hear him coming from a kilometer away. That is their last chance to run.",
    },
    {
        "key": "wasteland_master",
        "name": "Хозяин Пустошей", "name_en": "Wasteland Master",
        "desc": "Владыка выжженных нижних ярусов. Там, где он живёт, нет ничего живого.",
        "desc_en": "Ruler of the scorched lower tiers. Where he dwells, nothing lives.",
        "lore": "Пустошь — не место. Это он сам. Везде, куда он приходит.",
        "lore_en": "The wasteland is not a place. It is him. Everywhere he goes.",
    },
    {
        "key": "volcano_lord",
        "name": "Лорд Вулкана", "name_en": "Volcano Lord",
        "desc": "Рождён в жерле подземного вулкана. Его кожа — застывшая лава.",
        "desc_en": "Born in the crater of an underground volcano. His skin is solidified lava.",
        "lore": "Он не атакует. Он просто горит. А всё вокруг — вместе с ним.",
        "lore_en": "He does not attack. He simply burns. And everything around him burns with him.",
    },
    {
        "key": "ice_overlord",
        "name": "Владыка Льдов", "name_en": "Ice Overlord",
        "desc": "Ледяной тиран из глубочайших пластов. Его взгляд останавливает кровь.",
        "desc_en": "An icy tyrant from the deepest layers. His gaze stops the blood cold.",
        "lore": "−80 градусов — это его комфортная температура. Для остальных — смерть.",
        "lore_en": "−80 degrees is his comfortable temperature. For everyone else — death.",
    },
    {
        "key": "abyss_titan",
        "name": "Титан Бездны", "name_en": "Abyss Titan",
        "desc": "Колосс, рождённый в самой глубокой точке известных шахт.",
        "desc_en": "A colossus born at the deepest known point of the mines.",
        "lore": "Бездна не пустая. Там живёт он. И ему там тесно.",
        "lore_en": "The abyss is not empty. He lives there. And it feels cramped.",
    },
    {
        "key": "chasm_keeper",
        "name": "Хранитель Пропасти", "name_en": "Chasm Keeper",
        "desc": "Страж бесконечного провала. Никто не знает, что там внизу. Он не пускает узнать.",
        "desc_en": "Guardian of the endless chasm. No one knows what is down there. He makes sure it stays that way.",
        "lore": "Тысячи пытались заглянуть в пропасть. Хранитель помог им — столкнул.",
        "lore_en": "Thousands tried to peer into the chasm. The keeper helped them — by pushing them in.",
    },
    {
        "key": "storm_overlord",
        "name": "Повелитель Штормов", "name_en": "Storm Overlord",
        "desc": "Владыка электрических бурь в глубинах. Молния — его язык.",
        "desc_en": "Lord of electrical storms in the depths. Lightning is his language.",
        "lore": "Каждый удар молнии — слово. Он говорит быстро. Очень быстро.",
        "lore_en": "Every lightning strike is a word. He speaks fast. Very fast.",
    },
    {
        "key": "stone_monarch",
        "name": "Каменный Монарх", "name_en": "Stone Monarch",
        "desc": "Древнейший из каменных владык. Старше самой горы.",
        "desc_en": "The oldest of the stone rulers. Older than the mountain itself.",
        "lore": "Гора выросла вокруг него. Не наоборот. Это его трон.",
        "lore_en": "The mountain grew around him. Not the other way around. This is his throne.",
    },
    {
        "key": "ash_lands_lord",
        "name": "Владыка Пепельных Земель", "name_en": "Ash Lands Lord",
        "desc": "Правитель выжженных территорий нижнего яруса. Пепел — его армия.",
        "desc_en": "Ruler of the scorched territories of the lower tier. Ash is his army.",
        "lore": "Пепел не оседает там, где он стоит. Он держит его в воздухе. Как напоминание.",
        "lore_en": "Ash does not settle where he stands. He keeps it in the air. As a reminder.",
    },
    {
        "key": "ice_sovereign",
        "name": "Ледяной Властелин", "name_en": "Ice Sovereign",
        "desc": "Высший повелитель льда. Превращает тоннели в ледяные гробницы.",
        "desc_en": "The supreme lord of ice. Turns tunnels into frozen tombs.",
        "lore": "Его владения расширяются. Медленно. Неотвратимо. Как лёд.",
        "lore_en": "His domain expands. Slowly. Inevitably. Like ice.",
    },
    {
        "key": "dark_viceroy",
        "name": "Тёмный Наместник", "name_en": "Dark Viceroy",
        "desc": "Наместник тьмы в подземном царстве. Его глаза видят сквозь любую породу.",
        "desc_en": "The viceroy of darkness in the underground kingdom. His eyes see through any rock.",
        "lore": "Он знает о тебе всё. Давно. Просто ждал подходящего момента.",
        "lore_en": "He knows everything about you. Has for a while. He was simply waiting for the right moment.",
    },
    {
        "key": "ruin_overlord",
        "name": "Повелитель Руин", "name_en": "Ruin Overlord",
        "desc": "Владыка разрушенных цивилизаций под землёй. Руины — его дворец.",
        "desc_en": "Lord of destroyed underground civilizations. Ruins are his palace.",
        "lore": "Каждая цивилизация думала, что построит что-то вечное. Он доказал обратное.",
        "lore_en": "Every civilization thought it would build something eternal. He proved otherwise.",
    },
    {
        "key": "depths_master",
        "name": "Хозяин Глубин", "name_en": "Depths Master",
        "desc": "Властелин подземных морей и затопленных тоннелей.",
        "desc_en": "Master of underground seas and flooded tunnels.",
        "lore": "Глубины принадлежат ему. Каждая капля воды — его шпион.",
        "lore_en": "The depths belong to him. Every drop of water is his spy.",
    },
    {
        "key": "mountain_lord",
        "name": "Владыка Гор", "name_en": "Mountain Lord",
        "desc": "Дух самой горы, принявший форму великана. Гора и есть он.",
        "desc_en": "The spirit of the mountain itself, taking the form of a giant. The mountain is him.",
        "lore": "Ты думал, что копаешь в горе. На самом деле — в нём.",
        "lore_en": "You thought you were digging into the mountain. You were digging into him.",
    },
    {
        "key": "cursed_monarch",
        "name": "Проклятый Монарх", "name_en": "Cursed Monarch",
        "desc": "Король, которого прокляли собственные подданные. Проклятие сделало его сильнее.",
        "desc_en": "A king cursed by his own subjects. The curse made him stronger.",
        "lore": "Проклятие должно было убить его. Вместо этого — освободило.",
        "lore_en": "The curse was meant to kill him. Instead — it set him free.",
    },
    {
        "key": "void_king",
        "name": "Король Пустоты", "name_en": "Void King",
        "desc": "Абсолютный правитель пустого пространства между мирами.",
        "desc_en": "Absolute ruler of the empty space between worlds.",
        "lore": "Пустота — это не отсутствие чего-то. Это его присутствие.",
        "lore_en": "The void is not the absence of something. It is his presence.",
    },
    {
        "key": "last_keeper",
        "name": "Последний Хранитель", "name_en": "Last Keeper",
        "desc": "Последний из древних хранителей подземного мира. Остальные пали.",
        "desc_en": "The last of the ancient guardians of the underground world. The rest have fallen.",
        "lore": "Он пережил всех. Каждого. Он переживёт и тебя. Если не постараешься.",
        "lore_en": "He outlived everyone. Every single one. He will outlive you too. Unless you try.",
    },
    # ── Боссы 21–50 ──
    {
        "key": "iron_sentinel",
        "name": "Железный Страж", "name_en": "Iron Sentinel",
        "desc": "Живой голем из кованого железа. Охраняет врата нижних ярусов.",
        "desc_en": "A living golem of forged iron. Guards the gates of the lower tiers.",
        "lore": "Его не создавали. Шахта сделала его сама, за тысячу лет тишины.",
        "lore_en": "He was not made. The mine made him on its own, over a thousand years of silence.",
    },
    {
        "key": "bone_empress",
        "name": "Костяная Императрица", "name_en": "Bone Empress",
        "desc": "Правительница кладбища павших шахтёров. Её армия — те, кто не вернулся.",
        "desc_en": "Ruler of the graveyard of fallen miners. Her army — those who never returned.",
        "lore": "Она не убивает. Она просто ждёт. Рано или поздно каждый приходит к ней.",
        "lore_en": "She does not kill. She simply waits. Sooner or later, everyone comes to her.",
    },
    {
        "key": "magma_prophet",
        "name": "Пророк Магмы", "name_en": "Magma Prophet",
        "desc": "Провидец, рождённый в сердце подземного огня. Видит смерть каждого.",
        "desc_en": "A seer born in the heart of underground fire. Sees the death of everyone.",
        "lore": "Он знает, как ты умрёшь. Вопрос лишь в том — когда.",
        "lore_en": "He knows how you will die. The only question is — when.",
    },
    {
        "key": "crystal_tyrant",
        "name": "Кристальный Тиран", "name_en": "Crystal Tyrant",
        "desc": "Существо, целиком состоящее из смертоносных кристаллов глубин.",
        "desc_en": "A creature made entirely of lethal crystals from the depths.",
        "lore": "Каждый кристалл — чья-то застывшая душа. Их очень много.",
        "lore_en": "Every crystal is someone's frozen soul. There are very many of them.",
    },
    {
        "key": "plague_warden",
        "name": "Страж Чумы", "name_en": "Plague Warden",
        "desc": "Распространитель подземной заразы. Его присутствие губит всё живое.",
        "desc_en": "Spreader of underground plague. His presence destroys all living things.",
        "lore": "Шахтёры думали, что это болезнь шахты. Это был он. Всегда он.",
        "lore_en": "Miners thought it was the mine's disease. It was him. Always him.",
    },
    {
        "key": "twin_terror",
        "name": "Двойной Ужас", "name_en": "Twin Terror",
        "desc": "Двуглавое существо из древних глубин. Одна голова думает, другая атакует.",
        "desc_en": "A two-headed creature from the ancient depths. One head thinks, the other attacks.",
        "lore": "Они никогда не спорят. Потому что никогда не ошибаются.",
        "lore_en": "They never argue. Because they never make mistakes.",
    },
    {
        "key": "shadow_viceroy",
        "name": "Вице-король Теней", "name_en": "Shadow Viceroy",
        "desc": "Правитель теневого подкоролевства. Тень — его тело, тьма — его голос.",
        "desc_en": "Ruler of the shadow sub-kingdom. Shadow is his body, darkness is his voice.",
        "lore": "Ты никогда не видел его настоящего лица. Никто не видел. И не увидит.",
        "lore_en": "You have never seen his true face. No one has. And no one ever will.",
    },
    {
        "key": "quake_lord",
        "name": "Владыка Землетрясений", "name_en": "Quake Lord",
        "desc": "Повелитель сейсмических волн. Один удар его кулака — обвал тоннеля.",
        "desc_en": "Master of seismic waves. One punch of his fist — a tunnel collapse.",
        "lore": "Шахтёры боятся обвалов. Он — причина каждого из них.",
        "lore_en": "Miners fear cave-ins. He is the cause of every single one.",
    },
    {
        "key": "rust_king",
        "name": "Король Ржавчины", "name_en": "Rust King",
        "desc": "Существо, разъедающее металл одним прикосновением. Кошмар кузнецов.",
        "desc_en": "A creature that corrodes metal with a single touch. The nightmare of blacksmiths.",
        "lore": "Лучший меч против него уже стал ржавчиной. Надеюсь, ты принёс другой.",
        "lore_en": "The finest blade against him has already turned to rust. Hope you brought another.",
    },
    {
        "key": "ember_sovereign",
        "name": "Государь Угля", "name_en": "Ember Sovereign",
        "desc": "Вечно тлеющий владыка угольных пластов. Его тело — живой уголь.",
        "desc_en": "The eternally smoldering lord of coal seams. His body is living coal.",
        "lore": "Он не горит. Он тлеет. Века. И будет тлеть, пока есть уголь.",
        "lore_en": "He does not burn. He smolders. For centuries. And will smolder as long as coal exists.",
    },
    {
        "key": "acid_overlord",
        "name": "Повелитель Кислоты", "name_en": "Acid Overlord",
        "desc": "Хозяин подземных кислотных озёр. Его кровь растворяет камень.",
        "desc_en": "Master of underground acid lakes. His blood dissolves rock.",
        "lore": "Броня не поможет. Кислота найдёт любую щель. Всегда.",
        "lore_en": "Armor will not help. Acid finds every crack. Always.",
    },
    {
        "key": "grave_titan",
        "name": "Титан Могил", "name_en": "Grave Titan",
        "desc": "Древний великан, поднявшийся из самого глубокого захоронения глубин.",
        "desc_en": "An ancient giant risen from the deepest burial site in the depths.",
        "lore": "Его хоронили трижды. Трижды он выходил. На четвёртый — перестали пытаться.",
        "lore_en": "They buried him three times. Three times he came back. The fourth time — they stopped trying.",
    },
    {
        "key": "frost_reaper",
        "name": "Ледяной Жнец", "name_en": "Frost Reaper",
        "desc": "Вестник смерти из ледяных глубин. Его коса — замороженный воздух.",
        "desc_en": "A herald of death from the icy depths. His scythe — frozen air.",
        "lore": "Там, где он прошёл, остаётся иней. И больше ничего.",
        "lore_en": "Where he has passed, frost remains. And nothing else.",
    },
    {
        "key": "blood_archon",
        "name": "Архонт Крови", "name_en": "Blood Archon",
        "desc": "Древний владыка, питающийся кровью тех, кто осмеливается спуститься.",
        "desc_en": "An ancient ruler who feeds on the blood of those who dare descend.",
        "lore": "Он не злится. Он просто голоден. Всегда. Вечно.",
        "lore_en": "He is not angry. He is simply hungry. Always. Forever.",
    },
    {
        "key": "thunder_chancellor",
        "name": "Канцлер Грома", "name_en": "Thunder Chancellor",
        "desc": "Бюрократ бури, подписывающий смертные приговоры молниями.",
        "desc_en": "Bureaucrat of the storm, signing death sentences with lightning.",
        "lore": "Каждый гром — это его печать. Каждая молния — подпись.",
        "lore_en": "Every thunder is his seal. Every lightning bolt — his signature.",
    },
    {
        "key": "sand_devourer",
        "name": "Пожиратель Песка", "name_en": "Sand Devourer",
        "desc": "Существо из песчаных пустошей под землёй. Поглощает всё на своём пути.",
        "desc_en": "A creature from underground sandy wastes. It swallows everything in its path.",
        "lore": "Пустыня под землёй — его работа. Раньше здесь были леса.",
        "lore_en": "The underground desert is his doing. There were forests here once.",
    },
    {
        "key": "plague_monarch",
        "name": "Монарх Заразы", "name_en": "Plague Monarch",
        "desc": "Высший распространитель болезней глубин. Его корона — из кристаллов яда.",
        "desc_en": "Supreme spreader of diseases from the depths. His crown is made of poison crystals.",
        "lore": "Эпидемия 300-го яруса? Его работа. Он гордится.",
        "lore_en": "The epidemic on level 300? His doing. He is proud of it.",
    },
    {
        "key": "venom_sovereign",
        "name": "Суверен Яда", "name_en": "Venom Sovereign",
        "desc": "Повелитель ядовитых пауков и змей подземелья. Сам — живой яд.",
        "desc_en": "Ruler of the poisonous spiders and snakes of the underworld. Himself — living venom.",
        "lore": "Его укус — это не смерть. Это долгое прощание с жизнью.",
        "lore_en": "His bite is not death. It is a long farewell to life.",
    },
    {
        "key": "eclipse_king",
        "name": "Король Затмения", "name_en": "Eclipse King",
        "desc": "Тот, кто гасит свет в любом тоннеле. Абсолютная тьма — его оружие.",
        "desc_en": "The one who extinguishes light in any tunnel. Absolute darkness is his weapon.",
        "lore": "Фонари гаснут за секунду до его появления. Потом — тишина.",
        "lore_en": "Lanterns go out a second before he appears. Then — silence.",
    },
    {
        "key": "deep_herald",
        "name": "Глашатай Глубин", "name_en": "Deep Herald",
        "desc": "Посланник того, что живёт ниже любых известных ярусов.",
        "desc_en": "Messenger of whatever lives below any known tier.",
        "lore": "Он — только предупреждение. Страшно думать, кто идёт следом.",
        "lore_en": "He is only a warning. Terrifying to think who comes after him.",
    },
    {
        "key": "iron_colossus",
        "name": "Железный Колосс", "name_en": "Iron Colossus",
        "desc": "Гигант из сплавленного железа и горных пород. Ходячая гора.",
        "desc_en": "A giant of fused iron and rock. A walking mountain.",
        "lore": "Он не ходит. Он движется. Медленно. Неотвратимо. Как обвал.",
        "lore_en": "He does not walk. He moves. Slowly. Inevitably. Like a cave-in.",
    },
    {
        "key": "eternal_warden",
        "name": "Вечный Страж", "name_en": "Eternal Warden",
        "desc": "Тот, кто охраняет вход в шахту с самого начала времён.",
        "desc_en": "The one who has guarded the mine entrance since the beginning of time.",
        "lore": "Он видел первого шахтёра. И последнего. Ты — где-то посередине.",
        "lore_en": "He saw the first miner. And the last. You are somewhere in between.",
    },
    {
        "key": "cinder_baron",
        "name": "Барон Золы", "name_en": "Cinder Baron",
        "desc": "Правитель пепельных пустошей, где горели целые пласты угля.",
        "desc_en": "Ruler of the ash wastes where entire coal seams burned.",
        "lore": "Зола — его богатство. Каждый пожар — его налог с шахты.",
        "lore_en": "Ash is his wealth. Every fire — his tax from the mine.",
    },
    {
        "key": "rot_warlord",
        "name": "Военачальник Гнили", "name_en": "Rot Warlord",
        "desc": "Генерал армии разложения. Там, где он прошёл, гниёт даже камень.",
        "desc_en": "General of the army of decay. Where he has passed, even stone rots.",
        "lore": "Его армия не воюет. Она ждёт. Гниение — дело терпеливых.",
        "lore_en": "His army does not fight. It waits. Decay is a patient business.",
    },
    {
        "key": "rift_emperor",
        "name": "Император Разломов", "name_en": "Rift Emperor",
        "desc": "Высший повелитель пространственных трещин. Открывает разломы одним словом.",
        "desc_en": "Supreme lord of spatial cracks. Opens rifts with a single word.",
        "lore": "Его слово создаёт разлом. Второе слово — закрывает. Внутри — всё что было снаружи.",
        "lore_en": "His word creates a rift. The second word closes it. Inside — everything that was outside.",
    },
    {
        "key": "obsidian_lord",
        "name": "Владыка Обсидиана", "name_en": "Obsidian Lord",
        "desc": "Существо из застывшей лавы и обсидиана. Острее любого меча.",
        "desc_en": "A creature of solidified lava and obsidian. Sharper than any blade.",
        "lore": "Его тело — оружие. Каждый его шаг — удар.",
        "lore_en": "His body is a weapon. His every step — a strike.",
    },
    {
        "key": "nightmare_king",
        "name": "Король Кошмаров", "name_en": "Nightmare King",
        "desc": "Правитель сновидений шахтёров. Превращает страхи в реальных монстров.",
        "desc_en": "Ruler of miners' dreams. Turns fears into real monsters.",
        "lore": "Ты боишься? Он уже знает чего именно. И это уже идёт к тебе.",
        "lore_en": "You are afraid? He already knows of what exactly. And it is already coming.",
    },
    {
        "key": "titan_of_silence",
        "name": "Титан Тишины", "name_en": "Titan of Silence",
        "desc": "Тот, кто поглощает все звуки. В его присутствии абсолютная тишина.",
        "desc_en": "The one who absorbs all sound. In his presence — absolute silence.",
        "lore": "Ты не слышишь его шагов. Ты вообще ничего не слышишь. Это и есть он.",
        "lore_en": "You cannot hear his footsteps. You cannot hear anything at all. That is him.",
    },
    {
        "key": "ancient_dread",
        "name": "Древний Ужас", "name_en": "Ancient Dread",
        "desc": "Существо старше самих шахт. Оно было здесь до первого удара кирки.",
        "desc_en": "A creature older than the mines themselves. It was here before the first pickaxe strike.",
        "lore": "Шахты строили вокруг него. Шахтёры просто не знали об этом.",
        "lore_en": "The mines were built around it. Miners simply did not know.",
    },
    {
        "key": "prime_destroyer",
        "name": "Первичный Разрушитель", "name_en": "Prime Destroyer",
        "desc": "Воплощение разрушения. Существует только для того, чтобы уничтожать.",
        "desc_en": "The embodiment of destruction. Exists only to destroy.",
        "lore": "У него нет цели, нет мотива, нет ярости. Только разрушение. Чистое и окончательное.",
        "lore_en": "No goal, no motive, no rage. Only destruction. Pure and final.",
    },
    {
        "key": "abyss_emperor",
        "name": "Император Бездны", "name_en": "Abyss Emperor",
        "desc": "Абсолютный повелитель бездонных глубин. Никто не знает, где его трон.",
        "desc_en": "Absolute ruler of the bottomless depths. No one knows where his throne is.",
        "lore": "Бездна — это он. Он — это бездна. Граница стёрлась тысячу лет назад.",
        "lore_en": "The abyss is him. He is the abyss. The boundary was erased a thousand years ago.",
    },
]

BOSSES_BY_KEY = {b["key"]: b for b in BOSSES}

# ─────────────────────────────────────────
#  ХРАНИЛИЩЕ ГЛОБАЛЬНОГО СОСТОЯНИЯ БОССА
#  В отдельной таблице boss_state в SQLite
# ─────────────────────────────────────────

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_hunt_db():
    """Создаёт таблицы для охоты. Вызывать при старте."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS boss_slots (
                slot        INTEGER PRIMARY KEY,
                data_json   TEXT NOT NULL
            )
        """)
        conn.commit()
    _ensure_all_slots()


# ── Слот = отдельный босс ──
# Структура слота:
# {
#   "boss_key": str,
#   "boss_hp":  int,
#   "boss_max_hp": int,
#   "boss_alive": bool,
#   "boss_spawned": int,
#   "boss_died_at": int | None,
#   "boss_kill_duration": int | None,
#   "damage_log": {uid_str: total_dmg},   # кто сколько урона нанёс
#   "kill_duration": int | None,
# }

def _load_slot(slot: int) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT data_json FROM boss_slots WHERE slot=?", (slot,)
        ).fetchone()
    return json.loads(row["data_json"]) if row else {}


def _save_slot(slot: int, state: dict):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO boss_slots (slot, data_json) VALUES (?,?) "
            "ON CONFLICT(slot) DO UPDATE SET data_json=excluded.data_json",
            (slot, json.dumps(state, ensure_ascii=False))
        )
        conn.commit()


def _atomic_slot_update(slot: int, mutator):
    """
    Атомарно читает слот, передаёт его в mutator(state) -> (new_state, ret),
    сохраняет new_state и возвращает ret.

    Защита от гонок на двух уровнях:
      1) threading.Lock на слот — сериализует параллельные запросы
         внутри одного процесса бота.
      2) SQLite-транзакция BEGIN IMMEDIATE — берёт блокировку записи
         на уровне БД, защищая от гонок между процессами/воркерами.

    Без этого два одновременных удара по одному боссу могли читать
    одинаковый boss_hp "до" удара и затирать результат друг друга
    (потеря урона) либо оба фиксировать "boss_killed" и задвоить награду.
    """
    lock = _get_slot_lock(slot)
    with lock:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT data_json FROM boss_slots WHERE slot=?", (slot,)
            ).fetchone()
            state = json.loads(row["data_json"]) if row else {}

            new_state, ret = mutator(state)

            conn.execute(
                "INSERT INTO boss_slots (slot, data_json) VALUES (?,?) "
                "ON CONFLICT(slot) DO UPDATE SET data_json=excluded.data_json",
                (slot, json.dumps(new_state, ensure_ascii=False))
            )
            conn.commit()
            return ret
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _pick_random_boss(exclude_keys: list[str] = None) -> dict:
    """Выбирает случайного босса, не из исключённых (активные в других слотах)."""
    pool = [b for b in BOSSES if not exclude_keys or b["key"] not in exclude_keys]
    if not pool:
        pool = BOSSES  # крайний случай
    return random.choice(pool)


def _build_spawn_state(kill_duration: int = None, active_keys: list[str] = None) -> dict:
    """Строит новое состояние случайного босса (без сохранения в БД)."""
    if kill_duration is None:
        next_hp = BOSS_MAX_HP
    elif kill_duration <= 5 * 60:
        next_hp = BOSS_HP_FAST
    elif kill_duration <= 30 * 60:
        next_hp = BOSS_HP_MEDIUM
    else:
        next_hp = BOSS_HP_SLOW

    boss = _pick_random_boss(exclude_keys=active_keys or [])
    return {
        "boss_key":          boss["key"],
        "boss_hp":           next_hp,
        "boss_max_hp":       next_hp,
        "boss_alive":        True,
        "boss_spawned":      _now_ts(),
        "boss_died_at":      None,
        "boss_kill_duration": None,
        "damage_log":        {},
        # ── заглушка / подавление ──
        "hit_times":              {},     # uid_str -> ts последнего удара по этому боссу
        "stunned":                {},     # uid_str -> ts до которого игрок оглушён
        "last_stun_threshold_hp": next_hp,  # HP, от которого отсчитывается следующие -30%
        "suppression_active":     False,  # включена ли аура подавления (HP < 50%)
    }


def _spawn_slot(slot: int, kill_duration: int = None, active_keys: list[str] = None):
    """Спавнит нового случайного босса в слот."""
    state = _build_spawn_state(kill_duration=kill_duration, active_keys=active_keys)
    _save_slot(slot, state)
    return state


def revive_boss_with_potion(slot: int) -> tuple[bool, dict]:
    """
    Мгновенно возрождает босса в слоте, минуя таймер отката.
    Используется после успешной покупки «Зелья Возрождения» за звёзды.
    Возвращает (True, новое_состояние) если возрождение произошло,
    (False, текущее_состояние) если босс уже был жив.
    """
    def _mutator(state):
        if state.get("boss_alive"):
            return state, (False, state)
        active_keys = [
            st.get("boss_key")
            for s in range(ACTIVE_BOSS_SLOTS) if s != slot
            for st in [_load_slot(s)]
            if st.get("boss_alive")
        ]
        kill_dur = state.get("boss_kill_duration")
        new_state = _build_spawn_state(kill_duration=kill_dur, active_keys=active_keys)
        return new_state, (True, new_state)
    return _atomic_slot_update(slot, _mutator)


def _ensure_all_slots():
    """При старте инициализирует все 5 слотов если пусты."""
    used_keys = []
    for slot in range(ACTIVE_BOSS_SLOTS):
        st = _load_slot(slot)
        if st and st.get("boss_key") in BOSSES_BY_KEY:
            if st.get("boss_alive"):
                used_keys.append(st["boss_key"])
        else:
            st = _spawn_slot(slot, active_keys=used_keys)
            if st.get("boss_alive"):
                used_keys.append(st["boss_key"])


def get_all_slots() -> list[dict]:
    """Возвращает все 5 слотов, обновляя мёртвых боссов если прошло 30 минут."""
    now = _now_ts()
    slots = []
    active_keys = []

    # Первый проход — собираем живых
    raw = [_load_slot(s) for s in range(ACTIVE_BOSS_SLOTS)]
    for st in raw:
        if st.get("boss_alive") and st.get("boss_key") in BOSSES_BY_KEY:
            active_keys.append(st["boss_key"])

    result = []
    for slot, st in enumerate(raw):
        if not st or st.get("boss_key") not in BOSSES_BY_KEY:
            st = _spawn_slot(slot, active_keys=active_keys)
            if st.get("boss_alive"):
                active_keys.append(st["boss_key"])
        elif not st.get("boss_alive", True):
            died_at = st.get("boss_died_at", 0) or 0
            if now - died_at >= BOSS_RESPAWN_SEC:
                kill_dur = st.get("boss_kill_duration")
                st = _spawn_slot(slot, kill_duration=kill_dur, active_keys=active_keys)
                if st.get("boss_alive"):
                    active_keys.append(st["boss_key"])
        result.append((slot, st))
    return result


def get_slot(slot: int) -> tuple[int, dict]:
    """Возвращает один слот с авто-рефрешем."""
    all_slots = get_all_slots()
    for s, st in all_slots:
        if s == slot:
            return s, st
    return slot, _load_slot(slot)


# Для совместимости со старым кодом — возвращает первый живой слот
def get_boss_state() -> dict:
    slots = get_all_slots()
    for _, st in slots:
        if st.get("boss_alive"):
            return st
    # Все мертвы — вернуть первый
    return slots[0][1] if slots else {}


def _save_boss_state(state: dict):
    """Совместимость: сохраняет state в слот 0 (старый код)."""
    _save_slot(0, state)


def attack_boss(data: dict, slot: int = 0) -> dict:
    """
    Атака босса игроком в указанном слоте.
    data — словарь пользователя (должен содержать equipped_sword).
    Возвращает dict с ключами:
      hit, crit, dmg, boss_hp_before, boss_hp_after,
      boss_killed, reward, xp, damage_rewards, error
    damage_rewards — dict {uid: (coins, xp)} для всех участников при убийстве
    """
    result = {
        "hit": False, "crit": False, "dmg": 0,
        "boss_hp_before": 0, "boss_hp_after": 0,
        "boss_killed": False, "reward": 0, "xp": 0,
        "damage_rewards": {},
        "error": None,
        "slot": slot,
        "stunned_until": 0,
        "suppressed": False, "suppression_pct": 0.0,
        "suppression_triggered": False,
        "stun_triggered": False, "stunned_players": {},
    }

    now = _now_ts()
    last_hit = data.get("last_boss_hit", 0)
    if now - last_hit < 1:
        result["error"] = "cooldown"
        return result

    uid_str_check = str(data.get("id", 0))
    _peek_state = _load_slot(slot)
    _peek_until = (_peek_state.get("stunned", {}) or {}).get(uid_str_check, 0)
    if _peek_until > now:
        result["error"] = "stunned"
        result["stunned_until"] = _peek_until
        return result

    sword_key = data.get("equipped_sword")
    if not sword_key:
        result["error"] = "no_sword"
        return result

    sword = SWORDS_BY_KEY.get(sword_key)
    if not sword:
        result["error"] = "no_sword"
        return result

    # Фиксируем кулдаун сразу после валидации, до тяжёлых вычислений —
    # сужает окно гонки для параллельных запросов от одного игрока.
    data["last_boss_hit"] = now

    # Множители урона (не зависят от состояния босса — считаем их
    # до входа в блокировку слота, чтобы не держать lock дольше нужного)
    from datetime import datetime, timezone as _tz
    _now_check = datetime.now(_tz.utc).timestamp()
    _enh = data.get("active_enh_booster")
    enh_mult = (_enh["multiplier"] if _enh and _enh.get("ends_at", 0) > _now_check else 1.0)

    from shop import get_artifact_damage_multiplier
    art_dmg_mult = get_artifact_damage_multiplier(data)

    from status import get_status_multiplier as _status_dmg_mult, get_crit_chance_bonus as _status_crit_bonus
    status_dmg_mult = _status_dmg_mult(data)
    status_crit_add = _status_crit_bonus(data) / 100.0

    dmg = random.randint(sword["dmg_min"], sword["dmg_max"])
    crit = False
    if random.random() < sword["crit_chance"] + status_crit_add:
        dmg  = int(sword["dmg_max"] * sword["crit_mult"])
        crit = True
    dmg = max(0, int(dmg * enh_mult * art_dmg_mult * status_dmg_mult))

    is_infinite = bool(data.get("infinite_dmg"))
    uid_str = str(data.get("id", 0))

    def _mutator(state: dict):
        # Состояние перепроверяется уже ВНУТРИ блокировки/транзакции —
        # это защищает от гонок, когда между проверкой выше и этим
        # моментом другой запрос успел убить босса или респавнить слот.
        if not state or not state.get("boss_alive", False) or state.get("boss_key") not in BOSSES_BY_KEY:
            return state, {"error": "boss_dead"}

        # Финальная (авторитетная) проверка заглушки — уже под блокировкой,
        # чтобы исключить гонку между "проверил вне лока" и самим ударом.
        stunned_map = state.setdefault("stunned", {})
        stunned_until = stunned_map.get(uid_str, 0)
        if stunned_until > now:
            return state, {"error": "stunned", "stunned_until": stunned_until}

        max_hp = state.get("boss_max_hp", BOSS_MAX_HP)

        # Админ-режим "infinite_dmg": урон = текущий HP босса (мгновенный килл).
        # Считаем именно тут, под блокировкой, чтобы взять актуальный HP —
        # а не значение, прочитанное до захвата лока.
        hit_dmg  = state["boss_hp"] if is_infinite else dmg
        hit_crit = False if is_infinite else crit

        # ── Подавление: снижает урон тем, кто бил босса недавно ──
        suppressed = False
        suppression_pct = 0.0
        hit_times = state.setdefault("hit_times", {})
        if not is_infinite and state.get("suppression_active"):
            prev_hit_ts = hit_times.get(uid_str, 0)
            if now - prev_hit_ts <= SUPPRESSION_ATTACK_WINDOW_SEC:
                suppression_pct = random.uniform(SUPPRESSION_DMG_MIN, SUPPRESSION_DMG_MAX)
                hit_dmg = max(0, int(hit_dmg * (1 - suppression_pct)))
                suppressed = True

        hit_times[uid_str] = now
        # Чистим устаревшие метки атак, чтобы словарь не рос бесконечно
        stale_before = now - max(STUN_ATTACK_WINDOW_SEC, SUPPRESSION_ATTACK_WINDOW_SEC) * 4
        for u in list(hit_times.keys()):
            if hit_times[u] < stale_before:
                del hit_times[u]
        # Чистим истёкшие заглушки
        for u in list(stunned_map.keys()):
            if stunned_map[u] <= now:
                del stunned_map[u]

        hp_before = state["boss_hp"]
        hp_after  = max(0, hp_before - hit_dmg)
        state["boss_hp"] = hp_after

        damage_log = state.setdefault("damage_log", {})
        damage_log[uid_str] = damage_log.get(uid_str, 0) + hit_dmg

        out = {
            "hit": True, "crit": hit_crit, "dmg": hit_dmg,
            "boss_hp_before": hp_before, "boss_hp_after": hp_after,
            "boss_killed": False, "reward": 0, "xp": 0,
            "damage_rewards": {}, "error": None,
            "suppressed": suppressed, "suppression_pct": suppression_pct,
            "suppression_triggered": False,
            "stun_triggered": False, "stunned_players": {},
            "stunned_until": 0,
        }

        # ── Заглушка: срабатывает при потере очередных 30% HP ──
        if hp_after > 0:
            last_threshold = state.get("last_stun_threshold_hp", max_hp)
            loss_needed = max_hp * STUN_HP_LOSS_STEP
            if last_threshold - hp_after >= loss_needed:
                candidates = [
                    u for u, ts in hit_times.items()
                    if now - ts <= STUN_ATTACK_WINDOW_SEC
                ]
                target_count = max(1, round(len(candidates) * STUN_TARGET_SHARE))
                chosen = random.sample(candidates, min(target_count, len(candidates)))
                stunned_players = {}
                for u in chosen:
                    until = now + random.randint(STUN_DURATION_MIN, STUN_DURATION_MAX)
                    stunned_map[u] = until
                    stunned_players[u] = until
                state["last_stun_threshold_hp"] = hp_after
                out["stun_triggered"]   = True
                out["stunned_players"]  = stunned_players
                if uid_str in stunned_players:
                    out["stunned_until"] = stunned_players[uid_str]

        # ── Подавление: активируется, когда HP падает ниже 50% ──
        if hp_after > 0 and not state.get("suppression_active") and hp_after <= max_hp * SUPPRESSION_HP_THRESHOLD:
            state["suppression_active"] = True
            out["suppression_triggered"] = True

        if hp_after == 0:
            died_at = _now_ts()
            spawned_at = state.get("boss_spawned", died_at)
            kill_duration = died_at - spawned_at

            state["boss_alive"]         = False
            state["boss_died_at"]       = died_at
            state["boss_kill_duration"] = kill_duration
            out["boss_killed"]          = True

            # ── Пропорциональное распределение награды ──
            total_pool = _reward_for_hp(state.get("boss_max_hp", BOSS_MAX_HP))
            total_dmg  = sum(damage_log.values()) or 1
            killer_uid = uid_str

            damage_rewards = {}  # uid_str -> (coins, xp)
            for u_str, u_dmg in damage_log.items():
                share     = u_dmg / total_dmg
                coins     = int(total_pool * share)
                is_killer = (u_str == killer_uid)
                if is_killer:
                    xp = BOSS_XP_KILLER
                else:
                    xp = max(
                        BOSS_XP_PARTICIPANT_MIN,
                        int(BOSS_XP_PARTICIPANT_MAX * share)
                    )
                damage_rewards[u_str] = (coins, xp)

            out["damage_rewards"] = damage_rewards
            out["reward"]         = damage_rewards.get(uid_str, (0, 0))[0]
            out["xp"]             = damage_rewards.get(uid_str, (0, 0))[1]

        return state, out

    mutated = _atomic_slot_update(slot, _mutator)

    result.update({k: v for k, v in mutated.items() if k != "error"})

    if mutated.get("error"):
        result["error"] = mutated["error"]
        return result

    if result["boss_killed"]:
        # Начисляем убийце сразу (остальным — в main.py через damage_rewards)
        data["balance"] = data.get("balance", 0) + result["reward"]
        data["xp"]      = data.get("xp", 0) + result["xp"]

    return result


# ─────────────────────────────────────────
#  РАБОТА С МЕЧАМИ ПОЛЬЗОВАТЕЛЯ
# ─────────────────────────────────────────

def get_owned_swords(data: dict) -> list:
    return data.get("owned_swords", [])


def has_sword(data: dict, sword_key: str) -> bool:
    return sword_key in get_owned_swords(data)


def get_equipped_sword(data: dict) -> str | None:
    return data.get("equipped_sword")


def buy_sword(data: dict, sword_key: str, lang: str = "ru") -> tuple[bool, str]:
    sword = SWORDS_BY_KEY.get(sword_key)
    if not sword:
        return False, ("<b><i>❌ Sword not found.</i></b>" if lang == "en" else "<b><i>❌ Меч не найден.</i></b>")
    if has_sword(data, sword_key):
        return False, ("<b><i>❌ You already have this sword.</i></b>" if lang == "en" else "<b><i>❌ Этот меч уже у тебя есть.</i></b>")
    if data.get("balance", 0) < sword["price"]:
        need = sword["price"] - data.get("balance", 0)
        return False, (f'<b><i>❌ Not enough coins. Need {_fmt(need)} more {COIN}</i></b>' if lang == "en" else f'<b><i>❌ Недостаточно монет. Нужно ещё {_fmt(need)} {COIN}</i></b>')
    data["balance"] -= sword["price"]
    data.setdefault("owned_swords", []).append(sword_key)
    if not data.get("equipped_sword"):
        data["equipped_sword"] = sword_key
    return True, ("<b><i>✅ Sword purchased!</i></b>" if lang == "en" else "<b><i>✅ Меч куплен!</i></b>")


def equip_sword(data: dict, sword_key: str, lang: str = "ru") -> tuple[bool, str]:
    if not has_sword(data, sword_key):
        return False, ("<b><i>❌ This sword is not purchased.</i></b>" if lang == "en" else "<b><i>❌ Этот меч не куплен.</i></b>")
    if sword_is_rented_out(data, sword_key):
        return False, ("<b><i>❌ This sword is rented out — wait for it to return.</i></b>" if lang == "en" else "<b><i>❌ Этот меч сдан в аренду — дождись возврата.</i></b>")
    data["equipped_sword"] = sword_key
    return True, ("<b><i>✅ Sword equipped!</i></b>" if lang == "en" else "<b><i>✅ Меч экипирован!</i></b>")


# ─────────────────────────────────────────
#  ТЕКСТЫ
# ─────────────────────────────────────────


def hunt_main_text(data: dict, lang: str = "ru") -> str:
    owned = get_owned_swords(data)
    count = len(owned)
    eq_key = get_equipped_sword(data)
    sword = SWORDS_BY_KEY.get(eq_key) if eq_key else None
    eq_name = sword.get("name_en" if lang == "en" else "name", "—") if sword else "—"

    # Цитата: берём от текущего босса с его именем
    _state  = get_boss_state()
    _bkey   = _state.get('boss_key')
    _boss   = BOSSES_BY_KEY.get(_bkey)
    if lang == "en":
        _raw_quote = _BOSS_HUNT_QUOTES_EN.get(_bkey) or random.choice(_HUNT_QUOTES_EN)
    else:
        _raw_quote = _BOSS_HUNT_QUOTES.get(_bkey) or random.choice(_HUNT_QUOTES)
    if _boss:
        _boss_display_name = _boss.get("name_en", _boss["name"]) if lang == "en" else _boss["name"]
        _quote = f'<b><i>{_boss_display_name}:</i></b>\n{_raw_quote}'
    else:
        _quote = _raw_quote

    if lang == "en":
        header = (
            f'<blockquote>'
            f'{_tg(_E["hunt"], "💀")} <b><i>BOSS HUNT</i></b>\n'
            f'<b><i>Swords in arsenal: {count} / {len(SWORDS)}</i></b>\n\n'
            f'{_quote}'
            f'</blockquote>\n\n'
        )
    else:
        header = (
            f'<blockquote>'
            f'{_tg(_E["hunt"], "💀")} <b><i>ОХОТА НА БОССОВ</i></b>\n'
            f'<b><i>Мечей в арсенале: {count} / {len(SWORDS)}</i></b>\n\n'
            f'{_quote}'
            f'</blockquote>\n\n'
        )

    if eq_key and not sword:
        data["equipped_sword"] = None
        eq_key = None

    if sword:
        sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
        if lang == "en":
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["sword"], "⚔️")} <b><i>Active sword:</i></b> {_tg(sword["emoji_id"], "🗡")} <b><i>{sword_name}</i></b>\n'
                f'{_tg(_E["dmg"], "💥")} <b><i>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
                f'{_tg(_E["crit"], "⭐")} <b><i>Crit: 5% chance × 2.0 of max damage</i></b>'
                f'</blockquote>\n\n'
            )
        else:
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["sword"], "⚔️")} <b><i>Активный меч:</i></b> {_tg(sword["emoji_id"], "🗡")} <b><i>{sword_name}</i></b>\n'
                f'{_tg(_E["dmg"], "💥")} <b><i>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
                f'{_tg(_E["crit"], "⭐")} <b><i>Крит: 5% шанс × 2.0 от макс. урона</i></b>'
                f'</blockquote>\n\n'
            )
    else:
        if lang == "en":
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["lock"], "🔒")} <b><i>No active sword.</i></b>\n'
                f'<b><i>Buy a sword in the shop — and go into battle!</i></b>'
                f'</blockquote>\n\n'
            )
        else:
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["lock"], "🔒")} <b><i>Нет активного меча.</i></b>\n'
                f'<b><i>Купи меч в магазине — и иди в бой!</i></b>'
                f'</blockquote>\n\n'
            )

    return header + eq_block


def hunt_main_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="Attack Boss!" if lang == "en" else "Атаковать босса!",
        callback_data="hunt_boss_select",
        icon_custom_emoji_id=_E["skull"]
    ))
    builder.row(
        InlineKeyboardButton(
            text="My Swords" if lang == "en" else "Мои мечи",
            callback_data="hunt_my_swords",
            icon_custom_emoji_id=_E["my_swords"]
        ),
        InlineKeyboardButton(
            text="Armory" if lang == "en" else "Оружейная",
            callback_data="hunt_shop_swords",
            icon_custom_emoji_id=_E["shop"]
        )
    )
    builder.row(InlineKeyboardButton(
        text="Potions" if lang == "en" else "Зелья",
        callback_data="hunt_shop_potions",
        icon_custom_emoji_id=_E["potion"]
    ))
    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Магазин мечей ───

SHOP_PAGE_SIZE = 5  # мечей на одну страницу


def sword_shop_text(data: dict, page: int = 0, lang: str = "ru") -> str:
    total_pages = (len(SWORDS) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_swords = SWORDS[page * SHOP_PAGE_SIZE:(page + 1) * SHOP_PAGE_SIZE]

    owned_count = sum(1 for s in SWORDS if has_sword(data, s["key"]))

    quote_sword = random.choice(page_swords)
    if lang == "en":
        raw_quote = _SWORD_QUOTES_EN.get(quote_sword["key"], random.choice(_SHOP_QUOTES_EN))
        sword_name_display = quote_sword.get("name_en", quote_sword["name"])
    else:
        raw_quote = _SWORD_QUOTES.get(quote_sword["key"], random.choice(_SHOP_QUOTES))
        sword_name_display = quote_sword["name"]
    sword_emoji = _tg(quote_sword["emoji_id"], "🗡")
    quote = f'{sword_emoji} <b><i>{sword_name_display}:</i></b>\n{raw_quote}'

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["shop"], "🛒")} <b><i>ARMORY</i></b>\n'
            f'<b><i>Owned: {owned_count} / {len(SWORDS)}</i></b>  |  '
            f'<b><i>Page {page + 1} / {total_pages}</i></b>\n\n'
            f'{quote}'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["shop"], "🛒")} <b><i>ОРУЖЕЙНАЯ</i></b>\n'
        f'<b><i>Куплено: {owned_count} / {len(SWORDS)}</i></b>  |  '
        f'<b><i>Страница {page + 1} / {total_pages}</i></b>\n\n'
        f'{quote}'
        f'</blockquote>'
    )


def sword_shop_keyboard(data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    total_pages = (len(SWORDS) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    start = page * SHOP_PAGE_SIZE
    page_swords = SWORDS[start:start + SHOP_PAGE_SIZE]

    builder = InlineKeyboardBuilder()

    for sword in page_swords:
        owned = has_sword(data, sword["key"])
        equipped = get_equipped_sword(data) == sword["key"]
        sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
        if owned:
            builder.row(InlineKeyboardButton(
                text=sword_name,
                callback_data=f'sword_info_{sword["key"]}',
                icon_custom_emoji_id=sword["emoji_id"],
                style="primary" if equipped else "success"
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f'{sword_name} — {_fmt(sword["price"])}',
                callback_data=f'sword_info_{sword["key"]}',
                icon_custom_emoji_id=sword["emoji_id"]
            ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="Back" if lang == "en" else "Назад",
            callback_data=f'sword_shop_page_{page - 1}',
            icon_custom_emoji_id=_E["back_page"]
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next" if lang == "en" else "Вперёд",
            callback_data=f'sword_shop_page_{page + 1}',
            icon_custom_emoji_id=_E["forward"]
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(
        text="Hunt menu" if lang == "en" else "В меню охоты",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Магазин зелий ───

def potions_shop_text(lang: str = "ru") -> str:
    p = POTIONS[0]
    name   = p.get("name_en", p["name"]) if lang == "en" else p["name"]
    desc   = p.get("desc_en", p["desc"]) if lang == "en" else p["desc"]
    effect = p.get("effect_en", p["effect"]) if lang == "en" else p["effect"]
    star   = _tg(_E["star"], "⭐")
    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["potion"], "🧪")} <b><i>POTIONS</i></b>\n\n'
            f'{_tg(p["emoji_id"], "🧪")} <b><i>{name}</i></b>\n'
            f'{desc}\n\n'
            f'{effect}\n\n'
            f'<b><i>Price: {p["price_stars"]} {star}</i></b>'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["potion"], "🧪")} <b><i>ЗЕЛЬЯ</i></b>\n\n'
        f'{_tg(p["emoji_id"], "🧪")} <b><i>{name}</i></b>\n'
        f'{desc}\n\n'
        f'{effect}\n\n'
        f'<b><i>Цена: {p["price_stars"]} {star}</i></b>'
        f'</blockquote>'
    )


def potions_shop_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in POTIONS:
        name = p.get("name_en", p["name"]) if lang == "en" else p["name"]
        builder.row(InlineKeyboardButton(
            text=f'{name} — {p["price_stars"]} ⭐',
            callback_data=f'buy_potion_{p["key"]}',
            icon_custom_emoji_id="5262643974912355126",
            style="success"
        ))
    builder.row(InlineKeyboardButton(
        text="Hunt menu" if lang == "en" else "В меню охоты",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


def potion_invoice_params(potion_key: str, lang: str = "ru") -> dict | None:
    """
    Параметры для bot.send_invoice() (оплата через Telegram Stars, currency='XTR').
    Использовать в основном файле бота при нажатии на кнопку покупки зелья:

        params = potion_invoice_params(potion_key, lang)
        await bot.send_invoice(
            chat_id=..., title=params["title"], description=params["description"],
            payload=params["payload"], currency=params["currency"], prices=params["prices"],
        )
    """
    p = POTIONS_BY_KEY.get(potion_key)
    if not p:
        return None
    title = p.get("name_en", p["name"]) if lang == "en" else p["name"]
    raw_desc = p.get("effect_en", p["effect"]) if lang == "en" else p["effect"]
    plain_desc = re.sub(r'<[^>]+>', '', raw_desc)
    return {
        "title": title,
        "description": plain_desc,
        "payload": f'potion_{potion_key}',
        "currency": "XTR",
        "prices": [{"label": title, "amount": p["price_stars"]}],
    }


def confirm_potion_purchase(slot: int, potion_key: str, lang: str = "ru") -> tuple[bool, str]:
    """
    Вызывать после успешного платежа (successful_payment) за зелье.
    Применяет эффект зелья. Для 'revival' — мгновенно возрождает босса в слоте.
    """
    p = POTIONS_BY_KEY.get(potion_key)
    if not p:
        return False, ("<b><i>❌ Unknown potion.</i></b>" if lang == "en" else "<b><i>❌ Неизвестное зелье.</i></b>")

    if potion_key == "revival":
        ok, state = revive_boss_with_potion(slot)
        potion_emoji = _tg(p["emoji_id"], "🧪")
        if not ok:
            return False, (f'{potion_emoji} <b><i>❌ The boss is already alive — the potion was not needed.</i></b>'
                            if lang == "en" else
                            f'{potion_emoji} <b><i>❌ Босс уже жив — зелье не потребовалось.</i></b>')
        boss = BOSSES_BY_KEY.get(state.get("boss_key"))
        boss_name = (boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]) if boss else "?"
        if lang == "en":
            return True, (f'{potion_emoji} <b><i>Revival Potion used!</i></b>\n'
                          f'<b><i>The boss {boss_name} has risen again — go hunt!</i></b>')
        return True, (f'{potion_emoji} <b><i>Зелье возрождения применено!</i></b>\n'
                      f'<b><i>Босс {boss_name} восстал снова — иди в бой!</i></b>')

    return False, ("<b><i>❌ Unknown potion.</i></b>" if lang == "en" else "<b><i>❌ Неизвестное зелье.</i></b>")


def is_potion_cmd(text: str) -> bool:
    t = text.strip().lstrip("/").lower()
    return t in ("зелья", "зелье", "potions", "potion")


def sword_detail_text(data: dict, sword_key: str, lang: str = "ru") -> str:
    sword = SWORDS_BY_KEY.get(sword_key)
    if not sword:
        return "<b><i>❌ Sword not found.</i></b>" if lang == "en" else "<b><i>❌ Меч не найден.</i></b>"

    owned    = has_sword(data, sword_key)
    equipped = get_equipped_sword(data) == sword_key

    sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
    sword_desc = sword.get("desc_en", sword["desc"]) if lang == "en" else sword["desc"]

    status_parts = []
    if owned:
        status_parts.append(f'{_tg(_E["ok"], "✅")} <b><i>{"In arsenal" if lang == "en" else "Есть в арсенале"}</i></b>')
    else:
        status_parts.append(f'{_tg(_E["lock"], "🔒")} <b><i>{"Not purchased" if lang == "en" else "Не куплен"}</i></b>')
    if equipped:
        status_parts.append(f'{_tg(_E["fire"], "⚡")} <b><i>{"Equipped" if lang == "en" else "Экипирован"}</i></b>')

    status_line = "  |  ".join(status_parts)

    if lang == "en":
        sword_quote = _SWORD_QUOTES_EN.get(sword_key, "")
    else:
        sword_quote = _SWORD_QUOTES.get(sword_key, "")
    sword_quote_block = f'<blockquote>{sword_quote}</blockquote>\n\n' if sword_quote else ""

    sword_emoji = _tg(sword["emoji_id"], "🗡")

    if lang == "en":
        return (
            f'<blockquote>'
            f'{sword_emoji} <b><i>{sword_name}</i></b>\n'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{sword_desc}'
            f'</blockquote>\n\n'
            f'{sword_quote_block}'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b><i>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
            f'{_tg(_E["crit"], "⭐")} <b><i>Crit: 5% × ×{sword["crit_mult"]:.0f} — max {_fmt(int(sword["dmg_max"] * sword["crit_mult"]))}</i></b>\n'
            f'{_tg(_E["price"], "💲")} <b><i>Price: {_fmt(sword["price"])} {_tg(_E["coin"], "💰")}</i></b>\n\n'
            f'{status_line}'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{sword_emoji} <b><i>{sword_name}</i></b>\n'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{sword_desc}'
        f'</blockquote>\n\n'
        f'{sword_quote_block}'
        f'<blockquote>'
        f'{_tg(_E["dmg"], "💥")} <b><i>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
        f'{_tg(_E["crit"], "⭐")} <b><i>Крит: 5% × ×{sword["crit_mult"]:.0f} — макс. {_fmt(int(sword["dmg_max"] * sword["crit_mult"]))}</i></b>\n'
        f'{_tg(_E["price"], "💲")} <b><i>Цена: {_fmt(sword["price"])} {_tg(_E["coin"], "💰")}</i></b>\n\n'
        f'{status_line}'
        f'</blockquote>'
    )


def sword_detail_keyboard(data: dict, sword_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sword   = SWORDS_BY_KEY.get(sword_key)

    sword_index = next((i for i, s in enumerate(SWORDS) if s["key"] == sword_key), 0)
    back_page   = sword_index // SHOP_PAGE_SIZE

    if sword:
        owned    = has_sword(data, sword_key)
        equipped = get_equipped_sword(data) == sword_key

        if not owned:
            can_afford = data.get("balance", 0) >= sword["price"]
            builder.row(InlineKeyboardButton(
                text=f'{_fmt(sword["price"])}',
                callback_data=f'sword_buy_{sword_key}',
                icon_custom_emoji_id=_E["coin"],
                style="success" if can_afford else "danger"
            ))
        elif not equipped and not sword_is_rented_out(data, sword_key):
            sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
            builder.row(InlineKeyboardButton(
                text=f'{"Equip" if lang == "en" else "Экипировать"} {sword_name}',
                callback_data=f'sword_equip_{sword_key}',
                icon_custom_emoji_id=sword["emoji_id"]
            ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data=f'sword_shop_page_{back_page}',
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Мои мечи ───

def my_swords_text(data: dict, lang: str = "ru") -> str:
    owned   = get_owned_swords(data)
    eq_key  = get_equipped_sword(data)

    if not owned:
        if lang == "en":
            body = (
                f'{_tg(_E["lock"], "🔒")} <b><i>Arsenal is empty.</i></b>\n'
                f'<b><i>Check the armory — blades are waiting!</i></b>'
            )
        else:
            body = (
                f'{_tg(_E["lock"], "🔒")} <b><i>Арсенал пуст.</i></b>\n'
                f'<b><i>Загляни в магазин оружия — там ждут клинки!</i></b>'
            )
    else:
        lines = []
        for sk in owned:
            sw = SWORDS_BY_KEY.get(sk)
            if not sw:
                continue
            sw_name = sw.get("name_en", sw["name"]) if lang == "en" else sw["name"]
            eq_label = f' {_tg(_E["fire"], "⚡")} <b><i>{"[Eqp.]" if lang == "en" else "[Экип.]"}</i></b>' if sk == eq_key else ""
            sword_emoji = _tg(sw["emoji_id"], "🗡")
            dmg_label = "dmg" if lang == "en" else "урона"
            lines.append(
                f'{sword_emoji} <b><i>{sw_name}</i></b>{eq_label}\n'
                f'   {_tg(_E["dmg"], "💥")} <b><i>{_fmt(sw["dmg_min"])}–{_fmt(sw["dmg_max"])} {dmg_label}</i></b>'
            )
        body = "\n\n".join(lines)

    title = "MY SWORDS" if lang == "en" else "МОИ МЕЧИ"
    arsenal_label = "Arsenal" if lang == "en" else "Арсенал"
    return (
        f'<blockquote>'
        f'{_tg(_E["my_swords"], "⚔️")} <b><i>{title}</i></b>\n'
        f'<b><i>{arsenal_label}: {len(owned)} / {len(SWORDS)}</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def my_swords_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    owned   = get_owned_swords(data)
    eq_key  = get_equipped_sword(data)

    for sk in owned:
        sw = SWORDS_BY_KEY.get(sk)
        if not sw:
            continue
        sw_name = sw.get("name_en", sw["name"]) if lang == "en" else sw["name"]
        if sk != eq_key and not sword_is_rented_out(data, sk):
            builder.row(InlineKeyboardButton(
                text=f'{"Equip" if lang == "en" else "Экипировать"}: {sw_name}',
                callback_data=f'sword_equip_{sk}',
                icon_custom_emoji_id=sw["emoji_id"]
            ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Экран выбора босса ───

def boss_select_text(lang: str = "ru") -> str:
    slots = get_all_slots()
    now   = _now_ts()
    lines = []
    for slot_idx, st in slots:
        boss_key = st.get("boss_key")
        boss     = BOSSES_BY_KEY.get(boss_key)
        if st.get("boss_alive") and boss:
            bname = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
            lines.append(f'{_tg(_E["boss"], "🔥")} <b><i>#{slot_idx+1} {bname}</i></b>')
        else:
            died_at = st.get("boss_died_at", 0) or 0
            rem     = max(0, BOSS_RESPAWN_SEC - (now - died_at))
            m       = rem // 60
            if lang == "en":
                lines.append(f'{_tg(_E["dead"], "💀")} <b><i>#{slot_idx+1}</i></b> — next in {m}m')
            else:
                lines.append(f'{_tg(_E["dead"], "💀")} <b><i>#{slot_idx+1}</i></b> — след. через {m}м')

    body = "\n".join(lines)
    if lang == "en":
        return f'<blockquote>{_tg(_E["skull"], "💀")} <b><i>CHOOSE A BOSS</i></b>\n\n{body}\n</blockquote>'
    return f'<blockquote>{_tg(_E["skull"], "💀")} <b><i>ВЫБОР БОССА</i></b>\n\n{body}\n</blockquote>'


def boss_select_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    slots   = get_all_slots()

    for slot_idx, st in slots:
        boss_key = st.get("boss_key")
        boss     = BOSSES_BY_KEY.get(boss_key)
        alive    = st.get("boss_alive", False)
        if alive and boss:
            bname = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
            builder.row(InlineKeyboardButton(
                text=f" #{slot_idx+1} {bname}",
                callback_data=f"hunt_boss_{slot_idx}",
                icon_custom_emoji_id=_E["skull"]
            ))
        else:
            died_at = st.get("boss_died_at", 0) or 0
            rem     = max(0, BOSS_RESPAWN_SEC - (_now_ts() - died_at))
            m       = rem // 60
            label   = f" #{slot_idx+1} — {m}м" if lang == "ru" else f" #{slot_idx+1} — {m}m"
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data="hunt_boss_dead",
                icon_custom_emoji_id=_E["timer"]
            ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Экран атаки босса ───

def boss_attack_text(data: dict, lang: str = "ru", slot: int = 0) -> str:
    state    = _load_slot(slot)
    boss_key = state.get("boss_key")
    boss     = BOSSES_BY_KEY.get(boss_key)
    eq_key   = get_equipped_sword(data)
    sword    = SWORDS_BY_KEY.get(eq_key) if eq_key else None

    if not sword:
        if lang == "en":
            return (
                f'<blockquote>'
                f'{_tg(_E["lock"], "🔒")} <b><i>BOSS ATTACK</i></b>\n\n'
                f'<b><i>You have no sword.</i></b>\n'
                f'<b><i>Buy a weapon in the shop!</i></b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["lock"], "🔒")} <b><i>АТАКА БОССА</i></b>\n\n'
            f'<b><i>У тебя нет меча.</i></b>\n'
            f'<b><i>Купи оружие в магазине!</i></b>'
            f'</blockquote>'
        )

    if not state or not state.get("boss_alive"):
        died_at = (state.get("boss_died_at") or 0) if state else 0
        rem     = max(0, BOSS_RESPAWN_SEC - (_now_ts() - died_at))
        m       = rem // 60
        if lang == "en":
            return (
                f'<blockquote>'
                f'{_tg(_E["dead"], "💀")} <b><i>BOSS DEFEATED!</i></b>\n\n'
                f'{_tg(_E["timer"], "⏱")} <b><i>Next spawns in: {m}m</i></b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["dead"], "💀")} <b><i>БОСС ПОВЕРЖЕН!</i></b>\n\n'
            f'{_tg(_E["timer"], "⏱")} <b><i>Следующий появится через: {m}м</i></b>'
            f'</blockquote>'
        )

    if not boss:
        return "<b><i>❌ Boss not found.</i></b>" if lang == "en" else "<b><i>❌ Ошибка: босс не найден.</i></b>"

    # Мой урон по этому боссу
    damage_log = state.get("damage_log", {})
    my_dmg     = damage_log.get(str(data.get("id", 0)), 0)

    hp     = state["boss_hp"]
    max_hp = state.get("boss_max_hp", BOSS_MAX_HP)
    pct    = hp / max_hp * 100

    from datetime import datetime, timezone as _tz
    _now_check = datetime.now(_tz.utc).timestamp()
    _enh = data.get("active_enh_booster")
    if _enh and _enh.get("ends_at", 0) > _now_check:
        _rem = int(_enh["ends_at"] - _now_check)
        _h, _rem2 = divmod(_rem, 3600)
        _m, _s    = divmod(_rem2, 60)
        if lang == "en":
            _left = f"{_h}h {_m:02d}m" if _h else (f"{_m}m {_s:02d}s" if _m else f"{_s}s")
        else:
            _left = f"{_h}ч {_m:02d}м" if _h else (f"{_m}м {_s:02d}с" if _m else f"{_s}с")
        _mult = _enh["multiplier"]
        _ms   = str(_mult).rstrip("0").rstrip(".")
        if lang == "en":
            enh_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["fire"], "⚡")} <b><i>Damage booster: ×{_ms} active</i></b>\n'
                f'{_tg(_E["timer"], "⏱")} <b><i>Time left: {_left}</i></b>'
                f'</blockquote>'
            )
        else:
            enh_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["fire"], "⚡")} <b><i>Усилитель урона: ×{_ms} активен</i></b>\n'
                f'{_tg(_E["timer"], "⏱")} <b><i>Осталось: {_left}</i></b>'
                f'</blockquote>'
            )
    else:
        enh_line = ""

    try:
        from shop import get_artifact_damage_multiplier
        _art_dmg = get_artifact_damage_multiplier(data)
    except Exception:
        _art_dmg = 1.0
    if _art_dmg > 1.0:
        _art_dmg_str = f"{_art_dmg:.2f}".rstrip("0").rstrip(".")
        if lang == "en":
            art_dmg_line = (
                f'\n\n<blockquote>'
                f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b><i>Damage artifact: ×{_art_dmg_str}</i></b>'
                f'</blockquote>'
            )
        else:
            art_dmg_line = (
                f'\n\n<blockquote>'
                f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b><i>Артефакт урона: ×{_art_dmg_str}</i></b>'
                f'</blockquote>'
            )
    else:
        art_dmg_line = ""

    now_ts = _now_ts()
    stunned_until = (state.get("stunned", {}) or {}).get(str(data.get("id", 0)), 0)
    if stunned_until > now_ts:
        left = _fmt_stun_duration(stunned_until - now_ts)
        if lang == "en":
            status_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["lock"], "🔇")} <b><i>You are silenced!</i></b>\n'
                f'<b><i>The boss stunned you — you cannot attack for {left}.</i></b>'
                f'</blockquote>'
            )
        else:
            status_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["lock"], "🔇")} <b><i>Ты оглушён!</i></b>\n'
                f'<b><i>Босс заглушил тебя — атака недоступна ещё {left}.</i></b>'
                f'</blockquote>'
            )
    elif state.get("suppression_active"):
        if lang == "en":
            status_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["alert"], "🌀")} <b><i>Suppression aura active!</i></b>\n'
                f'<b><i>Hitting the boss again within {SUPPRESSION_ATTACK_WINDOW_SEC}s of your last strike weakens your damage by 20–50%.</i></b>'
                f'</blockquote>'
            )
        else:
            status_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["alert"], "🌀")} <b><i>Аура подавления активна!</i></b>\n'
                f'<b><i>Удар раньше чем через {SUPPRESSION_ATTACK_WINDOW_SEC}с после предыдущего снижает твой урон на 20–50%.</i></b>'
                f'</blockquote>'
            )
    else:
        status_line = ""

    boss_name  = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
    boss_lore  = boss.get("lore_en", boss["lore"]) if lang == "en" else boss["lore"]
    sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b><i>{boss_name}</i></b>\n'
            f'<b><i>{boss_lore}</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["hp"], "❤️")} <b><i>HP:</i></b> {_fmt_digits(hp)} / {_fmt_digits(max_hp)} <b><i>({pct:.1f}%)</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["sword"], "⚔️")} <b><i>Your sword: {_tg(sword["emoji_id"], "🗡")} {sword_name}</i></b>\n'
            f'{_tg(_E["dmg"], "💥")} <b><i>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
            f'{_tg(_E["crit"], "⭐")} <b><i>Crit: 5% × {sword["crit_mult"]:.0f} of max damage</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["trophy"], "🏆")} <b><i>Kill reward: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</i></b>'
            f'</blockquote>'
            f'{enh_line}'
            f'{art_dmg_line}'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["skull"], "💀")} <b><i>{boss_name}</i></b>\n'
        f'<b><i>{boss_lore}</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["hp"], "❤️")} <b><i>HP:</i></b> {_fmt_digits(hp)} / {_fmt_digits(max_hp)} <b><i>({pct:.1f}%)</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["sword"], "⚔️")} <b><i>Твой меч: {_tg(sword["emoji_id"], "🗡")} {sword_name}</i></b>\n'
        f'{_tg(_E["dmg"], "💥")} <b><i>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</i></b>\n'
        f'{_tg(_E["crit"], "⭐")} <b><i>Крит: 5% × {sword["crit_mult"]:.0f} от макс. урона</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["trophy"], "🏆")} <b><i>Награда за убийство: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</i></b>'
        f'</blockquote>'
        f'{enh_line}'
        f'{art_dmg_line}'
    )


def boss_attack_keyboard(data: dict, lang: str = "ru", slot: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    state   = _load_slot(slot)
    eq_key  = get_equipped_sword(data)

    if state.get("boss_alive") and eq_key:
        builder.row(InlineKeyboardButton(
            text="Strike!" if lang == "en" else "Ударить!",
            callback_data=f"hunt_strike_{slot}",
            icon_custom_emoji_id=_E["sword"]
        ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt_boss_select",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


def boss_strike_result_text(data: dict, result: dict, lang: str = "ru", slot: int = 0) -> str:
    """Текст после удара по боссу."""
    state    = _load_slot(result.get("slot", slot))
    boss_key = state.get("boss_key")
    boss     = BOSSES_BY_KEY.get(boss_key)

    if result.get("error") == "no_sword":
        return (
            f'{_tg(_E["lock"], "🔒")} <b><i>{"No sword — nothing to attack with!" if lang == "en" else "Нет меча — нечем атаковать!"}</i></b>'
        )

    if result.get("error") == "boss_dead":
        return (
            f'{_tg(_E["dead"], "💀")} <b><i>{"Boss is already dead! Wait for the next one." if lang == "en" else "Босс уже мёртв! Жди следующего."}</i></b>'
        )

    dmg       = result["dmg"]
    crit      = result["crit"]
    hp_after  = result["boss_hp_after"]
    killed    = result["boss_killed"]
    max_hp    = state.get("boss_max_hp", BOSS_MAX_HP)
    pct       = hp_after / max_hp * 100

    if lang == "en":
        crit_line = (
            f'\n{_tg(_E["crit"], "⭐")} <b><i>CRITICAL HIT!</i></b>'
            if crit else ""
        )
    else:
        crit_line = (
            f'\n{_tg(_E["crit"], "⭐")} <b><i>КРИТИЧЕСКИЙ УДАР!</i></b>'
            if crit else ""
        )

    if killed:
        reward = result["reward"]
        boss_name = boss.get("name_en", boss["name"]) if (lang == "en" and boss) else (boss["name"] if boss else ("Boss" if lang == "en" else "Босс"))
        if lang == "en":
            return (
                f'<blockquote>'
                f'{_tg(_E["skull"], "💀")} <b><i>BOSS DESTROYED!</i></b>\n\n'
                f'<b><i>{boss_name} has been defeated!</i></b>'
                f'</blockquote>\n\n'
                f'<blockquote>'
                f'{_tg(_E["dmg"], "💥")} <b><i>Final strike: {_fmt(dmg)}</i></b>{crit_line}\n'
                f'{_tg(_E["reward_coin"], "💰")} <b><i>Reward: +{_fmt(reward)} {_tg(_E["reward_coin"], "💰")}</i></b>'
                f'</blockquote>\n\n'
                f'<blockquote>'
                f'{_tg(_E["timer"], "⏱")} <b><i>Next boss appears in 2 hours.</i></b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b><i>БОСС УНИЧТОЖЕН!</i></b>\n\n'
            f'<b><i>{boss_name} повержен!</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b><i>Последний удар: {_fmt(dmg)}</i></b>{crit_line}\n'
            f'{_tg(_E["reward_coin"], "💰")} <b><i>Награда: +{_fmt(reward)} {_tg(_E["reward_coin"], "💰")}</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["timer"], "⏱")} <b><i>Следующий босс появится через 2 часа.</i></b>'
            f'</blockquote>'
        )

    boss_name = boss.get("name_en", boss["name"]) if (lang == "en" and boss) else (boss["name"] if boss else ("Boss" if lang == "en" else "Босс"))

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b><i>{boss_name}</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b><i>Your strike: {_fmt(dmg)}</i></b> {_tg(_E["dmg"], "💥")}{crit_line}'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["hp"], "❤️")} <b><i>HP:</i></b> {_fmt_digits(hp_after)} / {_fmt_digits(max_hp)} <b><i>({pct:.1f}%)</i></b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["trophy"], "🏆")} <b><i>Kill reward: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</i></b>'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["skull"], "💀")} <b><i>{boss_name}</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["dmg"], "💥")} <b><i>Твой удар: {_fmt(dmg)}</i></b> {_tg(_E["dmg"], "💥")}{crit_line}'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["hp"], "❤️")} <b><i>HP:</i></b> {_fmt_digits(hp_after)} / {_fmt_digits(max_hp)} <b><i>({pct:.1f}%)</i></b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["trophy"], "🏆")} <b><i>Награда за убийство: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</i></b>'
        f'</blockquote>'
    )


def boss_strike_keyboard(data: dict, lang: str = "ru", slot: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура после удара — даём ударить ещё раз или назад."""
    builder = InlineKeyboardBuilder()
    state   = _load_slot(slot)
    eq_key  = get_equipped_sword(data)

    if state.get("boss_alive") and eq_key:
        builder.row(InlineKeyboardButton(
            text="Strike again!" if lang == "en" else "Ударить ещё!",
            callback_data=f"hunt_strike_{slot}",
            icon_custom_emoji_id=_E["sword"]
        ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt_boss_select",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  АРСЕНАЛ — передача, подарок, аренда мечей
# ════════════════════════════════════════════════════════════

import time as _time_mod

# ─── Вспомогательные функции аренды ───

def get_rented_out(data: dict) -> dict:
    """Мечи, которые ты СДАЛ в аренду. {sword_key: {uid, until, name}}"""
    return data.get("arsenal_rented_out", {})

def get_rented_in(data: dict) -> dict:
    """Мечи, которые ты ВЗЯЛ в аренду. {sword_key: {from_uid, until, from_name}}"""
    return data.get("arsenal_rented_in", {})

def get_transferred(data: dict) -> dict:
    """Мечи, переданные тебе кем-то. {sword_key: from_name} — просто информация."""
    return data.get("arsenal_transferred_from", {})

def sword_is_rented_out(data: dict, sword_key: str) -> bool:
    """Этот меч сейчас сдан в аренду (и срок ещё не истёк)."""
    entry = get_rented_out(data).get(sword_key)
    if not entry:
        return False
    return entry["until"] > int(_time_mod.time())

def sword_is_rented_in(data: dict, sword_key: str) -> bool:
    """Этот меч взят в аренду у кого-то."""
    entry = get_rented_in(data).get(sword_key)
    if not entry:
        return False
    return entry["until"] > int(_time_mod.time())

def cleanup_expired_rentals(data: dict):
    """Убирает истёкшие аренды из user_data. Вызывать при открытии арсенала."""
    now = int(_time_mod.time())
    rented_out = data.get("arsenal_rented_out", {})
    rented_in  = data.get("arsenal_rented_in", {})
    expired_out = [k for k, v in rented_out.items() if v["until"] <= now]
    expired_in  = [k for k, v in rented_in.items()  if v["until"] <= now]
    for k in expired_out:
        del rented_out[k]
    for k in expired_in:
        # Меч возвращается — убрать из owned_swords если он был добавлен временно
        owned = data.get("owned_swords", [])
        if k in owned and k not in [s for s in data.get("owned_swords_original", [])]:
            owned.remove(k)
        # Если игрок экипировал арендованный меч — сбросить экипировку
        if data.get("equipped_sword") == k:
            remaining = [s for s in data.get("owned_swords", []) if s != k and not sword_is_rented_in(data, s)]
            data["equipped_sword"] = remaining[0] if remaining else None
        del rented_in[k]

def parse_duration(text: str) -> int | None:
    """
    Парсит строку длительности: '5м', '30м', '2ч', '24ч', '1д', '2д'.
    Возвращает секунды или None если не распознано.
    Минимум 5 минут, максимум 48 часов.
    """
    text = text.strip().lower()
    import re as _re
    m = _re.match(r'^(\d+)\s*(м|мин|ч|час|д|день|дней|h|m|d)$', text)
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2)
    if unit in ('м', 'мин', 'm'):
        secs = val * 60
    elif unit in ('ч', 'час', 'h'):
        secs = val * 3600
    elif unit in ('д', 'день', 'дней', 'd'):
        secs = val * 86400
    else:
        return None
    if secs < 5 * 60:
        return None      # меньше 5 минут
    if secs > 48 * 3600:
        return None      # больше 48 часов
    return secs

def _fmt_duration(secs: int) -> str:
    """Красиво форматирует длительность: '2ч 30м', '45м' и т.д."""
    secs = max(0, int(secs))
    h, rem = divmod(secs, 3600)
    m = rem // 60
    if h and m:
        return f"{h}ч {m}м"
    elif h:
        return f"{h}ч"
    else:
        return f"{m}м"

def _fmt_until(until_ts: int) -> str:
    """Сколько времени осталось до истечения аренды."""
    left = until_ts - int(_time_mod.time())
    if left <= 0:
        return "истекла"
    return _fmt_duration(left)


# ─── Арсенал: главный экран ───

def arsenal_main_text(data: dict) -> str:
    cleanup_expired_rentals(data)
    owned     = get_owned_swords(data)
    eq_key    = get_equipped_sword(data)
    rented_in = get_rented_in(data)

    title_line = (
        f'{_tg(_E["my_swords"], "⚔️")} <b><i>АРСЕНАЛ</i></b>\n'
        f'━━━━━━━━━━━━━━━━━━━━'
    )

    if not owned and not rented_in:
        return (
            f'{title_line}\n\n'
            f'<blockquote>'
            f'{_tg(_E["lock"], "🔒")} <b><i>Арсенал пуст.</i></b>\n'
            f'Загляни в магазин оружия — там ждут клинки!'
            f'</blockquote>'
        )

    lines = []
    idx = 1
    for sk in owned:
        sw = SWORDS_BY_KEY.get(sk)
        if not sw:
            continue
        # Арендованные у других отображаются отдельно ниже
        if sword_is_rented_in(data, sk):
            continue
        sword_emoji = _tg(sw["emoji_id"], "🗡")
        eq_mark = f' {_tg(_E["fire"], "⚡")}' if sk == eq_key else ""
        rented_mark = ""
        if sword_is_rented_out(data, sk):
            entry = get_rented_out(data)[sk]
            rented_mark = f'\n   {_tg(_E["timer"], "⏱")} <b><i>В аренде у <b><i>{entry["name"]}</i></b> — ещё {_fmt_until(entry["until"])}</i></b>'
        lines.append(
            f'<b><i>#{idx}</i></b> {sword_emoji} <b><i>{sw["name"]}</i></b>{eq_mark}{rented_mark}\n'
            f'   {_tg(_E["dmg"], "💥")} {_fmt(sw["dmg_min"])}–{_fmt(sw["dmg_max"])} урона'
        )
        idx += 1

    # Арендованные у других
    for sk, entry in rented_in.items():
        if entry["until"] <= int(_time_mod.time()):
            continue
        sw = SWORDS_BY_KEY.get(sk)
        if not sw:
            continue
        sword_emoji = _tg(sw["emoji_id"], "🗡")
        lines.append(
            f'<b><i>#{idx}</i></b> {sword_emoji} <b><i>{sw["name"]}</i></b> {_tg(_E["timer"], "⏱")}\n'
            f'   <b><i>Аренда от <b><i>{entry["from_name"]}</i></b> — ещё {_fmt_until(entry["until"])}</i></b>\n'
            f'   {_tg(_E["dmg"], "💥")} {_fmt(sw["dmg_min"])}–{_fmt(sw["dmg_max"])} урона'
        )
        idx += 1

    body = "\n\n".join(lines)

    hint = (
        f'\n\n<blockquote expandable>'
        f'<b><i>Команды арсенала:</i></b>\n'
        f'<code>подарить #N @user</code> — подарить меч навсегда\n'
        f'<code>передать #N @user</code> — передать меч навсегда\n'
        f'<code>арн #N 5м @user</code> — аренда на 5 минут\n'
        f'<code>арн #N 2ч @user</code> — аренда на 2 часа\n'
        f'<code>арн #N 24ч @user</code> — аренда на 24 часа\n'
        f'<b><i>Срок аренды: от 5м до 48ч</i></b>\n\n'
        f'<b><i>Аренда — важно знать:</i></b>\n'
        f'• Пока меч в аренде — ты не можешь им ударить босса\n'
        f'• Арендованный меч нельзя подарить или передать\n'
        f'• Арендатор не может экипировать чужой меч для боя\n'
        f'• После истечения срока меч автоматически возвращается\n'
        f'• Чтобы сдать в аренду: <code>арн #N 2ч @user</code>'
        f'</blockquote>'
    )

    return (
        f'{title_line}\n\n'
        f'<blockquote>{body}</blockquote>'
        f'{hint}'
    )


def arsenal_main_keyboard(data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    owned = get_owned_swords(data)

    # Кнопки быстрого экипа для НЕ экипированных мечей
    eq_key = get_equipped_sword(data)
    equippable = [sk for sk in owned if sk != eq_key and not sword_is_rented_out(data, sk)]
    if equippable:
        builder.row(InlineKeyboardButton(
            text="Сменить меч",
            callback_data="arsenal_equip_menu",
            icon_custom_emoji_id=_E["sword"]
        ))

    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Арсенал: экран выбора меча для экипировки ───

def arsenal_equip_menu_text(data: dict) -> str:
    owned  = get_owned_swords(data)
    eq_key = get_equipped_sword(data)
    lines  = []
    idx    = 1
    for sk in owned:
        sw = SWORDS_BY_KEY.get(sk)
        if not sw:
            continue
        sword_emoji = _tg(sw["emoji_id"], "🗡")
        eq_mark = f' {_tg(_E["fire"], "⚡")} <b><i>[Экип.]</i></b>' if sk == eq_key else ""
        lines.append(f'<b><i>#{idx}</i></b> {sword_emoji} <b><i>{sw["name"]}</i></b>{eq_mark}')
        idx += 1
    body = "\n".join(lines)
    return (
        f'{_tg(_E["my_swords"], "⚔️")} <b><i>ВЫБОР МЕЧА</i></b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def arsenal_equip_menu_keyboard(data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    owned  = get_owned_swords(data)
    eq_key = get_equipped_sword(data)
    for sk in owned:
        sw = SWORDS_BY_KEY.get(sk)
        if not sw or sk == eq_key:
            continue
        if sword_is_rented_out(data, sk):
            continue
        builder.row(InlineKeyboardButton(
            text=sw["name"],
            callback_data=f'sword_equip_{sk}',
            icon_custom_emoji_id=sw["emoji_id"]
        ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="hunt_arsenal",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


# ─── Логика: подарить меч ───

def arsenal_gift_sword(sender_data: dict, recipient_data: dict,
                       sword_key: str, sender_name: str) -> tuple[bool, str]:
    """
    Безвозвратно передаёт меч от sender к recipient.
    После передачи sender может купить этот меч снова.
    """
    sw = SWORDS_BY_KEY.get(sword_key)
    if not sw:
        return False, "<b><i>❌ Меч не найден.</i></b>"
    if sender_data is recipient_data or (
        sender_data.get("uid") is not None
        and sender_data.get("uid") == recipient_data.get("uid")
    ):
        return False, "<b><i>❌ Нельзя подарить меч самому себе.</i></b>"
    if not has_sword(sender_data, sword_key):
        return False, "<b><i>❌ У тебя нет этого меча.</i></b>"
    if sword_is_rented_out(sender_data, sword_key):
        return False, "<b><i>❌ Этот меч сейчас в аренде — дождись возврата.</i></b>"
    if sword_is_rented_in(sender_data, sword_key):
        return False, "<b><i>❌ Нельзя подарить арендованный меч.</i></b>"
    if has_sword(recipient_data, sword_key):
        return False, f"<b><i>❌ У получателя уже есть {sw['name']}.</i></b>"

    # Убираем у отправителя
    sender_data["owned_swords"].remove(sword_key)
    if sender_data.get("equipped_sword") == sword_key:
        remaining = sender_data.get("owned_swords", [])
        sender_data["equipped_sword"] = remaining[0] if remaining else None

    # Добавляем получателю
    recipient_data.setdefault("owned_swords", []).append(sword_key)
    if not recipient_data.get("equipped_sword"):
        recipient_data["equipped_sword"] = sword_key
    recipient_data.setdefault("arsenal_transferred_from", {})[sword_key] = sender_name

    return True, f'<b><i>✅ Меч {sw["name"]} подарен!</i></b>'


# ─── Логика: передать меч (псевдоним подарить) ───

def arsenal_transfer_sword(sender_data: dict, recipient_data: dict,
                            sword_key: str, sender_name: str) -> tuple[bool, str]:
    """Передача = подарок, но с другим сообщением."""
    ok, msg = arsenal_gift_sword(sender_data, recipient_data, sword_key, sender_name)
    if ok:
        sw = SWORDS_BY_KEY.get(sword_key)
        msg = f'<b><i>✅ Меч {sw["name"]} передан!</i></b>'
    return ok, msg


# ─── Логика: сдать в аренду ───

def arsenal_rent_sword(owner_data: dict, renter_data: dict,
                       sword_key: str, duration_secs: int,
                       owner_name: str, renter_name: str) -> tuple[bool, str]:
    """
    Владелец сдаёт меч в аренду арендатору на duration_secs секунд.
    Владелец не может купить другую копию (меч остаётся в owned_swords).
    Арендатор получает временный доступ.
    """
    sw = SWORDS_BY_KEY.get(sword_key)
    if not sw:
        return False, "<b><i>❌ Меч не найден.</i></b>"
    if owner_data is renter_data or (
        owner_data.get("uid") is not None
        and owner_data.get("uid") == renter_data.get("uid")
    ):
        return False, "<b><i>❌ Нельзя сдать меч в аренду самому себе.</i></b>"
    if not has_sword(owner_data, sword_key):
        return False, "<b><i>❌ У тебя нет этого меча.</i></b>"
    if sword_is_rented_out(owner_data, sword_key):
        return False, "<b><i>❌ Этот меч уже сдан в аренду.</i></b>"
    if sword_is_rented_in(owner_data, sword_key):
        return False, "<b><i>❌ Нельзя сдавать арендованный меч.</i></b>"
    if has_sword(renter_data, sword_key) and not sword_is_rented_in(renter_data, sword_key):
        return False, f"<b><i>❌ У арендатора уже есть {sw['name']}.</i></b>"
    if duration_secs is None:
        return False, "<b><i>❌ Неверный срок аренды. Пример:</i></b> <code>арн #1 2ч @user</code>"

    until = int(_time_mod.time()) + duration_secs

    # Помечаем у владельца
    owner_data.setdefault("arsenal_rented_out", {})[sword_key] = {
        "uid":   renter_data.get("uid", 0),
        "name":  renter_name,
        "until": until,
    }

    # Добавляем арендатору временный меч
    renter_data.setdefault("arsenal_rented_in", {})[sword_key] = {
        "from_uid":  owner_data.get("uid", 0),
        "from_name": owner_name,
        "until":     until,
    }
    if sword_key not in renter_data.get("owned_swords", []):
        renter_data.setdefault("owned_swords", []).append(sword_key)
    if not renter_data.get("equipped_sword"):
        renter_data["equipped_sword"] = sword_key

    dur_str = _fmt_duration(duration_secs)
    return True, f'<b><i>✅ Меч {sw["name"]} сдан в аренду на {dur_str}!</i></b>'


# ─── Тексты подтверждений (отображаются после операции) ───

def arsenal_gift_confirm_text(sword_key: str, recipient_name: str) -> str:
    sw = SWORDS_BY_KEY.get(sword_key)
    sword_emoji = _tg(sw["emoji_id"], "🗡") if sw else "🗡"
    sword_name  = sw["name"] if sw else sword_key
    return (
        f'{sword_emoji} <b><i>{sword_name}</i></b> подарен игроку <b><i>{recipient_name}</i></b>\n'
        f'<b><i>Теперь ты можешь купить этот меч снова.</i></b>'
    )

def arsenal_transfer_confirm_text(sword_key: str, recipient_name: str) -> str:
    sw = SWORDS_BY_KEY.get(sword_key)
    sword_emoji = _tg(sw["emoji_id"], "🗡") if sw else "🗡"
    sword_name  = sw["name"] if sw else sword_key
    return (
        f'{sword_emoji} <b><i>{sword_name}</i></b> передан игроку <b><i>{recipient_name}</i></b>\n'
        f'<b><i>Теперь ты можешь купить этот меч снова.</i></b>'
    )

def arsenal_rent_confirm_text(sword_key: str, renter_name: str, duration_secs: int) -> str:
    sw = SWORDS_BY_KEY.get(sword_key)
    sword_emoji = _tg(sw["emoji_id"], "🗡") if sw else "🗡"
    sword_name  = sw["name"] if sw else sword_key
    dur_str = _fmt_duration(duration_secs)
    return (
        f'{sword_emoji} <b><i>{sword_name}</i></b> сдан в аренду игроку <b><i>{renter_name}</i></b> на <b><i>{dur_str}</i></b>\n'
        f'<b><i>Пока меч в аренде — им нельзя бить босса.</i></b>'
    )

def arsenal_received_text(sword_key: str, from_name: str, mode: str = "gift", duration_secs: int = 0) -> str:
    """Уведомление получателю."""
    sw = SWORDS_BY_KEY.get(sword_key)
    sword_emoji = _tg(sw["emoji_id"], "🗡") if sw else "🗡"
    sword_name  = sw["name"] if sw else sword_key
    if mode == "rent":
        dur_str = f' на <b><i>{_fmt_duration(duration_secs)}</i></b>' if duration_secs else ''
        return (
            f'Получен {sword_emoji} <b><i>{sword_name}</i></b> от <b><i>{from_name}</i></b>{dur_str}\n'
            f'<b><i>Меч уже в твоём арсенале!</i></b>'
        )
    action = "подарил" if mode == "gift" else "передал"
    return (
        f'Получен {sword_emoji} <b><i>{sword_name}</i></b> от <b><i>{from_name}</i></b>\n'
        f'<b><i>Меч уже в твоём арсенале!</i></b>'
    )


# ─── Парсинг команд арсенала ───
# Ожидаемые форматы:
#   подарить #3 @user  /  передать #2 @user
#   арн #1 2ч @user    /  арн #1 2ч 123456789

import re as _re_ars

_CMD_GIFT     = _re_ars.compile(r'^(подарить|gift)\s+#(\d+)\s+(\S+)', _re_ars.IGNORECASE)
_CMD_TRANSFER = _re_ars.compile(r'^(передать|transfer)\s+#(\d+)\s+(\S+)', _re_ars.IGNORECASE)
_CMD_RENT     = _re_ars.compile(r'^(арн|аренда|rent)\s+#(\d+)\s+(\S+)\s+(\S+)', _re_ars.IGNORECASE)

def parse_arsenal_cmd(text: str):
    """
    Возвращает dict с полями:
      action: 'gift' | 'transfer' | 'rent'
      index:  int (1-based номер меча в арсенале)
      target: str (@username или числовой uid)
      duration_secs: int | None (только для rent)
    Или None если не распознано.
    """
    text = text.strip()
    m = _CMD_GIFT.match(text)
    if m:
        return {"action": "gift", "index": int(m.group(2)), "target": m.group(3), "duration_secs": None}
    m = _CMD_TRANSFER.match(text)
    if m:
        return {"action": "transfer", "index": int(m.group(2)), "target": m.group(3), "duration_secs": None}
    m = _CMD_RENT.match(text)
    if m:
        dur = parse_duration(m.group(3))
        return {"action": "rent", "index": int(m.group(2)), "target": m.group(4), "duration_secs": dur}
    return None


def get_sword_by_arsenal_index(data: dict, index: int) -> str | None:
    """
    Возвращает sword_key по номеру #N из арсенала (как в arsenal_main_text).
    Порядок: сначала owned_swords, потом rented_in.
    """
    cleanup_expired_rentals(data)
    owned     = get_owned_swords(data)
    rented_in = get_rented_in(data)
    items = list(owned) + [k for k in rented_in if rented_in[k]["until"] > int(_time_mod.time())]
    if 1 <= index <= len(items):
        return items[index - 1]
    return None


def arsenal_error_text(msg: str) -> str:
    return (
        f'{_tg(_E["alert"], "⚠️")} <b><i>АРСЕНАЛ</i></b>\n\n'
        f'<blockquote>{msg}</blockquote>'
    )

def arsenal_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Назад в арсенал",
        callback_data="hunt_arsenal",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()

def is_arsenal_cmd(text: str) -> bool:
    t = text.strip().lstrip("/").lower()
    return t in ("арс", "арсенал", "arsenal", "ars")
