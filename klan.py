# ============================================================
#  klan.py  —  Система кланов TGStellar
#  Таблицы: clans, clan_members, clan_applications,
#           clan_treasury_requests
#  Роли: creator / member
# ============================================================

import sqlite3
import time
import html as _html
import threading
import asyncio
from contextlib import contextmanager

DB_PATH = "tgstellar.db"

# ── Защита от гонок (дюпов) ──────────────────────────────────
# 1) Любая операция, которая читает баланс/казну, а потом отдельным
#    запросом списывает/начисляет — уязвима к гонке (двойной тап по
#    кнопке, параллельные апдейты от aiogram). Поэтому:
#      a) все изменения treasury/quest-флагов в этом модуле сделаны
#         атомарными: UPDATE ... WHERE <условие> с проверкой rowcount,
#         внутри транзакции BEGIN IMMEDIATE (блокирует файл БД на
#         запись на время операции — работает и между процессами);
#      b) операции, которые трогают баланс игрока (он хранится в
#         другой БД через database.get_user/save_user), дополнительно
#         сериализуются через per-uid / per-clan лок в рамках процесса.
#         Это закрывает наиболее частый сценарий дюпа (двойной тап в
#         одном процессе бота). Если бот работает в несколько
#         процессов/воркеров одновременно, баланс в database.py тоже
#         должен обновляться атомарным SQL UPDATE balance=balance-?
#         WHERE uid=? AND balance>=? с проверкой rowcount — см. TODO
#         у функций create_clan/deposit_treasury/approve_withdrawal.

_locks_guard = threading.Lock()
_uid_locks:  dict[int, threading.Lock] = {}
_clan_locks: dict[int, threading.Lock] = {}


def _get_uid_lock(uid: int) -> threading.Lock:
    with _locks_guard:
        lk = _uid_locks.get(uid)
        if lk is None:
            lk = threading.Lock()
            _uid_locks[uid] = lk
        return lk


def _get_clan_lock(clan_id: int) -> threading.Lock:
    with _locks_guard:
        lk = _clan_locks.get(clan_id)
        if lk is None:
            lk = threading.Lock()
            _clan_locks[clan_id] = lk
        return lk


@contextmanager
def _uid_lock(uid: int):
    lk = _get_uid_lock(uid)
    lk.acquire()
    try:
        yield
    finally:
        lk.release()


@contextmanager
def _clan_lock(clan_id: int):
    lk = _get_clan_lock(clan_id)
    lk.acquire()
    try:
        yield
    finally:
        lk.release()


@contextmanager
def _immediate_tx():
    """
    Соединение с явной BEGIN IMMEDIATE-транзакцией: блокирует БД на
    запись сразу, а не лениво на первом UPDATE. Это убирает окно между
    SELECT-проверкой и UPDATE даже при нескольких процессах/воркерах,
    использующих один и тот же файл sqlite.
    """
    c = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    try:
        c.execute("BEGIN IMMEDIATE")
        yield c
        c.execute("COMMIT")
    except Exception:
        try:
            c.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        c.close()


# Разумные верхние границы на единичный вклад в дневные задания —
# защита от накрутки клановых наград аномально большими значениями,
# даже если вызывающий код (бой/шахта) этого не проверил.
MAX_SINGLE_BOSS_DAMAGE = 50_000_000
MAX_SINGLE_MINE_AMOUNT = 50_000_000

# ── Проверенные Emoji IDs (из рабочего кода проекта) ────────
# Из database.py / main.py — эти ID гарантированно работают
_E_SWORD   = "5357122032674818130"   # ⛏ / ⚔️  — шахта/оружие
_E_CROWN   = "5229011542011299168"   # 👑        — создатель
_E_PEOPLE  = "5452085950022707790"   # 👥        — участники (pets)
_E_STAR    = "5262643974912355126"   # ⭐        — премиум
_E_STATS   = "5231200819986047254"   # 📊        — статистика
_E_COIN    = "5199552030615558774"   # 🪙        — монета (из miner)
_E_TROPHY  = "5440539497383087970"   # 🏆        — лидеры
_E_CHEST   = "5278467510604160626"   # 💰        — магазин/казна
_E_SEARCH  = "5231012545799666522"   # 🔍        — обмен/поиск
_E_PLUS    = "5397916757333654639"   # ➕        — из main.py кнопка
_E_CHECK   = "5206607081334906820"   # ✅        — из main.py кнопка
_E_CROSS   = "5210952531676504517"   # ❌        — из main.py кнопка
_E_APPS    = "5334544901428229844"   # 📋        — настройки иконка
_E_BACK    = "6039539366177541657"   # ←         — рабочий back из оригинала
_E_STATUS  = "5438496463044752972"   # 🎟        — статус
_E_HUNT    = "5424972470023104089"   # 🗡         — охота
_E_LEAVE   = "5210952531676504517"   # 🚪        — из main.py кнопка
_E_STATSE  = "5445355530111437729"
_E_ANTIMATTER = "5235611059909323996"   # 🟣 — антиматерия (ресурс уровня клана)
_E_CLAN_BONUS = "5449800250032143374"   # 🚀 — клановый бонус на добычу
# ── Emoji для топ-10 кланов (места/цифры) ───────────────────
_E_RANK_1  = "5440539497383087970"   # 🥇 — 1 место
_E_RANK_2  = "5447203607294265305"   # 🥈 — 2 место
_E_RANK_3  = "5453902265922376865"   # 🥉 — 3 место
_E_RANK_4  = "5382054253403577563"   # 4️⃣
_E_RANK_5  = "5391197405553107640"   # 5️⃣
_E_RANK_6  = "5390966190283694453"   # 6️⃣
_E_RANK_7  = "5382132232829804982"   # 7️⃣
_E_RANK_8  = "5391038994274329680"   # 8️⃣
_E_RANK_9  = "5391234698754138414"   # 9️⃣
_E_DIGIT_1 = "5382322671679708881"   # 1 (для "10")
_E_DIGIT_0 = "5393480373944459905"   # 0 (для "10")

# tg-emoji хелперы для текстов
def _e(eid: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


def _fmt(n) -> str:
    """
    Сокращённый формат чисел (стандартная короткая шкала, единый стиль
    с database.py -> format_amount и miner.py -> _fmt_num):
      999          -> "999"
      1500         -> "1.5K"
      100000       -> "100K"
      2300000      -> "2.3M"
      100000000    -> "100M"
      1500000000   -> "1.5B"
      1_000_000_000_000        -> "1T"
      1_000_000_000_000_000    -> "1Qa"  (quadrillion)
      1_000_000_000_000_000_000-> "1Qi"  (quintillion)
      10**21                   -> "1Sx"  (sextillion)
      10**24                   -> "1Sp"  (septillion)
      10**27                   -> "1Oc"  (octillion)
      10**30                   -> "1No"  (nonillion)
      10**33                   -> "1Dc"  (decillion)
    Если число ещё больше — формат не ломается: продолжаем Dc2, Dc3, ...
    Дробная часть показывается только если она не нулевая (1.5K, но не 1.0K).
    Знак сохраняется (для отрицательных значений, если вдруг понадобится).
    """
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)

    sign = "-" if n < 0 else ""
    n = abs(n)

    if n < 1000:
        # Целые числа без дробной части выводим как int, иначе с одним знаком
        if n == int(n):
            return f"{sign}{int(n)}"
        return f"{sign}{n:.1f}"

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
        # За пределами "Dc" (10^33) продолжаем нумеровать: Dc2, Dc3, ...
        suffix = f"Dc{idx - len(suffixes) + 2}"

    if val == int(val):
        return f"{sign}{int(val)}{suffix}"
    return f"{sign}{val:.1f}{suffix}"


COIN       = _e(_E_COIN,  "🪙")
CROWN      = _e(_E_CROWN, "👑")
ANTIMATTER = _e(_E_ANTIMATTER, "🟣")

MAX_CLAN_MEMBERS = 100
MAX_CLAN_APPS    = 50
APPS_PER_PAGE    = 10
CLANS_PER_PAGE   = 10
MIN_CLAN_NAME    = 3
MAX_CLAN_NAME    = 24
CREATE_COST      = 10_000

# ── Лимиты на вывод из казны по стажу в клане ───────────────
# Защита от схемы "вступил в клан ради вывода общей казны":
# чем меньше времени игрок состоит в клане, тем меньше он может
# вывести. Лимит накопительный — считается сумма всех его заявок
# со статусом pending/approved за всё время, а не разово на один
# запрос (иначе лимит легко обойти несколькими заявками подряд).
_DAY = 86_400
WITHDRAW_LIMIT_1D = 25_000     # < 1 дня в клане
WITHDRAW_LIMIT_3D = 150_000    # < 3 дней в клане
WITHDRAW_LIMIT_7D = 500_000    # < 7 дней в клане
                                # >= 7 дней — без ограничений


def get_membership_withdraw_limit(joined_ts: int) -> int | None:
    """
    Лимит на вывод из казны для игрока в зависимости от того, сколько
    времени он состоит в клане. Возвращает None, если ограничений нет
    (в клане неделю и больше).
    """
    elapsed = int(time.time()) - (joined_ts or 0)
    if elapsed < _DAY:
        return WITHDRAW_LIMIT_1D
    if elapsed < 3 * _DAY:
        return WITHDRAW_LIMIT_3D
    if elapsed < 7 * _DAY:
        return WITHDRAW_LIMIT_7D
    return None

# ── Ежедневные задания клана ────────────────────────────────
DAILY_QUEST_DMG_TARGET  = 1_000_000   # сколько урона боссу нужно нанести (суммарно кланом)
DAILY_QUEST_DMG_REWARD  = 500_000     # награда в казну за выполнение задания на урон
DAILY_QUEST_KILL_REWARD = 3_000_000   # награда в казну за убийство любого босса (общее задание)

# Задание 3: суммарный урон клана по боссу 5,000,000 → награда 2,000,000 в казну
DAILY_QUEST_DMG2_TARGET  = 5_000_000
DAILY_QUEST_DMG2_REWARD  = 2_000_000

# Задания на добычу монет в шахте (суммарно кланом, нарастающие пороги)
DAILY_QUEST_MINE1_TARGET = 1_500_000
DAILY_QUEST_MINE1_REWARD = 500_000

DAILY_QUEST_MINE2_TARGET = 5_000_000
DAILY_QUEST_MINE2_REWARD = 2_000_000

DAILY_QUEST_MINE3_TARGET = 30_000_000
DAILY_QUEST_MINE3_REWARD = 5_000_000

# ── Личные ежедневные задания (на каждого участника клана) ──
# В отличие от общих заданий (клан выполняет их сообща), личные
# задания засчитываются каждому игроку отдельно и хранятся в
# отдельной таблице clan_personal_quests (clan_id, uid, quest_date).
# Награда за личное задание тоже уходит в казну клана, но, в отличие
# от общих заданий, засчитывается прогресс только САМОГО игрока.
# Цели/награды масштабируются множителем ранга клана — как и общие.
PERSONAL_QUEST_DMG_TARGET  = 200_000
PERSONAL_QUEST_DMG_REWARD  = 100_000
PERSONAL_QUEST_MINE_TARGET = 300_000
PERSONAL_QUEST_MINE_REWARD = 100_000

# ── Клановый бонус на добычу (шахту) ────────────────────────
# Зависит от УРОВНЯ клана (level, прокачивается за антиматерию —
# см. CLAN_LEVEL_UP_COST): 1 уровень -> x1.1, 2 -> x1.2, 3 -> x1.35,
# 4 -> x1.5, 5 -> x1.8.
# Бонус АКТИВЕН только если игрок выполнил (получил награду за) хотя
# бы одно ЛИЧНОЕ клановое задание за последние 24 часа — иначе бонус
# временно отключается (не сгорает, просто не действует, пока игрок
# снова не выполнит личное задание).
CLAN_LEVEL_MINE_BONUS = {
    1: 1.10,
    2: 1.20,
    3: 1.35,
    4: 1.50,
    5: 1.80,
}
PERSONAL_QUEST_ACTIVITY_WINDOW = 86_400  # 24 часа


def get_clan_level_bonus_multiplier(level: int) -> float:
    """Базовый множитель добычи за уровень клана (без учёта активности)."""
    lvl = max(1, min(level or 1, MAX_CLAN_LEVEL))
    return CLAN_LEVEL_MINE_BONUS.get(lvl, 1.0)


def get_clan_bonus_info(clan: dict, member: dict) -> dict:
    """
    Собирает информацию о клановом бонусе на добычу для игрока:
    базовый множитель (по уровню клана), активен ли он сейчас
    (выполнялось ли личное клановое задание за последние 24ч),
    и итоговый множитель (1.0, если бонус не активен).
    """
    level     = (clan or {}).get("level") or 1
    base_mult = get_clan_level_bonus_multiplier(level)
    last_ts   = (member or {}).get("last_personal_quest_ts") or 0
    now       = int(time.time())
    elapsed   = now - last_ts
    active    = last_ts > 0 and elapsed < PERSONAL_QUEST_ACTIVITY_WINDOW
    return {
        "level":            level,
        "base_multiplier":  base_mult,
        "multiplier":       base_mult if active else 1.0,
        "active":           active,
        "last_ts":          last_ts,
        "seconds_left":     max(0, PERSONAL_QUEST_ACTIVITY_WINDOW - elapsed) if active else 0,
    }


def get_clan_mining_bonus_multiplier(uid: int) -> float:
    """
    Синхронная функция — итоговый множитель добычи от кланового бонуса
    для игрока (1.0, если игрок не в клане или бонус не активен).
    Использовать через aio_get_clan_mining_bonus_multiplier из async-кода.
    """
    m = get_member(uid)
    if not m:
        return 1.0
    clan = get_clan(m["clan_id"])
    if not clan:
        return 1.0
    return get_clan_bonus_info(clan, m)["multiplier"]


