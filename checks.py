# ============================================================
#  checks.py  —  Чеки и промокоды TGStellar
#  Чек:    одноразовая ссылка на сумму, N активаций
#  Промо:  код на сумму, N активаций, вводится вручную
# ============================================================

import sqlite3
import secrets
import string
from datetime import datetime

DB_PATH = "tgstellar.db"

_COIN = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'


# ──────────────────────────────────────────────
#  Инициализация таблиц
# ──────────────────────────────────────────────

def init_checks_db():
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM checks WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None


def activate_check(code: str, uid: int) -> tuple[bool, str, int]:
    """
    Активирует чек для uid.
    Возвращает (ok, причина, сумма).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM checks WHERE code=?", (code,))
        conn.commit()
    return cur.rowcount > 0


def list_checks() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM promos WHERE name=?", (name.strip().lower(),))
        conn.commit()
    return cur.rowcount > 0


def list_promos() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
