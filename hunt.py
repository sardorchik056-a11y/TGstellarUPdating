# ============================================================
#  hunt.py  —  Охота / Боссы TGStellar
#  Боссы: 10 уникальных, HP общие для всех игроков
#  3 босса в день; после смерти следующий через 2 часа
#  5 мечей с нарастающим уроном
#  Переписан для aiogram 3.x
# ============================================================

import random
import sqlite3
import json
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
    s = f"{int(n):,}".replace(",", " ")
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
        "desc": "<b>Выкован из слёз тех, кто не вернулся из глубин.</b>\n<b>Каждый удар — последний крик отчаявшейся души.</b>",
        "desc_en": "<b>Forged from the tears of those who never returned from the depths.</b>\n<b>Every strike is the last cry of a despairing soul.</b>",
        "dmg_min": 50, "dmg_max": 150,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 125_000,
    },
    {
        "key": "kings_bane",
        "name": "Погибель Королей", "name_en": "King's Bane",
        "emoji_id": SWORD_EMOJIS["kings_bane"],
        "desc": "<b>Им пали семь правителей подземных царств.</b>\n<b>Лезвие помнит каждую корону. И жаждет следующей.</b>",
        "desc_en": "<b>Seven rulers of underground kingdoms fell to this blade.</b>\n<b>The edge remembers every crown. And craves the next.</b>",
        "dmg_min": 80, "dmg_max": 250,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 250_000,
    },
    {
        "key": "frozen_doom",
        "name": "Ледяная Погибель", "name_en": "Frozen Doom",
        "emoji_id": SWORD_EMOJIS["frozen_doom"],
        "desc": "<b>Закалён в вечном льду самого холодного яруса.</b>\n<b>Прикосновение к рукояти оставляет ожог холодом.</b>",
        "desc_en": "<b>Tempered in the eternal ice of the coldest tier.</b>\n<b>Touching the hilt leaves a burn of cold.</b>",
        "dmg_min": 200, "dmg_max": 500,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 400_000,
    },
    {
        "key": "void_herald",
        "name": "Вестник Бездны", "name_en": "Void Herald",
        "emoji_id": SWORD_EMOJIS["void_herald"],
        "desc": "<b>Он появляется раньше, чем бездна открывается.</b>\n<b>Шёпот клинка слышат только обречённые.</b>",
        "desc_en": "<b>It arrives before the void even opens.</b>\n<b>Only the doomed can hear the blade's whisper.</b>",
        "dmg_min": 350, "dmg_max": 700,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 750_000,
    },
    {
        "key": "fate_cleaver",
        "name": "Рассекатель Судеб", "name_en": "Fate Cleaver",
        "emoji_id": SWORD_EMOJIS["fate_cleaver"],
        "desc": "<b>Разрезает не только плоть — но и нити судьбы.</b>\n<b>Те, кого он касался, больше не принадлежат этому миру.</b>",
        "desc_en": "<b>Cuts not just flesh — but the threads of fate itself.</b>\n<b>Those it has touched no longer belong to this world.</b>",
        "dmg_min": 500, "dmg_max": 1_250,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 1_250_000,
    },
    {
        "key": "deaths_whisper",
        "name": "Шепот Смерти", "name_en": "Death's Whisper",
        "emoji_id": SWORD_EMOJIS["deaths_whisper"],
        "desc": "<b>Не издаёт звука при ударе. Жертва слышит лишь тишину.</b>\n<b>Говорят, смерть сама подсказывает ему цель.</b>",
        "desc_en": "<b>It makes no sound on impact. The victim hears only silence.</b>\n<b>They say death itself guides it to its mark.</b>",
        "dmg_min": 700, "dmg_max": 1_800,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 3_500_000,
    },
    {
        "key": "ash_oath",
        "name": "Клятва Пепла", "name_en": "Ash Oath",
        "emoji_id": SWORD_EMOJIS["ash_oath"],
        "desc": "<b>Выкован из пепла сгоревших шахт и павших воинов.</b>\n<b>Клятва вложена в каждый удар: не остановиться.</b>",
        "desc_en": "<b>Forged from the ash of burned mines and fallen warriors.</b>\n<b>An oath sealed in every strike: never stop.</b>",
        "dmg_min": 900, "dmg_max": 2_400,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 7_000_000,
    },
    {
        "key": "desecrated_blade",
        "name": "Осквернённый Клинок", "name_en": "Desecrated Blade",
        "emoji_id": SWORD_EMOJIS["desecrated_blade"],
        "desc": "<b>Освящённый клинок, погружённый в чёрную магию глубин.</b>\n<b>Святость обернулась проклятием — и стала страшнее.</b>",
        "desc_en": "<b>A consecrated blade dipped into the dark magic of the depths.</b>\n<b>Holiness turned to a curse — and became far worse.</b>",
        "dmg_min": 1_200, "dmg_max": 3_200,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 15_000_000,
    },
    {
        "key": "last_verdict",
        "name": "Последний Приговор", "name_en": "Last Verdict",
        "emoji_id": SWORD_EMOJIS["last_verdict"],
        "desc": "<b>Вынесен миром, который устал ждать.</b>\n<b>Приговор окончателен. Обжалование невозможно.</b>",
        "desc_en": "<b>Passed by a world that grew tired of waiting.</b>\n<b>The verdict is final. No appeals.</b>",
        "dmg_min": 1_600, "dmg_max": 4_200,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 30_000_000,
    },
    {
        "key": "shadow_of_oblivion",
        "name": "Тень Забвения", "name_en": "Shadow of Oblivion",
        "emoji_id": SWORD_EMOJIS["shadow_of_oblivion"],
        "desc": "<b>Из него вышли все тени. В него они и вернутся.</b>\n<b>Забвение — не конец. Это начало чего-то хуже.</b>",
        "desc_en": "<b>All shadows came from it. To it they shall return.</b>\n<b>Oblivion is not the end. It is the beginning of something worse.</b>",
        "dmg_min": 2_000, "dmg_max": 5_500,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 60_000_000,
    },
    {
        "key": "soul_harvest",
        "name": "Жатва Душ", "name_en": "Soul Harvest",
        "emoji_id": SWORD_EMOJIS["soul_harvest"],
        "desc": "<b>Каждая убитая им душа остаётся внутри клинка.</b>\n<b>Их вопли — его боевой клич.</b>",
        "desc_en": "<b>Every soul it slays stays trapped within the blade.</b>\n<b>Their screams are its battle cry.</b>",
        "dmg_min": 2_600, "dmg_max": 7_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 120_000_000,
    },
    {
        "key": "blade_of_hopelessness",
        "name": "Клинок Безысходности", "name_en": "Blade of Hopelessness",
        "emoji_id": SWORD_EMOJIS["blade_of_hopelessness"],
        "desc": "<b>Тем, кто его видит, кажется — выхода нет.</b>\n<b>Они правы. Выхода нет.</b>",
        "desc_en": "<b>Those who see it feel there is no way out.</b>\n<b>They are right. There is none.</b>",
        "dmg_min": 3_500, "dmg_max": 9_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 250_000_000,
    },
    {
        "key": "seal_of_doom",
        "name": "Печать Гибели", "name_en": "Seal of Doom",
        "emoji_id": SWORD_EMOJIS["seal_of_doom"],
        "desc": "<b>Поставить печать — значит вынести приговор вечности.</b>\n<b>Никто не снял её ни разу. Никто и не снимет.</b>",
        "desc_en": "<b>To set the seal is to pass judgment upon eternity.</b>\n<b>No one has ever removed it. No one ever will.</b>",
        "dmg_min": 4_500, "dmg_max": 12_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 500_000_000,
    },
    {
        "key": "rift_of_eternity",
        "name": "Разлом Вечности", "name_en": "Rift of Eternity",
        "emoji_id": SWORD_EMOJIS["rift_of_eternity"],
        "desc": "<b>Разрезает ткань времени. Каждый удар — в прошлое и будущее одновременно.</b>\n<b>Вечность не бесконечна. Он это доказал.</b>",
        "desc_en": "<b>It tears the fabric of time. Every strike lands in the past and future at once.</b>\n<b>Eternity is not infinite. It proved that.</b>",
        "dmg_min": 6_000, "dmg_max": 16_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 1_000_000_000,
    },
    {
        "key": "star_devourer",
        "name": "Пожиратель Звёзд", "name_en": "Star Devourer",
        "emoji_id": SWORD_EMOJIS["star_devourer"],
        "desc": "<b>Им была погашена первая звезда. Им будет погашена последняя.</b>\n<b>Вселенная боится его. И правильно делает.</b>",
        "desc_en": "<b>The first star was extinguished by it. So will the last.</b>\n<b>The universe fears it. And rightly so.</b>",
        "dmg_min": 8_000, "dmg_max": 22_000,
        "crit_chance": 0.05, "crit_mult": 2.0,
        "price": 5_000_000_000,
    },
]

