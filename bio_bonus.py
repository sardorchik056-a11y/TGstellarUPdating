# ============================================================
#  bio_bonus.py — бонус за @TGStellarr_bot в описании профиля
#
#  Логика:
#   * Раз в BIO_CHECK_INTERVAL (30 минут) фоновая задача сама (без участия
#     клиента/пользователя) запрашивает у Telegram актуальный профиль
#     (bot.get_chat) и проверяет, есть ли в поле "bio" упоминание бота.
#   * Результат проверки сохраняется в data вместе с меткой времени.
#   * Множитель, который используют hunt.py / miner.py / pets.py,
#     смотрит НЕ только на флаг, но и на "свежесть" последней проверки —
#     если фоновая задача по какой-то причине перестала выполняться,
#     бонус сам угасает, а не остаётся висеть навсегда.
#
#  Почему так (защита от уязвимостей):
#   1. Флаг bio_bonus_active выставляется ТОЛЬКО сервером на основании
#      ответа Telegram API (bot.get_chat) — клиент/пользователь никак не
#      может напрямую записать этот флаг себе в профиль.
#   2. Проверка bio регулярно "протухает" (см. BIO_STALE_AFTER) — то есть
#      если игрок временно вписал @TGStellarr_bot, дождался бонуса, а потом
#      сразу стёр — бонус исчезнет максимум через один цикл проверки,
#      и не может быть "заморожен" навечно багом/рестартом бота.
#   3. Совпадение ищется как отдельный "токен" username'а (через regex с
#      границами слова), а не простым substring — нельзя подсунуть
#      похожий, но другой юзернейм (например TGStellarr_bot2) и получить
#      бонус по недосмотру.
#   4. Ошибки Telegram API (юзер заблокировал бота, чат не найден,
#      флуд-контроль и т.п.) НИКОГДА не приводят к автоматической выдаче
#      бонуса — при любой ошибке флаг просто не трогается на этом тике.
# ============================================================

import asyncio
import re
from datetime import datetime, timezone

# ─────────────────────────────────────────
#  НАСТРОЙКИ
# ─────────────────────────────────────────
BOT_USERNAME          = "Rpguniverse_bot"     # без @
BIO_BONUS_MULTIPLIER  = 1.1                  # +10% ко всей добыче/урону
BIO_CHECK_INTERVAL    = 1800                 # 30 минут — период фоновой проверки
BIO_STALE_AFTER       = BIO_CHECK_INTERVAL * 2  # если проверка не обновлялась дольше — бонус не действует
_BIO_SCAN_DELAY        = 0.05                # пауза между get_chat, чтобы не словить флуд-контроль

# Ищем именно юзернейм как отдельный токен: необязательный "@" перед ним и
# граница слова после — чтобы "TGStellarr_bot2" или "xTGStellarr_bot" не засчитывались.
_BOT_TAG_RE = re.compile(
    r'(?<![A-Za-z0-9_])@?' + re.escape(BOT_USERNAME) + r'(?![A-Za-z0-9_])',
    re.IGNORECASE,
)


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _bio_has_bot_tag(bio) -> bool:
    if not bio or not isinstance(bio, str):
        return False
    return bool(_BOT_TAG_RE.search(bio))


def get_bio_bonus_multiplier(data: dict) -> float:
    """
    Множитель для добычи/урона. Возвращает BIO_BONUS_MULTIPLIER только если:
      - флаг bio_bonus_active выставлен (сервером, см. refresh_bio_bonus), И
      - последняя проверка не "протухла" (см. BIO_STALE_AFTER).
    В любом другом случае — 1.0 (без бонуса), fail-safe по умолчанию.
    """
    if not data.get("bio_bonus_active"):
        return 1.0
    checked_at = data.get("bio_bonus_checked_at", 0)
    try:
        checked_at = float(checked_at)
    except (TypeError, ValueError):
        return 1.0
    if _now_ts() - checked_at > BIO_STALE_AFTER:
        return 1.0
    return BIO_BONUS_MULTIPLIER


def has_bio_bonus(data: dict) -> bool:
    """Удобный булев хелпер для текстовых экранов (показать плашку бонуса)."""
    return get_bio_bonus_multiplier(data) > 1.0


async def refresh_bio_bonus(bot, uid: int, data: dict) -> bool:
    """
    Делает один запрос bot.get_chat(uid), проверяет bio и обновляет data
    в оперативной памяти (сохранение в БД — забота вызывающего кода).

    Возвращает True, если удалось выполнить проверку (независимо от того,
    поменялся ли сам флаг) — вызывающий код должен сохранить data.
    Возвращает False, если проверку выполнить не удалось (ошибка API) —
    в этом случае data НЕ модифицируется вообще, сохранять не нужно.
    """
    try:
        from aiogram.exceptions import TelegramRetryAfter
    except Exception:
        TelegramRetryAfter = None

    try:
        chat = await bot.get_chat(uid)
    except Exception as e:
        if TelegramRetryAfter is not None and isinstance(e, TelegramRetryAfter):
            # Уважаем флуд-контроль Telegram и просто пропускаем этот тик —
            # текущий флаг НЕ трогаем, следующая попытка будет в след. цикле.
            await asyncio.sleep(min(e.retry_after, 30))
        return False

    bio = getattr(chat, "bio", None)
    has_tag = _bio_has_bot_tag(bio)

    data["bio_bonus_active"]      = has_tag
    data["bio_bonus_checked_at"]  = _now_ts()
    return True


async def bio_bonus_scan_loop(bot):
    """
    Фоновый цикл: раз в BIO_CHECK_INTERVAL обходит всех пользователей и
    обновляет их bio_bonus_active. Пишется по аналогии с уже существующими
    в mainhelp.py циклами (_users_scan_loop и т.п.) — та же обработка
    ошибок на пользователя, чтобы один сбой не ронял весь цикл.
    """
    from database import get_all_users, save_user as _sv

    while True:
        try:
            for _d in await asyncio.to_thread(get_all_users):
                uid = _d.get("id")
                if not uid:
                    continue
                try:
                    ok = await refresh_bio_bonus(bot, uid, _d)
                    if ok:
                        await asyncio.to_thread(_sv, uid, _d)
                except Exception as _e:
                    print(f"[bio_bonus_scan_loop] user {uid}: {_e}")
                # Пауза между запросами get_chat — анти-флуд, не перегружаем Bot API.
                await asyncio.sleep(_BIO_SCAN_DELAY)
        except Exception as _e:
            print(f"[bio_bonus_scan_loop] {_e}")
        await asyncio.sleep(BIO_CHECK_INTERVAL)