# ── Ранги клана (5 рангов) ──────────────────────────────────
# Ранг повышает сложность клановых заданий: цели и награды всех
# ежедневных заданий умножаются на multiplier ранга (x1/x2/x4/x8/x16 —
# каждый следующий ранг ровно в 2 раза сложнее предыдущего).
# Требования — сколько участников и казны нужно накопить, чтобы
# ранг был присвоен клану (проверяется автоматически при вступлении
# новых участников и при любом пополнении казны). Ранг не понижается
# при убыли участников/трате казны — достигнутое остаётся достигнутым.
#
# rank 1 — стартовый, без требований.
# rank 2 — 5 участников  + 10 000 000 в казне   → задания x2
# rank 3 — 15 участников + 150 000 000 в казне  → задания x4
# rank 4 — 30 участников + 1 000 000 000 в казне → задания x8
# rank 5 — 50 участников + 15 000 000 000 в казне → задания x16
CLAN_RANKS = [
    {"rank": 1, "name_ru": "Новичок", "name_en": "Novice",  "members_required": 0,  "treasury_required": 0,              "multiplier": 1},
    {"rank": 2, "name_ru": "Отряд",   "name_en": "Squad",   "members_required": 5,  "treasury_required": 10_000_000,     "multiplier": 2},
    {"rank": 3, "name_ru": "Легион",  "name_en": "Legion",  "members_required": 15, "treasury_required": 150_000_000,    "multiplier": 4},
    {"rank": 4, "name_ru": "Орден",   "name_en": "Order",   "members_required": 30, "treasury_required": 1_000_000_000,  "multiplier": 8},
    {"rank": 5, "name_ru": "Империя", "name_en": "Empire",  "members_required": 50, "treasury_required": 15_000_000_000, "multiplier": 16},
]
MAX_CLAN_RANK = len(CLAN_RANKS)

# Базовая цель для "боевого" общего задания (убийство босса) —
# на ранге 1 нужен 1 килл, дальше — умножается вместе со всеми
# остальными заданиями (rank 2 → 2 килла, rank 3 → 4 килла и т.д.)
DAILY_QUEST_KILL_BASE_TARGET = 1


def get_clan_rank_info(rank: int) -> dict:
    """Возвращает описание ранга (безопасно клэмпит в диапазон 1..5)."""
    idx = max(1, min(rank or 1, MAX_CLAN_RANK)) - 1
    return CLAN_RANKS[idx]


def get_clan_rank_multiplier(rank: int) -> int:
    return get_clan_rank_info(rank)["multiplier"]


def get_next_rank_info(rank: int) -> dict | None:
    """Требования для следующего ранга или None, если ранг уже максимальный."""
    rank = rank or 1
    if rank >= MAX_CLAN_RANK:
        return None
    return CLAN_RANKS[rank]  # CLAN_RANKS[0]=rank1, поэтому CLAN_RANKS[rank] = rank+1


def _maybe_rank_up(c, clan_id: int) -> int:
    """
    Проверяет условия и повышает ранг клана, если он их выполнил.
    Вызывается внутри уже открытой транзакции (после изменения
    численности участников или казны). Ранг никогда не понижается.
    Возвращает актуальный ранг клана после проверки.
    """
    row = c.execute("SELECT rank, treasury FROM clans WHERE id=?", (clan_id,)).fetchone()
    if not row:
        return 1
    cur_rank = row["rank"] or 1
    treasury = row["treasury"] or 0
    member_count = c.execute(
        "SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (clan_id,)
    ).fetchone()[0]

    new_rank = cur_rank
    for req in CLAN_RANKS:
        if req["rank"] <= new_rank:
            continue
        if member_count >= req["members_required"] and treasury >= req["treasury_required"]:
            new_rank = req["rank"]
        else:
            break  # требования идут по возрастанию — дальше проверять бессмысленно

    if new_rank != cur_rank:
        c.execute("UPDATE clans SET rank=? WHERE id=?", (new_rank, clan_id))
    return new_rank


# ── Антиматерия и уровень клана ─────────────────────────────
# Отдельный ресурс клана (не казна). Копится на убийствах боссов и
# тратится ТОЛЬКО на прокачку уровня клана (не влияет на ранг/задания
# выше — это независимая система).
#   простой (easy)   босс -> 1  антиматерия
#   средний (medium) босс -> 3  антиматерии
#   сложный (hard)   босс -> 10 антиматерий
ANTIMATTER_REWARD_EASY   = 1
ANTIMATTER_REWARD_MEDIUM = 3
ANTIMATTER_REWARD_HARD   = 10
ANTIMATTER_REWARD_BY_TIER = {
    "easy":   ANTIMATTER_REWARD_EASY,
    "medium": ANTIMATTER_REWARD_MEDIUM,
    "hard":   ANTIMATTER_REWARD_HARD,
}

# Стоимость (в антиматерии) повышения уровня клана. Ключ — уровень,
# ДО которого повышаемся (2, 3, 4, 5). Уровень 1 — стартовый, бесплатный.
CLAN_LEVEL_UP_COST = {
    2: 15,
    3: 125,
    4: 350,
    5: 1000,
}
MAX_CLAN_LEVEL = max(CLAN_LEVEL_UP_COST)


def get_clan_level_up_cost(level: int) -> int | None:
    """Стоимость антиматерии для повышения СЛЕДУЮЩЕГО уровня клана
    относительно текущего `level`. None, если уровень уже максимальный."""
    return CLAN_LEVEL_UP_COST.get((level or 1) + 1)


def get_clan_rank_progress(clan_id: int) -> dict:
    """
    Прогресс клана к следующему рангу — для UI (сколько участников/казны
    не хватает). Если ранг уже максимальный — next будет None.
    """
    clan = get_clan(clan_id)
    if not clan:
        return {"rank": 1, "next": None}
    rank = clan.get("rank") or 1
    member_count = get_member_count(clan_id)
    next_info = get_next_rank_info(rank)
    return {
        "rank":          rank,
        "rank_info":     get_clan_rank_info(rank),
        "member_count":  member_count,
        "treasury":      clan.get("treasury", 0),
        "next":          next_info,
    }

# ─────────────────────── БД ──────────────────────────────────

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_klan_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS clans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT    DEFAULT '',
                creator_uid INTEGER NOT NULL,
                treasury    INTEGER DEFAULT 0,
                created_ts  INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clan_members (
                uid         INTEGER PRIMARY KEY,
                clan_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'member',
                joined_ts   INTEGER NOT NULL,
                contributed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS clan_applications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id    INTEGER NOT NULL,
                uid        INTEGER NOT NULL,
                message    TEXT    DEFAULT '',
                applied_ts INTEGER NOT NULL,
                UNIQUE(clan_id, uid)
            );
            CREATE TABLE IF NOT EXISTS clan_treasury_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id     INTEGER NOT NULL,
                uid         INTEGER NOT NULL,
                amount      INTEGER NOT NULL,
                reason      TEXT    DEFAULT '',
                status      TEXT    DEFAULT 'pending',
                created_ts  INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clan_daily_quests (
                clan_id              INTEGER NOT NULL,
                quest_date           TEXT    NOT NULL,
                boss_damage          INTEGER DEFAULT 0,
                dmg_reward_claimed   INTEGER DEFAULT 0,
                kill_reward_claimed  INTEGER DEFAULT 0,
                dmg2_reward_claimed  INTEGER DEFAULT 0,
                mine_earned          INTEGER DEFAULT 0,
                mine1_reward_claimed INTEGER DEFAULT 0,
                mine2_reward_claimed INTEGER DEFAULT 0,
                mine3_reward_claimed INTEGER DEFAULT 0,
                PRIMARY KEY (clan_id, quest_date)
            );
            CREATE TABLE IF NOT EXISTS clan_personal_quests (
                clan_id            INTEGER NOT NULL,
                uid                INTEGER NOT NULL,
                quest_date         TEXT    NOT NULL,
                boss_damage        INTEGER DEFAULT 0,
                mine_earned        INTEGER DEFAULT 0,
                dmg_reward_claimed  INTEGER DEFAULT 0,
                mine_reward_claimed INTEGER DEFAULT 0,
                PRIMARY KEY (clan_id, uid, quest_date)
            );
        """)
        # Миграция: clan_chat_id в таблице clans
        clan_cols = {row[1] for row in c.execute("PRAGMA table_info(clans)").fetchall()}
        if "chat_id" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN chat_id INTEGER DEFAULT NULL")
        if "chat_username" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN chat_username TEXT DEFAULT NULL")
        if "chat_title" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN chat_title TEXT DEFAULT NULL")
        # Миграция: ранг клана (система рангов, задания x2 за ранг)
        if "rank" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN rank INTEGER DEFAULT 1")
        # Миграция: антиматерия (ресурс за убийство боссов) и уровень
        # клана (прокачивается за антиматерию, независимо от rank).
        if "antimatter" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN antimatter INTEGER DEFAULT 0")
        if "level" not in clan_cols:
            c.execute("ALTER TABLE clans ADD COLUMN level INTEGER DEFAULT 1")
        # Миграция: отметка времени последнего выполненного личного
        # кланового задания — на неё завязана активность кланового
        # бонуса на добычу (см. get_clan_bonus_info).
        member_cols = {row[1] for row in c.execute("PRAGMA table_info(clan_members)").fetchall()}
        if "last_personal_quest_ts" not in member_cols:
            c.execute("ALTER TABLE clan_members ADD COLUMN last_personal_quest_ts INTEGER DEFAULT 0")
        # Миграция: добавляем новые колонки к существующей таблице, если их нет
        existing_cols = {row[1] for row in c.execute("PRAGMA table_info(clan_daily_quests)").fetchall()}
        for col, ddl in [
            ("dmg2_reward_claimed",  "ALTER TABLE clan_daily_quests ADD COLUMN dmg2_reward_claimed INTEGER DEFAULT 0"),
            ("mine_earned",          "ALTER TABLE clan_daily_quests ADD COLUMN mine_earned INTEGER DEFAULT 0"),
            ("mine1_reward_claimed", "ALTER TABLE clan_daily_quests ADD COLUMN mine1_reward_claimed INTEGER DEFAULT 0"),
            ("mine2_reward_claimed", "ALTER TABLE clan_daily_quests ADD COLUMN mine2_reward_claimed INTEGER DEFAULT 0"),
            ("mine3_reward_claimed", "ALTER TABLE clan_daily_quests ADD COLUMN mine3_reward_claimed INTEGER DEFAULT 0"),
            ("boss_kills",           "ALTER TABLE clan_daily_quests ADD COLUMN boss_kills INTEGER DEFAULT 0"),
        ]:
            if col not in existing_cols:
                c.execute(ddl)
        c.commit()

# ─────────────────────── КЛАНЫ: CRUD ─────────────────────────

def get_clan(clan_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM clans WHERE id=?", (clan_id,)).fetchone()
    return dict(row) if row else None


def get_clan_by_name(name: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM clans WHERE LOWER(name)=LOWER(?)", (name,)
        ).fetchone()
    return dict(row) if row else None


def search_clans(query: str, page: int = 0) -> tuple[list[dict], int]:
    """Возвращает (список кланов на странице, total_count)."""
    offset = page * CLANS_PER_PAGE
    if query.strip():
        if query.strip().isdigit():
            clan_id = int(query.strip())
            with _conn() as c:
                rows = c.execute("""
                    SELECT c.*, COUNT(m.uid) AS member_count
                    FROM clans c
                    LEFT JOIN clan_members m ON m.clan_id = c.id
                    WHERE c.id=?
                    GROUP BY c.id
                """, (clan_id,)).fetchall()
            return [dict(r) for r in rows], len(rows)
        q = f"%{query.lower()}%"
        with _conn() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM clans WHERE LOWER(name) LIKE ?", (q,)
            ).fetchone()[0]
            rows = c.execute("""
                SELECT c.*, COUNT(m.uid) AS member_count
                FROM clans c
                LEFT JOIN clan_members m ON m.clan_id = c.id
                WHERE LOWER(c.name) LIKE ?
                GROUP BY c.id
                ORDER BY c.treasury DESC
                LIMIT ? OFFSET ?
            """, (q, CLANS_PER_PAGE, offset)).fetchall()
    else:
        with _conn() as c:
            total = c.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
            rows = c.execute("""
                SELECT c.*, COUNT(m.uid) AS member_count
                FROM clans c
                LEFT JOIN clan_members m ON m.clan_id = c.id
                GROUP BY c.id
                ORDER BY c.treasury DESC
                LIMIT ? OFFSET ?
            """, (CLANS_PER_PAGE, offset)).fetchall()
    return [dict(r) for r in rows], total


def get_top_clans(limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT c.*, COUNT(m.uid) AS member_count
            FROM clans c
            LEFT JOIN clan_members m ON m.clan_id = c.id
            GROUP BY c.id
            ORDER BY c.treasury DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_all_clans_stats() -> dict:
    with _conn() as c:
        total_clans    = c.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
        total_members  = c.execute("SELECT COUNT(*) FROM clan_members").fetchone()[0]
        total_treasury = c.execute("SELECT COALESCE(SUM(treasury),0) FROM clans").fetchone()[0]
    return {"total_clans": total_clans, "total_members": total_members, "total_treasury": total_treasury}


# ─────────────────────── ЧАТ КЛАНА ───────────────────────────

def set_clan_chat(clan_id: int, chat_id: int, chat_username: str | None, chat_title: str) -> None:
    """Привязать чат к клану."""
    with _conn() as c:
        c.execute(
            "UPDATE clans SET chat_id=?, chat_username=?, chat_title=? WHERE id=?",
            (chat_id, chat_username, chat_title, clan_id)
        )
        c.commit()


def remove_clan_chat(clan_id: int) -> None:
    """Открепить чат от клана."""
    with _conn() as c:
        c.execute(
            "UPDATE clans SET chat_id=NULL, chat_username=NULL, chat_title=NULL WHERE id=?",
            (clan_id,)
        )
        c.commit()

# ─────────────────────── ЧЛЕНЫ КЛАНА ─────────────────────────

def get_member(uid: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM clan_members WHERE uid=?", (uid,)).fetchone()
    return dict(row) if row else None


def get_clan_members(clan_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT m.uid, m.role, m.joined_ts, m.contributed,
                   json_extract(u.data_json, '$.first_name') AS first_name,
                   json_extract(u.data_json, '$.username')   AS username
            FROM clan_members m
            LEFT JOIN users u ON u.uid = m.uid
            WHERE m.clan_id=?
            ORDER BY CASE m.role WHEN 'creator' THEN 0 ELSE 1 END, m.contributed DESC
        """, (clan_id,)).fetchall()
    return [dict(r) for r in rows]


