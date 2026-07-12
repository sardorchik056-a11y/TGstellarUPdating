# ============================================================
#  stats.py  —  Статистика бота TGStellar
# ============================================================

import sqlite3
import time
import asyncio
from database import DB_PATH

# ---------- Инициализация ----------

def init_stats_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                uid       INTEGER PRIMARY KEY,
                last_seen INTEGER NOT NULL DEFAULT 0,
                joined_ts INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


# ---------- Трекинг ----------

def track_user(uid: int, joined_ts: int = 0):
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO user_stats (uid, last_seen, joined_ts)
            VALUES (?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET last_seen = excluded.last_seen
        """, (uid, now, joined_ts or now))
        conn.commit()


# ---------- Асинхронная обёртка (использовать из async-хендлеров!) ----------
# track_user() дёргает sqlite3 синхронно и раньше вызывалась напрямую из
# event loop почти в каждом хендлере mainhelp.py (диск-I/O блокировал всех
# пользователей одновременно). Теперь — только через asyncio.to_thread.

async def aio_track_user(uid: int, joined_ts: int = 0) -> None:
    await asyncio.to_thread(track_user, uid, joined_ts)


# ---------- Онлайн ----------

def _count_online(seconds: int) -> int:
    threshold = int(time.time()) - seconds
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM user_stats WHERE last_seen >= ?",
            (threshold,)
        ).fetchone()
    return row[0] if row else 0


# ---------- Новые пользователи ----------

def _count_new(seconds: int) -> int:
    threshold = int(time.time()) - seconds
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM user_stats WHERE joined_ts >= ?",
            (threshold,)
        ).fetchone()
    return row[0] if row else 0


def total_users() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM user_stats").fetchone()
    return row[0] if row else 0


# ---------- Текст и клавиатура ----------

_EMOJI_ONLINE = "5906727823355156804"
_EMOJI_USERS  = "5258513401784573443"
_EMOJI_CLOCK  = "5906852613629941703"
_EMOJI_ARROW  = "5332724926216428039"
_EMOJI_NEW    = "5397916757333654639"


def _e(eid: str, fallback: str = "▪️") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


def stats_text(lang: str = "ru") -> str:
    from lang import t
    o5m  = _count_online(5 * 60)
    o24h = _count_online(24 * 3600)
    o7d  = _count_online(7 * 24 * 3600)
    o30d = _count_online(30 * 24 * 3600)

    n5m  = _count_new(5 * 60)
    n24h = _count_new(24 * 3600)
    n7d  = _count_new(7 * 24 * 3600)
    n30d = _count_new(30 * 24 * 3600)

    total = total_users()

    return (
        f'<blockquote>'
        f'{_e(_EMOJI_ONLINE)} <b>{t(lang, "stats_title_online")}</b>\n\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_5min")} — <b>{o5m}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_24h")} — <b>{o24h}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_week")} — <b>{o7d}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_month")} — <b>{o30d}</b>'
        f'</blockquote>\n'
        f'<blockquote>'
        f'{_e(_EMOJI_USERS)} <b>{t(lang, "stats_title_users")}</b>\n\n'
        f'{_e(_EMOJI_ARROW)} {t(lang, "stats_total")} — <b>{total:,}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_5min")} — <b>{n5m}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_24h")} — <b>{n24h}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_week")} — <b>{n7d}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_month")} — <b>{n30d}</b>'
        f'</blockquote>'
    )


async def aio_stats_text(lang: str = "ru") -> str:
    """Асинхронная обёртка stats_text() — сама stats_text() внутри делает
    несколько синхронных sqlite3-запросов (COUNT'ы), поэтому в event loop
    её вызывать напрямую нельзя, только через to_thread."""
    return await asyncio.to_thread(stats_text, lang)


def stats_keyboard(lang: str = "ru"):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from miner import EMOJI_BACK
    from lang import t
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"),
        callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return builder.as_markup()