SWORDS_BY_KEY = {s["key"]: s for s in SWORDS}

# Рандомные цитаты для каждого меча в магазине
_SWORD_QUOTES_EN = {
    "blade_of_despair":     "<b>They say the first strike with this blade haunts your sleep every night.</b>",
    "kings_bane":           "<b>Seven crowns. Seven strikes. The eighth one is yours.</b>",
    "frozen_doom":          "<b>Even the hilt burns with cold. Imagine what the blade feels like.</b>",
    "void_herald":          "<b>The void stares back at you through it. Stare back.</b>",
    "fate_cleaver":         "<b>Fate's threads are thin. This blade knows exactly where to find them.</b>",
    "deaths_whisper":       "<b>The silence after the strike is more terrifying than any scream.</b>",
    "ash_oath":             "<b>The oath is never broken. Never. Under any circumstances.</b>",
    "desecrated_blade":     "<b>Consecration requires faith. Desecration requires only desire.</b>",
    "last_verdict":         "<b>No appeals. The judge has already ruled.</b>",
    "shadow_of_oblivion":   "<b>Oblivion is not death. It is worse. Much worse.</b>",
    "soul_harvest":         "<b>Thousands of voices inside. Soon there will be more.</b>",
    "blade_of_hopelessness":"<b>Those who see it stop looking for a way out. They are right.</b>",
    "seal_of_doom":         "<b>The seal cannot be removed. You can only receive the next one.</b>",
    "rift_of_eternity":     "<b>The past and the future are equally vulnerable to it.</b>",
    "star_devourer":        "<b>The first star went dark at its blow. The last one will too.</b>",
}

_SWORD_QUOTES = {
    "blade_of_despair":     "<b>Говорят, первый удар этим клинком снится тебе каждую ночь.</b>",
    "kings_bane":           "<b>Семь корон. Семь ударов. Восьмая твоя.</b>",
    "frozen_doom":          "<b>Даже рукоять обжигает холодом. Представь, каково лезвие.</b>",
    "void_herald":          "<b>Бездна смотрит в тебя сквозь него. Смотри в ответ.</b>",
    "fate_cleaver":         "<b>Нити судьбы тонкие. Этот клинок знает, как их найти.</b>",
    "deaths_whisper":       "<b>Тишина после удара — страшнее любого крика.</b>",
    "ash_oath":             "<b>Клятва не нарушается. Никогда. Ни при каких условиях.</b>",
    "desecrated_blade":     "<b>Освящение требует веры. Осквернение — только желания.</b>",
    "last_verdict":         "<b>Апелляций нет. Судья уже вынес решение.</b>",
    "shadow_of_oblivion":   "<b>Забвение — это не смерть. Это хуже. Гораздо хуже.</b>",
    "soul_harvest":         "<b>Внутри — тысячи голосов. Скоро станет больше.</b>",
    "blade_of_hopelessness":"<b>Те, кто его видит, перестают искать выход. Они правы.</b>",
    "seal_of_doom":         "<b>Печать нельзя снять. Можно только получить следующую.</b>",
    "rift_of_eternity":     "<b>Прошлое и будущее — одинаково уязвимы для него.</b>",
    "star_devourer":        "<b>Первая звезда погасла от его удара. Последняя — тоже его.</b>",
}