def get_member_count(clan_id: int) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (clan_id,)).fetchone()[0]

# ─────────────────────── ДЕЙСТВИЯ ────────────────────────────

CLAN_CREATE_COOLDOWN = 86400  # 24 часа — создать новый клан можно не чаще раза в сутки


def create_clan(uid: int, name: str) -> dict:
    from database import get_user, save_user
    name = name.strip()
    if len(name) < MIN_CLAN_NAME or len(name) > MAX_CLAN_NAME:
        return {"ok": False, "error": "bad_name_length"}

    # Лочим юзера на всю операцию: исключает дюп при двойном тапе
    # "Создать клан" (две параллельные попытки списать одни и те же
    # монеты / создать два клана разом).
    with _uid_lock(uid):
        if get_member(uid):
            return {"ok": False, "error": "already_in_clan"}
        # Проверяем занятость имени до INSERT (case-insensitive)
        if get_clan_by_name(name):
            return {"ok": False, "error": "name_taken"}

        d = get_user(uid)
        if not d:
            return {"ok": False, "error": "user_not_found"}

        # Лимит на создание клана — раз в сутки. Хранится на самом юзере
        # (а не в clan_members), поэтому переживает disband_clan — иначе
        # схему "создал -> распустил -> создал заново" нельзя было бы
        # ограничить вовсе.
        now_ts = int(time.time())
        last_create_ts = d.get("last_clan_create_ts", 0)
        elapsed = now_ts - last_create_ts
        if last_create_ts and elapsed < CLAN_CREATE_COOLDOWN:
            return {"ok": False, "error": "create_cooldown",
                     "retry_after": CLAN_CREATE_COOLDOWN - elapsed}

        if d.get("balance", 0) < CREATE_COST:
            return {"ok": False, "error": "no_coins"}

        # Списываем баланс ДО создания клана и сразу сохраняем —
        # минимизирует окно гонки с другими операциями над балансом
        # этого же uid (они тоже идут через _uid_lock).
        d["balance"] -= CREATE_COST
        d["last_clan_create_ts"] = now_ts
        save_user(uid, d)

        try:
            with _immediate_tx() as c:
                if c.execute(
                    "SELECT 1 FROM clan_members WHERE uid=?", (uid,)
                ).fetchone():
                    raise _AlreadyInClan()
                if c.execute(
                    "SELECT 1 FROM clans WHERE LOWER(name)=LOWER(?)", (name,)
                ).fetchone():
                    raise _NameTaken()
                cur = c.execute("""
                    INSERT INTO clans (name, description, creator_uid, treasury, created_ts)
                    VALUES (?, '', ?, 0, ?)
                """, (name, uid, int(time.time())))
                clan_id = cur.lastrowid
                c.execute("""
                    INSERT INTO clan_members (uid, clan_id, role, joined_ts, contributed)
                    VALUES (?, ?, 'creator', ?, 0)
                """, (uid, clan_id, int(time.time())))
        except (sqlite3.IntegrityError, _AlreadyInClan, _NameTaken) as e:
            # Откатываем списание и штамп времени создания, т.к. клан не создан
            d2 = get_user(uid)
            if d2:
                d2["balance"] = d2.get("balance", 0) + CREATE_COST
                d2["last_clan_create_ts"] = last_create_ts
                save_user(uid, d2)
            if isinstance(e, _AlreadyInClan):
                return {"ok": False, "error": "already_in_clan"}
            return {"ok": False, "error": "name_taken"}

    return {"ok": True, "clan_id": clan_id}


class _AlreadyInClan(Exception):
    pass


class _NameTaken(Exception):
    pass


