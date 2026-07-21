# ============================================================
#  pets.py  —  Питомцы TGStellar
#  10 уникальных питомцев-шахтёров
#  Каждые 12 часов питомец приносит монеты + шлёт уведомление
#  Переписан для aiogram 3.x
# ============================================================

import random
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from miner import COIN, EMOJI_BACK

_E = {
    "paw":   "5337047059180566409",
    "coin":  "5199552030615558774",
    "lock":  "5240241223632954241",
    "ok":    "5206607081334906820",
    "back":  "6039539366177541657",
    "alert": "5258203794772085854",
    "chest": "5310278924616356636",
    "timer": "5440621591387980068",
    "mine":  "5197371802136892976",
    "fire":  "5438571934210082705",
    "arrow": "5427168083074628963",
    "income":"5449683594425410231",
    "price": "5397782960512444700",
}

# Прем-эмодзи для каждого питомца
_PET_EMOJI = {
    "hamster": "5208535779348864977",
    "toad":    "5845830268044185765",
    "beaver":  "5352606295469871252",
    "mole":    "5427397704911177177",
    "raccoon": "5202166785230524217",
    "wolf":    "5296668976414203103",
    "lion":    "5375448597997316048",
    "bear":    "5206502842478638898",
    "croc":    "5217616693127293773",
    "gnome":   "4945387415205315532",
}

# Прем-эмодзи для купленных питомцев (светящийся)
_E_OWNED = "5206607081334906820"

def _tg(eid, fb): 
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
def _btn(eid, label, cb): 
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=eid)
def _back_btn(cb, label="Назад"):
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=_E["back"])