# Рандомные цитаты для каждого босса на главном экране охоты
_BOSS_HUNT_QUOTES_EN = {
    "ash_lord":         "<b>Ash does not lie. It shows what was. Soon it will show what you will be.</b>",
    "rift_lord":        "<b>The rift did not open by chance. It was waiting for you specifically.</b>",
    "ruin_warden":      "<b>Ruins hold secrets. He holds the ruins. You should not be here.</b>",
    "storm_king":       "<b>The storm in the tunnel is not a force of nature. It is his mood.</b>",
    "wasteland_master": "<b>The wasteland was once a forest. Before him. Keep that in mind.</b>",
    "volcano_lord":     "<b>The lava is not hot. That is just his blood, slightly cooled.</b>",
    "ice_overlord":     "<b>Cold is not a temperature. It is the way he looks at you.</b>",
    "abyss_titan":      "<b>The abyss stares into you. But he goes first.</b>",
    "chasm_keeper":     "<b>The chasm has no bottom. He checked. Personally. Many times.</b>",
    "storm_overlord":   "<b>Lightning strikes twice. If he missed the first time.</b>",
    "stone_monarch":    "<b>The mountain is his throne. You just walked into the palace.</b>",
    "ash_lands_lord":   "<b>The ashen lands remember those who came. For a long time. Very long.</b>",
    "ice_sovereign":    "<b>Ice does not melt. It waits. More patiently than you think.</b>",
    "dark_viceroy":     "<b>He already knows everything about you. Has for a while. He was just waiting.</b>",
    "ruin_overlord":    "<b>Every civilization built. He destroyed. The score is not in civilization's favor.</b>",
    "depths_master":    "<b>The depths are not silent. He is silent. For now.</b>",
    "mountain_lord":    "<b>You thought you were going up the mountain. You are going to him.</b>",
    "cursed_monarch":   "<b>The curse kills the weak. It only makes him angrier.</b>",
    "void_king":        "<b>The void is not nothing. It is his kingdom. Welcome.</b>",
    "last_keeper":      "<b>He outlived everyone. Every single one. He will outlive you too — unless you try.</b>",
}

_BOSS_HUNT_QUOTES = {
    "ash_lord":         "<b>Пепел не лжёт. Он показывает, что было. Скоро покажет, что будешь ты.</b>",
    "rift_lord":        "<b>Разлом открылся не случайно. Он ждал именно тебя.</b>",
    "ruin_warden":      "<b>Руины хранят тайны. Он хранит руины. Тебе сюда не надо.</b>",
    "storm_king":       "<b>Буря в тоннеле — это не стихия. Это его настроение.</b>",
    "wasteland_master": "<b>Пустошь была лесом. До него. Учти это.</b>",
    "volcano_lord":     "<b>Лава не горячая. Это просто его кровь остыла немного.</b>",
    "ice_overlord":     "<b>Холод — это не температура. Это его взгляд на тебя.</b>",
    "abyss_titan":      "<b>Бездна смотрит в тебя. Но сначала — он.</b>",
    "chasm_keeper":     "<b>Пропасть бездонная. Он проверял. Лично. Много раз.</b>",
    "storm_overlord":   "<b>Молния бьёт дважды. Если он промахнулся с первого раза.</b>",
    "stone_monarch":    "<b>Гора — это его трон. Ты только что вошёл во дворец.</b>",
    "ash_lands_lord":   "<b>Пепельные земли помнят тех, кто приходил. Долго. Очень долго.</b>",
    "ice_sovereign":    "<b>Лёд не тает. Он ждёт. Терпеливее, чем ты думаешь.</b>",
    "dark_viceroy":     "<b>Он уже знает о тебе всё. Ты о нём — почти ничего.</b>",
    "ruin_overlord":    "<b>Каждая цивилизация строила. Он разрушал. Счёт не в пользу цивилизаций.</b>",
    "depths_master":    "<b>Глубины не молчат. Это он молчит. Пока.</b>",
    "mountain_lord":    "<b>Ты думал, что идёшь в гору. Ты идёшь к нему.</b>",
    "cursed_monarch":   "<b>Проклятие убивает слабых. Его оно только злит.</b>",
    "void_king":        "<b>Пустота — это не ничто. Это его королевство. Добро пожаловать.</b>",
    "last_keeper":      "<b>Он пережил всех. Каждого. Он переживёт и тебя — если не постараешься.</b>",
}

# Запасные цитаты если босс/меч не найден в словаре
_SHOP_QUOTES_EN = [
    "<b>Every blade here is a story. Not all of them ended well.</b>",
    "<b>Weapons don't kill. Hands do. But a good weapon helps a great deal.</b>",
    "<b>They say the best sword is the one not yet tested in battle. Liars.</b>",
    "<b>Bosses don't fear you. Yet. Get the right blade — then we'll see.</b>",
    "<b>Iron remembers strikes. The best blades remember victories.</b>",
    "<b>The price of a sword is nothing compared to the price of defeat.</b>",
    "<b>A miner without a sword is just a miner. A miner with a sword is a hunter.</b>",
    "<b>Choose your weapon with your heart. But let your wallet think too.</b>",
    "<b>Some bosses have seen a thousand blades. They will remember yours.</b>",
    "<b>A good sword is not a purchase. It is an investment in someone else's end.</b>",
]