def disband_clan(uid: int) -> dict:
    m = get_member(uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    clan_id = m["clan_id"]
    with _clan_lock(clan_id), _uid_lock(uid):
        # Перечитываем актуальную казну под локом — на случай, если
        # параллельно прошёл approve_withdrawal/квестовая награда.
        with _immediate_tx() as c:
            row = c.execute("SELECT treasury FROM clans WHERE id=?", (clan_id,)).fetchone()
            if not row:
                return {"ok": False, "error": "not_found"}
            payout = row["treasury"]
            c.execute("DELETE FROM clan_members WHERE clan_id=?",           (clan_id,))
            c.execute("DELETE FROM clan_applications WHERE clan_id=?",      (clan_id,))
            c.execute("DELETE FROM clan_treasury_requests WHERE clan_id=?", (clan_id,))
            c.execute("DELETE FROM clan_daily_quests WHERE clan_id=?",      (clan_id,))
            c.execute("DELETE FROM clans WHERE id=?",                       (clan_id,))
        if payout > 0:
            from database import get_user, save_user
            d = get_user(uid)
            if d:
                d["balance"] = d.get("balance", 0) + payout
                save_user(uid, d)
    return {"ok": True}


def leave_clan(uid: int) -> dict:
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    if m["role"] == "creator":
        return {"ok": False, "error": "creator_cannot_leave"}
    with _conn() as c:
        c.execute("DELETE FROM clan_members WHERE uid=?", (uid,))
        c.commit()
    return {"ok": True}


def kick_member(creator_uid: int, target_uid: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    t = get_member(target_uid)
    if not t or t["clan_id"] != m["clan_id"]:
        return {"ok": False, "error": "not_in_your_clan"}
    if t["role"] == "creator":
        return {"ok": False, "error": "cannot_kick_creator"}
    with _conn() as c:
        c.execute("DELETE FROM clan_members WHERE uid=?", (target_uid,))
        c.commit()
    return {"ok": True}

# ─────────────────────── ЗАЯВКИ ──────────────────────────────

def apply_to_clan(uid: int, clan_id: int, message: str = "") -> dict:
    with _uid_lock(uid), _clan_lock(clan_id):
        if get_member(uid):
            return {"ok": False, "error": "already_in_clan"}
        with _immediate_tx() as c:
            member_count = c.execute(
                "SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (clan_id,)
            ).fetchone()[0]
            if member_count >= MAX_CLAN_MEMBERS:
                return {"ok": False, "error": "clan_full"}
            app_count = c.execute(
                "SELECT COUNT(*) FROM clan_applications WHERE clan_id=?", (clan_id,)
            ).fetchone()[0]
            if app_count >= MAX_CLAN_APPS:
                return {"ok": False, "error": "apps_full"}
            existing = c.execute(
                "SELECT id FROM clan_applications WHERE clan_id=? AND uid=?", (clan_id, uid)
            ).fetchone()
            if existing:
                return {"ok": False, "error": "already_applied"}
            c.execute("""
                INSERT INTO clan_applications (clan_id, uid, message, applied_ts)
                VALUES (?, ?, ?, ?)
            """, (clan_id, uid, message[:200], int(time.time())))
    return {"ok": True}


def get_applications(clan_id: int, page: int = 0) -> tuple[list[dict], int]:
    offset = page * APPS_PER_PAGE
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM clan_applications WHERE clan_id=?", (clan_id,)
        ).fetchone()[0]
        rows = c.execute("""
            SELECT a.id, a.uid, a.message, a.applied_ts,
                   json_extract(u.data_json, '$.first_name') AS first_name,
                   json_extract(u.data_json, '$.username')   AS username
            FROM clan_applications a
            LEFT JOIN users u ON u.uid = a.uid
            WHERE a.clan_id=?
            ORDER BY a.applied_ts ASC
            LIMIT ? OFFSET ?
        """, (clan_id, APPS_PER_PAGE, offset)).fetchall()
    return [dict(r) for r in rows], total


def accept_application(creator_uid: int, app_id: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    with _conn() as c:
        app = c.execute("SELECT * FROM clan_applications WHERE id=?", (app_id,)).fetchone()
        if not app:
            return {"ok": False, "error": "app_not_found"}
        if app["clan_id"] != m["clan_id"]:
            return {"ok": False, "error": "wrong_clan"}
        if get_member_count(m["clan_id"]) >= MAX_CLAN_MEMBERS:
            return {"ok": False, "error": "clan_full"}
        if get_member(app["uid"]):
            c.execute("DELETE FROM clan_applications WHERE id=?", (app_id,))
            c.commit()
            return {"ok": False, "error": "already_in_clan"}
        c.execute("""
            INSERT INTO clan_members (uid, clan_id, role, joined_ts, contributed)
            VALUES (?, ?, 'member', ?, 0)
        """, (app["uid"], m["clan_id"], int(time.time())))
        c.execute("DELETE FROM clan_applications WHERE clan_id=? AND uid=?",
                  (m["clan_id"], app["uid"]))
        _maybe_rank_up(c, m["clan_id"])
        c.commit()
    return {"ok": True, "uid": app["uid"]}


def reject_application(creator_uid: int, app_id: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    with _conn() as c:
        app = c.execute("SELECT * FROM clan_applications WHERE id=?", (app_id,)).fetchone()
        if not app or app["clan_id"] != m["clan_id"]:
            return {"ok": False, "error": "app_not_found"}
        c.execute("DELETE FROM clan_applications WHERE id=?", (app_id,))
        c.commit()
    return {"ok": True, "uid": app["uid"]}


def accept_all_applications(creator_uid: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    clan_id = m["clan_id"]
    with _conn() as c:
        all_apps = c.execute(
            "SELECT id, uid FROM clan_applications WHERE clan_id=? ORDER BY applied_ts ASC",
            (clan_id,)
        ).fetchall()
    accepted = 0
    skipped  = 0
    for app in all_apps:
        if get_member_count(clan_id) >= MAX_CLAN_MEMBERS:
            skipped += 1
            continue
        if get_member(app["uid"]):
            with _conn() as c:
                c.execute("DELETE FROM clan_applications WHERE id=?", (app["id"],))
                c.commit()
            continue
        with _conn() as c:
            c.execute("""
                INSERT OR IGNORE INTO clan_members (uid, clan_id, role, joined_ts, contributed)
                VALUES (?, ?, 'member', ?, 0)
            """, (app["uid"], clan_id, int(time.time())))
            c.execute("DELETE FROM clan_applications WHERE id=?", (app["id"],))
            c.commit()
        accepted += 1
    if accepted:
        with _conn() as c:
            _maybe_rank_up(c, clan_id)
            c.commit()
    return {"ok": True, "accepted": accepted, "skipped": skipped}


def reject_all_applications(creator_uid: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    clan_id = m["clan_id"]
    with _conn() as c:
        count = c.execute(
            "SELECT COUNT(*) FROM clan_applications WHERE clan_id=?", (clan_id,)
        ).fetchone()[0]
        c.execute("DELETE FROM clan_applications WHERE clan_id=?", (clan_id,))
        c.commit()
    return {"ok": True, "rejected": count}

# ─────────────────────── КАЗНА ───────────────────────────────

def deposit_treasury(uid: int, amount: int) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "bad_amount"}
    with _uid_lock(uid):
        m = get_member(uid)
        if not m:
            return {"ok": False, "error": "not_in_clan"}
        from database import get_user, save_user
        d = get_user(uid)
        if not d or d.get("balance", 0) < amount:
            return {"ok": False, "error": "no_coins"}
        d["balance"] -= amount
        save_user(uid, d)
        with _immediate_tx() as c:
            c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",              (amount, m["clan_id"]))
            c.execute("UPDATE clan_members SET contributed=contributed+? WHERE uid=?", (amount, uid))
            _maybe_rank_up(c, m["clan_id"])
    return {"ok": True}


def request_withdrawal(uid: int, amount: int, reason: str) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "bad_amount"}
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    clan_id = m["clan_id"]
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            clan = c.execute("SELECT treasury FROM clans WHERE id=?", (clan_id,)).fetchone()
            if not clan:
                return {"ok": False, "error": "not_in_clan"}

            # Лимит на вывод для игроков, недавно вступивших в клан
            # (защита от схемы "вступил ради вывода казны"). Считаем
            # накопительно: сколько этот игрок уже вывел/запросил за
            # всё время, пока действует его текущее ограничение по
            # стажу — так лимит нельзя обойти серией мелких заявок.
            limit = get_membership_withdraw_limit(m["joined_ts"])
            if limit is not None:
                already = c.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM clan_treasury_requests
                    WHERE uid=? AND status IN ('pending', 'approved')
                """, (uid,)).fetchone()[0]
                if already + amount > limit:
                    return {
                        "ok": False,
                        "error": "withdraw_limit_exceeded",
                        "limit": limit,
                        "already_used": already,
                        "remaining": max(0, limit - already),
                    }

            # Учитываем уже ожидающие выводы этого клана, чтобы нельзя
            # было запросить выводов суммарно больше, чем реально есть
            # в казне (даже если по отдельности каждый запрос валиден).
            pending_sum = c.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM clan_treasury_requests
                WHERE clan_id=? AND status='pending'
            """, (clan_id,)).fetchone()[0]
            if clan["treasury"] - pending_sum < amount:
                return {"ok": False, "error": "not_enough_treasury"}
            existing = c.execute("""
                SELECT id FROM clan_treasury_requests
                WHERE clan_id=? AND uid=? AND status='pending'
            """, (clan_id, uid)).fetchone()
            if existing:
                return {"ok": False, "error": "already_pending"}
            c.execute("""
                INSERT INTO clan_treasury_requests (clan_id, uid, amount, reason, status, created_ts)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (clan_id, uid, amount, reason[:300], int(time.time())))
    return {"ok": True}


def get_withdrawal_requests(clan_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT r.id, r.uid, r.amount, r.reason, r.created_ts,
                   json_extract(u.data_json, '$.first_name') AS first_name,
                   json_extract(u.data_json, '$.username')   AS username
            FROM clan_treasury_requests r
            LEFT JOIN users u ON u.uid = r.uid
            WHERE r.clan_id=? AND r.status='pending'
            ORDER BY r.created_ts ASC
        """, (clan_id,)).fetchall()
    return [dict(r) for r in rows]


def approve_withdrawal(creator_uid: int, req_id: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    clan_id = m["clan_id"]
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            req = c.execute(
                "SELECT * FROM clan_treasury_requests WHERE id=? AND status='pending'", (req_id,)
            ).fetchone()
            if not req:
                # Уже обработана (в т.ч. параллельно) или не существует
                return {"ok": False, "error": "req_not_found"}
            if req["clan_id"] != clan_id:
                return {"ok": False, "error": "wrong_clan"}

            # Атомарно: переводим заявку pending -> approved только
            # если она всё ещё pending (rowcount=0 => кто-то её уже
            # обработал между SELECT и этим UPDATE).
            cur = c.execute("""
                UPDATE clan_treasury_requests SET status='approved'
                WHERE id=? AND status='pending'
            """, (req_id,))
            if cur.rowcount == 0:
                return {"ok": False, "error": "req_not_found"}

            # Атомарно списываем из казны только если хватает средств.
            cur = c.execute("""
                UPDATE clans SET treasury=treasury-?
                WHERE id=? AND treasury>=?
            """, (req["amount"], clan_id, req["amount"]))
            if cur.rowcount == 0:
                c.execute("UPDATE clan_treasury_requests SET status='rejected' WHERE id=?", (req_id,))
                return {"ok": False, "error": "not_enough_treasury"}

    from database import get_user, save_user
    with _uid_lock(req["uid"]):
        d = get_user(req["uid"])
        if d:
            d["balance"] = d.get("balance", 0) + req["amount"]
            save_user(req["uid"], d)
    return {"ok": True, "uid": req["uid"], "amount": req["amount"]}


def reject_withdrawal(creator_uid: int, req_id: int) -> dict:
    m = get_member(creator_uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    with _clan_lock(m["clan_id"]):
        with _immediate_tx() as c:
            req = c.execute(
                "SELECT * FROM clan_treasury_requests WHERE id=? AND status='pending'", (req_id,)
            ).fetchone()
            if not req or req["clan_id"] != m["clan_id"]:
                return {"ok": False, "error": "req_not_found"}
            cur = c.execute("""
                UPDATE clan_treasury_requests SET status='rejected'
                WHERE id=? AND status='pending'
            """, (req_id,))
            if cur.rowcount == 0:
                return {"ok": False, "error": "req_not_found"}
    return {"ok": True, "uid": req["uid"]}

# ─────────────────────── ЕЖЕДНЕВНЫЕ ЗАДАНИЯ ──────────────────
# Задание 1: суммарный урон клана по боссу → DAILY_QUEST_DMG_TARGET,
#            награда DAILY_QUEST_DMG_REWARD в казну (один раз в день).
# Задание 2: суммарный урон клана по боссу → DAILY_QUEST_DMG2_TARGET,
#            награда DAILY_QUEST_DMG2_REWARD в казну (один раз в день).
# Задание 3: общее — убийство любого босса любым участником клана,
#            награда DAILY_QUEST_KILL_REWARD в казну (один раз в день).
# Задание 4: суммарный заработок клана в шахте → DAILY_QUEST_MINE1_TARGET,
#            награда DAILY_QUEST_MINE1_REWARD в казну (один раз в день).
# Задание 5: суммарный заработок клана в шахте → DAILY_QUEST_MINE2_TARGET,
#            награда DAILY_QUEST_MINE2_REWARD в казну (один раз в день).
# Задание 6: суммарный заработок клана в шахте → DAILY_QUEST_MINE3_TARGET,
#            награда DAILY_QUEST_MINE3_REWARD в казну (один раз в день).
# Прогресс хранится по дате (UTC), сбрасывается автоматически каждый день,
# т.к. для нового дня создаётся новая строка.

def _today_str() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _ensure_daily_quest_row(c, clan_id: int, date: str) -> None:
    c.execute("""
        INSERT OR IGNORE INTO clan_daily_quests (clan_id, quest_date)
        VALUES (?, ?)
    """, (clan_id, date))


def _ensure_personal_quest_row(c, clan_id: int, uid: int, date: str) -> None:
    c.execute("""
        INSERT OR IGNORE INTO clan_personal_quests (clan_id, uid, quest_date)
        VALUES (?, ?, ?)
    """, (clan_id, uid, date))


def _clan_rank_multiplier_tx(c, clan_id: int) -> int:
    """Множитель сложности заданий текущего ранга клана (внутри транзакции c)."""
    row = c.execute("SELECT rank FROM clans WHERE id=?", (clan_id,)).fetchone()
    return get_clan_rank_multiplier(row["rank"] if row else 1)


def get_daily_quests(clan_id: int) -> dict:
    """Прогресс по ежедневным заданиям клана за сегодня (создаёт запись при первом обращении)."""
    date = _today_str()
    with _conn() as c:
        _ensure_daily_quest_row(c, clan_id, date)
        c.commit()
        row = c.execute(
            "SELECT * FROM clan_daily_quests WHERE clan_id=? AND quest_date=?",
            (clan_id, date)
        ).fetchone()
    return dict(row)


def get_personal_quests(uid: int) -> dict | None:
    """
    Прогресс по ЛИЧНЫМ ежедневным заданиям игрока за сегодня (создаёт
    запись при первом обращении). None, если игрок не состоит в клане.
    """
    m = get_member(uid)
    if not m:
        return None
    clan_id = m["clan_id"]
    date    = _today_str()
    with _conn() as c:
        _ensure_personal_quest_row(c, clan_id, uid, date)
        c.commit()
        row = c.execute(
            "SELECT * FROM clan_personal_quests WHERE clan_id=? AND uid=? AND quest_date=?",
            (clan_id, uid, date)
        ).fetchone()
    return dict(row)


def add_clan_boss_damage(uid: int, damage: int) -> dict:
    """
    Вызывать каждый раз, когда игрок наносит урон боссу.
    Урон суммируется в общий дневной прогресс клана игрока.
    Цели и награды масштабируются множителем ранга клана (x1/x2/x4/x8/x16):
    когда суммарный урон клана за день достигает
    DAILY_QUEST_DMG_TARGET * multiplier, клан получает
    DAILY_QUEST_DMG_REWARD * multiplier в казну (один раз за день).
    Аналогично для второго порога (DMG2).
    """
    if damage <= 0:
        return {"ok": False, "error": "bad_damage"}
    if damage > MAX_SINGLE_BOSS_DAMAGE:
        # Подозрительно большое значение за один вызов — не доверяем,
        # обрезаем, чтобы нельзя было одним вызовом закрыть все
        # дневные задания клана.
        damage = MAX_SINGLE_BOSS_DAMAGE
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    clan_id   = m["clan_id"]
    date      = _today_str()
    rewarded  = False
    rewarded2 = False
    personal_rewarded = False
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            mult = _clan_rank_multiplier_tx(c, clan_id)
            target1, reward1 = DAILY_QUEST_DMG_TARGET  * mult, DAILY_QUEST_DMG_REWARD  * mult
            target2, reward2 = DAILY_QUEST_DMG2_TARGET * mult, DAILY_QUEST_DMG2_REWARD * mult

            _ensure_daily_quest_row(c, clan_id, date)
            c.execute("""
                UPDATE clan_daily_quests SET boss_damage = boss_damage + ?
                WHERE clan_id=? AND quest_date=?
            """, (damage, clan_id, date))
            row = c.execute("""
                SELECT boss_damage, dmg_reward_claimed, dmg2_reward_claimed FROM clan_daily_quests
                WHERE clan_id=? AND quest_date=?
            """, (clan_id, date)).fetchone()
            if row["boss_damage"] >= target1 and not row["dmg_reward_claimed"]:
                cur = c.execute("""
                    UPDATE clan_daily_quests SET dmg_reward_claimed=1
                    WHERE clan_id=? AND quest_date=? AND dmg_reward_claimed=0
                """, (clan_id, date))
                if cur.rowcount:
                    c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",
                              (reward1, clan_id))
                    rewarded = True
            if row["boss_damage"] >= target2 and not row["dmg2_reward_claimed"]:
                cur = c.execute("""
                    UPDATE clan_daily_quests SET dmg2_reward_claimed=1
                    WHERE clan_id=? AND quest_date=? AND dmg2_reward_claimed=0
                """, (clan_id, date))
                if cur.rowcount:
                    c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",
                              (reward2, clan_id))
                    rewarded2 = True
            if rewarded or rewarded2:
                _maybe_rank_up(c, clan_id)

            # ── Личное задание игрока на урон боссу ──
            p_target = PERSONAL_QUEST_DMG_TARGET * mult
            p_reward = PERSONAL_QUEST_DMG_REWARD * mult
            _ensure_personal_quest_row(c, clan_id, uid, date)
            c.execute("""
                UPDATE clan_personal_quests SET boss_damage = boss_damage + ?
                WHERE clan_id=? AND uid=? AND quest_date=?
            """, (damage, clan_id, uid, date))
            p_row = c.execute("""
                SELECT boss_damage, dmg_reward_claimed FROM clan_personal_quests
                WHERE clan_id=? AND uid=? AND quest_date=?
            """, (clan_id, uid, date)).fetchone()
            if p_row["boss_damage"] >= p_target and not p_row["dmg_reward_claimed"]:
                cur = c.execute("""
                    UPDATE clan_personal_quests SET dmg_reward_claimed=1
                    WHERE clan_id=? AND uid=? AND quest_date=? AND dmg_reward_claimed=0
                """, (clan_id, uid, date))
                if cur.rowcount:
                    c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",
                              (p_reward, clan_id))
                    c.execute("UPDATE clan_members SET last_personal_quest_ts=? WHERE uid=?",
                              (int(time.time()), uid))
                    personal_rewarded = True
    return {
        "ok": True, "clan_id": clan_id,
        "rewarded": rewarded, "reward": reward1,
        "rewarded2": rewarded2, "reward2": reward2,
        "personal_rewarded": personal_rewarded,
    }


def add_clan_mine_earnings(uid: int, amount: int) -> dict:
    """
    Вызывать каждый раз, когда игрок продаёт руду / зарабатывает монеты в шахте.
    Сумма суммируется в общий дневной прогресс клана игрока.
    Пороговые задания (нарастающие, кланом суммарно за день), цели и
    награды масштабируются множителем ранга клана (x1/x2/x4/x8/x16):
      DAILY_QUEST_MINE1_TARGET * mult → DAILY_QUEST_MINE1_REWARD * mult в казну
      DAILY_QUEST_MINE2_TARGET * mult → DAILY_QUEST_MINE2_REWARD * mult в казну
      DAILY_QUEST_MINE3_TARGET * mult → DAILY_QUEST_MINE3_REWARD * mult в казну
    Каждая награда выдаётся один раз за день.
    """
    if amount <= 0:
        return {"ok": False, "error": "bad_amount"}
    if amount > MAX_SINGLE_MINE_AMOUNT:
        amount = MAX_SINGLE_MINE_AMOUNT
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    clan_id = m["clan_id"]
    date    = _today_str()
    total_reward = 0
    rewarded_tiers = []
    personal_rewarded = False
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            mult = _clan_rank_multiplier_tx(c, clan_id)
            _ensure_daily_quest_row(c, clan_id, date)
            c.execute("""
                UPDATE clan_daily_quests SET mine_earned = mine_earned + ?
                WHERE clan_id=? AND quest_date=?
            """, (amount, clan_id, date))
            row = c.execute("""
                SELECT mine_earned, mine1_reward_claimed, mine2_reward_claimed, mine3_reward_claimed
                FROM clan_daily_quests WHERE clan_id=? AND quest_date=?
            """, (clan_id, date)).fetchone()
            earned = row["mine_earned"]
            tiers = [
                (DAILY_QUEST_MINE1_TARGET * mult, DAILY_QUEST_MINE1_REWARD * mult, "mine1_reward_claimed", row["mine1_reward_claimed"]),
                (DAILY_QUEST_MINE2_TARGET * mult, DAILY_QUEST_MINE2_REWARD * mult, "mine2_reward_claimed", row["mine2_reward_claimed"]),
                (DAILY_QUEST_MINE3_TARGET * mult, DAILY_QUEST_MINE3_REWARD * mult, "mine3_reward_claimed", row["mine3_reward_claimed"]),
            ]
            for target, reward, col, claimed in tiers:
                if earned >= target and not claimed:
                    cur = c.execute(f"""
                        UPDATE clan_daily_quests SET {col}=1
                        WHERE clan_id=? AND quest_date=? AND {col}=0
                    """, (clan_id, date))
                    if cur.rowcount:
                        c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?", (reward, clan_id))
                        total_reward += reward
                        rewarded_tiers.append(target)
            if total_reward:
                _maybe_rank_up(c, clan_id)

            # ── Личное задание игрока на заработок в шахте ──
            p_target = PERSONAL_QUEST_MINE_TARGET * mult
            p_reward = PERSONAL_QUEST_MINE_REWARD * mult
            _ensure_personal_quest_row(c, clan_id, uid, date)
            c.execute("""
                UPDATE clan_personal_quests SET mine_earned = mine_earned + ?
                WHERE clan_id=? AND uid=? AND quest_date=?
            """, (amount, clan_id, uid, date))
            p_row = c.execute("""
                SELECT mine_earned, mine_reward_claimed FROM clan_personal_quests
                WHERE clan_id=? AND uid=? AND quest_date=?
            """, (clan_id, uid, date)).fetchone()
            if p_row["mine_earned"] >= p_target and not p_row["mine_reward_claimed"]:
                cur = c.execute("""
                    UPDATE clan_personal_quests SET mine_reward_claimed=1
                    WHERE clan_id=? AND uid=? AND quest_date=? AND mine_reward_claimed=0
                """, (clan_id, uid, date))
                if cur.rowcount:
                    c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",
                              (p_reward, clan_id))
                    c.execute("UPDATE clan_members SET last_personal_quest_ts=? WHERE uid=?",
                              (int(time.time()), uid))
                    personal_rewarded = True
    return {
        "ok": True, "clan_id": clan_id,
        "rewarded_tiers": rewarded_tiers, "total_reward": total_reward,
        "personal_rewarded": personal_rewarded,
    }


