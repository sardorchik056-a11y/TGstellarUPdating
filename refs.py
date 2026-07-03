# ============================================================
#  refs.py  —  Реферальная система TGStellar
#  • Награда за обычного реферала:  3 000 монет
#  • Награда за Premium-реферала:   5 000 монет
#  • Капча после /start: простые примеры (5 попыток → блок 30 мин)
#  • Процентная реф-система: 10% / 15% (Premium) от ЛЮБОГО дохода
#    реферала начисляется рефереру автоматически (см. блок
#    "ПРОЦЕНТНАЯ РЕФ-СИСТЕМА" ниже — реализовано SQL-триггером,
#    database.py НЕ модифицируется).
# ============================================================

import sqlite3
import time
import random
import math
import threading
import unicodedata
from datetime import datetime, timezone, timedelta

DB_PATH = "tgstellar.db"

REF_REWARD_NORMAL  = 3_000
REF_REWARD_PREMIUM = 8_000
CAPTCHA_MAX_TRIES  = 5
CAPTCHA_BLOCK_SEC  = 30 * 60

# Процент от ЛЮБОГО дохода реферала, который автоматически уходит
# рефереру (пассивный доход). Считается от каждого положительного
# изменения баланса (начисление монет), не только от разовой награды
# за приглашение.
REF_PERCENT_NORMAL  = 10   # обычный реферал (без Telegram Premium)
REF_PERCENT_PREMIUM = 15   # реферал с Telegram Premium

# Рабочие emoji-id из проекта
_E_PREMIUM = "5427168083074628963"
_E_COIN    = "5199552030615558774"
_E_TIMER   = "5382194935057372936"
_E_LEVEL   = "5375338737028841420"
_E_BAL     = "5278467510604160626"
_E_STAR    = "5267500801240092311"
_E_STATUS  = "5438496463044752972"
_E_FRIENDS = "5332724926216428039"

COIN = f'<tg-emoji emoji-id="{_E_COIN}">🪙</tg-emoji>'

# ─────────────────────────────────────────
#  ТОП РЕФЕРЕРОВ — константы
# ─────────────────────────────────────────

REFTOP_SIZE = 10  # топ-10 пригласивших

REFTOP_PERIODS = ("today", "week", "alltime")

_REFTOP_E = {
    "trophy":   "5413566144986503832",
    "friends":  _E_FRIENDS,
    "coin":     "5452085950022707790",
    "premium":  _E_PREMIUM,
    "calendar": "5382194935057372936",
    "back":     "6039539366177541657",
    "empty":    "5397916757333654639",
    "shield":   "5354905713585975489",
}

_REFTOP_PERIOD_ICON = {
    "today":   ("5274055917766202507", "📅"),
    "week":    ("5274055917766202507", "📅"),
    "alltime": ("5274055917766202507", "📅"),
}

# Иконки мест 1-10 (те же медали, что и в leaders.py — единый стиль)
_REFTOP_PLACE_EMOJI = {
    1:  "5440539497383087970",
    2:  "5447203607294265305",
    3:  "5453902265922376865",
    4:  "5382054253403577563",
    5:  "5391197405553107640",
    6:  "5390966190283694453",
    7:  "5382132232829804982",
    8:  "5391038994274329680",
    9:  "5391234698754138414",
    10: "5393480373944459905",
}

# Защита от bidi-атак в именах игроков (см. leaders.py для подробностей)
_LRM = "\u200e"
_LRI = "\u2066"
_PDI = "\u2069"


def _tg(eid: str, fb: str = "") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


def _strip_invisible(text: str) -> str:
    """Убирает непечатаемые control/format-символы (защита от 'троянских' имён)."""
    return "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))


def _fmt(n) -> str:
    """Сокращённый формат чисел: 1500 -> '1.5к', 100000 -> '100к' и т.д."""
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

# ─────────────────────── инициализация БД ────────────────────