_HUNT_QUOTES_EN = [
    "<b>Every boss is a wall. Every strike is a crack in it.</b>",
    "<b>They don't die on their own. Someone has to help them. That someone is you.</b>",
    "<b>The hunt is not cruelty. It is economics.</b>",
    "<b>The boss is waiting. He is patient. But not eternal.</b>",
    "<b>Five million coins for one death. Not a bad deal.</b>",
    "<b>The depths are full of monsters. Good thing you have a sword.</b>",
    "<b>They say bosses can sense a hunter's fear. Don't give them that pleasure.</b>",
    "<b>Every strike brings you closer to the reward. Don't stop.</b>",
    "<b>The mine is not just ore. Sometimes it is blood too.</b>",
    "<b>Legendary hunters started with an iron blade. You have already begun.</b>",
]

_SHOP_QUOTES = [
    "<b>Каждый клинок здесь — это история. Не все из них хорошо закончились.</b>",
    "<b>Оружие не убивает. Убивают руки. Но хорошее оружие очень помогает.</b>",
    "<b>Говорят, лучший меч тот, который ещё не пробовали на деле. Лжецы.</b>",
    "<b>Боссы не боятся тебя. Пока. Купи правильный клинок — и посмотрим.</b>",
    "<b>Железо помнит удары. Лучшие клинки помнят победы.</b>",
    "<b>Цена меча — ничто по сравнению с ценой поражения.</b>",
    "<b>Шахтёр без меча — просто шахтёр. Шахтёр с мечом — охотник.</b>",
    "<b>Выбирай оружие сердцем. Но кошельком тоже думай.</b>",
    "<b>Некоторые боссы видели тысячи клинков. Твой они запомнят.</b>",
    "<b>Хороший меч — это не покупка. Это инвестиция в чужую гибель.</b>",
]

_HUNT_QUOTES = [
    "<b>Каждый босс — это стена. Каждый удар — трещина в ней.</b>",
    "<b>Они не умирают сами. Кто-то должен им помочь. Этот кто-то — ты.</b>",
    "<b>Охота — это не жестокость. Это экономика.</b>",
    "<b>Босс ждёт. Он терпеливый. Но не вечный.</b>",
    "<b>Пять миллионов монет за одну смерть. Неплохая ставка.</b>",
    "<b>Глубины полны чудовищ. Хорошо, что у тебя есть меч.</b>",
    "<b>Говорят, боссы чувствуют страх охотника. Не давай им эту радость.</b>",
    "<b>Каждый удар приближает награду. Не останавливайся.</b>",
    "<b>Шахта — это не только руда. Иногда это ещё и кровь.</b>",
    "<b>Легендарные охотники начинали с железного клинка. Ты уже начал.</b>",
]

# ─────────────────────────────────────────
#  БОССЫ
# ─────────────────────────────────────────
BOSS_MAX_HP       = 10_000_000
BOSS_RESPAWN_SEC  = 30 * 60    # 30 минут после смерти — следующий босс в слоте
ACTIVE_BOSS_SLOTS = 5          # одновременно активных боссов

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


def _pick_random_boss(exclude_keys: list[str] = None) -> dict:
    """Выбирает случайного босса, не из исключённых (активные в других слотах)."""
    pool = [b for b in BOSSES if not exclude_keys or b["key"] not in exclude_keys]
    if not pool:
        pool = BOSSES  # крайний случай
    return random.choice(pool)