def register_clan_boss_kill(uid: int) -> dict:
    """
    Вызывать каждый раз, когда игрок убивает босса.
    Задание общее на весь клан: нужно суммарно DAILY_QUEST_KILL_BASE_TARGET *
    multiplier убийств боссов (любыми участниками) за день — на ранге 1
    достаточно 1 килла, на ранге 5 нужно уже 16. Награда
    DAILY_QUEST_KILL_REWARD * multiplier выдаётся один раз за день,
    как только цель достигнута.
    """
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    clan_id  = m["clan_id"]
    date     = _today_str()
    rewarded = False
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            mult   = _clan_rank_multiplier_tx(c, clan_id)
            target = DAILY_QUEST_KILL_BASE_TARGET * mult
            reward = DAILY_QUEST_KILL_REWARD * mult

            _ensure_daily_quest_row(c, clan_id, date)
            c.execute("""
                UPDATE clan_daily_quests SET boss_kills = boss_kills + 1
                WHERE clan_id=? AND quest_date=?
            """, (clan_id, date))
            row = c.execute("""
                SELECT boss_kills, kill_reward_claimed FROM clan_daily_quests
                WHERE clan_id=? AND quest_date=?
            """, (clan_id, date)).fetchone()
            if row["boss_kills"] >= target and not row["kill_reward_claimed"]:
                cur = c.execute("""
                    UPDATE clan_daily_quests SET kill_reward_claimed=1
                    WHERE clan_id=? AND quest_date=? AND kill_reward_claimed=0
                """, (clan_id, date))
                if cur.rowcount:
                    c.execute("UPDATE clans SET treasury=treasury+? WHERE id=?",
                              (reward, clan_id))
                    rewarded = True
                    _maybe_rank_up(c, clan_id)
    return {"ok": True, "clan_id": clan_id, "rewarded": rewarded, "reward": reward}


def add_clan_antimatter(uid: int, tier_key: str) -> dict:
    """
    Вызывать каждый раз, когда игрок убивает босса — начисляет клану
    антиматерию в зависимости от сложности убитого босса:
      простой (easy)   -> 1  антиматерия
      средний (medium) -> 3  антиматерии
      сложный (hard)   -> 10 антиматерий
    Антиматерия — отдельный ресурс клана (не казна), тратится только
    на прокачку уровня клана через level_up_clan().
    """
    amount = ANTIMATTER_REWARD_BY_TIER.get(tier_key)
    if not amount:
        return {"ok": False, "error": "bad_tier"}
    m = get_member(uid)
    if not m:
        return {"ok": False, "error": "not_in_clan"}
    clan_id = m["clan_id"]
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            c.execute("UPDATE clans SET antimatter=antimatter+? WHERE id=?", (amount, clan_id))
    return {"ok": True, "clan_id": clan_id, "amount": amount}


def level_up_clan(uid: int) -> dict:
    """
    Повышает уровень клана, списывая антиматерию из её баланса у клана.
    Доступно только создателю клана. Стоимость по уровням:
      2 уровень — 15 антиматерий
      3 уровень — 125 антиматерий
      4 уровень — 350 антиматерий
      5 уровень — 1000 антиматерий (максимум)
    Атомарно: UPDATE с проверкой level/antimatter в WHERE, чтобы
    исключить дюп при параллельных нажатиях.
    """
    m = get_member(uid)
    if not m or m["role"] != "creator":
        return {"ok": False, "error": "not_creator"}
    clan_id = m["clan_id"]
    with _clan_lock(clan_id):
        with _immediate_tx() as c:
            row = c.execute(
                "SELECT level, antimatter FROM clans WHERE id=?", (clan_id,)
            ).fetchone()
            if not row:
                return {"ok": False, "error": "not_in_clan"}
            cur_level  = row["level"] or 1
            antimatter = row["antimatter"] or 0
            cost = CLAN_LEVEL_UP_COST.get(cur_level + 1)
            if cost is None:
                return {"ok": False, "error": "max_level"}
            if antimatter < cost:
                return {
                    "ok": False, "error": "not_enough_antimatter",
                    "cost": cost, "have": antimatter,
                }
            cur = c.execute("""
                UPDATE clans SET level=level+1, antimatter=antimatter-?
                WHERE id=? AND level=? AND antimatter>=?
            """, (cost, clan_id, cur_level, cost))
            if cur.rowcount == 0:
                return {"ok": False, "error": "race_condition"}
    return {"ok": True, "clan_id": clan_id, "new_level": cur_level + 1, "cost": cost}


# ---------- Async-обёртки ----------
# sqlite3 в этом модуле синхронный (блокирующий), как и в database.py.
# Прямой вызов любой из функций выше из async-хэндлера или фонового цикла
# останавливает ВЕСЬ event loop бота на время диск-I/O — то есть замирают
# ВСЕ пользователи разом, а не только тот, кто нажал кнопку клана.
# Использовать эти обёртки из любого async-кода вместо прямого вызова
# синхронных версий выше (аналогично aio_-обёрткам в database.py/cdl.py).
#
# *args/**kwargs — передаём аргументы как есть в оригинальную синхронную
# функцию, чтобы не дублировать и не рассинхронизировать сигнатуры вручную.

async def aio_get_member(*args, **kwargs) -> dict | None:
    return await asyncio.to_thread(get_member, *args, **kwargs)


async def aio_get_clan(*args, **kwargs) -> dict | None:
    return await asyncio.to_thread(get_clan, *args, **kwargs)


async def aio_get_clan_members(*args, **kwargs) -> list[dict]:
    return await asyncio.to_thread(get_clan_members, *args, **kwargs)


async def aio_get_member_count(*args, **kwargs) -> int:
    return await asyncio.to_thread(get_member_count, *args, **kwargs)


async def aio_search_clans(*args, **kwargs):
    return await asyncio.to_thread(search_clans, *args, **kwargs)


async def aio_get_top_clans(*args, **kwargs):
    return await asyncio.to_thread(get_top_clans, *args, **kwargs)


async def aio_get_all_clans_stats(*args, **kwargs) -> dict:
    return await asyncio.to_thread(get_all_clans_stats, *args, **kwargs)


async def aio_create_clan(*args, **kwargs) -> dict:
    return await asyncio.to_thread(create_clan, *args, **kwargs)


async def aio_disband_clan(*args, **kwargs) -> dict:
    return await asyncio.to_thread(disband_clan, *args, **kwargs)


async def aio_leave_clan(*args, **kwargs) -> dict:
    return await asyncio.to_thread(leave_clan, *args, **kwargs)


async def aio_kick_member(*args, **kwargs) -> dict:
    return await asyncio.to_thread(kick_member, *args, **kwargs)


async def aio_apply_to_clan(*args, **kwargs) -> dict:
    return await asyncio.to_thread(apply_to_clan, *args, **kwargs)


async def aio_get_applications(*args, **kwargs):
    return await asyncio.to_thread(get_applications, *args, **kwargs)


async def aio_accept_application(*args, **kwargs) -> dict:
    return await asyncio.to_thread(accept_application, *args, **kwargs)


async def aio_reject_application(*args, **kwargs) -> dict:
    return await asyncio.to_thread(reject_application, *args, **kwargs)


async def aio_accept_all_applications(*args, **kwargs) -> dict:
    return await asyncio.to_thread(accept_all_applications, *args, **kwargs)


async def aio_reject_all_applications(*args, **kwargs) -> dict:
    return await asyncio.to_thread(reject_all_applications, *args, **kwargs)


async def aio_deposit_treasury(*args, **kwargs) -> dict:
    return await asyncio.to_thread(deposit_treasury, *args, **kwargs)


async def aio_request_withdrawal(*args, **kwargs) -> dict:
    return await asyncio.to_thread(request_withdrawal, *args, **kwargs)


async def aio_get_withdrawal_requests(*args, **kwargs):
    return await asyncio.to_thread(get_withdrawal_requests, *args, **kwargs)


async def aio_approve_withdrawal(*args, **kwargs) -> dict:
    return await asyncio.to_thread(approve_withdrawal, *args, **kwargs)


async def aio_reject_withdrawal(*args, **kwargs) -> dict:
    return await asyncio.to_thread(reject_withdrawal, *args, **kwargs)


async def aio_set_clan_chat(*args, **kwargs) -> None:
    await asyncio.to_thread(set_clan_chat, *args, **kwargs)


async def aio_remove_clan_chat(*args, **kwargs) -> None:
    await asyncio.to_thread(remove_clan_chat, *args, **kwargs)


async def aio_add_clan_boss_damage(*args, **kwargs) -> dict:
    return await asyncio.to_thread(add_clan_boss_damage, *args, **kwargs)


async def aio_add_clan_mine_earnings(*args, **kwargs) -> dict:
    return await asyncio.to_thread(add_clan_mine_earnings, *args, **kwargs)


async def aio_register_clan_boss_kill(*args, **kwargs) -> dict:
    return await asyncio.to_thread(register_clan_boss_kill, *args, **kwargs)


async def aio_get_daily_quests(*args, **kwargs) -> dict:
    return await asyncio.to_thread(get_daily_quests, *args, **kwargs)


async def aio_get_personal_quests(*args, **kwargs) -> dict | None:
    return await asyncio.to_thread(get_personal_quests, *args, **kwargs)


async def aio_get_clan_mining_bonus_multiplier(*args, **kwargs) -> float:
    return await asyncio.to_thread(get_clan_mining_bonus_multiplier, *args, **kwargs)


async def aio_add_clan_antimatter(*args, **kwargs) -> dict:
    return await asyncio.to_thread(add_clan_antimatter, *args, **kwargs)


async def aio_level_up_clan(*args, **kwargs) -> dict:
    return await asyncio.to_thread(level_up_clan, *args, **kwargs)


def _esc(s) -> str:
    """Экранирует HTML-спецсимволы, чтобы пользовательский текст (имя клана,
    описание, username, причина заявки и т.п.) нельзя было вставить как
    HTML-разметку в сообщения Telegram (parse_mode='HTML')."""
    if s is None:
        return ""
    return _html.escape(str(s), quote=False)


def _name(r: dict) -> str:
    return _esc(r.get("first_name") or r.get("username") or str(r.get("uid", "?")))


def _member_name(r: dict) -> str:
    """Для списка участников: @username, если есть; иначе — ID участника."""
    username = r.get("username")
    if username:
        return f"@{_esc(username)}"
    return _esc(str(r.get("uid", "?")))


def _progress_bar(current: int, target: int, length: int = 10) -> str:
    if target <= 0:
        return "▱" * length
    filled = int(length * min(current, target) / target)
    return "▰" * filled + "▱" * (length - filled)



async def klan_main_text(lang: str = "ru") -> str:
    stats = await aio_get_all_clans_stats()
    e_sword  = _e(_E_SWORD,  "⚔️")
    e_people = _e(_E_PEOPLE, "👥")
    e_chest  = _e(_E_CHEST,  "💰")
    if lang == "en":
        return (
            f'{e_sword} <b>CLANS</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>'
            f'{e_sword} <b>Clans:</b> {stats["total_clans"]}\n'
            f'{e_people} <b>Members:</b> {stats["total_members"]}\n'
            f'{e_chest} <b>Total treasury:</b> {_fmt(stats["total_treasury"])} {COIN}'
            f'</blockquote>\n\n'
            f'<i>Search for a clan or create your own!</i>'
        )
    return (
        f'{e_sword} <b>КЛАНЫ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'{e_sword} <b>Кланов:</b> {stats["total_clans"]}\n'
        f'{e_people} <b>Участников:</b> {stats["total_members"]}\n'
        f'{e_chest} <b>В казнах:</b> {_fmt(stats["total_treasury"])} {COIN}'
        f'</blockquote>\n\n'
        f'<i>Найди клан по душе или создай свой!</i>'
    )