def _fmt(n) -> str:
    """
    Сокращённый формат чисел (стандартная короткая шкала, единый стиль
    с database.py -> format_amount, miner.py -> _fmt_num, klan.py -> _fmt):
      999          -> "999"
      1500         -> "1.5K"
      100000       -> "100K"
      2300000      -> "2.3M"
      1500000000   -> "1.5B"
      1_000_000_000_000        -> "1T"
      1_000_000_000_000_000    -> "1Qa"  (quadrillion)
      1_000_000_000_000_000_000-> "1Qi"  (quintillion)
    Если число ещё больше — формат не ломается: продолжаем Sx/Sp/Oc/No/Dc, Dc2, ...
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

def _now_ts(): 
    return int(datetime.now(timezone.utc).timestamp())

PET_INCOME_INTERVAL = 12 * 3600
PAGE_SIZE = 5

_PETS_MENU_TEXTS_EN = [
    "Your pets are already underground — digging, trying, bringing coins.",
    "Every pet is a miner with their own personality. Some even have complaints.",
    "The more pets, the more noise in the mine. And more coins too.",
    "Pets don't sleep. Pets work. Especially the mole — he doesn't understand what night is.",
    "They say the hamster found a golden vein and hid it in his cheek. Couldn't verify.",
    "The beaver has already drawn next week's plan. The gnome hasn't read it but earned more.",
    "The raccoon found something again. Won't say where. But the coins are real.",
    "The wolf held a meeting. Everyone attended. Voluntarily. Almost.",
    "Croc is on shift again. He's always on shift. No one checked if he ever left.",
    "The Crystal Gnome sees through stone. Won't say what exactly. Delivers coins on time.",
]

PETS = [
    {"key":"hamster","name":"Hamster Miner","name_en":"Hamster Miner","emoji":"🐹",
     "desc":"<b>Неутомимый малыш с кирочкой.</b>\n<b>Всегда прячет находки за щеками.</b>",
     "desc_en":"<b>A tireless little guy with a pickaxe.</b>\n<b>Always stashes finds in his cheeks.</b>",
     "price":500_000,"rarity":"Обычный","rarity_en":"Common",
     "bonus":"<b>Таскает камни и мелочёвку</b>","bonus_en":"<b>Hauls stones and small finds</b>",
     "income_min":15_000,"income_max":50_000},
    {"key":"toad","name":"Болотный Жабакоп","name_en":"Swamp Toadforeman","emoji":"🐸",
     "desc":"<b>Прораб с болота.</b>\n<b>Любит сырые тоннели и считает каждый булыжник.</b>",
     "desc_en":"<b>A foreman from the swamp.</b>\n<b>Loves damp tunnels and counts every cobblestone.</b>",
     "price":2_500_000,"rarity":"Необычный","rarity_en":"Uncommon",
     "bonus":"<b>Чует медь и уголь лучше других</b>","bonus_en":"<b>Sniffs out copper and coal better than anyone</b>",
     "income_min":45_000,"income_max":150_000},
    {"key":"beaver","name":"Бобёр Прораб","name_en":"Beaver Foreman","emoji":"🦫",
     "desc":"<b>Строит тоннели быстрее всех.</b>\n<b>Без чертежей не работает.</b>",
     "desc_en":"<b>Builds tunnels faster than anyone.</b>\n<b>Won't work without blueprints.</b>",
     "price":7_000_000,"rarity":"Необычный","rarity_en":"Uncommon",
     "bonus":"<b>Укрепляет тоннели — меньше обвалов</b>","bonus_en":"<b>Reinforces tunnels — fewer cave-ins</b>",
     "income_min":105_000,"income_max":325_000},
    {"key":"mole","name":"Крот на Энергетиках","name_en":"Energy Drink Mole","emoji":"🦔",
     "desc":"<b>Выпил пятую банку — и уже на глубине 500 метров.</b>\n<b>Спать не планирует.</b>",
     "desc_en":"<b>Downed his fifth can — already 500 meters deep.</b>\n<b>Has no plans to sleep.</b>",
     "price":25_000_000,"rarity":"Редкий","rarity_en":"Rare",
     "bonus":"<b>Копает в 2 раза быстрее ночью</b>","bonus_en":"<b>Digs twice as fast at night</b>",
     "income_min":510_000,"income_max":735_000},
    {"key":"raccoon","name":"Енот Мародёр","name_en":"Raccoon Looter","emoji":"🦝",
     "desc":"<b>Найдёт что угодно где угодно.</b>\n<b>Но сначала сам решит — отдавать или нет.</b>",
     "desc_en":"<b>Finds anything, anywhere.</b>\n<b>But decides for himself whether to hand it over.</b>",
     "price":65_000_000,"rarity":"Редкий","rarity_en":"Rare",
     "bonus":"<b>Шанс найти потерянные ресурсы</b>","bonus_en":"<b>Chance to find lost resources</b>",
     "income_min":850_000,"income_max":1_500_000},
    {"key":"wolf","name":"Волк Бригадир","name_en":"Wolf Crew Boss","emoji":"🐺",
     "desc":"<b>Держит всю шахту в страхе.</b>\n<b>Без его команды никто не копает.</b>",
     "desc_en":"<b>Keeps the entire mine in fear.</b>\n<b>Nobody digs without his orders.</b>",
     "price":120_000_000,"rarity":"Эпический","rarity_en":"Epic",
     "bonus":"<b>Бонус к добыче железа и золота</b>","bonus_en":"<b>Bonus to iron and gold mining</b>",
     "income_min":2_500_000,"income_max":4_000_000},
    {"key":"lion","name":"Лев Колека","name_en":"Lion Colleague","emoji":"🦁",
     "desc":"<b>Говорит что просто колека.</b>\n<b>Но все знают — он тут главный.</b>",
     "desc_en":"<b>Says he's just a colleague.</b>\n<b>But everyone knows — he's the boss.</b>",
     "price":500_000_000,"rarity":"Эпический","rarity_en":"Epic",
     "bonus":"<b>Повышает шанс редких руд</b>","bonus_en":"<b>Increases rare ore chance</b>",
     "income_min":7_000_000,"income_max":18_000_000},
    {"key":"bear","name":"Хромой Медведь","name_en":"Limping Bear","emoji":"🐻",
     "desc":"<b>Хромает, но не сдаётся.</b>\n<b>За смену выносит столько, сколько другие за неделю.</b>",
     "desc_en":"<b>Limps but never gives up.</b>\n<b>Hauls in one shift what others do in a week.</b>",
     "price":1_800_000_000,"rarity":"Легендарный","rarity_en":"Legendary",
     "bonus":"<b>Удваивает добычу тяжёлых руд</b>","bonus_en":"<b>Doubles heavy ore yield</b>",
     "income_min":24_000_000,"income_max":50_000_000},
    {"key":"croc","name":"Крокодил Гена","name_en":"Croc Gena","emoji":"🐊",
     "desc":"<b>Пришёл из подземной реки в 1987 году.</b>\n<b>Никто не сказал уходить. Он остался.</b>",
     "desc_en":"<b>Came from an underground river in 1987.</b>\n<b>Nobody told him to leave. He stayed.</b>",
     "price":3_500_000_000,"rarity":"Легендарный","rarity_en":"Legendary",
     "bonus":"<b>Зубами дробит породу — открывает скрытые жилы</b>","bonus_en":"<b>Crushes rock with his teeth — reveals hidden veins</b>",
     "income_min":60_000_000,"income_max":90_000_000},
    {"key":"gnome","name":"Кристальный Гном","name_en":"Crystal Gnome","emoji":"💎",
     "desc":"<b>Соткан из чистого кристалла.</b>\n<b>Видит сквозь породу. Находит то, чего не существует.</b>",
     "desc_en":"<b>Woven from pure crystal.</b>\n<b>Sees through stone. Finds what doesn't exist.</b>",
     "price":15_000_000_000,"rarity":"Мифический","rarity_en":"Mythic",
     "bonus":"<b>Находит мифрил, уран и аметист</b>","bonus_en":"<b>Finds mithril, uranium and amethyst</b>",
     "income_min":150_000_000,"income_max":300_000_000},
]

PETS_BY_KEY = {p["key"]: p for p in PETS}

def _get_pet_page(pet_key):
    """Возвращает номер страницы для питомца (начиная с 0)."""
    for i, pet in enumerate(PETS):
        if pet["key"] == pet_key:
            return i // PAGE_SIZE
    return 0

def _n(eid, fb, name, text):
    return f'{_tg(eid, fb)} <b>{name}</b> <b>{text}</b>'

_NOTIFICATIONS = {
    "hamster": [
        _n("5208535779348864977","🐹","Шахтёр Хомяк","набил щёки рудой и не мог выбраться из тоннеля. Вытащили — принёс монетки!"),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","украл у крота лопату и теперь делает вид, что она всегда была его."),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","обнаружил, что за щеками умещается ровно 47 монет. Проверял весь день."),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","уснул прямо в забое. Проснулся — рядом лежала добыча. Откуда? Сам не помнит."),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","пожаловался, что кирка тяжёлая. Взял две — стало веселее."),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","нашёл монетку и спрятал на потом. Потом ещё. Итого — принёс всё тебе."),
        _n("5208535779348864977","🐹","Шахтёр Хомяк","устроил соревнование с собой. Победил. Деньги твои."),
    ],
    "toad": [
        _n("5845830268044185765","🐸","Болотный Жабакоп","нашёл медь и сказал, что она «недостаточно влажная». Всё равно принёс."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","утверждает, что чует монеты на 30 метров. Вернулся с добычей."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","прорыл тоннель к подземному озеру. По пути собрал всё ценное."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","провёл инспекцию шахты. Нашёл 3 нарушения и неплохую выручку."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","записал в журнал: «Сегодня добыто. Вчера тоже. Завтра больше»."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","нашёл залежь меди, пересчитал трижды — принёс честно."),
        _n("5845830268044185765","🐸","Болотный Жабакоп","потребовал повышения зарплаты. Пока ждёт ответа — работает."),
    ],
    "beaver": [
        _n("5352606295469871252","🦫","Бобёр Прораб","построил новый тоннель без чертежей. По пути нашёл деньги."),
        _n("5352606295469871252","🦫","Бобёр Прораб","укреплял потолок зубами. Слышно с поверхности. Монеты уже у тебя."),
        _n("5352606295469871252","🦫","Бобёр Прораб","написал план на 3 страницы как правильно зарабатывать. Потом заработал."),
        _n("5352606295469871252","🦫","Бобёр Прораб","нашёл золото, составил акт в двух экземплярах и всё равно принёс."),
        _n("5352606295469871252","🦫","Бобёр Прораб","расширил тоннель «немного» — обнаружил целый пласт добычи."),
        _n("5352606295469871252","🦫","Бобёр Прораб","провёл совещание с кротом. Итог: заработок выше, кофе тот же."),
        _n("5352606295469871252","🦫","Бобёр Прораб","нашёл железо и уже придумал как продать его подороже."),
    ],
    "mole": [
        _n("5427397704911177177","🦔","Крот на Энергетиках","выпил 6-ю банку и пробурил новый ярус. Там монеты."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","не спал 40 часов. «Деньги сами себя не найдут» — и нашёл."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","обогнал всех питомцев по скорости. И по заработку."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","нашёл золото в 3 часа ночи. Разбудил всех. Не жалеет."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","попросил ящик энергетиков. «Рабочие нужды». Работа идёт."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","уснул на секунду — проснулся с набитыми карманами."),
        _n("5427397704911177177","🦔","Крот на Энергетиках","прошёл 10 км по тоннелям. «Разминка». Ты считаешь прибыль."),
    ],
    "raccoon": [
        _n("5202166785230524217","🦝","Енот Мародёр","добыл дорогой алмаз. Долго думал, отдавать ли — всё же принёс монеты."),
        _n("5202166785230524217","🦝","Енот Мародёр","нашёл чужую кирку в тоннеле. Теперь у него две. Работает обеими."),
        _n("5202166785230524217","🦝","Енот Мародёр","провёл ревизию склада. Часть руды «перераспределилась» в твою копилку."),
        _n("5202166785230524217","🦝","Енот Мародёр","нашёл секретную жилу. Показывать не будет — но монеты принёс."),
        _n("5202166785230524217","🦝","Енот Мародёр","принёс золото. Откуда — не говорит. Лапы чистые, взгляд невинный."),
        _n("5202166785230524217","🦝","Енот Мародёр","стащил фонарь у хомяка. Нашёл больше. Все довольны."),
        _n("5202166785230524217","🦝","Енот Мародёр","нашёл клад и дождался «подходящего момента» — принёс."),
    ],
    "wolf": [
        _n("5296668976414203103","🐺","Волк Бригадир","провёл планёрку. Все присутствовали. Добровольно. Доход вырос."),
        _n("5296668976414203103","🐺","Волк Бригадир","приказал удвоить добычу. Удвоили. Никто не спорил."),
        _n("5296668976414203103","🐺","Волк Бригадир","нашёл золотую жилу и лично контролировал каждый удар кирки."),
        _n("5296668976414203103","🐺","Волк Бригадир","провёл ночную смену лично. Утром — рекорд заработка."),
        _n("5296668976414203103","🐺","Волк Бригадир","написал правила: «Пункт 1: Работать. Пункт 2: Смотри пункт 1». Работает."),
        _n("5296668976414203103","🐺","Волк Бригадир","разрешил перерыв на 10 минут. Первый за неделю. Все заработали."),
        _n("5296668976414203103","🐺","Волк Бригадир","проверил каждый тоннель лично. Нашёл что искал."),
    ],
    "lion": [
        _n("5375448597997316048","🦁","Лев Колека","говорит что «просто помогает». Помог на несколько миллионов."),
        _n("5375448597997316048","🦁","Лев Колека","нашёл аметист. Осмотрел. Конвертировал в монеты. Принёс."),
        _n("5375448597997316048","🦁","Лев Колека","«случайно» откопал редкую руду, пока точил когти о стену."),
        _n("5375448597997316048","🦁","Лев Колека","считает, что деньги сами его находят. Статистика подтверждает."),
        _n("5375448597997316048","🦁","Лев Колека","официально не работает. Но сегодня в казне стало заметно больше."),
        _n("5375448597997316048","🦁","Лев Колека","заглянул «на пять минут». Вышел через 6 часов с трофеями."),
        _n("5375448597997316048","🦁","Лев Колека","нашёл 3 скрытых жилы. «Я просто гулял», — говорит."),
    ],
    "bear": [
        _n("5206502842478638898","🐻","Хромой Медведь","хромает, но за смену заработал больше всех. И не устал."),
        _n("5206502842478638898","🐻","Хромой Медведь","уронил кирку в пропасть. Спустился. Принёс кирку и деньги."),
        _n("5206502842478638898","🐻","Хромой Медведь","говорит что нога не болит. Все делают вид что верят. Монеты настоящие."),
        _n("5206502842478638898","🐻","Хромой Медведь","нашёл золото левой лапой — правой держал мешок с ещё большим золотом."),
        _n("5206502842478638898","🐻","Хромой Медведь","прошёл 10 км по тоннелям. «Разминка». Принёс рекорд."),
        _n("5206502842478638898","🐻","Хромой Медведь","обнаружил жилу размером с дом. Разработал лично. Заработок твой."),
        _n("5206502842478638898","🐻","Хромой Медведь","доказал: хромота не помеха, если три лапы работают за четыре."),
    ],
    "croc": [
        _n("5217616693127293773","🐊","Крокодил Гена","укусил скалу. Скала извинилась и рассыпалась. Там было золото."),
        _n("5217616693127293773","🐊","Крокодил Гена","спал 20 часов. Оставшиеся 4 — добыл больше всех за смену. Деньги твои."),
        _n("5217616693127293773","🐊","Крокодил Гена","техника безопасности запрещает в шахте. Он не умеет читать. Работает исправно."),
        _n("5217616693127293773","🐊","Крокодил Гена","прораб пытался его уволить. Теперь прораб работает на Гену."),
        _n("5217616693127293773","🐊","Крокодил Гена","говорят, ест породу на завтрак. Никто не проверял. Все живы. Монеты настоящие."),
        _n("5217616693127293773","🐊","Крокодил Гена","новенький спросил зачем он здесь. Гена посмотрел. Новенький больше не спрашивает."),
        _n("5217616693127293773","🐊","Крокодил Гена","геологи нанесли его на карту как «опасный объект». Он нашёл там золото и был доволен."),
    ],
    "gnome": [
        _n("4945387415205315532","💎","Кристальный Гном","просветил породу взором. Нашёл то, чего нет ни на одной карте."),
        _n("4945387415205315532","💎","Кристальный Гном","прошептал заклинание — стена стала прозрачной. За ней был мифрил."),
        _n("4945387415205315532","💎","Кристальный Гном","сверкнул в темноте шахты. Все зажмурились. Открыли глаза — он уже с добычей."),
        _n("4945387415205315532","💎","Кристальный Гном","нашёл уран там, где по всем картам должен быть камень. Карты врут."),
        _n("4945387415205315532","💎","Кристальный Гном","говорит на языке кристаллов. Кристаллы рассказали, где прячется аметист."),
        _n("4945387415205315532","💎","Кристальный Гном","существует вне законов физики. Деньги, которые он приносит — вполне реальные."),
        _n("4945387415205315532","💎","Кристальный Гном","растворился в стене. Вернулся через час с горстью мифрила. Обычный вечер."),
    ],
}


def get_owned_pets(data):
    return data.get("owned_pets", [])

def has_pet(data, pet_key):
    return pet_key in get_owned_pets(data)

def buy_pet(data, pet_key, lang: str = "ru"):
    from lang import t
    if pet_key not in PETS_BY_KEY:
        return False, t(lang, "pet_not_found")
    if has_pet(data, pet_key):
        return False, t(lang, "pet_already_owned")
    pet = PETS_BY_KEY[pet_key]
    if data.get("balance", 0) < pet["price"]:
        return False, t(lang, "pet_no_coins").format(cost=f'{_fmt(pet["price"])} {_tg(_E["coin"], "💰")}')
    data["balance"] -= pet["price"]
    data.setdefault("owned_pets", []).append(pet_key)
    now = _now_ts()
    data.setdefault("pet_last_notify", {})[pet_key] = now
    data.setdefault("pet_last_income", {})[pet_key] = now
    return True, (
        f'{_tg(_E_OWNED, "✅")} <b>{t(lang, "pet_bought_title").format(name=pet["name"])}</b>\n\n'
        f'{_tg(_E["chest"], "🎒")} <b>{t(lang, "pet_bought_hint")}</b>\n'
        f'{_tg(_E["timer"], "⏱")} <b>{t(lang, "pet_bought_timer")}</b>'
    )

def get_pending_income(data):
    owned   = get_owned_pets(data)
    incomes = data.setdefault("pet_last_income", {})
    now     = _now_ts()
    # Множитель артефактов к добыче питомцов
    try:
        from shop import get_artifact_pets_multiplier
        art_mult = get_artifact_pets_multiplier(data)
    except Exception:
        art_mult = 1.0
    # Множитель статуса к добыче питомцов
    try:
        from status import get_status_multiplier as _status_pets_mult
        status_mult = _status_pets_mult(data)
    except Exception:
        status_mult = 1.0
    # Множитель реферального ивента (см. ivent.py) — глобальный бафф
    # дохода питомцев, если ивент активен и набран порог.
    try:
        from ivent import get_current_multiplier as _event_pets_mult
        event_mult = _event_pets_mult()
    except Exception:
        event_mult = 1.0
    result  = []
    for pk in owned:
        last = incomes.get(pk, now)
        if now - last >= PET_INCOME_INTERVAL:
            pet = PETS_BY_KEY.get(pk)
            if not pet:
                continue
            amount = int(random.randint(pet["income_min"], pet["income_max"]) * art_mult * status_mult * event_mult)
            result.append((pk, amount))
            incomes[pk] = now
    return result

def get_pending_notifications(data):
    owned   = get_owned_pets(data)
    notifs  = data.setdefault("pet_last_notify", {})
    incomes = data.get("pet_last_income", {})
    result  = []
    for pk in owned:
        if incomes.get(pk, 0) > notifs.get(pk, 0):
            msgs = _NOTIFICATIONS.get(pk, [])
            if msgs:
                result.append((pk, random.choice(msgs)))
                notifs[pk] = incomes.get(pk, 0)
    return result

def pet_income_text(pet_key, amount, notification, lang: str = "ru"):
    from lang import t
    return (
        f'<blockquote>{notification}</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg("5427168083074628963", "➡️")} <b>{t(lang, "pet_income_msg").format(amount=_fmt(amount))} {_tg(_E["coin"], "💰")}</b>'
        f'</blockquote>'
    )

# 10 уникальных случайных текстов для раздела питомцев
_PETS_MENU_TEXTS = [
    "Твои питомцы уже под землёй — копают, стараются, несут монеты.",
    "Каждый питомец — это шахтёр со своим характером. Некоторые даже с претензиями.",
    "Чем больше питомцев, тем больше шума в шахте. И монет тоже.",
    "Питомцы не спят. Питомцы работают. Особенно крот — он вообще не понимает что такое ночь.",
    "Говорят, хомяк нашёл золотую жилу и спрятал её за щекой. Проверить не удалось.",
    "Бобёр уже нарисовал план на следующую неделю. Гном его не читал, но добыл больше.",
    "Енот опять что-то нашёл. Откуда — молчит. Но монеты настоящие.",
    "Волк провёл планёрку. Все были. Добровольно. Почти.",
    "Крокодил Гена снова на смене. Он всегда на смене. Никто не проверял, уходил ли он вообще.",
    "Кристальный Гном видит сквозь породу. Что именно — не рассказывает. Монеты приносит исправно.",
]

def pets_main_text(data, lang: str = "ru"):
    from lang import t
    owned = get_owned_pets(data)
    count = len(owned)
    total = len(PETS)

    header = (
        f'<blockquote>'
        f'{_tg(_E["paw"], "🐾")} <b>{t(lang, "pets_title")}</b>\n'
        f'<b>{t(lang, "pets_count")}: {count} / {total}</b>'
        f'</blockquote>\n\n'
    )

    if not owned:
        pets_block = (
            f'<blockquote>'
            f'{_tg(_E["lock"], "🔒")} <b>{t(lang, "pets_none")}</b>\n'
            f'<b>{t(lang, "pets_none_hint")}</b>'
            f'</blockquote>\n\n'
        )
    else:
        pets_block = ""

    random_quote = random.choice(_PETS_MENU_TEXTS if lang == "ru" else _PETS_MENU_TEXTS_EN)
    footer = (
        f'<blockquote>'
        f'<tg-emoji emoji-id="5443038326535759644">🎟</tg-emoji> <b>{random_quote}</b>\n\n'
        f'{_tg(_E["alert"], "💡")} <b>{t(lang, "pets_notify_hint")}</b>'
        f'</blockquote>'
    )
    return header + pets_block + footer

def pets_main_keyboard(data, page=0, lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    builder   = InlineKeyboardBuilder()
    start     = page * PAGE_SIZE
    chunk     = PETS[start:start + PAGE_SIZE]

    for pet in chunk:
        pet_eid  = _PET_EMOJI.get(pet["key"], "")
        pet_name = pet.get("name_en", pet["name"]) if lang == "en" else pet["name"]
        if has_pet(data, pet["key"]):
            if pet_eid:
                builder.row(InlineKeyboardButton(
                    text=pet_name,
                    callback_data=f'pet_info_{pet["key"]}',
                    icon_custom_emoji_id=pet_eid,
                    style="success"
                ))
            else:
                builder.row(InlineKeyboardButton(
                    text=pet_name,
                    callback_data=f'pet_info_{pet["key"]}',
                    style="success"
                ))
        elif pet_eid:
            builder.row(InlineKeyboardButton(
                text=pet_name,
                callback_data=f'pet_info_{pet["key"]}',
                icon_custom_emoji_id=pet_eid
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=pet_name,
                callback_data=f'pet_info_{pet["key"]}'
            ))

    nav_btns = []
    if page > 0:
        nav_btns.append(InlineKeyboardButton(
            text="1", callback_data=f"pets_page_{page-1}",
            icon_custom_emoji_id="5255703720078879038"
        ))
    if start + PAGE_SIZE < len(PETS):
        nav_btns.append(InlineKeyboardButton(
            text="2", callback_data=f"pets_page_{page+1}",
            icon_custom_emoji_id="5253767677670862169"
        ))
    if nav_btns:
        builder.row(*nav_btns)

    builder.row(_back_btn("back_to_menu", t(lang, "btn_back")))
    return builder.as_markup()

def pet_detail_text(data, pet_key, lang: str = "ru"):
    from lang import t
    pet = PETS_BY_KEY.get(pet_key)
    if not pet:
        return f"<b>{t(lang, 'pet_not_found')}</b>"
    owned    = has_pet(data, pet_key)
    pet_eid  = _PET_EMOJI.get(pet_key, "")
    pet_icon = _tg(pet_eid, pet["emoji"]) if pet_eid else pet["emoji"]
    pet_name = pet.get("name_en", pet["name"]) if lang == "en" else pet["name"]
    pet_desc = pet.get("desc_en", pet["desc"]) if lang == "en" else pet["desc"]
    pet_bonus= pet.get("bonus_en", pet["bonus"]) if lang == "en" else pet["bonus"]
    pet_rar  = pet.get("rarity_en", pet["rarity"]) if lang == "en" else pet["rarity"]
    if owned:
        status = f'{_tg(_E_OWNED, "✅")} <b>{t(lang, "pet_owned")}</b>'
        diff   = _now_ts() - data.get("pet_last_income", {}).get(pet_key, 0)
        if diff >= PET_INCOME_INTERVAL:
            income_line = f'{_tg(_E["alert"], "💡")} <b>{t(lang, "pet_ready")}</b>'
        else:
            rem = PET_INCOME_INTERVAL - diff
            h, m = rem // 3600, (rem % 3600) // 60
            income_line = f'{_tg(_E["timer"], "⏱")} <b>{t(lang, "pet_next_payout")} {h}h {m}m</b>' if lang == "en" else f'{_tg(_E["timer"], "⏱")} <b>{t(lang, "pet_next_payout")} {h}ч {m}м</b>'
        timing_block = f'\n<blockquote>{income_line}</blockquote>'
    else:
        status       = f'{_tg(_E["lock"], "🔒")} <b>{t(lang, "pet_not_owned")}</b>'
        timing_block = ""
    return (
        f'<blockquote>'
        f'<b>{pet_icon} {pet_name}</b>\n'
        f'<b>{pet_rar}</b>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["arrow"], "➡️")} <b>{t(lang, "pet_feature")}</b> {pet_bonus}\n\n'
        f'{pet_desc}'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'{_tg(_E["income"], "💰")} <b>{t(lang, "pet_income_label")}</b>\n'
        f'<b>{_fmt(pet["income_min"])} — {_fmt(pet["income_max"])} {_tg(_E["coin"], "💰")}</b>\n\n'
        f'{_tg(_E["price"], "🏷️")} <b>{t(lang, "pet_price_label")} {_fmt(pet["price"])} {_tg(_E["coin"], "💰")}</b>\n'
        f'{status}'
        f'</blockquote>'
        f'{timing_block}'
    )

def pet_detail_keyboard(data, pet_key, page=None, lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    builder = InlineKeyboardBuilder()
    if page is None:
        page = _get_pet_page(pet_key)
    if not has_pet(data, pet_key):
        builder.button(
            text=t(lang, "pets_btn_buy"),
            callback_data=f"pet_buy_{pet_key}",
            icon_custom_emoji_id=_E["coin"]
        )
        builder.adjust(1)
    builder.row(_back_btn(f"pets_page_{page}", t(lang, "btn_back")))
    return builder.as_markup()