def _spawn_slot(slot: int, kill_duration: int = None, active_keys: list[str] = None):
    """Спавнит нового случайного босса в слот."""
    if kill_duration is None:
        next_hp = BOSS_MAX_HP
    elif kill_duration <= 5 * 60:
        next_hp = BOSS_HP_FAST
    elif kill_duration <= 30 * 60:
        next_hp = BOSS_HP_MEDIUM
    else:
        next_hp = BOSS_HP_SLOW

    boss = _pick_random_boss(exclude_keys=active_keys or [])
    state = {
        "boss_key":          boss["key"],
        "boss_hp":           next_hp,
        "boss_max_hp":       next_hp,
        "boss_alive":        True,
        "boss_spawned":      _now_ts(),
        "boss_died_at":      None,
        "boss_kill_duration": None,
        "damage_log":        {},
    }
    _save_slot(slot, state)
    return state


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
    }

    now = _now_ts()
    last_hit = data.get("last_boss_hit", 0)
    if now - last_hit < 1:
        result["error"] = "cooldown"
        return result

    sword_key = data.get("equipped_sword")
    if not sword_key:
        result["error"] = "no_sword"
        return result

    sword = SWORDS_BY_KEY.get(sword_key)
    if not sword:
        result["error"] = "no_sword"
        return result

    state = _load_slot(slot)

    if not state or not state.get("boss_alive", False):
        result["error"] = "boss_dead"
        return result

    if state.get("boss_key") not in BOSSES_BY_KEY:
        result["error"] = "boss_dead"
        return result

    data["last_boss_hit"] = now

    # Множители урона
    from datetime import datetime, timezone as _tz
    _now_check = datetime.now(_tz.utc).timestamp()
    _enh = data.get("active_enh_booster")
    enh_mult = (_enh["multiplier"] if _enh and _enh.get("ends_at", 0) > _now_check else 1.0)

    from shop import get_artifact_damage_multiplier
    art_dmg_mult = get_artifact_damage_multiplier(data)

    from status import get_status_multiplier as _status_dmg_mult, get_crit_chance_bonus as _status_crit_bonus
    status_dmg_mult = _status_dmg_mult(data)
    status_crit_add = _status_crit_bonus(data) / 100.0

    if data.get("infinite_dmg"):
        dmg  = state["boss_hp"]
        crit = False
    else:
        dmg = random.randint(sword["dmg_min"], sword["dmg_max"])
        crit = False
        if random.random() < sword["crit_chance"] + status_crit_add:
            dmg  = int(sword["dmg_max"] * sword["crit_mult"])
            crit = True
        dmg = int(dmg * enh_mult * art_dmg_mult * status_dmg_mult)

    hp_before = state["boss_hp"]
    hp_after  = max(0, hp_before - dmg)
    state["boss_hp"] = hp_after

    # Записываем урон в лог
    uid_str = str(data.get("id", 0))
    damage_log = state.setdefault("damage_log", {})
    damage_log[uid_str] = damage_log.get(uid_str, 0) + dmg

    result["hit"]            = True
    result["crit"]           = crit
    result["dmg"]            = dmg
    result["boss_hp_before"] = hp_before
    result["boss_hp_after"]  = hp_after

    if hp_after == 0:
        died_at = _now_ts()
        spawned_at = state.get("boss_spawned", died_at)
        kill_duration = died_at - spawned_at

        state["boss_alive"]          = False
        state["boss_died_at"]        = died_at
        state["boss_kill_duration"]  = kill_duration
        result["boss_killed"]        = True

        # ── Пропорциональное распределение награды ──
        total_pool = _reward_for_hp(state.get("boss_max_hp", BOSS_MAX_HP))
        total_dmg  = sum(damage_log.values()) or 1
        killer_uid = uid_str

        damage_rewards = {}  # uid_str -> (coins, xp)
        for u_str, u_dmg in damage_log.items():
            share      = u_dmg / total_dmg
            coins      = int(total_pool * share)
            is_killer  = (u_str == killer_uid)
            if is_killer:
                xp = BOSS_XP_KILLER
            else:
                xp = max(
                    BOSS_XP_PARTICIPANT_MIN,
                    int(BOSS_XP_PARTICIPANT_MAX * share)
                )
            damage_rewards[u_str] = (coins, xp)

        result["damage_rewards"] = damage_rewards
        result["reward"]         = damage_rewards.get(uid_str, (0, 0))[0]
        result["xp"]             = damage_rewards.get(uid_str, (0, 0))[1]

        # Начисляем убийце сразу (остальным — в main.py через damage_rewards)
        data["balance"] = data.get("balance", 0) + result["reward"]
        data["xp"]      = data.get("xp", 0) + result["xp"]

    _save_slot(slot, state)
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
        return False, ("❌ Sword not found." if lang == "en" else "❌ Меч не найден.")
    if has_sword(data, sword_key):
        return False, ("❌ You already have this sword." if lang == "en" else "❌ Этот меч уже у тебя есть.")
    if data.get("balance", 0) < sword["price"]:
        need = sword["price"] - data.get("balance", 0)
        return False, (f'❌ Not enough coins. Need {_fmt(need)} more {COIN}' if lang == "en" else f'❌ Недостаточно монет. Нужно ещё {_fmt(need)} {COIN}')
    data["balance"] -= sword["price"]
    data.setdefault("owned_swords", []).append(sword_key)
    if not data.get("equipped_sword"):
        data["equipped_sword"] = sword_key
    return True, ("✅ Sword purchased!" if lang == "en" else "✅ Меч куплен!")


def equip_sword(data: dict, sword_key: str, lang: str = "ru") -> tuple[bool, str]:
    if not has_sword(data, sword_key):
        return False, ("❌ This sword is not purchased." if lang == "en" else "❌ Этот меч не куплен.")
    data["equipped_sword"] = sword_key
    return True, ("✅ Sword equipped!" if lang == "en" else "✅ Меч экипирован!")


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
        _quote = f'<b>{_boss_display_name}:</b>\n{_raw_quote}'
    else:
        _quote = _raw_quote

    if lang == "en":
        header = (
            f'<blockquote>'
            f'{_tg(_E["hunt"], "💀")} <b>BOSS HUNT</b>\n'
            f'<b>Swords in arsenal: {count} / {len(SWORDS)}</b>\n\n'
            f'{_quote}'
            f'</blockquote>\n\n'
        )
    else:
        header = (
            f'<blockquote>'
            f'{_tg(_E["hunt"], "💀")} <b>ОХОТА НА БОССОВ</b>\n'
            f'<b>Мечей в арсенале: {count} / {len(SWORDS)}</b>\n\n'
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
                f'{_tg(_E["sword"], "⚔️")} <b>Active sword:</b> {_tg(sword["emoji_id"], "🗡")} <b>{sword_name}</b>\n'
                f'{_tg(_E["dmg"], "💥")} <b>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
                f'{_tg(_E["crit"], "⭐")} <b>Crit: 5% chance × 2.0 of max damage</b>'
                f'</blockquote>\n\n'
            )
        else:
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["sword"], "⚔️")} <b>Активный меч:</b> {_tg(sword["emoji_id"], "🗡")} <b>{sword_name}</b>\n'
                f'{_tg(_E["dmg"], "💥")} <b>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
                f'{_tg(_E["crit"], "⭐")} <b>Крит: 5% шанс × 2.0 от макс. урона</b>'
                f'</blockquote>\n\n'
            )
    else:
        if lang == "en":
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["lock"], "🔒")} <b>No active sword.</b>\n'
                f'<b>Buy a sword in the shop — and go into battle!</b>'
                f'</blockquote>\n\n'
            )
        else:
            eq_block = (
                f'<blockquote>'
                f'{_tg(_E["lock"], "🔒")} <b>Нет активного меча.</b>\n'
                f'<b>Купи меч в магазине — и иди в бой!</b>'
                f'</blockquote>\n\n'
            )

    # Статус всех 5 боссов
    slots = get_all_slots()
    now   = _now_ts()
    boss_lines = ""
    for slot_idx, st in slots:
        boss_key = st.get("boss_key")
        boss     = BOSSES_BY_KEY.get(boss_key)
        if st.get("boss_alive") and boss:
            hp     = st["boss_hp"]
            max_hp = st.get("boss_max_hp", BOSS_MAX_HP)
            pct    = hp / max_hp * 100
            bname  = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
            boss_lines += (
                f'\n{_tg(_E["boss"], "🔥")} <b>#{slot_idx+1} {bname}</b>\n'
                f'   {_tg(_E["hp"], "❤️")} {_fmt_digits(hp)} / {_fmt_digits(max_hp)} <b>({pct:.1f}%)</b>'
            )
        else:
            died_at = st.get("boss_died_at", 0) or 0
            rem     = max(0, BOSS_RESPAWN_SEC - (now - died_at))
            m       = rem // 60
            if lang == "en":
                boss_lines += f'\n{_tg(_E["dead"], "💀")} <b>#{slot_idx+1}</b> — next in {m}m'
            else:
                boss_lines += f'\n{_tg(_E["dead"], "💀")} <b>#{slot_idx+1}</b> — след. через {m}м'

    if lang == "en":
        boss_block = f'<blockquote><b>Active bosses:</b>{boss_lines}\n</blockquote>'
    else:
        boss_block = f'<blockquote><b>Активные боссы:</b>{boss_lines}\n</blockquote>'

    return header + eq_block + boss_block