def klan_search_text(query: str, results: list[dict], page: int, total: int, lang: str = "ru") -> str:
    total_pages = max(1, (total + CLANS_PER_PAGE - 1) // CLANS_PER_PAGE)
    q_esc = _esc(query) if query.strip() else ""
    e_search = _e(_E_SEARCH, "🔍")
    e_sword  = _e(_E_SWORD,  "⚔️")
    e_people = _e(_E_PEOPLE, "👥")

    if not results:
        if lang == "en":
            header = f'{e_search} <b>Search: «{q_esc}»</b>' if q_esc else f'{e_search} <b>All Clans</b>'
            return f'{header}\n━━━━━━━━━━━━━━━━━━━━\n\n<blockquote><i>Nothing found.</i></blockquote>'
        header = f'{e_search} <b>Поиск: «{q_esc}»</b>' if q_esc else f'{e_search} <b>Все кланы</b>'
        return f'{header}\n━━━━━━━━━━━━━━━━━━━━\n\n<blockquote><i>Ничего не найдено.</i></blockquote>'

    lines = []
    start = page * CLANS_PER_PAGE
    for i, cl in enumerate(results, start + 1):
        lines.append(
            f'<b>{i}.</b> {e_sword} <b>{_esc(cl["name"])}</b> <code>#{cl["id"]}</code>\n'
            f'    {e_people} <b>{cl["member_count"]}/{MAX_CLAN_MEMBERS}</b> · {COIN} <b>{_fmt(cl["treasury"])}</b>'
        )
    body = "\n\n".join(lines)

    if lang == "en":
        header = f'{e_search} <b>Search: «{q_esc}»</b>' if q_esc else f'{e_search} <b>All Clans</b>'
        return (
            f'{header}\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'<i>Page {page + 1}/{total_pages} · Found: {total}</i>\n\n'
            f'<blockquote>{body}</blockquote>'
        )
    header = f'{e_search} <b>Поиск: «{q_esc}»</b>' if q_esc else f'{e_search} <b>Все кланы</b>'
    return (
        f'{header}\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>Стр. {page + 1}/{total_pages} · Найдено: {total}</i>\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def klan_card_text(clan: dict, member_count: int, lang: str = "ru") -> str:
    desc    = _esc(clan.get("description") or "—")
    name    = _esc(clan["name"])
    from datetime import datetime, timezone
    created = datetime.fromtimestamp(clan["created_ts"], tz=timezone.utc).strftime("%d.%m.%Y")
    e_sword  = _e(_E_SWORD,  "⚔️")
    e_people = _e(_E_PEOPLE, "👥")
    e_chest  = _e(_E_CHEST,  "💰")
    e_star   = _e(_E_STAR,   "📅")
    e_apps   = _e(_E_APPS,   "📋")
    e_chat   = _e("5443038326535759644", "💬")

    chat_id  = clan.get("chat_id")
    chat_un  = clan.get("chat_username")
    chat_ttl = _esc(clan.get("chat_title") or "")

    if chat_id:
        if chat_un:
            chat_line_ru = f'\n{e_chat} <b>Чат:</b> <a href="https://t.me/{chat_un}">{chat_ttl}</a>'
            chat_line_en = f'\n{e_chat} <b>Chat:</b> <a href="https://t.me/{chat_un}">{chat_ttl}</a>'
        else:
            chat_line_ru = f'\n{e_chat} <b>Чат:</b> {chat_ttl} <i>(закрытый)</i>'
            chat_line_en = f'\n{e_chat} <b>Chat:</b> {chat_ttl} <i>(private)</i>'
    else:
        chat_line_ru = ""
        chat_line_en = ""

    if lang == "en":
        return (
            f'{e_sword} <b>{name}</b> <code>#{clan["id"]}</code>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>'
            f'{e_star} <b>Rank:</b> {clan.get("rank") or 1}/{MAX_CLAN_RANK} · {get_clan_rank_info(clan.get("rank") or 1)["name_en"]}\n'
            f'{e_people} <b>Members:</b> {member_count}/{MAX_CLAN_MEMBERS}\n'
            f'{e_chest} <b>Treasury:</b> {_fmt(clan["treasury"])} {COIN}\n'
            f'{e_star} <b>Founded:</b> {created}\n'
            f'{e_apps} <b>About:</b> <i>{desc}</i>'
            f'{chat_line_en}'
            f'</blockquote>'
        )
    return (
        f'{e_sword} <b>{name}</b> <code>#{clan["id"]}</code>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'{e_star} <b>Ранг:</b> {clan.get("rank") or 1}/{MAX_CLAN_RANK} · {get_clan_rank_info(clan.get("rank") or 1)["name_ru"]}\n'
        f'{e_people} <b>Участников:</b> {member_count}/{MAX_CLAN_MEMBERS}\n'
        f'{e_chest} <b>Казна:</b> {_fmt(clan["treasury"])} {COIN}\n'
        f'{e_star} <b>Основан:</b> {created}\n'
        f'{e_apps} <b>О клане:</b> <i>{desc}</i>'
        f'{chat_line_ru}'
        f'</blockquote>'
    )


def _clan_rank_block(clan: dict, member_count: int, lang: str = "ru") -> str:
    """Блок с текущим рангом клана и прогрессом до следующего (для my_klan_text)."""
    rank      = clan.get("rank") or 1
    rank_info = get_clan_rank_info(rank)
    rank_name = rank_info["name_en"] if lang == "en" else rank_info["name_ru"]
    e_star    = _e(_E_STAR, "⭐")
    stars     = "⭐" * rank

    next_info = get_next_rank_info(rank)
    if next_info is None:
        max_label = "Max rank" if lang == "en" else "Максимальный ранг"
        return (
            f'{e_star} <b>{"Rank" if lang=="en" else "Ранг"} {rank}/{MAX_CLAN_RANK} · {rank_name}</b> {stars}\n'
            f'<i>{max_label} — {"quests" if lang=="en" else "задания"} x{rank_info["multiplier"]}</i>'
        )

    treasury = clan.get("treasury", 0)
    need_members  = max(0, next_info["members_required"] - member_count)
    need_treasury = max(0, next_info["treasury_required"] - treasury)
    next_name = next_info["name_en"] if lang == "en" else next_info["name_ru"]

    if lang == "en":
        req_lines = []
        if need_members > 0:
            req_lines.append(f'👥 {member_count}/{next_info["members_required"]} members')
        if need_treasury > 0:
            req_lines.append(f'💰 {_fmt(treasury)}/{_fmt(next_info["treasury_required"])} {COIN}')
        req_text = "  ·  ".join(req_lines) if req_lines else "ready to rank up!"
        return (
            f'{e_star} <b>Rank {rank}/{MAX_CLAN_RANK} · {rank_name}</b> {stars} <i>(quests x{rank_info["multiplier"]})</i>\n'
            f'<i>Next: {next_name} (x{next_info["multiplier"]}) — {req_text}</i>'
        )
    req_lines = []
    if need_members > 0:
        req_lines.append(f'👥 {member_count}/{next_info["members_required"]} участников')
    if need_treasury > 0:
        req_lines.append(f'💰 {_fmt(treasury)}/{_fmt(next_info["treasury_required"])} {COIN}')
    req_text = "  ·  ".join(req_lines) if req_lines else "все условия выполнены!"
    return (
        f'{e_star} <b>Ранг {rank}/{MAX_CLAN_RANK} · {rank_name}</b> {stars} <i>(задания x{rank_info["multiplier"]})</i>\n'
        f'<i>Следующий: {next_name} (x{next_info["multiplier"]}) — {req_text}</i>'
    )


def my_klan_text(clan: dict, member: dict, member_count: int, lang: str = "ru") -> str:
    name     = _esc(clan["name"])
    e_sword  = _e(_E_SWORD,  "⚔️")
    e_crown  = _e(_E_CROWN,  "👑")
    e_people = _e(_E_PEOPLE, "👥")
    e_chest  = _e(_E_CHEST,  "💰")
    e_plus   = _e(_E_PLUS,   "➕")
    e_chat   = _e("5443038326535759644", "💬")

    chat_id  = clan.get("chat_id")
    chat_un  = clan.get("chat_username")
    chat_ttl = _esc(clan.get("chat_title") or "")

    if chat_id:
        if chat_un:
            chat_line_ru = f'\n{e_chat} <b>Чат клана:</b> <a href="https://t.me/{chat_un}">{chat_ttl}</a>'
            chat_line_en = f'\n{e_chat} <b>Clan chat:</b> <a href="https://t.me/{chat_un}">{chat_ttl}</a>'
        else:
            chat_line_ru = f'\n{e_chat} <b>Чат клана:</b> {chat_ttl} <i>(закрытый)</i>'
            chat_line_en = f'\n{e_chat} <b>Clan chat:</b> {chat_ttl} <i>(private)</i>'
    else:
        chat_line_ru = ""
        chat_line_en = ""

    rank_block  = _clan_rank_block(clan, member_count, lang)
    level_block = _clan_level_block(clan, lang)
    bonus_block = _clan_bonus_block(clan, member, lang)

    if lang == "en":
        role_label = f'{e_crown} <b>Creator</b>' if member['role'] == 'creator' else '<tg-emoji emoji-id="5452085950022707790">⭐</tg-emoji> <b>Member</b>'
        return (
            f'{e_sword} <b>{name}</b> <code>#{clan["id"]}</code>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5848400681416793625">⭐</tg-emoji> <b>Your role:</b> {role_label}\n'
            f'{e_people} <b>Members:</b> {member_count}/{MAX_CLAN_MEMBERS}\n'
            f'{e_chest} <b>Treasury:</b> {_fmt(clan["treasury"])} {COIN}\n'
            f'{e_plus} <b>Your contribution:</b> {_fmt(member["contributed"])} {COIN}'
            f'{chat_line_en}'
            f'</blockquote>\n'
            f'<blockquote>{rank_block}</blockquote>\n'
            f'<blockquote>{level_block}</blockquote>\n'
            f'<blockquote>{bonus_block}</blockquote>'
        )
    role_label = f'{e_crown} <b>Создатель</b>' if member['role'] == 'creator' else '<tg-emoji emoji-id="5452085950022707790">⭐</tg-emoji> <b>Участник</b>'
    return (
        f'{e_sword} <b>{name}</b> <code>#{clan["id"]}</code>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5848400681416793625">⭐</tg-emoji> <b>Твоя роль:</b> {role_label}\n'
        f'{e_people} <b>Участников:</b> {member_count}/{MAX_CLAN_MEMBERS}\n'
        f'{e_chest} <b>Казна:</b> {_fmt(clan["treasury"])} {COIN}\n'
        f'{e_plus} <b>Твой вклад:</b> {_fmt(member["contributed"])} {COIN}'
        f'{chat_line_ru}'
        f'</blockquote>\n'
        f'<blockquote>{rank_block}</blockquote>\n'
        f'<blockquote>{level_block}</blockquote>\n'
        f'<blockquote>{bonus_block}</blockquote>'
    )




def klan_members_text(clan: dict, members: list[dict], lang: str = "ru") -> str:
    e_people = _e(_E_PEOPLE, "👥")
    e_crown  = _e(_E_CROWN,  "👑")
    lines = []
    for m in members:
        icon = e_crown if m["role"] == "creator" else '<tg-emoji emoji-id="5452085950022707790">⭐</tg-emoji>'
        lines.append(f'{icon} <b>{_member_name(m)}</b> — {COIN} <b>{_fmt(m["contributed"])}</b>')
    body = "\n".join(lines) if lines else "<i>—</i>"
    name = _esc(clan["name"])
    if lang == "en":
        return (
            f'{e_people} <b>{name} — Members</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>{body}</blockquote>'
        )
    return (
        f'{e_people} <b>{name} — Участники</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def _clan_level_block(clan: dict, lang: str = "ru") -> str:
    """Блок с уровнем клана, балансом антиматерии и стоимостью следующего уровня."""
    level      = clan.get("level") or 1
    antimatter = clan.get("antimatter") or 0
    next_cost  = get_clan_level_up_cost(level)
    if lang == "en":
        if next_cost is None:
            status = "<i>Max level</i>"
        else:
            status = f'<i>Next level {level + 1}: {antimatter}/{next_cost} {ANTIMATTER}</i>'
        return (
            f'{ANTIMATTER} <b>Level {level}/{MAX_CLAN_LEVEL}</b> · '
            f'<b>Antimatter:</b> {_fmt(antimatter)}\n{status}'
        )
    if next_cost is None:
        status = "<i>Максимальный уровень</i>"
    else:
        status = f'<i>Следующий уровень {level + 1}: {antimatter}/{next_cost} {ANTIMATTER}</i>'
    return (
        f'{ANTIMATTER} <b>Уровень {level}/{MAX_CLAN_LEVEL}</b> · '
        f'<b>Антиматерия:</b> {_fmt(antimatter)}\n{status}'
    )


def _clan_bonus_block(clan: dict, member: dict, lang: str = "ru") -> str:
    """Блок статуса кланового бонуса на добычу (для my_klan_text)."""
    info      = get_clan_bonus_info(clan, member)
    mult_str  = f'{info["base_multiplier"]:g}'
    e_boost   = _e(_E_CLAN_BONUS, "🚀")
    if lang == "en":
        title = f'{e_boost} <b>Clan bonus: ×{mult_str} mining</b>'
        if info["active"]:
            return (
                f'{title} — <b>ACTIVE ✅</b>\n'
                f'<i>Stays active while you complete at least one clan personal quest every 24h</i>'
            )
        return (
            f'{title} — <b>NOT ACTIVE ❌</b>\n'
            f'<i>To activate: complete at least 1 clan personal quest (see «Daily quests») in the last 24 hours</i>'
        )
    title = f'{e_boost} <b>Клановый бонус: ×{mult_str} к добыче</b>'
    if info["active"]:
        return (
            f'{title} — <b>АКТИВЕН ✅</b>\n'
            f'<i>Бонус держится, пока ты выполняешь хотя бы одно личное клановое задание раз в 24 часа</i>'
        )
    return (
        f'{title} — <b>НЕ АКТИВЕН ❌</b>\n'
        f'<i>Условие активации: выполни хотя бы 1 личное клановое задание (раздел «Ежедневные задания») за последние 24 часа</i>'
    )


def klan_treasury_text(clan: dict, lang: str = "ru") -> str:
    name    = _esc(clan["name"])
    e_chest = _e(_E_CHEST, "💰")
    e_plus  = _e(_E_PLUS,  "➕")
    e_stats = _e(_E_STATS, "📊")
    level_block = _clan_level_block(clan, lang)
    if lang == "en":
        return (
            f'{e_chest} <b>{name} — Treasury</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>'
            f'{e_chest} <b>Balance:</b> {_fmt(clan["treasury"])} {COIN}'
            f'</blockquote>\n'
            f'<blockquote>{level_block}</blockquote>\n\n'
            f'<i>{e_plus} Deposit to grow the treasury\n'
            f'<tg-emoji emoji-id="5445355530111437729">⭐</tg-emoji> Withdrawals require creator approval\n'
            f'{ANTIMATTER} Antimatter drops from bosses and levels up the clan</i>'
        )
    return (
        f'{e_chest} <b>{name} — Казна</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'{e_chest} <b>Баланс:</b> {_fmt(clan["treasury"])} {COIN}'
        f'</blockquote>\n'
        f'<blockquote>{level_block}</blockquote>\n\n'
        f'<i>{e_plus} Пополни казну клана\n'
        f'<tg-emoji emoji-id="5445355530111437729">⭐</tg-emoji> Вывод средств требует одобрения создателя\n'
        f'{ANTIMATTER} Антиматерия падает с боссов и прокачивает уровень клана</i>'
    )


def klan_applications_text(clan: dict, apps: list[dict], page: int, total: int, lang: str = "ru") -> str:
    name        = _esc(clan["name"])
    total_pages = max(1, (total + APPS_PER_PAGE - 1) // APPS_PER_PAGE)
    e_apps      = _e(_E_APPS, "📋")

    if not apps:
        if lang == "en":
            return (
                f'{e_apps} <b>{name} — Applications</b>\n'
                f'━━━━━━━━━━━━━━━━━━━━\n\n'
                f'<blockquote><i>No pending applications.</i></blockquote>'
            )
        return (
            f'{e_apps} <b>{name} — Заявки</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote><i>Нет входящих заявок.</i></blockquote>'
        )

    lines = []
    start = page * APPS_PER_PAGE
    for i, a in enumerate(apps, start + 1):
        msg = f'\n    <i>«{_esc(a["message"])}»</i>' if a.get("message") else ""
        lines.append(f'<b>{i}.</b> <tg-emoji emoji-id="5452085950022707790">⭐</tg-emoji> <b>{_name(a)}</b>{msg}')
    body = "\n\n".join(lines)

    if lang == "en":
        return (
            f'{e_apps} <b>{name} — Applications</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'<i>Page {page + 1}/{total_pages} · Total: {total}</i>\n\n'
            f'<blockquote>{body}</blockquote>'
        )
    return (
        f'{e_apps} <b>{name} — Заявки</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>Стр. {page + 1}/{total_pages} · Всего: {total}</i>\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def _rank_emoji(i: int) -> str:
    """Возвращает HTML-эмодзи для места в топе (1-10)."""
    ranks = {
        1: (_E_RANK_1, "🥇"), 2: (_E_RANK_2, "🥈"), 3: (_E_RANK_3, "🥉"),
        4: (_E_RANK_4, "4️⃣"), 5: (_E_RANK_5, "5️⃣"), 6: (_E_RANK_6, "6️⃣"),
        7: (_E_RANK_7, "7️⃣"), 8: (_E_RANK_8, "8️⃣"), 9: (_E_RANK_9, "9️⃣"),
    }
    if i in ranks:
        eid, fb = ranks[i]
        return _e(eid, fb)
    if i == 10:
        return _e(_E_DIGIT_1, "1️⃣") + _e(_E_DIGIT_0, "0️⃣")
    return f"{i}."

def klan_top_text(clans: list[dict], lang: str = "ru") -> str:
    e_trophy = _e(_E_TROPHY, "🏆")
    e_people = _e(_E_PEOPLE, "👥")
    e_chest  = _e(_E_CHEST,  "💰")
    title = "ТОП КЛАНОВ" if lang == "ru" else "TOP CLANS"
    if not clans:
        msg = "Кланов пока нет." if lang == "ru" else "No clans yet."
        return (
            f'{e_trophy} <b>{title}</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote><i>{msg}</i></blockquote>'
        )
    lines = []
    for i, cl in enumerate(clans, 1):
        place = _rank_emoji(i)
        clan_rank = cl.get("rank") or 1
        rank_badge = "⭐" * clan_rank
        lines.append(
            f'{place} <b>{_esc(cl["name"])}</b> {rank_badge}\n'
            f'    {e_people} <b>{cl["member_count"]}</b> · {e_chest} <b>{_fmt(cl["treasury"])}</b> {COIN}'
        )
    body = "\n\n".join(lines)
    return (
        f'{e_trophy} <b>{title}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{body}</blockquote>'
    )


async def klan_stats_text(lang: str = "ru") -> str:
    stats    = await aio_get_all_clans_stats()
    e_stats  = _e(_E_STATS,  "📊")
    e_sword  = _e(_E_SWORD,  "⚔️")
    e_people = _e(_E_PEOPLE, "👥")
    e_chest  = _e(_E_CHEST,  "💰")
    if lang == "en":
        return (
            f'{e_stats} <b>CLAN STATS</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote>'
            f'{e_sword} <b>Total clans:</b> {stats["total_clans"]}\n'
            f'{e_people} <b>Total members:</b> {stats["total_members"]}\n'
            f'{e_chest} <b>All treasuries:</b> {_fmt(stats["total_treasury"])} {COIN}'
            f'</blockquote>'
        )
    return (
        f'{e_stats} <b>СТАТИСТИКА КЛАНОВ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'{e_sword} <b>Всего кланов:</b> {stats["total_clans"]}\n'
        f'{e_people} <b>Всего участников:</b> {stats["total_members"]}\n'
        f'{e_chest} <b>Все казны:</b> {_fmt(stats["total_treasury"])} {COIN}'
        f'</blockquote>'
    )


def klan_withdrawal_requests_text(clan: dict, reqs: list[dict], lang: str = "ru") -> str:
    name    = _esc(clan["name"])
    e_chest = _e(_E_CHEST, "💰")
    e_stats = _e(_E_STATS, "📊")
    if lang == "en":
        title = f'{name} — Withdrawal Requests'
    else:
        title = f'{name} — Запросы на вывод'
    if not reqs:
        msg = "No pending requests." if lang == "en" else "Нет ожидающих запросов."
        return (
            f'{e_chest} <b>{title}</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'<blockquote><i>{msg}</i></blockquote>'
        )
    lines = []
    for r in reqs:
        reason = f'<i>«{_esc(r["reason"])}»</i>' if r.get("reason") else "<i>—</i>"
        lines.append(f'<tg-emoji emoji-id="5452085950022707790">⭐</tg-emoji> <b>{_name(r)}</b> — {COIN} <b>{_fmt(r["amount"])}</b>\n    {reason}')
    body = "\n\n".join(lines)
    hint = 'Нажми ✅ чтобы одобрить · ❌ отклонить' if lang == "ru" else 'Tap ✅ to approve · ❌ to reject'
    return (
        f'{e_chest} <b>{title}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{body}</blockquote>\n\n'
        f'<i>{e_stats} {hint}</i>'
    )


def _personal_quests_block(clan: dict, personal: dict | None, member: dict | None, lang: str = "ru") -> str:
    """Блок с личными ежедневными заданиями игрока + статус кланового бонуса."""
    e_chest = _e(_E_CHEST, "💰")
    e_check = _e(_E_CHECK, "✅")
    e_cross = _e(_E_CROSS, "❌")

    rank = clan.get("rank") or 1
    mult = get_clan_rank_multiplier(rank)
    p_dmg_target,  p_dmg_reward  = PERSONAL_QUEST_DMG_TARGET  * mult, PERSONAL_QUEST_DMG_REWARD  * mult
    p_mine_target, p_mine_reward = PERSONAL_QUEST_MINE_TARGET * mult, PERSONAL_QUEST_MINE_REWARD * mult

    personal = personal or {}
    p_dmg       = personal.get("boss_damage", 0)
    p_dmg_done  = bool(personal.get("dmg_reward_claimed", 0))
    p_mine      = personal.get("mine_earned", 0)
    p_mine_done = bool(personal.get("mine_reward_claimed", 0))

    dmg_icon  = e_check if p_dmg_done  else e_cross
    mine_icon = e_check if p_mine_done else e_cross
    dmg_bar   = _progress_bar(p_dmg, p_dmg_target)
    mine_bar  = _progress_bar(p_mine, p_mine_target)

    bonus_line = _clan_bonus_block(clan, member or {}, lang) if member is not None else ""

    if lang == "en":
        body = (
            f'{dmg_icon} <b>1. Deal {_fmt(p_dmg_target)} damage to the boss (yourself)</b>\n'
            f'    {dmg_bar}\n'
            f'    {_fmt(min(p_dmg, p_dmg_target))} / {_fmt(p_dmg_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(p_dmg_reward)}</b> {COIN} to clan treasury\n\n'
            f'{mine_icon} <b>2. Earn {_fmt(p_mine_target)} {COIN} from the mine (yourself)</b>\n'
            f'    {mine_bar}\n'
            f'    {_fmt(min(p_mine, p_mine_target))} / {_fmt(p_mine_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(p_mine_reward)}</b> {COIN} to clan treasury\n\n'
            f'<i>Personal quests — only your own progress counts. Completing at least one'
            f' unlocks the clan mining bonus for 24h.</i>'
        )
        header = f'<b>Personal quests</b>'
    else:
        body = (
            f'{dmg_icon} <b>1. Нанести {_fmt(p_dmg_target)} урона боссу (лично)</b>\n'
            f'    {dmg_bar}\n'
            f'    {_fmt(min(p_dmg, p_dmg_target))} / {_fmt(p_dmg_target)}\n'
            f'    {e_chest} Награда: <b>{_fmt(p_dmg_reward)}</b> {COIN} в казну клана\n\n'
            f'{mine_icon} <b>2. Заработать {_fmt(p_mine_target)} {COIN} с шахты (лично)</b>\n'
            f'    {mine_bar}\n'
            f'    {_fmt(min(p_mine, p_mine_target))} / {_fmt(p_mine_target)}\n'
            f'    {e_chest} Награда: <b>{_fmt(p_mine_reward)}</b> {COIN} в казну клана\n\n'
            f'<i>Личные задания — считается только твой собственный прогресс. Выполнение'
            f' хотя бы одного включает клановый бонус на добычу на 24 часа.</i>'
        )
        header = f'<b>Личные задания</b>'

    block = f'{header}\n<blockquote>{body}</blockquote>'
    if bonus_line:
        block += f'\n<blockquote>{bonus_line}</blockquote>'
    return block


def klan_quests_text(clan: dict, quests: dict, lang: str = "ru", personal: dict | None = None, member: dict | None = None) -> str:
    name    = _esc(clan["name"])
    e_hunt  = _e(_E_HUNT,  "🗡")
    e_chest = _e(_E_CHEST, "💰")
    e_check = _e(_E_CHECK, "✅")
    e_cross = _e(_E_CROSS, "❌")
    e_star  = _e(_E_STAR,  "⭐")

    rank      = clan.get("rank") or 1
    rank_info = get_clan_rank_info(rank)
    mult      = rank_info["multiplier"]
    rank_name = rank_info["name_en"] if lang == "en" else rank_info["name_ru"]

    # Все цели/награды масштабируются множителем текущего ранга клана
    dmg_target,   dmg_reward   = DAILY_QUEST_DMG_TARGET   * mult, DAILY_QUEST_DMG_REWARD   * mult
    dmg2_target,  dmg2_reward  = DAILY_QUEST_DMG2_TARGET  * mult, DAILY_QUEST_DMG2_REWARD  * mult
    kill_target,  kill_reward  = DAILY_QUEST_KILL_BASE_TARGET * mult, DAILY_QUEST_KILL_REWARD * mult
    mine1_target, mine1_reward = DAILY_QUEST_MINE1_TARGET * mult, DAILY_QUEST_MINE1_REWARD * mult
    mine2_target, mine2_reward = DAILY_QUEST_MINE2_TARGET * mult, DAILY_QUEST_MINE2_REWARD * mult
    mine3_target, mine3_reward = DAILY_QUEST_MINE3_TARGET * mult, DAILY_QUEST_MINE3_REWARD * mult

    dmg        = quests["boss_damage"]
    dmg_done   = bool(quests["dmg_reward_claimed"])
    kills      = quests.get("boss_kills", 0)
    kill_done  = bool(quests["kill_reward_claimed"])
    dmg2_done  = bool(quests.get("dmg2_reward_claimed", 0))
    mine       = quests.get("mine_earned", 0)
    mine1_done = bool(quests.get("mine1_reward_claimed", 0))
    mine2_done = bool(quests.get("mine2_reward_claimed", 0))
    mine3_done = bool(quests.get("mine3_reward_claimed", 0))

    dmg_icon   = e_check if dmg_done   else e_cross
    kill_icon  = e_check if kill_done  else e_cross
    dmg2_icon  = e_check if dmg2_done  else e_cross
    mine1_icon = e_check if mine1_done else e_cross
    mine2_icon = e_check if mine2_done else e_cross
    mine3_icon = e_check if mine3_done else e_cross

    dmg_bar    = _progress_bar(dmg, dmg_target)
    dmg_shown  = min(dmg, dmg_target)
    dmg2_bar   = _progress_bar(dmg, dmg2_target)
    dmg2_shown = min(dmg, dmg2_target)

    mine1_bar   = _progress_bar(mine, mine1_target)
    mine1_shown = min(mine, mine1_target)
    mine2_bar   = _progress_bar(mine, mine2_target)
    mine2_shown = min(mine, mine2_target)
    mine3_bar   = _progress_bar(mine, mine3_target)
    mine3_shown = min(mine, mine3_target)

    kill_bar    = _progress_bar(kills, kill_target)
    kill_shown  = min(kills, kill_target)

    rank_line_en = f'{e_star} <b>Rank {rank}/{MAX_CLAN_RANK} · {rank_name}</b> — quests x{mult}'
    rank_line_ru = f'{e_star} <b>Ранг {rank}/{MAX_CLAN_RANK} · {rank_name}</b> — задания x{mult}'

    if lang == "en":
        kill_line = (
            f'    <i>Shared quest — counts for any clan member</i>'
            if kill_target <= 1 else
            f'    {kill_bar}\n    {kill_shown} / {kill_target} kills\n'
            f'    <i>Shared quest — counts for any clan member</i>'
        )
        personal_block = _personal_quests_block(clan, personal, member, lang)
        return (
            f'{e_hunt} <b>{name} — Daily Quests</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'{rank_line_en}\n\n'
            f'<b>Shared quests (whole clan)</b>\n'
            f'<blockquote>'
            f'{dmg_icon} <b>1. Deal {_fmt(dmg_target)} damage to the boss</b>\n'
            f'    {dmg_bar}\n'
            f'    {_fmt(dmg_shown)} / {_fmt(dmg_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(dmg_reward)}</b> {COIN} to clan treasury\n\n'
            f'{dmg2_icon} <b>2. Deal {_fmt(dmg2_target)} damage to the boss</b>\n'
            f'    {dmg2_bar}\n'
            f'    {_fmt(dmg2_shown)} / {_fmt(dmg2_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(dmg2_reward)}</b> {COIN} to clan treasury\n\n'
            f'{kill_icon} <b>3. Defeat {kill_target} boss(es)</b>\n'
            f'{kill_line}\n'
            f'    {e_chest} Reward: <b>{_fmt(kill_reward)}</b> {COIN} to clan treasury\n\n'
            f'{mine1_icon} <b>4. Earn {_fmt(mine1_target)} {COIN} from the mine</b>\n'
            f'    {mine1_bar}\n'
            f'    {_fmt(mine1_shown)} / {_fmt(mine1_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(mine1_reward)}</b> {COIN} to clan treasury\n\n'
            f'{mine2_icon} <b>5. Earn {_fmt(mine2_target)} {COIN} from the mine</b>\n'
            f'    {mine2_bar}\n'
            f'    {_fmt(mine2_shown)} / {_fmt(mine2_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(mine2_reward)}</b> {COIN} to clan treasury\n\n'
            f'{mine3_icon} <b>6. Earn {_fmt(mine3_target)} {COIN} from the mine</b>\n'
            f'    {mine3_bar}\n'
            f'    {_fmt(mine3_shown)} / {_fmt(mine3_target)}\n'
            f'    {e_chest} Reward: <b>{_fmt(mine3_reward)}</b> {COIN} to clan treasury'
            f'</blockquote>\n\n'
            f'{personal_block}\n\n'
            f'<i>Quests reset every day at 00:00 UTC · higher clan rank = harder quests, bigger rewards</i>'
        )
    kill_line = (
        f'    <i>Общее задание — засчитывается любому участнику клана</i>'
        if kill_target <= 1 else
        f'    {kill_bar}\n    {kill_shown} / {kill_target} убийств\n'
        f'    <i>Общее задание — засчитывается любому участнику клана</i>'
    )
    personal_block = _personal_quests_block(clan, personal, member, lang)
    return (
        f'{e_hunt} <b>{name} — Ежедневные задания</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'{rank_line_ru}\n\n'
        f'<b>Общие задания (весь клан)</b>\n'
        f'<blockquote>'
        f'{dmg_icon} <b>1. Нанести {_fmt(dmg_target)} урона боссу</b>\n'
        f'    {dmg_bar}\n'
        f'    {_fmt(dmg_shown)} / {_fmt(dmg_target)}\n'
        f'    {e_chest} Награда: <b>{_fmt(dmg_reward)}</b> {COIN} в казну клана\n\n'
        f'{dmg2_icon} <b>2. Нанести {_fmt(dmg2_target)} урона боссу</b>\n'
        f'    {dmg2_bar}\n'
        f'    {_fmt(dmg2_shown)} / {_fmt(dmg2_target)}\n'
        f'    {e_chest} Награда: <b>{_fmt(dmg2_reward)}</b> {COIN} в казну клана\n\n'
        f'{kill_icon} <b>3. Убить {kill_target} босса(ов)</b>\n'
        f'{kill_line}\n'
        f'    {e_chest} Награда: <b>{_fmt(kill_reward)}</b> {COIN} в казну клана\n\n'
        f'{mine1_icon} <b>4. Заработать {_fmt(mine1_target)} {COIN} с шахты</b>\n'
        f'    {mine1_bar}\n'
        f'    {_fmt(mine1_shown)} / {_fmt(mine1_target)}\n'
        f'    {e_chest} Награда: <b>{_fmt(mine1_reward)}</b> {COIN} в казну клана\n\n'
        f'{mine2_icon} <b>5. Заработать {_fmt(mine2_target)} {COIN} с шахты</b>\n'
        f'    {mine2_bar}\n'
        f'    {_fmt(mine2_shown)} / {_fmt(mine2_target)}\n'
        f'    {e_chest} Награда: <b>{_fmt(mine2_reward)}</b> {COIN} в казну клана\n\n'
        f'{mine3_icon} <b>6. Заработать {_fmt(mine3_target)} {COIN} с шахты</b>\n'
        f'    {mine3_bar}\n'
        f'    {_fmt(mine3_shown)} / {_fmt(mine3_target)}\n'
        f'    {e_chest} Награда: <b>{_fmt(mine3_reward)}</b> {COIN} в казну клана'
        f'</blockquote>\n\n'
        f'{personal_block}\n\n'
        f'<i>Задания обновляются каждый день в 00:00 UTC · чем выше ранг клана, тем сложнее задания и больше награда</i>'
    )


# ─────────────────────── КЛАВИАТУРЫ ──────────────────────────

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _btn(text: str, cb: str, eid: str | None = None) -> InlineKeyboardButton:
    if eid:
        return InlineKeyboardButton(text=text, callback_data=cb, icon_custom_emoji_id=eid)
    return InlineKeyboardButton(text=text, callback_data=cb)


def _back_btn(cb: str, lang: str = "ru") -> InlineKeyboardButton:
    label = "Назад" if lang == "ru" else "Back"
    return InlineKeyboardButton(text=label, callback_data=cb, icon_custom_emoji_id=_E_BACK)


async def klan_main_keyboard(uid: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Главное меню кланов — без кнопки «Назад».
    Возврат через кнопку Reply-клавиатуры «🎮 Меню».
    """
    member = await aio_get_member(uid)
    b = InlineKeyboardBuilder()
    if lang == "en":
        b.row(
            _btn("Search",  "klan_search", _E_SEARCH),
            _btn("Top",     "klan_top",    _E_TROPHY),
        )
        if member:
            b.row(_btn("My clan", "klan_my", _E_SWORD))
        else:
            b.row(_btn("Create clan", "klan_create", _E_PLUS))
        b.row(
            _btn("Stats", "klan_stats", _E_STATS),
        )
    else:
        b.row(
            _btn("Поиск",  "klan_search", _E_SEARCH),
            _btn("Топ",    "klan_top",    _E_TROPHY),
        )
        if member:
            b.row(_btn("Мой клан", "klan_my", _E_SWORD))
        else:
            b.row(_btn("Создать клан", "klan_create", _E_PLUS))
        b.row(
            _btn("Статистика", "klan_stats", _E_STATS),
        )
    return b.as_markup()


def klan_search_keyboard(
    results: list[dict],
    query: str,
    page: int,
    total: int,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    b           = InlineKeyboardBuilder()
    total_pages = max(1, (total + CLANS_PER_PAGE - 1) // CLANS_PER_PAGE)
    for cl in results:
        b.row(_btn(
            f'⚔️ {cl["name"]} | 👥{cl["member_count"]} | 💰{_fmt(cl["treasury"])}',
            f'klan_view_{cl["id"]}',
        ))
    # Кнопка поиска
    search_label = "Search by name / ID" if lang == "en" else "Поиск по названию / ID"
    b.row(_btn(search_label, "klan_do_search", _E_SEARCH))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f'klan_search_page_{page - 1}_{query}'))
    if page < total_pages - 1:
        nav.append(_btn("▶️", f'klan_search_page_{page + 1}_{query}'))
    if nav:
        b.row(*nav)
    b.row(_back_btn("klan_main", lang))
    return b.as_markup()


async def klan_card_keyboard(clan_id: int, uid: int, lang: str = "ru") -> InlineKeyboardMarkup:
    b      = InlineKeyboardBuilder()
    member = await aio_get_member(uid)
    if not member:
        label = "Apply" if lang == "en" else "Подать заявку"
        b.row(_btn(label, f"klan_apply_{clan_id}", _E_APPS))
    b.row(_back_btn("klan_search", lang))
    return b.as_markup()


async def my_klan_keyboard(uid: int, lang: str = "ru") -> InlineKeyboardMarkup:
    member     = await aio_get_member(uid)
    b          = InlineKeyboardBuilder()
    is_creator = member and member["role"] == "creator"

    # Получаем данные клана для проверки наличия чата
    clan = await aio_get_clan(member["clan_id"]) if member else None
    has_chat = bool(clan and clan.get("chat_id"))

    _E_CHAT = "5443038326535759644"   # 💬 чат клана

    if lang == "en":
        b.row(
            _btn("Members",  "klan_members",  _E_PEOPLE),
            _btn("Treasury", "klan_treasury", _E_CHEST),
        )
        b.row(_btn("Daily quests", "klan_quests", _E_HUNT))
        if is_creator:
            b.row(_btn("Level up clan", "klan_level_up", _E_ANTIMATTER))
        # Кнопка чата (если привязан — для всех, прямая URL-ссылка)
        if has_chat:
            chat_un  = clan.get("chat_username")
            chat_ttl = clan.get("chat_title") or "Clan Chat"
            if chat_un:
                b.row(InlineKeyboardButton(
                    text=chat_ttl,
                    url=f"https://t.me/{chat_un}",
                    icon_custom_emoji_id=_E_CHAT,
                ))
            else:
                b.row(_btn("Clan Chat (private)", "klan_chat_private", _E_CHAT))
        if is_creator:
            b.row(_btn("Applications", "klan_apps", _E_APPS))
            b.row(
                _btn("Withdrawals",    "klan_withdraw_list", _E_CHEST),
                _btn("Kick",          "klan_kick",          _E_CROSS),
            )
            if has_chat:
                b.row(_btn("Unlink Chat", "klan_chat_unlink", _E_CROSS))
            else:
                b.row(_btn("Link Chat", "klan_chat_link", _E_CHAT))
            b.row(_btn("Disband clan", "klan_disband", _E_CROSS))
        else:
            b.row(_btn("Leave clan", "klan_leave", _E_LEAVE))
    else:
        b.row(
            _btn("Участники", "klan_members",  _E_PEOPLE),
            _btn("Казна",     "klan_treasury", _E_CHEST),
        )
        b.row(_btn("Ежедневные задания", "klan_quests", _E_HUNT))
        if is_creator:
            b.row(_btn("Прокачать уровень", "klan_level_up", _E_ANTIMATTER))
        # Кнопка чата (если привязан — для всех, прямая URL-ссылка)
        if has_chat:
            chat_un  = clan.get("chat_username")
            chat_ttl = clan.get("chat_title") or "Чат клана"
            if chat_un:
                b.row(InlineKeyboardButton(
                    text=chat_ttl,
                    url=f"https://t.me/{chat_un}",
                    icon_custom_emoji_id=_E_CHAT,
                ))
            else:
                b.row(_btn("Чат клана (закрытый)", "klan_chat_private", _E_CHAT))
        if is_creator:
            b.row(_btn("Заявки", "klan_apps", _E_APPS))
            b.row(
                _btn("Запросы на вывод", "klan_withdraw_list", _E_CHEST),
                _btn("Исключить",        "klan_kick",          _E_CROSS),
            )
            if has_chat:
                b.row(_btn("Открепить чат", "klan_chat_unlink", _E_CROSS))
            else:
                b.row(_btn("Привязать чат", "klan_chat_link", _E_CHAT))
            b.row(_btn("Расформировать", "klan_disband", _E_CROSS))
        else:
            b.row(_btn("Покинуть клан", "klan_leave", _E_LEAVE))
    b.row(_back_btn("klan_main", lang))
    return b.as_markup()


def klan_treasury_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if lang == "en":
        b.row(
            _btn("Deposit",    "klan_deposit",  _E_PLUS),
            _btn("Withdrawal", "klan_withdraw", _E_STATSE),
        )
        b.row(_btn("Level up clan", "klan_level_up", _E_ANTIMATTER))
    else:
        b.row(
            _btn("Пополнить",       "klan_deposit",  _E_PLUS),
            _btn("Запрос на вывод", "klan_withdraw", _E_STATSE),
        )
        b.row(_btn("Прокачать уровень", "klan_level_up", _E_ANTIMATTER))
    b.row(_back_btn("klan_my", lang))
    return b.as_markup()


def klan_quests_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(_back_btn("klan_my", lang))
    return b.as_markup()


def klan_applications_keyboard(
    apps: list[dict],
    page: int,
    total: int,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    b           = InlineKeyboardBuilder()
    total_pages = max(1, (total + APPS_PER_PAGE - 1) // APPS_PER_PAGE)
    for a in apps:
        name = _name(a)
        b.row(
            _btn(f' {name}', f'klan_app_accept_{a["id"]}', _E_CHECK),
            _btn('Отмена',          f'klan_app_reject_{a["id"]}', _E_CROSS),
        )
    if total > 0:
        if lang == "en":
            b.row(
                _btn("Accept all",  "klan_app_accept_all", _E_CHECK),
                _btn("Reject all",  "klan_app_reject_all", _E_CROSS),
            )
        else:
            b.row(
                _btn("Принять все",   "klan_app_accept_all", _E_CHECK),
                _btn("Отклонить все", "klan_app_reject_all", _E_CROSS),
            )
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f'klan_apps_page_{page - 1}'))
    if page < total_pages - 1:
        nav.append(_btn("▶️", f'klan_apps_page_{page + 1}'))
    if nav:
        b.row(*nav)
    b.row(_back_btn("klan_my", lang))
    return b.as_markup()


def klan_withdrawal_keyboard(reqs: list[dict], lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in reqs:
        b.row(
            _btn(f' {_name(r)} · {_fmt(r["amount"])}', f'klan_wd_approve_{r["id"]}', _E_CHECK),
            _btn('Reject',                                  f'klan_wd_reject_{r["id"]}',  _E_CROSS),
        )
    b.row(_back_btn("klan_my", lang))
    return b.as_markup()


def klan_top_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(_back_btn("klan_main", lang))
    return b.as_markup()


def klan_stats_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(_back_btn("klan_main", lang))
    return b.as_markup()


def klan_back_keyboard(cb: str, lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(_back_btn(cb, lang))
    return b.as_markup()
