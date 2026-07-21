# ============================================================
#  checks.py  —  Чеки и промокоды TGStellar
#  Чек:    одноразовая ссылка на сумму, N активаций
#  Промо:  код на сумму, N активаций, вводится вручную
# ============================================================

import sqlite3
import secrets
import string
import asyncio
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "tgstellar.db"

_COIN = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'


# ──────────────────────────────────────────────
#  Соединение с БД
# ──────────────────────────────────────────────
#
# Раньше здесь везде было "with sqlite3.connect(DB_PATH) as conn:" — это
# управляет ТОЛЬКО транзакцией (commit/rollback), а не закрывает соединение
# (conn.close() не вызывался нигде). Плюс не было ни WAL, ни busy_timeout,
# так что при занятой БД соединение ждало лишь 5 сек по умолчанию вместо
# 30 сек, как во всех остальных модулях (database.py/hunt.py/leaders.py).
# Из-за этого именно checks.py первым ловил "database is locked" и течь
# файловых дескрипторов на tgstellar.db. Приводим к тому же виду, что и
# везде в проекте.

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def _conn_ctx():
    conn = _get_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# ──────────────────────────────────────────────
#  Инициализация таблиц
# ──────────────────────────────────────────────

def init_checks_db():
    with _conn_ctx() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                code        TEXT PRIMARY KEY,
                amount      INTEGER NOT NULL,
                uses_left   INTEGER NOT NULL,
                uses_total  INTEGER NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_activations (
                code    TEXT NOT NULL,
                uid     INTEGER NOT NULL,
                at      TEXT NOT NULL,
                PRIMARY KEY (code, uid)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS promos (
                name        TEXT PRIMARY KEY,
                amount      INTEGER NOT NULL,
                uses_left   INTEGER NOT NULL,
                uses_total  INTEGER NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS promo_activations (
                name    TEXT NOT NULL,
                uid     INTEGER NOT NULL,
                at      TEXT NOT NULL,
                PRIMARY KEY (name, uid)
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────
#  Чеки
# ──────────────────────────────────────────────

def _gen_check_code() -> str:
    """Генерирует уникальный код чека (8 символов a-z0-9)."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def create_check(amount: int, uses: int) -> str:
    """Создаёт чек. Возвращает код."""
    with _conn_ctx() as conn:
        while True:
            code = _gen_check_code()
            exists = conn.execute(
                "SELECT 1 FROM checks WHERE code=?", (code,)
            ).fetchone()
            if not exists:
                break
        conn.execute(
            "INSERT INTO checks (code, amount, uses_left, uses_total, created_at) VALUES (?,?,?,?,?)",
            (code, amount, uses, uses, datetime.utcnow().isoformat())
        )
        conn.commit()
    return code


def get_check(code: str) -> dict | None:
    with _conn_ctx() as conn:
        row = conn.execute("SELECT * FROM checks WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None


def activate_check(code: str, uid: int) -> tuple[bool, str, int]:
    """
    Активирует чек для uid.
    Возвращает (ok, причина, сумма).
    """
    with _conn_ctx() as conn:
        row = conn.execute("SELECT * FROM checks WHERE code=?", (code,)).fetchone()
        if not row:
            return False, "not_found", 0
        if row["uses_left"] <= 0:
            return False, "exhausted", 0
        already = conn.execute(
            "SELECT 1 FROM check_activations WHERE code=? AND uid=?", (code, uid)
        ).fetchone()
        if already:
            return False, "already_used", 0
        # Активируем
        conn.execute(
            "INSERT INTO check_activations (code, uid, at) VALUES (?,?,?)",
            (code, uid, datetime.utcnow().isoformat())
        )
        conn.execute(
            "UPDATE checks SET uses_left=uses_left-1 WHERE code=?", (code,)
        )
        conn.commit()
        return True, "ok", row["amount"]


def delete_check(code: str) -> bool:
    with _conn_ctx() as conn:
        cur = conn.execute("DELETE FROM checks WHERE code=?", (code,))
        conn.commit()
    return cur.rowcount > 0


def list_checks() -> list[dict]:
    with _conn_ctx() as conn:
        rows = conn.execute("SELECT * FROM checks ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
#  Промокоды
# ──────────────────────────────────────────────

def create_promo(name: str, amount: int, uses: int) -> tuple[bool, str]:
    """
    Создаёт промокод с именем `name`.
    Возвращает (ok, причина).
    """
    name = name.strip().lower()
    with _conn_ctx() as conn:
        exists = conn.execute(
            "SELECT 1 FROM promos WHERE name=?", (name,)
        ).fetchone()
        if exists:
            return False, "exists"
        conn.execute(
            "INSERT INTO promos (name, amount, uses_left, uses_total, created_at) VALUES (?,?,?,?,?)",
            (name, amount, uses, uses, datetime.utcnow().isoformat())
        )
        conn.commit()
    return True, "ok"


def get_promo(name: str) -> dict | None:
    with _conn_ctx() as conn:
        row = conn.execute(
            "SELECT * FROM promos WHERE name=?", (name.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def activate_promo(name: str, uid: int) -> tuple[bool, str, int]:
    """
    Активирует промокод для uid.
    Возвращает (ok, причина, сумма).
    """
    name = name.strip().lower()
    with _conn_ctx() as conn:
        row = conn.execute("SELECT * FROM promos WHERE name=?", (name,)).fetchone()
        if not row:
            return False, "not_found", 0
        if row["uses_left"] <= 0:
            return False, "exhausted", 0
        already = conn.execute(
            "SELECT 1 FROM promo_activations WHERE name=? AND uid=?", (name, uid)
        ).fetchone()
        if already:
            return False, "already_used", 0
        conn.execute(
            "INSERT INTO promo_activations (name, uid, at) VALUES (?,?,?)",
            (name, uid, datetime.utcnow().isoformat())
        )
        conn.execute(
            "UPDATE promos SET uses_left=uses_left-1 WHERE name=?", (name,)
        )
        conn.commit()
        return True, "ok", row["amount"]


def delete_promo(name: str) -> bool:
    with _conn_ctx() as conn:
        cur = conn.execute("DELETE FROM promos WHERE name=?", (name.strip().lower(),))
        conn.commit()
    return cur.rowcount > 0


def list_promos() -> list[dict]:
    with _conn_ctx() as conn:
        rows = conn.execute("SELECT * FROM promos ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
#  Тексты
# ──────────────────────────────────────────────

def check_activate_text(amount: int, lang: str = "ru") -> str:
    if lang == "en":
        return (
            f'<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji> <b>Check activated!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5397916757333654639">🪙</tg-emoji> <b><i>{amount:,} <tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> added to your balance</i></b>'
            f'</blockquote>'
        )
    return (
        f'<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji> <b>Чек активирован!</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5397916757333654639">🪙</tg-emoji> <b><i>{amount:,} <tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> зачислено на баланс</i></b>'
        f'</blockquote>'
    )


def check_error_text(reason: str, lang: str = "ru") -> str:
    msgs = {
        "not_found":   ("❌ Чек не найден.", "❌ Check not found."),
        "exhausted":   ("❌ Чек уже исчерпан.", "❌ Check is exhausted."),
        "already_used": ("❌ Ты уже активировал этот чек.", "❌ You already used this check."),
    }
    ru, en = msgs.get(reason, ("❌ Ошибка.", "❌ Error."))
    return en if lang == "en" else ru


def promo_activate_text(amount: int, lang: str = "ru") -> str:
    if lang == "en":
        return (
            f'<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji> <b>Promo activated!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5397916757333654639">🪙</tg-emoji> <b><i>{amount:,} <tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> added to your balance</i></b>'
            f'</blockquote>'
        )
    return (
        f'<tg-emoji emoji-id="5206607081334906820">✅</tg-emoji> <b>Промокод активирован!</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5397916757333654639">🪙</tg-emoji> <b><i>{amount:,} <tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> зачислено на баланс</i></b>'
        f'</blockquote>'
    )


def promo_error_text(reason: str, lang: str = "ru") -> str:
    msgs = {
        "not_found":    ("❌ Промокод не найден.", "❌ Promo code not found."),
        "exhausted":    ("❌ Промокод уже исчерпан.", "❌ Promo code is exhausted."),
        "already_used": ("❌ Ты уже активировал этот промокод.", "❌ You already used this promo."),
    }
    ru, en = msgs.get(reason, ("❌ Ошибка.", "❌ Error."))
    return en if lang == "en" else ru


def promo_input_text(lang: str = "ru") -> str:
    if lang == "en":
        return (
            '<tg-emoji emoji-id="5197269100878907942">🎁</tg-emoji> <b>Enter promo code</b>\n\n'
            '<blockquote><i>Send the code as a message'
            'or use: <code>/promo code</code></i></blockquote>'
        )
    return (
        '<tg-emoji emoji-id="5197269100878907942">🎁</tg-emoji> <b>Введи промокод</b>\n\n'
        '<blockquote><i>Отправь код сообщением'
        'или используй: <code>/промо код</code></i></blockquote>'
    )


# ──────────────────────────────────────────────
#  Async-обёртки
# ──────────────────────────────────────────────
# sqlite3 в этом модуле синхронный (блокирующий). Прямой вызов любой из
# функций выше из async-хендлера (как было раньше в mainhelp.py) морозит
# ВЕСЬ event loop бота на время диск-I/O — то есть зависают все пользователи
# сразу, а не только тот, кто активирует чек/промокод. Использовать эти
# обёртки из любого async-кода вместо прямого вызова синхронных версий.

async def aio_create_check(amount: int, uses: int) -> str:
    return await asyncio.to_thread(create_check, amount, uses)


async def aio_get_check(code: str) -> dict | None:
    return await asyncio.to_thread(get_check, code)


async def aio_activate_check(code: str, uid: int) -> tuple[bool, str, int]:
    return await asyncio.to_thread(activate_check, code, uid)


async def aio_delete_check(code: str) -> bool:
    return await asyncio.to_thread(delete_check, code)


async def aio_list_checks() -> list[dict]:
    return await asyncio.to_thread(list_checks)


async def aio_create_promo(name: str, amount: int, uses: int) -> tuple[bool, str]:
    return await asyncio.to_thread(create_promo, name, amount, uses)


async def aio_get_promo(name: str) -> dict | None:
    return await asyncio.to_thread(get_promo, name)


async def aio_activate_promo(name: str, uid: int) -> tuple[bool, str, int]:
    return await asyncio.to_thread(activate_promo, name, uid)


async def aio_delete_promo(name: str) -> bool:
    return await asyncio.to_thread(delete_promo, name)


async def aio_list_promos() -> list[dict]:
    return await asyncio.to_thread(list_promos)