def hunt_main_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder  = InlineKeyboardBuilder()
    slots    = get_all_slots()
    eq_key   = get_equipped_sword(data)

    # Кнопки боссов — по 2-3 в ряд
    row_btns = []
    for slot_idx, st in slots:
        boss_key = st.get("boss_key")
        boss     = BOSSES_BY_KEY.get(boss_key)
        alive    = st.get("boss_alive", False)
        if alive and boss:
            hp     = st["boss_hp"]
            max_hp = st.get("boss_max_hp", BOSS_MAX_HP)
            pct    = int(hp / max_hp * 100)
            bname  = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
            btn    = InlineKeyboardButton(
                text=f"⚔️ #{slot_idx+1} {bname} {pct}%",
                callback_data=f"hunt_boss_{slot_idx}",
                icon_custom_emoji_id=_E["skull"]
            )
        else:
            died_at = st.get("boss_died_at", 0) or 0
            rem     = max(0, BOSS_RESPAWN_SEC - (_now_ts() - died_at))
            m       = rem // 60
            label   = f"⏳ #{slot_idx+1} {m}м" if lang == "ru" else f"⏳ #{slot_idx+1} {m}m"
            btn     = InlineKeyboardButton(
                text=label,
                callback_data=f"hunt_boss_{slot_idx}",
                icon_custom_emoji_id=_E["timer"]
            )
        row_btns.append(btn)

    # Две кнопки в ряд, последняя отдельно если нечётное
    for i in range(0, len(row_btns) - 1, 2):
        builder.row(row_btns[i], row_btns[i+1])
    if len(row_btns) % 2 == 1:
        builder.row(row_btns[-1])

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
    quote = f'{sword_emoji} <b>{sword_name_display}:</b>\n{raw_quote}'

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["shop"], "🛒")} <b>ARMORY</b>\n'
            f'<b>Owned: {owned_count} / {len(SWORDS)}</b>  |  '
            f'<b>Page {page + 1} / {total_pages}</b>\n\n'
            f'{quote}'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["shop"], "🛒")} <b>ОРУЖЕЙНАЯ</b>\n'
        f'<b>Куплено: {owned_count} / {len(SWORDS)}</b>  |  '
        f'<b>Страница {page + 1} / {total_pages}</b>\n\n'
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
        sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
        if owned:
            builder.row(InlineKeyboardButton(
                text=sword_name,
                callback_data=f'sword_info_{sword["key"]}',
                icon_custom_emoji_id=sword["emoji_id"],
                style="success"
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


def sword_detail_text(data: dict, sword_key: str, lang: str = "ru") -> str:
    sword = SWORDS_BY_KEY.get(sword_key)
    if not sword:
        return "<b>❌ Sword not found.</b>" if lang == "en" else "<b>❌ Меч не найден.</b>"

    owned    = has_sword(data, sword_key)
    equipped = get_equipped_sword(data) == sword_key

    sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]
    sword_desc = sword.get("desc_en", sword["desc"]) if lang == "en" else sword["desc"]

    status_parts = []
    if owned:
        status_parts.append(f'{_tg(_E["ok"], "✅")} <b>{"In arsenal" if lang == "en" else "Есть в арсенале"}</b>')
    else:
        status_parts.append(f'{_tg(_E["lock"], "🔒")} <b>{"Not purchased" if lang == "en" else "Не куплен"}</b>')
    if equipped:
        status_parts.append(f'{_tg(_E["fire"], "⚡")} <b>{"Equipped" if lang == "en" else "Экипирован"}</b>')

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
            f'{sword_emoji} <b>{sword_name}</b>\n'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{sword_desc}'
            f'</blockquote>\n\n'
            f'{sword_quote_block}'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
            f'{_tg(_E["crit"], "⭐")} <b>Crit: 5% × ×{sword["crit_mult"]:.0f} — max {_fmt(int(sword["dmg_max"] * sword["crit_mult"]))}</b>\n'
            f'{_tg(_E["price"], "💲")} <b>Price: {_fmt(sword["price"])} {_tg(_E["coin"], "💰")}</b>\n\n'
            f'{status_line}'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{sword_emoji} <b>{sword_name}</b>\n'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{sword_desc}'
        f'</blockquote>\n\n'
        f'{sword_quote_block}'
        f'<blockquote>'
        f'{_tg(_E["dmg"], "💥")} <b>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
        f'{_tg(_E["crit"], "⭐")} <b>Крит: 5% × ×{sword["crit_mult"]:.0f} — макс. {_fmt(int(sword["dmg_max"] * sword["crit_mult"]))}</b>\n'
        f'{_tg(_E["price"], "💲")} <b>Цена: {_fmt(sword["price"])} {_tg(_E["coin"], "💰")}</b>\n\n'
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
            builder.row(InlineKeyboardButton(
                text=f'{_fmt(sword["price"])}',
                callback_data=f'sword_buy_{sword_key}',
                icon_custom_emoji_id=_E["coin"]
            ))
        elif not equipped:
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
                f'{_tg(_E["lock"], "🔒")} <b>Arsenal is empty.</b>\n'
                f'<b>Check the armory — blades are waiting!</b>'
            )
        else:
            body = (
                f'{_tg(_E["lock"], "🔒")} <b>Арсенал пуст.</b>\n'
                f'<b>Загляни в магазин оружия — там ждут клинки!</b>'
            )
    else:
        lines = []
        for sk in owned:
            sw = SWORDS_BY_KEY.get(sk)
            if not sw:
                continue
            sw_name = sw.get("name_en", sw["name"]) if lang == "en" else sw["name"]
            eq_label = f' {_tg(_E["fire"], "⚡")} <b>{"[Eqp.]" if lang == "en" else "[Экип.]"}</b>' if sk == eq_key else ""
            sword_emoji = _tg(sw["emoji_id"], "🗡")
            dmg_label = "dmg" if lang == "en" else "урона"
            lines.append(
                f'{sword_emoji} <b>{sw_name}</b>{eq_label}\n'
                f'   {_tg(_E["dmg"], "💥")} <b>{_fmt(sw["dmg_min"])}–{_fmt(sw["dmg_max"])} {dmg_label}</b>'
            )
        body = "\n\n".join(lines)

    title = "MY SWORDS" if lang == "en" else "МОИ МЕЧИ"
    arsenal_label = "Arsenal" if lang == "en" else "Арсенал"
    return (
        f'<blockquote>'
        f'{_tg(_E["my_swords"], "⚔️")} <b>{title}</b>\n'
        f'<b>{arsenal_label}: {len(owned)} / {len(SWORDS)}</b>'
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
        if sk != eq_key:
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
                f'{_tg(_E["lock"], "🔒")} <b>BOSS ATTACK</b>\n\n'
                f'<b>You have no sword.</b>\n'
                f'<b>Buy a weapon in the shop!</b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["lock"], "🔒")} <b>АТАКА БОССА</b>\n\n'
            f'<b>У тебя нет меча.</b>\n'
            f'<b>Купи оружие в магазине!</b>'
            f'</blockquote>'
        )

    if not state or not state.get("boss_alive"):
        died_at = (state.get("boss_died_at") or 0) if state else 0
        rem     = max(0, BOSS_RESPAWN_SEC - (_now_ts() - died_at))
        m       = rem // 60
        if lang == "en":
            return (
                f'<blockquote>'
                f'{_tg(_E["dead"], "💀")} <b>BOSS DEFEATED!</b>\n\n'
                f'{_tg(_E["timer"], "⏱")} <b>Next spawns in: {m}m</b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["dead"], "💀")} <b>БОСС ПОВЕРЖЕН!</b>\n\n'
            f'{_tg(_E["timer"], "⏱")} <b>Следующий появится через: {m}м</b>'
            f'</blockquote>'
        )

    if not boss:
        return "<b>❌ Boss not found.</b>" if lang == "en" else "<b>❌ Ошибка: босс не найден.</b>"

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
                f'{_tg(_E["fire"], "⚡")} <b>Damage booster: ×{_ms} active</b>\n'
                f'{_tg(_E["timer"], "⏱")} <b>Time left: {_left}</b>'
                f'</blockquote>'
            )
        else:
            enh_line = (
                f'\n\n<blockquote>'
                f'{_tg(_E["fire"], "⚡")} <b>Усилитель урона: ×{_ms} активен</b>\n'
                f'{_tg(_E["timer"], "⏱")} <b>Осталось: {_left}</b>'
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
                f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>Damage artifact: ×{_art_dmg_str}</b>'
                f'</blockquote>'
            )
        else:
            art_dmg_line = (
                f'\n\n<blockquote>'
                f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>Артефакт урона: ×{_art_dmg_str}</b>'
                f'</blockquote>'
            )
    else:
        art_dmg_line = ""

    boss_name  = boss.get("name_en", boss["name"]) if lang == "en" else boss["name"]
    boss_lore  = boss.get("lore_en", boss["lore"]) if lang == "en" else boss["lore"]
    sword_name = sword.get("name_en", sword["name"]) if lang == "en" else sword["name"]

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b>{boss_name}</b>\n'
            f'<i>{boss_lore}</i>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["hp"], "❤️")} <b>HP:</b> {_fmt_digits(hp)} / {_fmt_digits(max_hp)} <b>({pct:.1f}%)</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["sword"], "⚔️")} <b>Your sword: {_tg(sword["emoji_id"], "🗡")} {sword_name}</b>\n'
            f'{_tg(_E["dmg"], "💥")} <b>Damage: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
            f'{_tg(_E["crit"], "⭐")} <b>Crit: 5% × {sword["crit_mult"]:.0f} of max damage</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["trophy"], "🏆")} <b>Kill reward: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</b>'
            f'</blockquote>'
            f'{enh_line}'
            f'{art_dmg_line}'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["skull"], "💀")} <b>{boss_name}</b>\n'
        f'<i>{boss_lore}</i>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["hp"], "❤️")} <b>HP:</b> {_fmt_digits(hp)} / {_fmt_digits(max_hp)} <b>({pct:.1f}%)</b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["sword"], "⚔️")} <b>Твой меч: {_tg(sword["emoji_id"], "🗡")} {sword_name}</b>\n'
        f'{_tg(_E["dmg"], "💥")} <b>Урон: {_fmt(sword["dmg_min"])} — {_fmt(sword["dmg_max"])}</b>\n'
        f'{_tg(_E["crit"], "⭐")} <b>Крит: 5% × {sword["crit_mult"]:.0f} от макс. урона</b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["trophy"], "🏆")} <b>Награда за убийство: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</b>'
        f'</blockquote>'
        f'{enh_line}'
        f'{art_dmg_line}'
    )