def init_refs_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS refs (
                uid         INTEGER PRIMARY KEY,
                inviter_uid INTEGER,
                rewarded    INTEGER DEFAULT 0,
                joined_ts   INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ref_stats (
                uid          INTEGER PRIMARY KEY,
                total_refs   INTEGER DEFAULT 0,
                premium_refs INTEGER DEFAULT 0,
                earned_coins INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS captcha_state (
                uid           INTEGER PRIMARY KEY,
                question      TEXT    NOT NULL,
                answer        INTEGER NOT NULL,
                tries         INTEGER DEFAULT 0,
                blocked_until INTEGER DEFAULT 0,
                passed        INTEGER DEFAULT 0,
                chat_id       INTEGER,
                msg_id        INTEGER
            );
        """)
        c.commit()
        # Миграция: добавляем chat_id/msg_id если таблица создана старой версией
        cols = {row["name"] for row in c.execute("PRAGMA table_info(captcha_state)").fetchall()}
        if "chat_id" not in cols:
            c.execute("ALTER TABLE captcha_state ADD COLUMN chat_id INTEGER")
        if "msg_id" not in cols:
            c.execute("ALTER TABLE captcha_state ADD COLUMN msg_id INTEGER")
        c.commit()

        # ── Миграция: колонки для процентной реф-системы ──
        # is_premium — есть ли у реферала Telegram Premium (фиксируется
        #              в момент подтверждения реферала, см. reward_inviter);
        # percent    — % отчислений рефереру с любого дохода этого реферала
        #              (10 обычный / 15 Telegram Premium).
        ref_cols = {row["name"] for row in c.execute("PRAGMA table_info(refs)").fetchall()}
        if "is_premium" not in ref_cols:
            c.execute("ALTER TABLE refs ADD COLUMN is_premium INTEGER DEFAULT 0")
        if "percent" not in ref_cols:
            c.execute(f"ALTER TABLE refs ADD COLUMN percent INTEGER DEFAULT {REF_PERCENT_NORMAL}")
        c.commit()

        _install_ref_income_trigger(c)


def _install_ref_income_trigger(c: sqlite3.Connection):
    """
    ПРОЦЕНТНАЯ РЕФ-СИСТЕМА (10% / 15%).

    Ставим задачу так: "проверять ЛЮБОЕ начисление" пользователю и
    отдавать % его рефереру — а database.py трогать нельзя, потому что
    от save_user() зависит куча других файлов проекта.

    Решение: SQL-триггер прямо на таблице users (её создаёт database.py,
    но триггер вешается отдельным DDL-запросом и не требует правок
    самого database.py — он будет отрабатывать при КАЖДОМ UPDATE
    data_json, откуда бы он ни пришёл: из miner.py, shop.py, admin-панели
    и т.д.).

    Как это работает:
      1. Триггер сравнивает старый и новый JSON-баланс пользователя.
      2. Если баланс ВЫРОС (delta > 0) и у пользователя есть реферер —
         реферер получает delta * percent / 100 монет (округление до
         целого), где percent берётся из refs.percent (10 или 15).
      3. Если баланс уменьшился (трата, покупка, вывод и т.п.) —
         триггер не срабатывает, комиссия не начисляется.
      4. Начисление комиссии рефереру — это тоже UPDATE users, но
         SQLite по умолчанию (recursive_triggers = OFF) НЕ запускает
         триггеры из других триггеров. Поэтому комиссия уходит только
         на 1 уровень вверх (прямому рефереру), а не каскадом по всей
         цепочке — как и требовалось.
      5. Параллельно обновляется earned_coins в ref_stats — те же
         цифры, что уже показываются в /refs.
    """
    c.executescript(f"""
        DROP TRIGGER IF EXISTS trg_ref_income;
        CREATE TRIGGER trg_ref_income
        AFTER UPDATE OF data_json ON users
        FOR EACH ROW
        WHEN
            CAST(json_extract(NEW.data_json, '$.balance') AS REAL)
              > CAST(json_extract(OLD.data_json, '$.balance') AS REAL)
            AND (SELECT inviter_uid FROM refs WHERE uid = NEW.uid) IS NOT NULL
        BEGIN
            UPDATE users
            SET data_json = json_set(
                    data_json, '$.balance',
                    CAST(
                        CAST(json_extract(data_json, '$.balance') AS REAL)
                        + ROUND(
                            (CAST(json_extract(NEW.data_json, '$.balance') AS REAL)
                             - CAST(json_extract(OLD.data_json, '$.balance') AS REAL))
                            * (SELECT COALESCE(percent, {REF_PERCENT_NORMAL}) FROM refs WHERE uid = NEW.uid) / 100.0
                          )
                    AS INTEGER)
                )
            WHERE uid = (SELECT inviter_uid FROM refs WHERE uid = NEW.uid);

            INSERT INTO ref_stats (uid, total_refs, premium_refs, earned_coins)
            VALUES (
                (SELECT inviter_uid FROM refs WHERE uid = NEW.uid),
                0, 0,
                CAST(ROUND(
                    (CAST(json_extract(NEW.data_json, '$.balance') AS REAL)
                     - CAST(json_extract(OLD.data_json, '$.balance') AS REAL))
                    * (SELECT COALESCE(percent, {REF_PERCENT_NORMAL}) FROM refs WHERE uid = NEW.uid) / 100.0
                ) AS INTEGER)
            )
            ON CONFLICT(uid) DO UPDATE SET
                earned_coins = earned_coins + CAST(ROUND(
                    (CAST(json_extract(NEW.data_json, '$.balance') AS REAL)
                     - CAST(json_extract(OLD.data_json, '$.balance') AS REAL))
                    * (SELECT COALESCE(percent, {REF_PERCENT_NORMAL}) FROM refs WHERE uid = NEW.uid) / 100.0
                ) AS INTEGER);
        END;
    """)
    c.commit()


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

# ───────────────── защита от гонок (anti-dupe locks) ──────────
#
# get_user/save_user (database.py) живут вне SQLite-транзакции refs.py,
# поэтому одного database-уровня атомарности недостаточно: между
# "прочитали rewarded=0" и "записали баланс" возможна гонка при
# параллельных вызовах (повторный апдейт от Telegram, спам командой
# и т.п.). Чтобы исключить дюп монет/наград, любая операция, которая
# читает и затем изменяет состояние одного и того же uid, должна
# выполняться под этим локом.

_locks_guard = threading.Lock()
_uid_locks: dict[int, threading.Lock] = {}


def _lock_for(uid: int) -> threading.Lock:
    with _locks_guard:
        lock = _uid_locks.get(uid)
        if lock is None:
            lock = threading.Lock()
            _uid_locks[uid] = lock
        return lock

# ─────────────────────────── капча ───────────────────────────

def _gen_question() -> tuple[str, int]:
    op = random.choice(["+", "-"])
    if op == "+":
        a, b   = random.randint(1, 9), random.randint(1, 9)
        answer = a + b
        text   = f"{a} + {b}"
    else:
        a = random.randint(1, 9)
        b = random.randint(1, a)
        answer = a - b
        text   = f"{a} − {b}"
    return text, answer


def get_captcha_state(uid: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM captcha_state WHERE uid=?", (uid,)).fetchone()
    return dict(row) if row else None


def create_captcha(uid: int) -> dict:
    question, answer = _gen_question()
    now   = int(time.time())
    state = get_captcha_state(uid)
    if state and state["blocked_until"] > now:
        return state
    with _conn() as c:
        c.execute("""
            INSERT INTO captcha_state (uid, question, answer, tries, blocked_until, passed)
            VALUES (?, ?, ?, 0, 0, 0)
            ON CONFLICT(uid) DO UPDATE SET
                question=excluded.question, answer=excluded.answer,
                tries=0, blocked_until=0, passed=0
        """, (uid, question, answer))
        c.commit()
    return get_captcha_state(uid)


def set_captcha_msg(uid: int, chat_id: int, msg_id: int):
    with _conn() as c:
        c.execute("UPDATE captcha_state SET chat_id=?, msg_id=? WHERE uid=?", (chat_id, msg_id, uid))
        c.commit()


def get_captcha_msg(uid: int) -> tuple[int, int] | None:
    state = get_captcha_state(uid)
    if state and state.get("chat_id") and state.get("msg_id"):
        return state["chat_id"], state["msg_id"]
    return None


def check_captcha(uid: int, user_answer: int) -> dict:
    with _lock_for(uid):
        return _check_captcha_locked(uid, user_answer)


def _check_captcha_locked(uid: int, user_answer: int) -> dict:
    state = get_captcha_state(uid)
    now   = int(time.time())
    if not state:
        return {"status": "no_captcha"}
    if state["passed"]:
        return {"status": "ok", "tries_left": 0, "blocked_until": 0, "unblock_in_min": 0}
    if state["blocked_until"] > now:
        mins = math.ceil((state["blocked_until"] - now) / 60)
        return {"status": "blocked", "tries_left": 0,
                "blocked_until": state["blocked_until"], "unblock_in_min": mins}
    if user_answer == state["answer"]:
        with _conn() as c:
            c.execute("UPDATE captcha_state SET passed=1, tries=0 WHERE uid=?", (uid,))
            c.commit()
        return {"status": "ok", "tries_left": 0, "blocked_until": 0, "unblock_in_min": 0}
    new_tries = state["tries"] + 1
    if new_tries >= CAPTCHA_MAX_TRIES:
        blocked_until = now + CAPTCHA_BLOCK_SEC
        q, a = _gen_question()
        with _conn() as c:
            c.execute("""
                UPDATE captcha_state
                SET tries=?, blocked_until=?, question=?, answer=?
                WHERE uid=?
            """, (new_tries, blocked_until, q, a, uid))
            c.commit()
        return {"status": "blocked", "tries_left": 0,
                "blocked_until": blocked_until, "unblock_in_min": 30}
    q, a = _gen_question()
    with _conn() as c:
        c.execute("UPDATE captcha_state SET tries=?, question=?, answer=? WHERE uid=?", (new_tries, q, a, uid))
        c.commit()
    return {"status": "wrong", "tries_left": CAPTCHA_MAX_TRIES - new_tries,
            "blocked_until": 0, "unblock_in_min": 0, "question": q}


def is_captcha_passed(uid: int) -> bool:
    state = get_captcha_state(uid)
    return bool(state and state["passed"])


def is_captcha_blocked(uid: int) -> tuple[bool, int]:
    state = get_captcha_state(uid)
    if not state:
        return False, 0
    now = int(time.time())
    if state["blocked_until"] > now:
        return True, state["blocked_until"] - now
    return False, 0

# ────────────────────────── рефералы ─────────────────────────

def register_referral(uid: int, inviter_uid: int | None):
    # Защита от само-реферала: пользователь не может пригласить сам себя
    # (например, передав свой же uid в start=ref_<uid>).
    if inviter_uid is not None and inviter_uid == uid:
        inviter_uid = None
    ts = int(time.time())
    with _conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO refs (uid, inviter_uid, rewarded, joined_ts)
            VALUES (?, ?, 0, ?)
        """, (uid, inviter_uid, ts))
        c.commit()


def is_new_user(uid: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT uid FROM refs WHERE uid=?", (uid,)).fetchone()
    return row is None


def reward_inviter(uid: int, is_premium: bool) -> tuple[bool, int]:
    """
    Начисляет награду пригласившему за реферала `uid`.
    Защита от дюпа: флаг rewarded "захватывается" одной атомарной
    UPDATE ... WHERE rewarded=0, поэтому даже при параллельном вызове
    (повторный апдейт от Telegram, гонка хендлеров) награду сможет
    забрать только один вызов — остальные сразу увидят rowcount=0
    и завершатся без начисления. Дополнительно операция сериализуется
    локом по uid, чтобы исключить гонки и на уровне save_user().
    """
    with _lock_for(uid):
        with _conn() as c:
            # Атомарный "захват" права на начисление: строка обновится
            # ТОЛЬКО если rewarded ещё не был выставлен. Это устраняет
            # классический TOCTOU (read rewarded -> ... -> write rewarded),
            # из-за которого было возможно двойное начисление монет.
            # Заодно фиксируем is_premium и % отчислений (10/15) для этого
            # реферала — с этого момента SQL-триггер trg_ref_income начнёт
            # автоматически отдавать рефереру процент с ЛЮБОГО дохода uid.
            # Активация привязана к тому же моменту, что и разовая награда
            # (после капчи), чтобы не начислять % с ещё не подтверждённых
            # рефералов.
            percent = REF_PERCENT_PREMIUM if is_premium else REF_PERCENT_NORMAL
            cur = c.execute(
                """
                UPDATE refs
                SET rewarded=1, is_premium=?, percent=?
                WHERE uid=? AND rewarded=0 AND inviter_uid IS NOT NULL
                """,
                (1 if is_premium else 0, percent, uid),
            )
            c.commit()
            if cur.rowcount == 0:
                # Либо записи нет, либо уже была вознаграждена, либо нет inviter_uid.
                return False, 0
            ref_row = c.execute(
                "SELECT inviter_uid FROM refs WHERE uid=?", (uid,)
            ).fetchone()

        inviter = ref_row["inviter_uid"]
        coins   = REF_REWARD_PREMIUM if is_premium else REF_REWARD_NORMAL

        from database import get_user, save_user
        d = get_user(inviter)
        if not d:
            # Получателя награды не существует — откатываем захваченный
            # флаг, чтобы награда не "сгорела" безвозвратно и не возникло
            # рассинхрона между rewarded=1 и реально начисленными монетами.
            with _conn() as c:
                c.execute("UPDATE refs SET rewarded=0 WHERE uid=?", (uid,))
                c.commit()
            return False, 0

        d["balance"] = d.get("balance", 0) + coins
        save_user(inviter, d)

        with _conn() as c:
            if is_premium:
                c.execute("""
                    INSERT INTO ref_stats (uid, total_refs, premium_refs, earned_coins)
                    VALUES (?, 1, 1, ?)
                    ON CONFLICT(uid) DO UPDATE SET
                        total_refs=total_refs+1, premium_refs=premium_refs+1, earned_coins=earned_coins+?
                """, (inviter, coins, coins))
            else:
                c.execute("""
                    INSERT INTO ref_stats (uid, total_refs, premium_refs, earned_coins)
                    VALUES (?, 1, 0, ?)
                    ON CONFLICT(uid) DO UPDATE SET
                        total_refs=total_refs+1, earned_coins=earned_coins+?
                """, (inviter, coins, coins))
            c.commit()
        return True, coins


def get_ref_stats(uid: int) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM ref_stats WHERE uid=?", (uid,)).fetchone()
    return dict(row) if row else {"uid": uid, "total_refs": 0, "premium_refs": 0, "earned_coins": 0}


def get_referrals_list(uid: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT r.uid, r.joined_ts, r.rewarded,
                   json_extract(u.data_json, '$.first_name') AS first_name,
                   json_extract(u.data_json, '$.username')   AS username
            FROM refs r
            LEFT JOIN users u ON u.uid = r.uid
            WHERE r.inviter_uid=? ORDER BY r.joined_ts DESC LIMIT 50
        """, (uid,)).fetchall()
    return [dict(r) for r in rows]


def get_inviter(uid: int) -> int | None:
    with _conn() as c:
        row = c.execute("SELECT inviter_uid FROM refs WHERE uid=?", (uid,)).fetchone()
    return row["inviter_uid"] if row else None


def get_ref_percent_info(uid: int) -> dict:
    """
    Возвращает информацию об активной % ставке для пользователя uid как
    для реферала (сколько % с его дохода уходит его рефереру и активна
    ли уже эта ставка — она включается после reward_inviter()).
    """
    with _conn() as c:
        row = c.execute(
            "SELECT inviter_uid, rewarded, is_premium, percent FROM refs WHERE uid=?",
            (uid,),
        ).fetchone()
    if not row or row["inviter_uid"] is None:
        return {"active": False, "percent": 0, "is_premium": False}
    return {
        "active":     bool(row["rewarded"]),
        "percent":    row["percent"] if row["rewarded"] else 0,
        "is_premium": bool(row["is_premium"]),
    }

# ──────────────────────── тексты UI ──────────────────────────

def refs_main_text(uid: int, bot_username: str, lang: str = "ru") -> str:
    from lang import t
    stats    = get_ref_stats(uid)
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    total    = stats["total_refs"]
    premium  = stats["premium_refs"]
    earned   = stats["earned_coins"]

    return (
        f'<tg-emoji emoji-id="{_E_FRIENDS}">👥</tg-emoji> <b>{t(lang, "refs_title")}</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="{_E_STAR}">🎯</tg-emoji> <b>{t(lang, "refs_rewards_title")}</b>\n'
        f'<tg-emoji emoji-id="5452085950022707790">🪙</tg-emoji> <i>{t(lang, "refs_reward_normal")} — <b>+{REF_REWARD_NORMAL:,}</b> {COIN}\n'
        f'<tg-emoji emoji-id="{_E_PREMIUM}">⭐</tg-emoji> {t(lang, "refs_reward_premium")} — <b>+{REF_REWARD_PREMIUM:,}</b> </i>{COIN}\n'
        f'<tg-emoji emoji-id="5199552030615558774">📈</tg-emoji> <i>+ {REF_PERCENT_NORMAL}% / {REF_PERCENT_PREMIUM}% <tg-emoji emoji-id="{_E_PREMIUM}">⭐</tg-emoji> {"от дохода реферала — навсегда" if lang != "en" else "of referral income — forever"}</i>'
        f'</blockquote>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> <b>{t(lang, "refs_stats_title")}</b>\n'
        f'<tg-emoji emoji-id="{_E_FRIENDS}">👤</tg-emoji> <i>{t(lang, "refs_total")} — <b>{total}</b>\n'
        f'<tg-emoji emoji-id="{_E_PREMIUM}">⭐</tg-emoji> {t(lang, "refs_premium_count")} — <b>{premium}</b>\n'
        f'<tg-emoji emoji-id="5449683594425410231">🪙</tg-emoji> {t(lang, "refs_earned")} — <b>{earned:,}</b></i> {COIN}'
        f'</blockquote>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji> <code>{ref_link}</code>\n\n'
        f'<i>{t(lang, "refs_link_hint")}</i> 👇'
        f'</blockquote>'
    )


def captcha_start_text(question: str) -> str:
    return f'<b>{question} = ?</b>'


def captcha_wrong_text(question: str, tries_left: int) -> str:
    return f'<b>{question} = ?</b>'


def captcha_blocked_text(unblock_in_min: int, lang: str = "ru") -> str:
    from lang import t
    return f'❗️ <b>{t(lang, "captcha_blocked").format(min=unblock_in_min)}</b>'


def refs_notif_text(new_user_name: str, reward: int, is_premium: bool, lang: str = "ru") -> str:
    from lang import t
    if is_premium:
        return f'<tg-emoji emoji-id="5262643974912355126">⭐</tg-emoji> <b>{t(lang, "refs_notif_premium")} | +{reward:,}<tg-emoji emoji-id="5199552030615558774">⭐</tg-emoji></b>'
    else:
        return f'<tg-emoji emoji-id="{_E_FRIENDS}">✨</tg-emoji> <b>{t(lang, "refs_notif_normal")} | +{reward:,}<tg-emoji emoji-id="5199552030615558774">⭐</tg-emoji></b>'


def refs_list_text(uid: int, lang: str = "ru") -> str:
    from lang import t
    refs  = get_referrals_list(uid)
    stats = get_ref_stats(uid)

    if not refs:
        body = (
            f'<blockquote>'
            f'<tg-emoji emoji-id="{_E_FRIENDS}">📭</tg-emoji> <i>{t(lang, "refs_list_empty")}</i>\n\n'
            f'<i>{t(lang, "refs_list_empty_hint")}</i>'
            f'</blockquote>'
        )
    else:
        from datetime import datetime, timezone
        lines = []
        for i, r in enumerate(refs[:20], 1):
            dt      = datetime.fromtimestamp(r["joined_ts"], tz=timezone.utc).strftime("%d.%m.%Y")
            check   = "✅" if r["rewarded"] else "⏳"
            name    = r.get("first_name") or r.get("username") or str(r["uid"])
            lines.append(f"<b>{i:>2}.</b> <tg-emoji emoji-id=\"5452085950022707790\">🪙</tg-emoji> <b>{name}</b>  {check}  <i>{dt}</i>")
        more = f"\n\n<i>{t(lang, 'refs_list_more')} {len(refs)-20} {t(lang, 'refs_list_more_sfx')}</i>" if len(refs) > 20 else ""
        body = (
            f'<blockquote>' + "\n".join(lines) + more + '</blockquote>\n'
            f'<i><tg-emoji emoji-id="{_E_TIMER}">⏳</tg-emoji> — {t(lang, "refs_list_pending")}  '
            f'·  ✅ — {t(lang, "refs_list_rewarded")}</i>'
        )

    return (
        f'<tg-emoji emoji-id="{_E_FRIENDS}">👥</tg-emoji> <b>{t(lang, "refs_list_title")}</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5258513401784573443">📋</tg-emoji> {t(lang, "refs_list_invited")} — <b>{stats["total_refs"]}</b>\n'
        f'<tg-emoji emoji-id="{_E_PREMIUM}">⭐</tg-emoji> {t(lang, "refs_list_premium")} — <b>{stats["premium_refs"]}</b>\n'
        f'<tg-emoji emoji-id="5449683594425410231">🪙</tg-emoji> {t(lang, "refs_list_earned")} — <b>{stats["earned_coins"]:,}</b> {COIN}'
        f'</blockquote>\n'
        f'{body}'
    )

# ───────────────────────── клавиатуры ────────────────────────

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from miner import EMOJI_BACK


def refs_main_keyboard(bot_username: str, uid: int, lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    builder  = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "refs_btn_share"),
        url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20TGStellar%21",
        icon_custom_emoji_id="5271604874419647061"
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "refs_btn_list"),
        callback_data="refs_list",
        icon_custom_emoji_id="5258513401784573443"
    ))
    builder.row(InlineKeyboardButton(
        text=" Top Referrers" if lang == "en" else " Топ рефереров",
        callback_data="reftop_alltime",
        icon_custom_emoji_id=_REFTOP_E["trophy"],
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"),
        callback_data="profile",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return builder.as_markup()


def refs_list_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"),
        callback_data="refs_main",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return builder.as_markup()


# ───────────────────────── топ рефереров ─────────────────────

_REFTOP_PERIODS_LABEL_RU = {"today": "Сегодня", "week": "Неделя", "alltime": "Всё время"}
_REFTOP_PERIODS_LABEL_EN = {"today": "Today",   "week": "Week",   "alltime": "All Time"}


def get_reftop(period: str) -> list[dict]:
    """Возвращает топ-10 рефереров за период (сегодня / неделя / всё время)."""
    from datetime import datetime, timezone, timedelta
    now   = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        ts_from = int(today.timestamp())
        where   = "AND r.joined_ts >= ?"
        params  = (ts_from,)
    elif period == "week":
        week_start = today - timedelta(days=today.weekday())
        ts_from    = int(week_start.timestamp())
        where      = "AND r.joined_ts >= ?"
        params     = (ts_from,)
    else:  # alltime
        where  = ""
        params = ()

    with _conn() as c:
        rows = c.execute(f"""
            SELECT r.inviter_uid AS uid,
                   COUNT(*) AS total,
                   json_extract(u.data_json, '$.first_name') AS first_name,
                   json_extract(u.data_json, '$.username')   AS username
            FROM refs r
            LEFT JOIN users u ON u.uid = r.inviter_uid
            WHERE r.inviter_uid IS NOT NULL {where}
            GROUP BY r.inviter_uid
            ORDER BY total DESC
            LIMIT {REFTOP_SIZE}
        """, params).fetchall()
    return [dict(r) for r in rows]


def reftop_text(period: str, viewer_uid: int | None = None, lang: str = "ru") -> str:
    leaders     = get_reftop(period)
    _LABELS     = _REFTOP_PERIODS_LABEL_EN if lang == "en" else _REFTOP_PERIODS_LABEL_RU
    period_name = _LABELS.get(period, period)

    e_trophy  = _tg(_REFTOP_E["trophy"],  "🏆")
    e_friends = _tg(_REFTOP_E["friends"], "👥")
    e_empty   = _tg(_REFTOP_E["empty"],   "🎟")
    e_shield  = _tg(_REFTOP_E["shield"],  "🛡")

    if lang == "en":
        header = (
            f'<blockquote>'
            f'{e_trophy} <b>Top Referrers</b>\n'
            f'{e_friends} <b>Period: {period_name}</b>'
            f'</blockquote>\n'
        )
    else:
        header = (
            f'<blockquote>'
            f'{e_trophy} <b>Топ рефереров</b>\n'
            f'{e_friends} <b>Период: {period_name}</b>'
            f'</blockquote>\n'
        )

    if not leaders:
        if lang == "en":
            body = (
                f'<blockquote>'
                f'{e_empty} <b>No data yet.</b>\n'
                f'<i>Invite friends and be first!</i>'
                f'</blockquote>'
            )
        else:
            body = (
                f'<blockquote>'
                f'{e_empty} <b>Данных пока нет.</b>\n'
                f'<i>Приглашай друзей и будь первым!</i>'
                f'</blockquote>'
            )
        return header + body

    lines: list[str] = []
    for i, row in enumerate(leaders):
        place = i + 1
        fname = _strip_invisible((row.get("first_name") or "")).strip()
        uname = _strip_invisible((row.get("username")   or "")).strip()
        name  = fname or (f"@{uname}" if uname else f"id{row['uid']}")
        total = row["total"]
        is_me = (viewer_uid is not None and row["uid"] == viewer_uid)

        place_str = _tg(_REFTOP_PLACE_EMOJI[place], "🏅") if place in _REFTOP_PLACE_EMOJI else f"<b>{place}.</b>"
        name_str  = f"<b>{_LRI}{name}{_PDI}</b>" if is_me else f"{_LRI}{name}{_PDI}"
        val_label = "refs" if lang == "en" else "рефов"
        val_str   = f"<b>{total} {val_label}</b>" if is_me else f"{total} {val_label}"
        me_mark   = " ←" if is_me else ""

        lines.append(f'{_LRM}{place_str} {name_str} — {e_friends} {val_str}{me_mark}')

    body = "<blockquote>" + "\n".join(lines) + "</blockquote>"

    if viewer_uid is not None:
        in_top = any(r["uid"] == viewer_uid for r in leaders)
        if not in_top:
            if lang == "en":
                body += (
                    f'\n<blockquote>'
                    f'{e_shield} <b>You are not in the top {REFTOP_SIZE}</b>\n'
                    f'<i>Invite more friends!</i>'
                    f'</blockquote>'
                )
            else:
                body += (
                    f'\n<blockquote>'
                    f'{e_shield} <b>Тебя нет в топ-{REFTOP_SIZE}</b>\n'
                    f'<i>Приглашай больше друзей!</i>'
                    f'</blockquote>'
                )

    return header + body


def reftop_keyboard(period: str, lang: str = "ru") -> InlineKeyboardMarkup:
    from lang import t
    _LABELS = _REFTOP_PERIODS_LABEL_EN if lang == "en" else _REFTOP_PERIODS_LABEL_RU
    builder = InlineKeyboardBuilder()

    period_buttons = []
    for key in REFTOP_PERIODS:
        label    = _LABELS[key]
        btn_text = f"· {label} ·" if key == period else label
        period_buttons.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"reftop_{key}",
            icon_custom_emoji_id=_REFTOP_E["calendar"],
        ))
    builder.row(*period_buttons)

    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"),
        callback_data="refs_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()
