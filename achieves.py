# ============================================================
#  achieves.py  —  Система достижений
#  50 достижений: деньги, уровень, шахта, охота на боссов,
#  арсенал (мечи), дуэли, кейсы/артефакты, питомцы, клан,
#  рефералы, донат, вклады, разное.
# ============================================================
#
#  КАК ПОДКЛЮЧИТЬ
#  ────────────────
#  1) from achieves import check_achievements, achievement_unlocked_text,
#         achievements_list_text, achievements_keyboard, achievements_summary_line
#
#  2) После ЛЮБОГО действия, которое может выполнить условие ачивки
#     (собрал добычу, ударил босса, выиграл дуэль, открыл кейс,
#     вступил в клан, внёс вклад и т.д.) — вызови ПЕРЕД save_user(...):
#
#         newly = check_achievements(u)
#         save_user(uid, u)
#         await notify_new_achievements(bot, uid, newly, lang)   # шлёт уведомление СРАЗУ
#
#     check_achievements() сама начисляет награды (монеты/опыт) в переданный
#     словарь data и возвращает список новых достижений — сохранять базу
#     после неё обязательно. notify_new_achievements() шлёт уведомление
#     мгновенно, в момент выполнения действия — а не когда игрок в следующий
#     раз откроет /достижения. Важно вызывать check_achievements() (и следом
#     notify_new_achievements()) буквально в каждом хендлере, где прогресс
#     мог продвинуться, иначе игрок узнает об ачивке с опозданием.
#
#  3) Готовый хендлер команды /достижения — см. пример в самом низу файла
#     (закомментирован, просто скопируй в mainhelp.py и поправь импорты).
#
#  ПОЛЯ, КОТОРЫЕ ИСПОЛЬЗУЕТ МОДУЛЬ
#  ────────────────────────────────
#  Уже существующие в проекте (проверено по вашим файлам) — работают из коробки:
#    balance, level, owned_pickaxes, owned_durations, owned_swords,
#    duel_wins, artifact_cases_opened, owned_pets, clan_id (из get_or_create_user)
#
#  ⛏ ШАХТА — уже подключена и работает из коробки. miner.py сам ведёт
#  счётчики за всю игру (не сбрасываются продажей/остановкой шахты):
#    mine_lifetime_campaigns, mine_sessions_completed, mine_early_stops,
#    mine_total_ore_collected, mine_total_sold, mine_lifetime_ore_counts
#  Ничего доинкрементировать не нужно — collect_mine/sell_all_ores/stop_mine
#  в miner.py уже обновляют эти поля сами.
#
#  НОВЫЕ счётчики, которых в data пока нет — модуль просто вернёт для них
#  прогресс 0/цель, пока вы не начнёте их инкрементировать в нужных местах
#  (по одной строке в нужном хендлере, ничего сложного):
#    stats_boss_hits, stats_boss_kills   — в hunt_strike после успешного удара
#    ref_count                            — в хендлере обработки /start c реф-ссылкой
#    clan_created                         — в хендлере создания клана (klan_create)
#    clan_treasury_deposited              — после успешного deposit_treasury(...)
#    is_vip / vip_until                   — в месте выдачи VIP/premium статуса
#    donate_purchases                     — после успешной оплаты доната
#    deposits_opened, deposits_claimed    — после _cdl_open_deposit / _cdl_claim
#    promo_activations                    — после успешного activate_promo(...)
#    daily_streak                         — уже может считаться в cmd_daily,
#                                            если нет — прибавляйте +1 при
#                                            получении бонуса без пропуска дня
#
#  Если какое-то поле у вас называется иначе — просто поправьте .get(...)
#  внутри нужного achievement'а ниже, структура одинаковая везде.
# ============================================================

import time as _time
import os as _os
import sqlite3 as _sqlite3

# ─── Счётчик "сколько игроков всего открыли эту ачивку" (глобальная, не пер-игрок) ───
# Собственная лёгкая sqlite-табличка внутри модуля — ничего в database.py трогать
# не нужно. Инкрементируется 1 раз на игрока прямо внутри check_achievements().

_ACH_DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "achievements_stats.db")