def boss_attack_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    state   = get_boss_state()
    eq_key  = get_equipped_sword(data)

    if state.get("boss_alive") and eq_key:
        builder.row(InlineKeyboardButton(
            text="Strike!" if lang == "en" else "Ударить!",
            callback_data="hunt_strike",
            icon_custom_emoji_id=_E["sword"]
        ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()


def boss_strike_result_text(data: dict, result: dict, lang: str = "ru") -> str:
    """Текст после удара по боссу."""
    state    = get_boss_state()
    boss_key = state.get("boss_key")
    boss     = BOSSES_BY_KEY.get(boss_key)

    if result.get("error") == "no_sword":
        return (
            f'{_tg(_E["lock"], "🔒")} <b>{"No sword — nothing to attack with!" if lang == "en" else "Нет меча — нечем атаковать!"}</b>'
        )

    if result.get("error") == "boss_dead":
        return (
            f'{_tg(_E["dead"], "💀")} <b>{"Boss is already dead! Wait for the next one." if lang == "en" else "Босс уже мёртв! Жди следующего."}</b>'
        )

    dmg       = result["dmg"]
    crit      = result["crit"]
    hp_after  = result["boss_hp_after"]
    killed    = result["boss_killed"]
    max_hp    = state.get("boss_max_hp", BOSS_MAX_HP)
    pct       = hp_after / max_hp * 100

    if lang == "en":
        crit_line = (
            f'\n{_tg(_E["crit"], "⭐")} <b>CRITICAL HIT!</b>'
            if crit else ""
        )
    else:
        crit_line = (
            f'\n{_tg(_E["crit"], "⭐")} <b>КРИТИЧЕСКИЙ УДАР!</b>'
            if crit else ""
        )

    if killed:
        reward = result["reward"]
        boss_name = boss.get("name_en", boss["name"]) if (lang == "en" and boss) else (boss["name"] if boss else ("Boss" if lang == "en" else "Босс"))
        if lang == "en":
            return (
                f'<blockquote>'
                f'{_tg(_E["skull"], "💀")} <b>BOSS DESTROYED!</b>\n\n'
                f'<b>{boss_name} has been defeated!</b>'
                f'</blockquote>\n\n'
                f'<blockquote>'
                f'{_tg(_E["dmg"], "💥")} <b>Final strike: {_fmt(dmg)}</b>{crit_line}\n'
                f'{_tg(_E["reward_coin"], "💰")} <b>Reward: +{_fmt(reward)} {_tg(_E["reward_coin"], "💰")}</b>'
                f'</blockquote>\n\n'
                f'<blockquote>'
                f'{_tg(_E["timer"], "⏱")} <b>Next boss appears in 2 hours.</b>'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b>БОСС УНИЧТОЖЕН!</b>\n\n'
            f'<b>{boss_name} повержен!</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b>Последний удар: {_fmt(dmg)}</b>{crit_line}\n'
            f'{_tg(_E["reward_coin"], "💰")} <b>Награда: +{_fmt(reward)} {_tg(_E["reward_coin"], "💰")}</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["timer"], "⏱")} <b>Следующий босс появится через 2 часа.</b>'
            f'</blockquote>'
        )

    boss_name = boss.get("name_en", boss["name"]) if (lang == "en" and boss) else (boss["name"] if boss else ("Boss" if lang == "en" else "Босс"))

    if lang == "en":
        return (
            f'<blockquote>'
            f'{_tg(_E["skull"], "💀")} <b>{boss_name}</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["dmg"], "💥")} <b>Your strike: {_fmt(dmg)}</b> {_tg(_E["dmg"], "💥")}{crit_line}'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["hp"], "❤️")} <b>HP:</b> {_fmt_digits(hp_after)} / {_fmt_digits(max_hp)} <b>({pct:.1f}%)</b>'
            f'</blockquote>\n\n'
            f'<blockquote>'
            f'{_tg(_E["trophy"], "🏆")} <b>Kill reward: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</b>'
            f'</blockquote>'
        )
    return (
        f'<blockquote>'
        f'{_tg(_E["skull"], "💀")} <b>{boss_name}</b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["dmg"], "💥")} <b>Твой удар: {_fmt(dmg)}</b> {_tg(_E["dmg"], "💥")}{crit_line}'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["hp"], "❤️")} <b>HP:</b> {_fmt_digits(hp_after)} / {_fmt_digits(max_hp)} <b>({pct:.1f}%)</b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["trophy"], "🏆")} <b>Награда за убийство: {_fmt(_reward_for_hp(max_hp))} {_tg(_E["coin"], "💰")}</b>'
        f'</blockquote>'
    )


def boss_strike_keyboard(data: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после удара — даём ударить ещё раз или назад."""
    builder = InlineKeyboardBuilder()
    state   = get_boss_state()
    eq_key  = get_equipped_sword(data)

    if state.get("boss_alive") and eq_key:
        builder.row(InlineKeyboardButton(
            text="Strike again!" if lang == "en" else "Ударить ещё!",
            callback_data="hunt_strike",
            icon_custom_emoji_id=_E["sword"]
        ))

    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="hunt",
        icon_custom_emoji_id=_E["back"]
    ))
    return builder.as_markup()