def init_achievements_db(db_path: str | None = None) -> None:
    """
    Создаёт таблицу счётчиков открытий ачивок, если её ещё нет.
    Вызовите один раз при старте бота (как init_stats_db() и т.п.):
        from achieves import init_achievements_db
        init_achievements_db()
    """
    global _ACH_DB_PATH
    if db_path:
        _ACH_DB_PATH = db_path
    conn = _sqlite3.connect(_ACH_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievement_unlock_counts (
            ach_id TEXT PRIMARY KEY,
            unlocked_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def _bump_achievement_count(ach_id: str) -> None:
    """+1 к счётчику 'сколько игроков открыли эту ачивку'. Вызывается из check_achievements."""
    try:
        conn = _sqlite3.connect(_ACH_DB_PATH)
        conn.execute(
            "INSERT INTO achievement_unlock_counts (ach_id, unlocked_count) VALUES (?, 1) "
            "ON CONFLICT(ach_id) DO UPDATE SET unlocked_count = unlocked_count + 1",
            (ach_id,),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_achievement_unlock_count(ach_id: str) -> int:
    """Сколько игроков всего открыли эту ачивку — используется в карточке достижения."""
    try:
        conn = _sqlite3.connect(_ACH_DB_PATH)
        row = conn.execute(
            "SELECT unlocked_count FROM achievement_unlock_counts WHERE ach_id = ?", (ach_id,)
        ).fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def backfill_achievement_counts(all_users_data) -> None:
    """
    Разовая миграция: пересчитывает счётчики с нуля по уже существующим игрокам —
    полезно один раз после подключения этой версии модуля, чтобы счётчики не
    начинались с нуля для тех, кто уже давно открыл ачивки. Передайте туда
    database.get_all_users():

        from achieves import backfill_achievement_counts
        from database import get_all_users
        backfill_achievement_counts(get_all_users())

    Дальше счётчики сами растут через check_achievements() — вызывать повторно
    не нужно (но и не страшно, просто пересчитает заново с тем же результатом).
    """
    from collections import Counter
    counts = Counter()
    for u in all_users_data:
        for ach_id in (u.get("achievements_unlocked") or []):
            counts[ach_id] += 1
    try:
        conn = _sqlite3.connect(_ACH_DB_PATH)
        for ach_id, cnt in counts.items():
            conn.execute(
                "INSERT INTO achievement_unlock_counts (ach_id, unlocked_count) VALUES (?, ?) "
                "ON CONFLICT(ach_id) DO UPDATE SET unlocked_count = ?",
                (ach_id, cnt, cnt),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─── Безопасные лениво-импортируемые константы (чтобы не ловить циклический импорт) ───

def _swords_total() -> int:
    try:
        from hunt import SWORDS
        return len(SWORDS)
    except Exception:
        return 25  # запасное значение, поправьте если поменяли список мечей


def _pickaxes_total() -> int:
    try:
        from miner import PICKAXES
        return len(PICKAXES)
    except Exception:
        return 6  # запасное значение — поправьте под свой список кирок


def _durations_total() -> int:
    try:
        from miner import DURATIONS_ORDER
        return len(DURATIONS_ORDER)
    except Exception:
        return 10  # запасное значение — поправьте под свой список длительностей


def _pets_total() -> int:
    try:
        from pets import PETS
        return len(PETS)
    except Exception:
        return 10  # запасное значение — поправьте под свой список питомцев


def _max_level() -> int:
    try:
        from miner import MAX_LEVEL
        return MAX_LEVEL
    except Exception:
        return 100


# ─── Вспомогательный конструктор ───

def _ach(id_, emoji, name, desc, category, check, progress=None,
         reward_coins=0, reward_xp=0,
         name_en=None, desc_en=None):
    return {
        "id": id_,
        "emoji": emoji,
        "name": name,
        "name_en": name_en or name,
        "desc": desc,
        "desc_en": desc_en or desc,
        "category": category,
        "check": check,          # data -> bool
        "progress": progress,    # data -> (current, target) | None
        "reward_coins": reward_coins,
        "reward_xp": reward_xp,
    }


# ─── Категории (для группировки в списке) ───

CATEGORIES = {
    "money":   {"emoji": "💰", "name": "Богатство",     "name_en": "Wealth"},
    "level":   {"emoji": "⭐", "name": "Прогресс",       "name_en": "Progress"},
    "mine":    {"emoji": "⛏",  "name": "Шахта",          "name_en": "Mining"},
    "hunt":    {"emoji": "⚔️", "name": "Охота",          "name_en": "Hunt"},
    "arsenal": {"emoji": "🗡",  "name": "Арсенал",        "name_en": "Arsenal"},
    "duel":    {"emoji": "🤺", "name": "Дуэли",          "name_en": "Duels"},
    "cases":   {"emoji": "🎁", "name": "Кейсы",          "name_en": "Cases"},
    "pets":    {"emoji": "🐾", "name": "Питомцы",        "name_en": "Pets"},
    "clan":    {"emoji": "🏰", "name": "Клан",           "name_en": "Clan"},
    "refs":    {"emoji": "👥", "name": "Рефералы",       "name_en": "Referrals"},
    "donate":  {"emoji": "💎", "name": "Донат",          "name_en": "Donate"},
    "deposit": {"emoji": "🏦", "name": "Вклады",         "name_en": "Deposits"},
    "misc":    {"emoji": "🎯", "name": "Разное",         "name_en": "Misc"},
}


# ============================================================
#  СПИСОК ДОСТИЖЕНИЙ (50 шт.)
# ============================================================

ACHIEVEMENTS = [

    # ───────────── 💰 ДЕНЬГИ (5) ─────────────
    _ach("money_100k", "🪙", "Стартовый капитал",
         "Накопи 100 000 монет",
         "money",
         lambda d: d.get("balance", 0) >= 100_000,
         progress=lambda d: (d.get("balance", 0), 100_000),
         reward_coins=10_000, reward_xp=50,
         name_en="Starting Capital", desc_en="Save up 100,000 coins"),

    _ach("money_1m", "💵", "Миллионер",
         "Накопи 1 000 000 монет",
         "money",
         lambda d: d.get("balance", 0) >= 1_000_000,
         progress=lambda d: (d.get("balance", 0), 1_000_000),
         reward_coins=100_000, reward_xp=150,
         name_en="Millionaire", desc_en="Save up 1,000,000 coins"),

    _ach("money_50m", "🏦", "Магнат",
         "Накопи 50 000 000 монет",
         "money",
         lambda d: d.get("balance", 0) >= 50_000_000,
         progress=lambda d: (d.get("balance", 0), 50_000_000),
         reward_coins=2_500_000, reward_xp=400,
         name_en="Tycoon", desc_en="Save up 50,000,000 coins"),

    _ach("money_1b", "👑", "Олигарх",
         "Накопи 1 000 000 000 монет",
         "money",
         lambda d: d.get("balance", 0) >= 1_000_000_000,
         progress=lambda d: (d.get("balance", 0), 1_000_000_000),
         reward_coins=50_000_000, reward_xp=1000,
         name_en="Oligarch", desc_en="Save up 1,000,000,000 coins"),

    _ach("money_25b", "🌌", "Повелитель Богатства",
         "Накопи 25 000 000 000 монет",
         "money",
         lambda d: d.get("balance", 0) >= 25_000_000_000,
         progress=lambda d: (d.get("balance", 0), 25_000_000_000),
         reward_coins=1_000_000_000, reward_xp=3000,
         name_en="Lord of Wealth", desc_en="Save up 25,000,000,000 coins"),

    # ───────────── ⭐ УРОВЕНЬ (5) ─────────────
    _ach("level_10", "🔹", "Уверенный старт",
         "Достигни 10 уровня",
         "level",
         lambda d: d.get("level", 1) >= 10,
         progress=lambda d: (d.get("level", 1), 10),
         reward_coins=5_000, reward_xp=0),

    _ach("level_25", "🔷", "Опытный игрок",
         "Достигни 25 уровня",
         "level",
         lambda d: d.get("level", 1) >= 25,
         progress=lambda d: (d.get("level", 1), 25),
         reward_coins=25_000, reward_xp=0),

    _ach("level_50", "💠", "Ветеран",
         "Достигни 50 уровня",
         "level",
         lambda d: d.get("level", 1) >= 50,
         progress=lambda d: (d.get("level", 1), 50),
         reward_coins=100_000, reward_xp=0),

    _ach("level_75", "🔶", "Легенда",
         "Достигни 75 уровня",
         "level",
         lambda d: d.get("level", 1) >= 75,
         progress=lambda d: (d.get("level", 1), 75),
         reward_coins=500_000, reward_xp=0),

    _ach("level_max", "🏵", "Живая легенда",
         "Достигни максимального уровня",
         "level",
         lambda d: d.get("level", 1) >= _max_level(),
         progress=lambda d: (d.get("level", 1), _max_level()),
         reward_coins=2_000_000, reward_xp=0),

    # ───────────── ⛏ ШАХТА (25) ─────────────

    # — Прогресс: количество завершённых экспедиций за всю игру —
    _ach("mine_1", "⛏", "Первая вылазка",
         "Заверши первую экспедицию в шахту",
         "mine",
         lambda d: d.get("mine_lifetime_campaigns", 0) >= 1,
         progress=lambda d: (d.get("mine_lifetime_campaigns", 0), 1),
         reward_coins=1_000, reward_xp=10),

    _ach("mine_10", "🪨", "Трудяга",
         "Заверши 10 экспедиций в шахту",
         "mine",
         lambda d: d.get("mine_lifetime_campaigns", 0) >= 10,
         progress=lambda d: (d.get("mine_lifetime_campaigns", 0), 10),
         reward_coins=5_000, reward_xp=30),

    _ach("mine_100", "⚒️", "Шахтёр по призванию",
         "Заверши 100 экспедиций в шахту",
         "mine",
         lambda d: d.get("mine_lifetime_campaigns", 0) >= 100,
         progress=lambda d: (d.get("mine_lifetime_campaigns", 0), 100),
         reward_coins=50_000, reward_xp=150),

    _ach("mine_500", "🏔", "Король забоя",
         "Заверши 500 экспедиций в шахту",
         "mine",
         lambda d: d.get("mine_lifetime_campaigns", 0) >= 500,
         progress=lambda d: (d.get("mine_lifetime_campaigns", 0), 500),
         reward_coins=300_000, reward_xp=500),

    _ach("mine_2500", "🕳", "Легенда подземелья",
         "Заверши 2 500 экспедиций в шахту",
         "mine",
         lambda d: d.get("mine_lifetime_campaigns", 0) >= 2_500,
         progress=lambda d: (d.get("mine_lifetime_campaigns", 0), 2_500),
         reward_coins=2_000_000, reward_xp=1500),

    # — Снаряжение —
    _ach("mine_all_pickaxes", "🧰", "Полный арсенал кирок",
         "Приобрети все кирки",
         "mine",
         lambda d: len(d.get("owned_pickaxes", [])) >= _pickaxes_total(),
         progress=lambda d: (len(d.get("owned_pickaxes", [])), _pickaxes_total()),
         reward_coins=150_000, reward_xp=200),

    _ach("mine_netherite_pickaxe", "⬛", "Кирка из преисподней",
         "Приобрети кирку тира Netherite",
         "mine",
         lambda d: any(str(k).startswith("netherite") for k in d.get("owned_pickaxes", [])),
         reward_coins=1_000_000, reward_xp=600),

    # — Сессии и длительность —
    _ach("mine_all_durations", "⏱", "Хронометрист",
         "Открой все варианты длительности экспедиции",
         "mine",
         lambda d: len(d.get("owned_durations", [])) >= _durations_total(),
         progress=lambda d: (len(d.get("owned_durations", [])), _durations_total()),
         reward_coins=200_000, reward_xp=250),

    _ach("mine_sessions_10", "📦", "Марафонец",
         "Полностью заверши 10 сессий шахты",
         "mine",
         lambda d: d.get("mine_sessions_completed", 0) >= 10,
         progress=lambda d: (d.get("mine_sessions_completed", 0), 10),
         reward_coins=20_000, reward_xp=80),

    _ach("mine_sessions_50", "🌙", "Бессонная смена",
         "Полностью заверши 50 сессий шахты",
         "mine",
         lambda d: d.get("mine_sessions_completed", 0) >= 50,
         progress=lambda d: (d.get("mine_sessions_completed", 0), 50),
         reward_coins=250_000, reward_xp=400),

    _ach("mine_early_stop", "⏹", "Нетерпеливый",
         "Останови экспедицию досрочно",
         "mine",
         lambda d: d.get("mine_early_stops", 0) >= 1,
         progress=lambda d: (d.get("mine_early_stops", 0), 1),
         reward_coins=2_000, reward_xp=15),

    # — Объёмы добычи —
    _ach("mine_ore_1000", "🪵", "Добытчик",
         "Добудь 1 000 единиц руды за всю игру",
         "mine",
         lambda d: d.get("mine_total_ore_collected", 0) >= 1_000,
         progress=lambda d: (d.get("mine_total_ore_collected", 0), 1_000),
         reward_coins=10_000, reward_xp=50),

    _ach("mine_ore_100000", "📦", "Оптовик",
         "Добудь 100 000 единиц руды за всю игру",
         "mine",
         lambda d: d.get("mine_total_ore_collected", 0) >= 100_000,
         progress=lambda d: (d.get("mine_total_ore_collected", 0), 100_000),
         reward_coins=100_000, reward_xp=250),

    _ach("mine_ore_1000000", "🏭", "Промышленник",
         "Добудь 1 000 000 единиц руды за всю игру",
         "mine",
         lambda d: d.get("mine_total_ore_collected", 0) >= 1_000_000,
         progress=lambda d: (d.get("mine_total_ore_collected", 0), 1_000_000),
         reward_coins=1_500_000, reward_xp=1000),

    # — Редкие находки (первая добыча руды каждого ценного вида) —
    _ach("mine_first_iron", "⚙️", "Первое железо",
         "Добудь железо впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("iron", 0) >= 1,
         reward_coins=3_000, reward_xp=15),

    _ach("mine_first_silver", "🩶", "Серебряная жила",
         "Добудь серебро впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("silver", 0) >= 1,
         reward_coins=5_000, reward_xp=20),

    _ach("mine_first_diamond", "💎", "Первый алмаз",
         "Добудь алмаз впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("diamond", 0) >= 1,
         reward_coins=30_000, reward_xp=60),

    _ach("mine_first_mithril", "🔮", "Мифриловая жила",
         "Добудь мифрил впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("mithril", 0) >= 1,
         reward_coins=100_000, reward_xp=120),

    _ach("mine_first_uranium", "☢️", "Радиоактивная находка",
         "Добудь уран впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("uranium", 0) >= 1,
         reward_coins=200_000, reward_xp=180),

    _ach("mine_first_amethyst", "💜", "Фиолетовый блеск",
         "Добудь аметист впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("amethyst", 0) >= 1,
         reward_coins=350_000, reward_xp=250),

    _ach("mine_first_jade", "🟢", "Нефритовый секрет",
         "Добудь нефрит впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("jade", 0) >= 1,
         reward_coins=600_000, reward_xp=350),

    _ach("mine_first_emerald", "🌿", "Изумрудная жила",
         "Добудь изумруд впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("emerald", 0) >= 1,
         reward_coins=900_000, reward_xp=450),

    _ach("mine_first_obsidian", "💀", "Чёрное стекло",
         "Добудь обсидиан впервые",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("obsidian", 0) >= 1,
         reward_coins=1_200_000, reward_xp=550),

    _ach("mine_first_sapphire", "🔷", "Сапфировая мечта",
         "Добудь сапфир впервые — самую редкую руду в игре",
         "mine",
         lambda d: d.get("mine_lifetime_ore_counts", {}).get("sapphire", 0) >= 1,
         reward_coins=2_000_000, reward_xp=800),

    # — Экономика шахты —
    _ach("mine_sold_100m", "🏦", "Шахтный магнат",
         "Выручи в сумме 100 000 000 монет с продажи руды",
         "mine",
         lambda d: d.get("mine_total_sold", 0) >= 100_000_000,
         progress=lambda d: (d.get("mine_total_sold", 0), 100_000_000),
         reward_coins=5_000_000, reward_xp=700),

    # ───────────── ⚔️ ОХОТА НА БОССОВ (6) ─────────────
    _ach("hunt_first_hit", "🗡", "Первая кровь",
         "Нанеси первый удар боссу",
         "hunt",
         lambda d: d.get("stats_boss_hits", 0) >= 1,
         progress=lambda d: (d.get("stats_boss_hits", 0), 1),
         reward_coins=1_000, reward_xp=10),

    _ach("hunt_first_kill", "💀", "Охотник",
         "Убей своего первого босса",
         "hunt",
         lambda d: d.get("stats_boss_kills", 0) >= 1,
         progress=lambda d: (d.get("stats_boss_kills", 0), 1),
         reward_coins=10_000, reward_xp=50),

    _ach("hunt_kills_10", "⚔️", "Опытный охотник",
         "Убей 10 боссов",
         "hunt",
         lambda d: d.get("stats_boss_kills", 0) >= 10,
         progress=lambda d: (d.get("stats_boss_kills", 0), 10),
         reward_coins=50_000, reward_xp=150),

    _ach("hunt_kills_100", "☠️", "Гроза боссов",
         "Убей 100 боссов",
         "hunt",
         lambda d: d.get("stats_boss_kills", 0) >= 100,
         progress=lambda d: (d.get("stats_boss_kills", 0), 100),
         reward_coins=500_000, reward_xp=600),

    _ach("hunt_first_sword", "🗡", "Вооружён",
         "Купи свой первый меч",
         "hunt",
         lambda d: len(d.get("owned_swords", [])) >= 1,
         progress=lambda d: (len(d.get("owned_swords", [])), 1),
         reward_coins=2_000, reward_xp=20),

    _ach("hunt_all_swords", "🏆", "Коллекционер клинков",
         "Собери все мечи в арсенале",
         "hunt",
         lambda d: len(d.get("owned_swords", [])) >= _swords_total(),
         progress=lambda d: (len(d.get("owned_swords", [])), _swords_total()),
         reward_coins=5_000_000, reward_xp=1000),

    # ───────────── 🗡 АРСЕНАЛ: подарки/аренда (3) ─────────────
    _ach("arsenal_gift", "🎁", "Щедрая рука",
         "Подари или передай меч другому игроку",
         "arsenal",
         lambda d: d.get("stats_swords_gifted", 0) >= 1,
         progress=lambda d: (d.get("stats_swords_gifted", 0), 1),
         reward_coins=5_000, reward_xp=25),

    _ach("arsenal_rent_out", "📤", "Арендодатель",
         "Сдай меч в аренду другому игроку",
         "arsenal",
         lambda d: d.get("stats_swords_rented_out", 0) >= 1,
         progress=lambda d: (d.get("stats_swords_rented_out", 0), 1),
         reward_coins=5_000, reward_xp=25),

    _ach("arsenal_rent_in", "📥", "Арендатор",
         "Возьми меч в аренду у другого игрока",
         "arsenal",
         lambda d: d.get("stats_swords_rented_in", 0) >= 1,
         progress=lambda d: (d.get("stats_swords_rented_in", 0), 1),
         reward_coins=5_000, reward_xp=25),

    # ───────────── 🤺 ДУЭЛИ (4) ─────────────
    _ach("duel_first_win", "🥇", "Первая победа",
         "Выиграй свою первую дуэль",
         "duel",
         lambda d: d.get("duel_wins", 0) >= 1,
         progress=lambda d: (d.get("duel_wins", 0), 1),
         reward_coins=5_000, reward_xp=30),

    _ach("duel_wins_10", "🤺", "Дуэлянт",
         "Выиграй 10 дуэлей",
         "duel",
         lambda d: d.get("duel_wins", 0) >= 10,
         progress=lambda d: (d.get("duel_wins", 0), 10),
         reward_coins=25_000, reward_xp=100),

    _ach("duel_wins_50", "🗡️", "Мастер клинка",
         "Выиграй 50 дуэлей",
         "duel",
         lambda d: d.get("duel_wins", 0) >= 50,
         progress=lambda d: (d.get("duel_wins", 0), 50),
         reward_coins=150_000, reward_xp=350),

    _ach("duel_wins_100", "👊", "Непобедимый",
         "Выиграй 100 дуэлей",
         "duel",
         lambda d: d.get("duel_wins", 0) >= 100,
         progress=lambda d: (d.get("duel_wins", 0), 100),
         reward_coins=500_000, reward_xp=800),

    # ───────────── 🎁 КЕЙСЫ / АРТЕФАКТЫ (3) ─────────────
    _ach("cases_first", "📦", "Искатель удачи",
         "Открой свой первый кейс артефактов",
         "cases",
         lambda d: d.get("artifact_cases_opened", 0) >= 1,
         progress=lambda d: (d.get("artifact_cases_opened", 0), 1),
         reward_coins=3_000, reward_xp=20),

    _ach("cases_25", "🎰", "Азартный игрок",
         "Открой 25 кейсов артефактов",
         "cases",
         lambda d: d.get("artifact_cases_opened", 0) >= 25,
         progress=lambda d: (d.get("artifact_cases_opened", 0), 25),
         reward_coins=50_000, reward_xp=150),

    _ach("cases_collection", "🏺", "Коллекционер артефактов",
         "Собери 10 разных артефактов",
         "cases",
         lambda d: len(d.get("owned_artifacts", [])) >= 10,
         progress=lambda d: (len(d.get("owned_artifacts", [])), 10),
         reward_coins=300_000, reward_xp=400),

    # ───────────── 🐾 ПИТОМЦЫ (3) ─────────────
    _ach("pets_first", "🐣", "Друг найден",
         "Получи своего первого питомца",
         "pets",
         lambda d: len(d.get("owned_pets", [])) >= 1,
         progress=lambda d: (len(d.get("owned_pets", [])), 1),
         reward_coins=3_000, reward_xp=20),

    _ach("pets_5", "🐾", "Зоопарк",
         "Собери 5 разных питомцев",
         "pets",
         lambda d: len(d.get("owned_pets", [])) >= 5,
         progress=lambda d: (len(d.get("owned_pets", [])), 5),
         reward_coins=40_000, reward_xp=120),

    _ach("pets_all", "🦄", "Повелитель зверей",
         "Собери всех питомцев",
         "pets",
         lambda d: len(d.get("owned_pets", [])) >= _pets_total(),
         progress=lambda d: (len(d.get("owned_pets", [])), _pets_total()),
         reward_coins=1_000_000, reward_xp=500),

    # ───────────── 🏰 КЛАН (4) ─────────────
    _ach("clan_join", "🤝", "Часть команды",
         "Вступи в клан",
         "clan",
         lambda d: bool(d.get("clan_id")),
         reward_coins=5_000, reward_xp=30),

    _ach("clan_create", "🏰", "Основатель",
         "Создай собственный клан",
         "clan",
         lambda d: bool(d.get("clan_created")),
         reward_coins=20_000, reward_xp=80),

    _ach("clan_treasury", "💰", "Меценат",
         "Внеси монеты в казну клана",
         "clan",
         lambda d: d.get("clan_treasury_deposited", 0) >= 1,
         progress=lambda d: (d.get("clan_treasury_deposited", 0), 1),
         reward_coins=5_000, reward_xp=25),

    _ach("clan_boss_damage", "🛡", "Клановый воин",
         "Нанеси урон клановому боссу",
         "clan",
         lambda d: d.get("clan_boss_damage_total", 0) >= 1,
         progress=lambda d: (d.get("clan_boss_damage_total", 0), 1),
         reward_coins=10_000, reward_xp=50),

    # ───────────── 👥 РЕФЕРАЛЫ (4) ─────────────
    _ach("refs_1", "👤", "Пригласил друга",
         "Пригласи 1 реферала",
         "refs",
         lambda d: d.get("ref_count", 0) >= 1,
         progress=lambda d: (d.get("ref_count", 0), 1),
         reward_coins=5_000, reward_xp=30),

    _ach("refs_5", "👥", "Рекрутер",
         "Пригласи 5 рефералов",
         "refs",
         lambda d: d.get("ref_count", 0) >= 5,
         progress=lambda d: (d.get("ref_count", 0), 5),
         reward_coins=25_000, reward_xp=100),

    _ach("refs_25", "📣", "Посол",
         "Пригласи 25 рефералов",
         "refs",
         lambda d: d.get("ref_count", 0) >= 25,
         progress=lambda d: (d.get("ref_count", 0), 25),
         reward_coins=150_000, reward_xp=300),

    _ach("refs_100", "🌍", "Легенда рефералки",
         "Пригласи 100 рефералов",
         "refs",
         lambda d: d.get("ref_count", 0) >= 100,
         progress=lambda d: (d.get("ref_count", 0), 100),
         reward_coins=1_000_000, reward_xp=800),

    # ───────────── 💎 ДОНАТ (2) ─────────────
    _ach("donate_first", "💎", "Спонсор",
         "Соверши первую покупку доната",
         "donate",
         lambda d: d.get("donate_purchases", 0) >= 1,
         progress=lambda d: (d.get("donate_purchases", 0), 1),
         reward_coins=20_000, reward_xp=50),

    _ach("donate_vip", "👑", "Элита",
         "Получи VIP-статус",
         "donate",
         lambda d: bool(d.get("is_vip")) or d.get("vip_until", 0) > int(_time.time()),
         reward_coins=50_000, reward_xp=100),

    # ───────────── 🏦 ВКЛАДЫ (2) ─────────────
    _ach("deposit_first_open", "🏦", "Инвестор",
         "Открой свой первый вклад",
         "deposit",
         lambda d: d.get("deposits_opened", 0) >= 1,
         progress=lambda d: (d.get("deposits_opened", 0), 1),
         reward_coins=5_000, reward_xp=25),

    _ach("deposit_first_claim", "💹", "Терпеливый капиталист",
         "Забери созревший вклад",
         "deposit",
         lambda d: d.get("deposits_claimed", 0) >= 1,
         progress=lambda d: (d.get("deposits_claimed", 0), 1),
         reward_coins=10_000, reward_xp=40),

    # ───────────── 🎯 РАЗНОЕ (4) ─────────────
    _ach("misc_onboarded", "🚪", "Добро пожаловать",
         "Пройди обучение и начни игру",
         "misc",
         lambda d: bool(d.get("onboarded")),
         reward_coins=500, reward_xp=5),

    _ach("misc_promo", "🎟", "Охотник за скидками",
         "Активируй промокод",
         "misc",
         lambda d: d.get("promo_activations", 0) >= 1,
         progress=lambda d: (d.get("promo_activations", 0), 1),
         reward_coins=1_000, reward_xp=10),

    _ach("misc_daily_7", "📅", "Верный игрок",
         "Забирай ежедневный бонус 7 дней подряд",
         "misc",
         lambda d: d.get("daily_streak", 0) >= 7,
         progress=lambda d: (d.get("daily_streak", 0), 7),
         reward_coins=15_000, reward_xp=60),

    _ach("misc_leaderboard_top10", "🏅", "Топ игрок",
         "Войди в топ-10 таблицы лидеров",
         "misc",
         lambda d: bool(d.get("was_in_top10")),
         reward_coins=200_000, reward_xp=300),
]

assert len(ACHIEVEMENTS) == 70, f"Ожидалось 70 достижений, а получилось {len(ACHIEVEMENTS)}"

ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


# ============================================================
#  ЛОГИКА
# ============================================================

def check_achievements(data: dict) -> list[dict]:
    """
    Проверяет ВСЕ ещё не открытые достижения игрока.
    При выполнении условия: добавляет id в data["achievements_unlocked"],
    начисляет reward_coins/reward_xp прямо в data и возвращает список
    только что открытых достижений (dict'ов из ACHIEVEMENTS).

    Вызывать после любого действия, способного продвинуть прогресс,
    ПЕРЕД save_user(...).
    """
    unlocked = data.setdefault("achievements_unlocked", [])
    unlocked_set = set(unlocked)
    newly = []

    for ach in ACHIEVEMENTS:
        if ach["id"] in unlocked_set:
            continue
        try:
            done = bool(ach["check"](data))
        except Exception:
            done = False
        if not done:
            continue

        unlocked.append(ach["id"])
        unlocked_set.add(ach["id"])
        _bump_achievement_count(ach["id"])

        if ach["reward_coins"]:
            data["balance"] = data.get("balance", 0) + ach["reward_coins"]
        if ach["reward_xp"]:
            data["xp"] = data.get("xp", 0) + ach["reward_xp"]

        newly.append(ach)

    return newly


async def notify_new_achievements(bot, user_id: int, newly: list[dict], lang: str = "ru") -> None:
    """
    Отправляет уведомление о каждом только что открытом достижении СРАЗУ —
    в момент выполнения действия, а не при следующем открытии /достижения.

    Вызывайте сразу после check_achievements(...) в ЛЮБОМ хендлере, где
    мог продвинуться прогресс (после сбора шахты, победы в дуэли,
    открытия кейса и т.д.):

        newly = check_achievements(u)
        save_user(uid, u)
        await notify_new_achievements(bot, uid, newly, lang)

    Ошибки отправки (например, если бот заблокирован) молча игнорируются,
    чтобы одно упавшее уведомление не ломало остальную логику хендлера.
    """
    for ach in newly:
        try:
            await bot.send_message(user_id, achievement_unlocked_text(ach, lang), parse_mode="HTML")
        except Exception:
            pass


def get_progress(data: dict, ach: dict) -> tuple[int, int] | None:
    """Текущий прогресс/цель для достижения, если оно числовое. Иначе None."""
    if not ach.get("progress"):
        return None
    try:
        cur, target = ach["progress"](data)
        return int(cur), int(target)
    except Exception:
        return None


def _progress_bar(cur: int, target: int, length: int = 10) -> str:
    if target <= 0:
        return ""
    pct = max(0.0, min(1.0, cur / target))
    filled = int(round(pct * length))
    return "▰" * filled + "▱" * (length - filled)


def _fmt_num(n: int) -> str:
    """1234567 -> '1 234 567' — единый формат чисел во всех текстах модуля."""
    return f"{n:,}".replace(",", " ")


def _fmt_reward(ach: dict, lang: str = "ru") -> str:
    """Собирает строку награды вида '+10 000 монет · +50 XP' (или пусто, если награды нет)."""
    parts = []
    if ach["reward_coins"]:
        parts.append(f'+{_fmt_num(ach["reward_coins"])} {"монет" if lang == "ru" else "coins"}')
    if ach["reward_xp"]:
        parts.append(f'+{ach["reward_xp"]} {"опыта" if lang == "ru" else "XP"}')
    return " · ".join(parts)


# ============================================================
#  ТЕКСТЫ / UI
# ============================================================

def achievement_unlocked_text(ach: dict, lang: str = "ru") -> str:
    name = ach["name_en"] if lang == "en" else ach["name"]
    desc = ach["desc_en"] if lang == "en" else ach["desc"]
    reward_str = _fmt_reward(ach, lang)

    title = "Новое достижение" if lang == "ru" else "New achievement"
    lines = [
        f'🏆 <b>{title}:</b> {ach["emoji"]} <b>{name}</b>',
        f'<i>{desc}</i>',
    ]
    if reward_str:
        lines.append(f'🎁 {reward_str}')
    return "\n".join(lines)


DEFAULT_CATEGORY = "money"  # раздел, который показывается первым при входе в него
PAGE_SIZE = 1                 # 1 достижение = 1 страница — подробная карточка на каждую ачивку


def achievements_summary_line(data: dict, lang: str = "ru") -> str:
    unlocked = len(data.get("achievements_unlocked", []))
    total = len(ACHIEVEMENTS)
    pct = round(100 * unlocked / total) if total else 0
    bar = _progress_bar(unlocked, total, length=12)
    if lang == "en":
        return f'🏆 <b>Achievements</b>\n<b>{unlocked}/{total}</b> unlocked  <i>({pct}%)</i>\n{bar}'
    return f'🏆 <b>Достижения</b>\n<b>{unlocked}/{total}</b> открыто  <i>({pct}%)</i>\n{bar}'


def _category_items(category: str) -> list[dict]:
    if category == "all":
        return list(ACHIEVEMENTS)
    return [a for a in ACHIEVEMENTS if a["category"] == category]


def category_page_count(category: str) -> int:
    """Сколько страниц выходит для раздела (при PAGE_SIZE=1 — это просто число ачивок в разделе)."""
    total = len(_category_items(category))
    return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)


def achievements_list_text(data: dict, lang: str = "ru", category: str | None = None, page: int = 0) -> str:
    """
    Текст ОДНОЙ карточки достижения (уровень 1) — подробная информация:
    статус, описание, прогресс, награда и сколько игроков всего открыли эту
    ачивку. Листается по одной штуке за раз (см. achievements_keyboard).

    По умолчанию (category не передана) берётся DEFAULT_CATEGORY. Выполненные
    достижения всегда идут первыми внутри раздела.
    """
    if category is None:
        category = DEFAULT_CATEGORY

    unlocked_set = set(data.get("achievements_unlocked", []))
    items = _category_items(category)
    if not items:
        return achievements_summary_line(data, lang)

    items_sorted = sorted(items, key=lambda a: a["id"] not in unlocked_set)
    total_pages = category_page_count(category)
    page = max(0, min(page, total_pages - 1))
    ach = items_sorted[page]

    cat_info = CATEGORIES.get(category)
    cat_done = sum(1 for a in items if a["id"] in unlocked_set)
    cat_name = cat_info["name_en"] if (cat_info and lang == "en") else (cat_info["name"] if cat_info else ("All" if lang == "en" else "Все разделы"))
    cat_emoji = cat_info["emoji"] if cat_info else "🗂"

    done = ach["id"] in unlocked_set
    name = ach["name_en"] if lang == "en" else ach["name"]
    desc = ach["desc_en"] if lang == "en" else ach["desc"]
    status_lbl = ("Выполнено" if lang == "ru" else "Unlocked") if done else ("Не выполнено" if lang == "ru" else "Locked")
    status_emoji = "✅" if done else "🔒"

    players_count = get_achievement_unlock_count(ach["id"])
    if lang == "ru":
        players_line = f'👥 <i>Выполнили {_fmt_num(players_count)} {_ru_plural(players_count, "игрок", "игрока", "игроков")}</i>'
    else:
        players_line = f'👥 <i>Unlocked by {_fmt_num(players_count)} player{"s" if players_count != 1 else ""}</i>'

    lines = [
        achievements_summary_line(data, lang),
        "",
        f'{cat_emoji} <b>{cat_name}</b>  <i>({cat_done}/{len(items)})</i>',
        "――――――――――――――――――――",
        "",
        f'{ach["emoji"]} <b>{name}</b>',
        f'<i>{desc}</i>',
        "",
        f'{status_emoji} <b>{status_lbl}</b>',
    ]

    if not done:
        prog = get_progress(data, ach)
        if prog:
            cur, target = prog
            cur_c = min(cur, target)
            lines.append(f'{_progress_bar(cur_c, target)}  <b>{_fmt_num(cur_c)}/{_fmt_num(target)}</b>')

    reward_str = _fmt_reward(ach, lang)
    if reward_str:
        lines.append(f'🎁 <i>{reward_str}</i>')

    lines.append("")
    lines.append(players_line)

    return "\n".join(lines).strip()


def _ru_plural(n: int, one: str, few: str, many: str) -> str:
    """Простое склонение под русские числительные (1 игрок / 2 игрока / 5 игроков)."""
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 14:
        return many
    if n1 == 1:
        return one
    if 2 <= n1 <= 4:
        return few
    return many


def achievements_menu_text(data: dict, lang: str = "ru") -> str:
    """
    Текст ГЛАВНОГО экрана достижений (уровень 0) — общий прогресс и список
    разделов с их прогрессом. Отсюда игрок выбирает конкретный раздел.
    """
    unlocked_set = set(data.get("achievements_unlocked", []))
    prompt = "Выберите раздел" if lang == "ru" else "Choose a category"

    lines = [achievements_summary_line(data, lang), "", f'<b>{prompt}:</b>', ""]
    for cat, info in CATEGORIES.items():
        items = _category_items(cat)
        done = sum(1 for a in items if a["id"] in unlocked_set)
        name = info["name_en"] if lang == "en" else info["name"]
        mark = "✅" if done == len(items) else "▫️"
        lines.append(f'{mark} {info["emoji"]} <b>{name}</b>  <i>{done}/{len(items)}</i>')

    return "\n".join(lines).strip()


def achievements_menu_keyboard(lang: str = "ru"):
    """
    Клавиатура ГЛАВНОГО экрана достижений (уровень 0): кнопки всех разделов
    + выход в главное меню бота. Требует aiogram (импортируется лениво).
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    menu_lbl = "🔙 Menu" if lang == "en" else "🔙 В меню"

    builder = InlineKeyboardBuilder()
    for cat, info in CATEGORIES.items():
        name = info["name_en"] if lang == "en" else info["name"]
        builder.button(text=f'{info["emoji"]} {name}', callback_data=f"ach_cat_{cat}")
    builder.adjust(2)

    builder.row(InlineKeyboardButton(text=menu_lbl, callback_data="back_to_menu"))

    return builder.as_markup()


def achievements_keyboard(lang: str = "ru", category: str | None = None, page: int = 0):
    """
    Клавиатура ВНУТРИ РАЗДЕЛА (уровень 1): одна строка пагинации из 3 кнопок —
    "◀ Назад", "X/Y" (просто индикатор текущей страницы, листание по кругу)
    и "Вперёд ▶" — и отдельной строкой ниже "🔙 Разделы", которая возвращает
    в меню достижений (callback "ach_menu"). Кнопки других разделов здесь не
    показываются. Требует aiogram (импортируется лениво).
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    if category is None:
        category = DEFAULT_CATEGORY

    back_lbl = "Назад" if lang == "ru" else "Back"
    fwd_lbl  = "Вперёд" if lang == "ru" else "Next"
    to_menu_lbl = "🔙 Разделы" if lang == "ru" else "🔙 Categories"

    total_pages = category_page_count(category)
    page = max(0, min(page, total_pages - 1))

    builder = InlineKeyboardBuilder()

    if total_pages > 1:
        prev_page = (page - 1) % total_pages
        next_page = (page + 1) % total_pages
        builder.row(
            InlineKeyboardButton(text=f'◀ {back_lbl}', callback_data=f"ach_page_{category}_{prev_page}"),
            InlineKeyboardButton(text=f'{page + 1}/{total_pages}', callback_data="ach_noop"),
            InlineKeyboardButton(text=f'{fwd_lbl} ▶', callback_data=f"ach_page_{category}_{next_page}"),
        )

    builder.row(InlineKeyboardButton(text=to_menu_lbl, callback_data="ach_menu"))

    return builder.as_markup()


# ============================================================
#  ПРИМЕР ХЕНДЛЕРА (скопируйте в mainhelp.py и раскомментируйте,
#  поправив импорты под свой проект)
#
#  Схема двухуровневая:
#   • Уровень 0 — меню достижений (achievements_menu_text/keyboard):
#     список разделов кнопками, открывается командой и кнопкой "🔙 Разделы"
#     из любого раздела. Отсюда же — выход в главное меню бота.
#   • Уровень 1 — карточка ОДНОГО достижения (achievements_list_text/keyboard,
#     PAGE_SIZE=1): статус, прогресс, награда, сколько игроков её открыли +
#     строка пагинации "◀ Назад — X/Y — Вперёд ▶" (листание по кругу) и
#     отдельная кнопка "🔙 Разделы" — назад в меню достижений (уровень 0).
#
#  НЕ ЗАБУДЬТЕ один раз при старте бота вызвать init_achievements_db() —
#  так же, как init_stats_db() и другие init_*_db():
#
#     from achieves import init_achievements_db
#     init_achievements_db()
# ============================================================
#
# from achieves import (
#     achievements_menu_text, achievements_menu_keyboard,
#     achievements_list_text, achievements_keyboard,
# )
#
# @dp.message(Command("достижения", "ачивки", "achievements", "ach"))
# @dp.message(_text_in("достижения", "ачивки", "achievements", "ach"))
# async def cmd_achievements(message: Message):
#     u    = get_or_create_user(message.from_user)
#     lang = get_lang(u)
#     track_user(message.from_user.id)
#     if await _check_onboarded(message, u):
#         return
#     await message.reply(
#         achievements_menu_text(u, lang),
#         parse_mode="HTML",
#         reply_markup=achievements_menu_keyboard(lang),
#     )
#
# И в handle_callback (mainhelp.py) добавить обработку:
#   cd == "ach_menu"             -> вернуться в меню достижений (уровень 0)
#   cd == "ach_noop"             -> кнопка-индикатор страницы, просто call.answer()
#   cd.startswith("ach_cat_")    -> открыть раздел, всегда со page=0
#   cd.startswith("ach_page_")   -> пагинация внутри текущего раздела
#
# Пример:
#
# @dp.callback_query(F.data == "ach_menu")
# async def cb_ach_menu(cq: CallbackQuery):
#     u    = get_or_create_user(cq.from_user)
#     lang = get_lang(u)
#     await cq.message.edit_text(
#         achievements_menu_text(u, lang),
#         parse_mode="HTML",
#         reply_markup=achievements_menu_keyboard(lang),
#     )
#
# @dp.callback_query(F.data == "ach_noop")
# async def cb_ach_noop(cq: CallbackQuery):
#     await cq.answer()  # просто индикатор страницы, ничего не делает
#
# @dp.callback_query(F.data.startswith("ach_cat_"))
# async def cb_ach_category(cq: CallbackQuery):
#     u    = get_or_create_user(cq.from_user)
#     lang = get_lang(u)
#     category = cq.data.removeprefix("ach_cat_")
#     await cq.message.edit_text(
#         achievements_list_text(u, lang, category=category, page=0),
#         parse_mode="HTML",
#         reply_markup=achievements_keyboard(lang, category=category, page=0),
#     )
#
# @dp.callback_query(F.data.startswith("ach_page_"))
# async def cb_ach_page(cq: CallbackQuery):
#     u    = get_or_create_user(cq.from_user)
#     lang = get_lang(u)
#     category, page_str = cq.data.removeprefix("ach_page_").rsplit("_", 1)
#     page = int(page_str)
#     await cq.message.edit_text(
#         achievements_list_text(u, lang, category=category, page=page),
#         parse_mode="HTML",
#         reply_markup=achievements_keyboard(lang, category=category, page=page),
#     )
