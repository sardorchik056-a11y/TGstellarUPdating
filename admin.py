# admin.py — ВСЕ админские команды и кнопки бота в одном месте.
#
# Раньше эти хендлеры жили прямо в mainhelp.py вперемешку с остальной
# игровой логикой. Здесь ничего не переписано и не изменено по смыслу —
# код перенесён 1-в-1 (те же проверки ADMIN_IDS, те же тексты, те же
# callback_data), просто вынесен в отдельный файл, чтобы админку было
# проще найти и поддерживать отдельно от остального бота.
#
# Подключается точно так же, как case.py / green.py / ivent.py — через
# импорт в main.py (используется тот же bot и тот же dp, так что все
# хендлеры регистрируются в общем диспетчере наравне со старыми).
#
# ВАЖНО: команда /rass умеет ждать свободный текст/фото/видео от админа
# (мастер рассылки) — эта часть логики завязана на общие "ловушки" ввода
# в mainhelp.py (_has_pending_text_input / handle_pending_text_input) и
# на общий callback-роутер (rass_confirm_yes/rass_confirm_no внутри
# большого обработчика инлайн-кнопок). Эти куски специально НЕ трогали и
# оставили в mainhelp.py как есть — они слишком плотно вплетены в общие
# хендлеры, и выдёргивать их оттуда было бы неоправданным риском что-то
# сломать. Сюда вынесены только самостоятельные команды/кнопки админки:
# сами команды /rass и /rass_cancel, и отдельный хендлер приёма медиа
# для рассылки (F.photo | F.video) — они самодостаточны.

import asyncio

from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from mainhelp import bot, dp, ADMIN_IDS, _esc, _parse_amount

from database import (
    format_amount,
    aio_get_user,
    aio_get_user_by_id_or_username,
    aio_save_user,
    aio_clear_all_boosters,
)
from checks import (
    aio_create_check as create_check,
    aio_list_checks as list_checks,
    aio_delete_check as delete_check,
    aio_create_promo as create_promo,
    aio_list_promos as list_promos,
    aio_delete_promo as delete_promo,
)
from status import activate_status
from stats import aio_clear_unregistered
from rass import is_in_rass, rass_start, rass_cancel, rass_fsm_message
from klan import aio_get_member as get_member, aio_leave_clan as leave_clan


# ── /add — выдать/снять монеты игроку ─────────────────────────────────

@dp.message(Command("add"))
async def cmd_add_balance(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split()
    # /add <username|id> <сумма>
    if len(parts) != 3:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/add username|id сумма</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    try:
        amount = int(parts[2])
    except ValueError:
        await message.reply("❌ Сумма должна быть целым числом.", parse_mode="HTML")
        return

    # Поиск пользователя в БД
    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    old_balance = found.get("balance", 0)
    new_balance = old_balance + amount
    if new_balance < 0:
        new_balance = 0  # не уходим в минус

    found["balance"] = new_balance
    await aio_save_user(found["id"], found)

    name   = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    action = "➕ Выдано" if amount >= 0 else "➖ Снято"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'

    await message.reply(
        f"✅ <b>Готово!</b>\n\n"
        f"<blockquote>👤 Игрок: <b>{name}</b> (<code>{found['id']}</code>)\n"
        f"{action}: <b>{format_amount(abs(amount))}</b> {coin}\n"
        f"Было: <b>{format_amount(old_balance)}</b> {coin}\n"
        f"Стало: <b>{format_amount(new_balance)}</b> {coin}</blockquote>",
        parse_mode="HTML"
    )


# ── /getallart — выдать себе/игроку все артефакты ─────────────────────

@dp.message(Command("getallart"))
async def cmd_getallart(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    from shop import _ARTIFACT_POOL, get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier

    parts = message.text.strip().split()

    # Определяем целевого пользователя
    if len(parts) >= 2:
        # /getallart @username  или  /getallart 123456789
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        if not data:
            await message.reply(
                f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
                parse_mode="HTML",
            )
            return
        uid = data["id"]
    else:
        # без аргумента — выдаём себе
        uid  = message.from_user.id
        data = await aio_get_user(uid)
        if not data:
            await message.reply(
                "❌ Пользователь не найден в БД. Напиши /start сначала.",
                parse_mode="HTML",
            )
            return

    artifacts = data.setdefault("artifacts", [])
    already   = {e["key"] for e in artifacts}
    added     = []
    for a in _ARTIFACT_POOL:
        if a["key"] not in already:
            artifacts.append({"key": a["key"]})
            added.append(a)
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + len(added)
    await aio_save_user(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    name = _esc(data.get("first_name") or data.get("username") or str(uid))
    if added:
        lines  = "\n".join(f'<b>✅ {a["name"]} — {a["multiplier"]}×</b>' for a in added)
        status = f"<b>Добавлено: {len(added)} шт.</b>\n{lines}"
    else:
        status = "<b>Все артефакты уже были в коллекции.</b>"

    await message.reply(
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GETALLART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{status}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>',
        parse_mode="HTML",
    )


# ── /updamage — переключить бесконечный урон игроку ───────────────────

@dp.message(Command("updamage"))
async def cmd_updamage(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/updamage username|id</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    current = found.get("infinite_dmg", False)
    found["infinite_dmg"] = not current
    await aio_save_user(found["id"], found)

    name = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    status = "✅ <b>Включён</b>" if found["infinite_dmg"] else "❌ <b>Выключен</b>"

    await message.reply(
        f'⚔️ <b>Бесконечный урон для {name}:</b> {status}',
        parse_mode="HTML"
    )


# ── /checkmine — посмотреть кирки и статус шахты у игрока ─────────────

@dp.message(Command("checkmine"))
async def cmd_checkmine(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    from miner import PICKAXES, PICKAXES_ORDER, TIER_LABELS, fmt_time, calc_mine_progress

    parts = message.text.strip().split()

    # Определяем целевого пользователя: реплай > @username/id аргумент > себя
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
    elif len(parts) >= 2:
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
    else:
        uid  = message.from_user.id
        data = await aio_get_user(uid)

    if not data:
        await message.reply(
            "❌ Пользователь не найден в базе.\n"
            "Использование: <code>/checkmine @username</code> или <code>/checkmine id</code>, "
            "либо ответом (reply) на сообщение игрока.",
            parse_mode="HTML",
        )
        return

    name    = _esc(data.get("first_name") or data.get("username") or str(uid))
    owned   = data.get("owned_pickaxes", ["wood_1"])
    current = data.get("pickaxe", "wood_1")

    # Сортируем открытые кирки в порядке их появления в игре
    owned_sorted = [k for k in PICKAXES_ORDER if k in owned]

    lines = []
    for key in owned_sorted:
        p = PICKAXES.get(key)
        if not p:
            continue
        tier = TIER_LABELS.get(p.get("tier", ""), "")
        mark = "✅" if key == current else "▫️"
        lines.append(
            f"{mark} <b>{_esc(p['name'])}</b> {tier}\n"
            f"    ⛏ {p['dig_min']}–{p['dig_max']} за удар"
        )
    pickaxes_block = "\n".join(lines) if lines else "<i>Нет открытых кирок</i>"

    # Статус текущей добычи
    if data.get("mine_start"):
        prog = calc_mine_progress(data)
        if prog["finished"]:
            mine_status = "✅ <b>Добыча завершена, ждёт сбора</b>"
        else:
            mine_status = f"⏳ <b>Идёт добыча</b> — осталось {fmt_time(prog['time_left'])}"
    else:
        mine_status = "⛔️ <b>Шахта не запущена</b>"

    await message.reply(
        f'⛏ <b>CHECKMINE</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{mine_status}</blockquote>\n\n'
        f'<b>Открытые кирки ({len(owned_sorted)}/{len(PICKAXES_ORDER)}):</b>\n'
        f'<blockquote>{pickaxes_block}</blockquote>',
        parse_mode="HTML",
    )


# ── /deletebd — полное удаление данных игрока (с подтверждением) ──────

_pending_delete_bd: dict[int, int] = {}


@dp.message(Command("deletebd"))
async def cmd_deletebd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split()

    # Определяем целевого пользователя: реплай > @username/id аргумент
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
    elif len(parts) >= 2:
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
    else:
        await message.reply(
            "❌ Не указан игрок.\n"
            "Использование: <code>/deletebd @username</code> или <code>/deletebd id</code>, "
            "либо ответом (reply) на сообщение игрока.",
            parse_mode="HTML",
        )
        return

    if not data:
        await message.reply("❌ Пользователь не найден в базе.", parse_mode="HTML")
        return

    if uid in ADMIN_IDS:
        await message.reply("❌ Нельзя удалить данные администратора этой командой.", parse_mode="HTML")
        return

    name = _esc(data.get("first_name") or data.get("username") or str(uid))
    _pending_delete_bd[message.from_user.id] = uid

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить всё", callback_data=f"delbd_yes:{uid}")
    kb.button(text="❌ Отмена", callback_data="delbd_no")
    kb.adjust(1)

    await message.reply(
        f'⚠️ <b>ВНИМАНИЕ — ПОЛНОЕ УДАЛЕНИЕ ДАННЫХ</b>\n\n'
        f'<blockquote>Игрок: <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'Будут стёрты <b>все</b> данные: баланс, шахта, кирки, питомцы, '
        f'оружие/бои, статус, инвентарь, достижения и весь прогресс.\n'
        f'Игрок начнёт игру полностью заново, как новый пользователь.\n\n'
        f'<b>Это действие необратимо!</b></blockquote>',
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


def _delete_user_row_sync(uid: int):
    """
    Синхронная часть удаления игрока — выполняется ТОЛЬКО через
    asyncio.to_thread (см. вызов в cb_deletebd_confirm), никогда напрямую
    из event loop. Те же PRAGMA, что и в остальных местах проекта (WAL +
    busy_timeout), чтобы соединение вело себя предсказуемо.
    """
    import sqlite3 as _sq
    _conn = _sq.connect("tgstellar.db", timeout=30)
    try:
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=30000")
        _conn.execute("DELETE FROM users WHERE uid=?", (uid,))
        _conn.commit()
    finally:
        # `with _conn:` управляет только транзакцией (commit/rollback), но
        # НЕ закрывает соединение — close() обязателен, иначе fd на
        # tgstellar.db копятся и БД начинает "залипать" (database is locked).
        _conn.close()


@dp.callback_query(F.data.startswith("delbd_yes:"))
async def cb_deletebd_confirm(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа.", show_alert=True)
        return

    target_uid = int(call.data.split(":", 1)[1])

    # Подтверждение должно приходить именно от админа, запустившего команду,
    # и совпадать с сохранённой целью — защита от гонок/устаревших кнопок
    if _pending_delete_bd.get(call.from_user.id) != target_uid:
        await call.answer("Запрос устарел, повтори команду заново.", show_alert=True)
        return
    _pending_delete_bd.pop(call.from_user.id, None)

    # Best-effort: аккуратно выходим из клана, чтобы не оставить "мёртвого" участника
    try:
        if await get_member(target_uid):
            await leave_clan(target_uid)
    except Exception as _e:
        print(f"[deletebd] leave_clan error: {_e}")

    # Полное удаление записи игрока — при следующем /start он создастся заново с нуля.
    # Синхронный sqlite-доступ выполняется в отдельном потоке (asyncio.to_thread),
    # чтобы не блокировать event loop для всех остальных пользователей.
    try:
        await asyncio.to_thread(_delete_user_row_sync, target_uid)
    except Exception as _e:
        await call.message.edit_text(f"❌ Ошибка при удалении: {_e}")
        return

    await call.message.edit_text(
        f'🗑 <b>Данные игрока <code>{target_uid}</code> полностью удалены.</b>\n\n'
        f'<blockquote>При следующем /start он начнёт игру с чистого листа.</blockquote>',
        parse_mode="HTML",
    )
    await call.answer("Удалено.")


@dp.callback_query(F.data == "delbd_no")
async def cb_deletebd_cancel(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    _pending_delete_bd.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Удаление отменено.")
    await call.answer()


# ── /giveart — выдать конкретный артефакт игроку ───────────────────────

@dp.message(Command("giveart"))
async def cmd_giveart(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    from shop import _ARTIFACT_POOL, get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier

    text = message.text.strip()

    # Определяем целевого пользователя и название артефакта:
    # /giveart @username Название артефакта
    # /giveart 123456789 Название артефакта
    # ответом (reply) на игрока: /giveart Название артефакта
    if message.reply_to_message and message.reply_to_message.from_user:
        uid  = message.reply_to_message.from_user.id
        data = await aio_get_user(uid)
        rest = text.split(maxsplit=1)
        name_query = rest[1] if len(rest) >= 2 else ""
    else:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply(
                "❌ Использование: <code>/giveart @username Название артефакта</code>\n"
                "или <code>/giveart id Название артефакта</code>,\n"
                "либо ответом (reply) на игрока: <code>/giveart Название артефакта</code>.",
                parse_mode="HTML",
            )
            return
        target_raw = parts[1].lstrip("@")
        data = await aio_get_user_by_id_or_username(target_raw)
        uid  = data["id"] if data else None
        name_query = parts[2]

    if not data:
        await message.reply("❌ Пользователь не найден в базе.", parse_mode="HTML")
        return

    name_query = name_query.strip()
    if not name_query:
        await message.reply("❌ Не указано название артефакта.", parse_mode="HTML")
        return

    # Поиск артефакта: точное совпадение по RU/EN названию или ключу,
    # затем — частичное совпадение (по подстроке)
    q = name_query.lower()
    found = None
    for a in _ARTIFACT_POOL:
        if q in (a["name"].lower(), a.get("name_en", "").lower(), a["key"].lower()):
            found = a
            break
    if not found:
        for a in _ARTIFACT_POOL:
            if q in a["name"].lower() or q in a.get("name_en", "").lower():
                found = a
                break

    if not found:
        listing = "\n".join(f"• {a['name']} ({a.get('name_en', '')})" for a in _ARTIFACT_POOL)
        await message.reply(
            f"❌ Артефакт «{_esc(name_query)}» не найден.\n\n"
            f"<b>Доступные артефакты:</b>\n{_esc(listing)}",
            parse_mode="HTML",
        )
        return

    artifacts = data.setdefault("artifacts", [])
    name  = _esc(data.get("first_name") or data.get("username") or str(uid))

    if any(entry["key"] == found["key"] for entry in artifacts):
        await message.reply(
            f'⚠️ У игрока <b>{name}</b> (<code>{uid}</code>) артефакт '
            f'«<b>{_esc(found["name"])}</b>» уже есть. Повторно не выдаю.',
            parse_mode="HTML",
        )
        return

    artifacts.append({"key": found["key"]})
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1
    await aio_save_user(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    art_name_line = f'{found["name"]} ({found.get("name_en", "")}) — {found["multiplier"]}×'

    await message.reply(
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GIVEART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote><b>✅ Выдан артефакт:</b>\n{_esc(art_name_line)}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>',
        parse_mode="HTML",
    )


# ── /addalldiamond — начислить кристаллы всем игрокам города ──────────

@dp.message(Command("addalldiamond"))
async def cmd_addalldiamond(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # тихо игнорируем

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/addalldiamond сумма</code>\n"
            "<i>Например: /addalldiamond 500 или /addalldiamond 1к</i>",
            parse_mode="HTML"
        )
        return

    amount = _parse_amount(parts[1])
    if amount is None or amount == 0:
        await message.reply("❌ Не удалось распознать сумму.", parse_mode="HTML")
        return

    from city import aio_add_crystals_to_all
    count = await aio_add_crystals_to_all(amount)

    sign = "+" if amount > 0 else ""
    await message.reply(
        f"💎 <b>Кристаллы начислены!</b>\n"
        f"Всем игрокам города ({count}) выдано <b>{sign}{amount}</b> кристаллов.",
        parse_mode="HTML"
    )


# ── /getstatus — выдать VIP/Premium статус игроку ──────────────────────

@dp.message(Command("getstatus"))
async def cmd_getstatus(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.strip().split()
    # /getstatus <username|id> <vip|pr>
    if len(parts) != 3 or parts[2].lower() not in ("vip", "pr", "premium"):
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/getstatus username|id vip|pr</code>",
            parse_mode="HTML"
        )
        return

    target_raw = parts[1].lstrip("@")
    tier_arg   = parts[2].lower()
    tier       = "premium" if tier_arg in ("pr", "premium") else "vip"

    found = await aio_get_user_by_id_or_username(target_raw)

    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML"
        )
        return

    ok, msg = activate_status(found, tier)
    if ok:
        await aio_save_user(found["id"], found)

    name  = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    label = "VIP" if tier == "vip" else "Premium"
    await message.reply(
        f'✅ <b>Статус {label} выдан!</b>\n\n'
        f'<blockquote>👤 Игрок: <b>{name}</b> (<code>{found["id"]}</code>)\n'
        f'📅 Срок: <b>30 дней</b></blockquote>',
        parse_mode="HTML"
    )


# ── /addcheck, /checks, /delcheck — чеки ────────────────────────────────

@dp.message(Command("addcheck"))
async def cmd_addcheck(message: Message):
    """/addcheck <сумма> <кол-во активаций>"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.reply(
            "❌ Формат: <code>/addcheck сумма кол-во</code>\n"
            "Пример: <code>/addcheck 10000 10</code>",
            parse_mode="HTML"
        )
        return
    try:
        amount = int(parts[1])
        uses   = int(parts[2])
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    bot_me = await bot.get_me()
    code   = await create_check(amount, uses)
    link   = f"https://t.me/{bot_me.username}?start=check_{code}"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    await message.reply(
        f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Чек создан!</b>\n\n'
        f'<blockquote>'
        f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
        f'<tg-emoji emoji-id="5330320040883411678">🎁</tg-emoji> <b>Активаций:</b> {uses}\n'
        f'<tg-emoji emoji-id="5444856076954520455">🔗</tg-emoji> <b>Код:</b> <code>{code}</code>'
        f'</blockquote>\n\n'
        f'<b><tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji>Ссылка:</b> {link}',
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@dp.message(Command("checks"))
async def cmd_list_checks(message: Message):
    """Список активных чеков."""
    if message.from_user.id not in ADMIN_IDS:
        return
    items = await list_checks()
    if not items:
        await message.reply("📭 Чеков нет.", parse_mode="HTML")
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{c["code"]}</code> — {coin} {format_amount(c["amount"])} · [{c["uses_left"]}/{c["uses_total"]}]'
        for c in items
    ]
    await message.reply(
        f'<b>📋 Чеки ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML"
    )


@dp.message(Command("delcheck"))
async def cmd_delcheck(message: Message):
    """Удалить чек. /delcheck код"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/delcheck код</code>", parse_mode="HTML")
        return
    ok = await delete_check(parts[1])
    await message.reply("✅ Чек удалён." if ok else "❌ Чек не найден.", parse_mode="HTML")


# ── /addpromo, /promos, /delpromo — промокоды ──────────────────────────

@dp.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
    """/addpromo <название> <сумма> <кол-во активаций>"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 4:
        await message.reply(
            "❌ Формат: <code>/addpromo название сумма кол-во</code>\n"
            "Пример: <code>/addpromo stars 1000 10</code>",
            parse_mode="HTML"
        )
        return
    name = parts[1]
    try:
        amount = int(parts[2])
        uses   = int(parts[3])
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    ok, reason = await create_promo(name, amount, uses)
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    if ok:
        await message.reply(
            f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Промокод создан!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5444856076954520455">🎁</tg-emoji> <b>Код:</b> <code>{name}</code>\n'
            f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
            f'<tg-emoji emoji-id="5330320040883411678">🎟</tg-emoji> <b>Активаций:</b> {uses}'
            f'</blockquote>',
            parse_mode="HTML",
        )
    else:
        await message.reply(
            f'❌ Промокод <code>{name}</code> уже существует.',
            parse_mode="HTML"
        )


@dp.message(Command("promos"))
async def cmd_list_promos(message: Message):
    """Список промокодов."""
    if message.from_user.id not in ADMIN_IDS:
        return
    items = await list_promos()
    if not items:
        await message.reply("📭 Промокодов нет.", parse_mode="HTML")
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{p["name"]}</code> — {coin} {format_amount(p["amount"])} · [{p["uses_left"]}/{p["uses_total"]}]'
        for p in items
    ]
    await message.reply(
        f'<b>📋 Промокоды ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML"
    )


@dp.message(Command("delpromo"))
async def cmd_delpromo(message: Message):
    """Удалить промокод. /delpromo название"""
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>/delpromo название</code>", parse_mode="HTML")
        return
    ok = await delete_promo(parts[1])
    await message.reply("✅ Промокод удалён." if ok else "❌ Промокод не найден.", parse_mode="HTML")


# ── /clear — чистка накрутки в статистике ────────────────────────────

@dp.message(Command("clear"))
async def cmd_clear_stats(message: Message):
    """
    Удаляет из статистики (/stats) пользователей, которые нажали /start,
    но так и не прошли онбординг (капчу/выбор языка) — они не реальные
    пользователи и не попадают в рассылку (/rass), поэтому не должны
    учитываться и в счётчиках.
    """
    if message.from_user.id not in ADMIN_IDS:
        return
    removed = await aio_clear_unregistered()
    await message.reply(
        f'🧹 <b>Очистка завершена.</b>\n\n'
        f'<blockquote>Удалено незавершённых регистраций: <b>{removed}</b></blockquote>',
        parse_mode="HTML",
    )


# ── /rass, /rass_cancel — рассылка ─────────────────────────────────────

@dp.message(Command("rass"))
async def cmd_rass(message: Message):
    await rass_start(message, ADMIN_IDS)


@dp.message(Command("rass_cancel"))
async def cmd_rass_cancel(message: Message):
    await rass_cancel(message, ADMIN_IDS)


# ── Рассылка: приём медиа (фото/видео) от админа ───────────────────────
# Единственный в проекте хендлер на F.photo | F.video — самодостаточен,
# порядок регистрации относительно остальных хендлеров mainhelp.py тут
# не важен.

@dp.message(F.photo | F.video)
async def handle_rass_media(message: Message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS or not is_in_rass(uid):
        return
    await rass_fsm_message(message, ADMIN_IDS)


# ═══════════════════════════════════════════════════════════════════════
#  /admin — КНОПОЧНАЯ АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════════════════════════════════
#
# Всё, что выше в этом файле — старые команды админки (/add, /giveart,
# /addcheck и т.д.), они трогать не трогаем, работают как работали.
#
# Ниже — отдельная кнопочная панель по команде /admin, которая даёт доступ
# к тем же действиям через инлайн-кнопки, без необходимости помнить
# синтаксис команд. Там, где действию нужен текстовый ввод (юзернейм/id,
# сумма и т.п.), панель переводит админа в специальное FSM-состояние и
# ждёт следующее сообщение именно от него.
#
# ВАЖНО про порядок хендлеров (это принципиально для корректной работы):
#   1. В mainhelp.py есть глобальный перехватчик ЛЮБОГО текста без "/"
#      (handle_free_text: `@dp.message(F.text & ~F.text.startswith("/"))`),
#      зарегистрированный РАНЬШЕ хендлеров этого файла. Поэтому наши
#      FSM-хендлеры ввода (StateFilter) сами по себе просто не получали бы
#      management, aiogram отдавал бы текст сначала в handle_free_text.
#   2. Там же есть общий callback-роутер
#      `@dp.callback_query(~F.data.startswith("city_") & ~F.data.startswith("crystop_"))`,
#      который перехватывает буквально ЛЮБОЙ callback_data, кроме
#      начинающихся на "city_"/"crystop_" — то есть и наши "adm_*"
#      кнопки тоже, если ничего не делать.
#   3. В main.py уже есть готовое решение той же проблемы для
#      /startcase — функция `_prioritize_message_handlers`, которая
#      переставляет НАШИ уже зарегистрированные хендлеры в начало
#      внутреннего списка dp.message.handlers. Мы используем тот же приём
#      и добавляем аналогичный `_prioritize_callback_handlers` для
#      dp.callback_query.handlers (см. main.py — там же, в самом низу,
#      наши хендлеры добавлены в списки на приоритизацию).
#   4. Все хендлеры этой панели сами проверяют StateFilter/callback_data,
#      поэтому для всех остальных пользователей (и для админа вне панели)
#      они просто не совпадают по фильтру и aiogram идёт дальше по списку —
#      никакого влияния на остальной бот это не оказывает.


class AdminPanel(StatesGroup):
    balance_input          = State()   # /add: "юзернейм|id сумма"
    diamond_all_input      = State()   # /addalldiamond: "сумма"
    status_target_input    = State()   # /getstatus: юзернейм|id → потом кнопки VIP/Premium
    status_pick_tier       = State()
    artifact_all_target    = State()   # getallart игроку (не себе)
    giveart_target_input   = State()   # /giveart: юзернейм|id → потом кнопка артефакта
    giveart_pick           = State()
    updamage_target_input  = State()   # /updamage: юзернейм|id
    checkmine_target_input = State()   # /checkmine: юзернейм|id
    deletebd_target_input  = State()   # /deletebd: юзернейм|id → подтверждение
    check_create_input     = State()   # /addcheck: "сумма кол-во"
    check_delete_input     = State()   # /delcheck: "код"
    promo_create_input     = State()   # /addpromo: "название сумма кол-во"
    promo_delete_input     = State()   # /delpromo: "название"


def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ── Общие клавиатуры ────────────────────────────────────────────────────

def _admin_main_text() -> str:
    return (
        "🛠 <b>Админ-панель</b>\n\n"
        "<blockquote>Выбери раздел ниже.</blockquote>"
    )


def _admin_main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс",             callback_data="adm_menu:balance")
    kb.button(text="💎 Кристаллы всем",     callback_data="adm_menu:diamondall")
    kb.button(text="👑 Статус",             callback_data="adm_menu:status")
    kb.button(text="⚔️ Беск. урон",         callback_data="adm_menu:updamage")
    kb.button(text="🎁 Артефакты",          callback_data="adm_menu:artifacts")
    kb.button(text="⛏ Шахта игрока",       callback_data="adm_menu:checkmine")
    kb.button(text="🗑 Удалить игрока",     callback_data="adm_menu:deletebd")
    kb.button(text="🎟 Чеки",               callback_data="adm_menu:checks")
    kb.button(text="🏷 Промокоды",          callback_data="adm_menu:promos")
    kb.button(text="🧹 Очистка статистики", callback_data="adm_menu:clearstats")
    kb.button(text="⚡ Очистить ускорители", callback_data="adm_menu:clearboosters")
    kb.button(text="📢 Рассылка",           callback_data="adm_menu:broadcast")
    kb.button(text="❌ Закрыть",            callback_data="adm_close")
    kb.adjust(2, 2, 2, 1, 2, 1, 1, 1)
    return kb.as_markup()


def _back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="adm_back")
    kb.adjust(1)
    return kb.as_markup()


def _cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="adm_back")
    kb.adjust(1)
    return kb.as_markup()


# ── Общие async-хелперы, повторяющие логику команд выше (без изменений
#    самих команд — чтобы ничего из уже работающего не сломать) ─────────

async def _do_add_balance(found: dict, amount: int) -> str:
    old_balance = found.get("balance", 0)
    new_balance = old_balance + amount
    if new_balance < 0:
        new_balance = 0
    found["balance"] = new_balance
    await aio_save_user(found["id"], found)

    name   = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    action = "➕ Выдано" if amount >= 0 else "➖ Снято"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'

    return (
        f"✅ <b>Готово!</b>\n\n"
        f"<blockquote>👤 Игрок: <b>{name}</b> (<code>{found['id']}</code>)\n"
        f"{action}: <b>{format_amount(abs(amount))}</b> {coin}\n"
        f"Было: <b>{format_amount(old_balance)}</b> {coin}\n"
        f"Стало: <b>{format_amount(new_balance)}</b> {coin}</blockquote>"
    )


async def _do_getallart(uid: int, data: dict) -> str:
    from shop import _ARTIFACT_POOL, get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier

    artifacts = data.setdefault("artifacts", [])
    already   = {e["key"] for e in artifacts}
    added     = []
    for a in _ARTIFACT_POOL:
        if a["key"] not in already:
            artifacts.append({"key": a["key"]})
            added.append(a)
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + len(added)
    await aio_save_user(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    name = _esc(data.get("first_name") or data.get("username") or str(uid))
    if added:
        lines  = "\n".join(f'<b>✅ {a["name"]} — {a["multiplier"]}×</b>' for a in added)
        status = f"<b>Добавлено: {len(added)} шт.</b>\n{lines}"
    else:
        status = "<b>Все артефакты уже были в коллекции.</b>"

    return (
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GETALLART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{status}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>'
    )


async def _do_giveart(uid: int, data: dict, art: dict) -> str:
    from shop import get_artifact_mine_multiplier, get_artifact_damage_multiplier, get_artifact_pets_multiplier

    artifacts = data.setdefault("artifacts", [])
    name = _esc(data.get("first_name") or data.get("username") or str(uid))

    if any(entry["key"] == art["key"] for entry in artifacts):
        return (
            f'⚠️ У игрока <b>{name}</b> (<code>{uid}</code>) артефакт '
            f'«<b>{_esc(art["name"])}</b>» уже есть. Повторно не выдаю.'
        )

    artifacts.append({"key": art["key"]})
    data["artifact_cases_opened"] = data.get("artifact_cases_opened", 0) + 1
    await aio_save_user(uid, data)

    mine_mult   = get_artifact_mine_multiplier(data)
    damage_mult = get_artifact_damage_multiplier(data)
    pets_mult   = get_artifact_pets_multiplier(data)

    art_name_line = f'{art["name"]} ({art.get("name_en", "")}) — {art["multiplier"]}×'

    return (
        f'<tg-emoji emoji-id="5442939099906325301">💎</tg-emoji> <b>GIVEART</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote><b>✅ Выдан артефакт:</b>\n{_esc(art_name_line)}</blockquote>\n\n'
        f'<blockquote>'
        f'<b>Итоговые бонусы:</b>\n'
        f'<b>⛏ Добыча руды: ×{mine_mult}</b>\n'
        f'<b>⚔️ Урон по боссу: ×{damage_mult}</b>\n'
        f'<b>🐾 Добыча питомцов: ×{pets_mult}</b>'
        f'</blockquote>'
    )


async def _do_updamage(found: dict) -> str:
    current = found.get("infinite_dmg", False)
    found["infinite_dmg"] = not current
    await aio_save_user(found["id"], found)
    name   = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    status = "✅ <b>Включён</b>" if found["infinite_dmg"] else "❌ <b>Выключен</b>"
    return f'⚔️ <b>Бесконечный урон для {name}:</b> {status}'


def _do_checkmine_text(uid: int, data: dict) -> str:
    from miner import PICKAXES, PICKAXES_ORDER, TIER_LABELS, fmt_time, calc_mine_progress

    name    = _esc(data.get("first_name") or data.get("username") or str(uid))
    owned   = data.get("owned_pickaxes", ["wood_1"])
    current = data.get("pickaxe", "wood_1")
    owned_sorted = [k for k in PICKAXES_ORDER if k in owned]

    lines = []
    for key in owned_sorted:
        p = PICKAXES.get(key)
        if not p:
            continue
        tier = TIER_LABELS.get(p.get("tier", ""), "")
        mark = "✅" if key == current else "▫️"
        lines.append(
            f"{mark} <b>{_esc(p['name'])}</b> {tier}\n"
            f"    ⛏ {p['dig_min']}–{p['dig_max']} за удар"
        )
    pickaxes_block = "\n".join(lines) if lines else "<i>Нет открытых кирок</i>"

    if data.get("mine_start"):
        prog = calc_mine_progress(data)
        if prog["finished"]:
            mine_status = "✅ <b>Добыча завершена, ждёт сбора</b>"
        else:
            mine_status = f"⏳ <b>Идёт добыча</b> — осталось {fmt_time(prog['time_left'])}"
    else:
        mine_status = "⛔️ <b>Шахта не запущена</b>"

    return (
        f'⛏ <b>CHECKMINE</b>\n'
        f'👤 <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'<blockquote>{mine_status}</blockquote>\n\n'
        f'<b>Открытые кирки ({len(owned_sorted)}/{len(PICKAXES_ORDER)}):</b>\n'
        f'<blockquote>{pickaxes_block}</blockquote>'
    )


async def _do_getstatus(found: dict, tier: str) -> str:
    ok, msg = activate_status(found, tier)
    name  = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    label = "VIP" if tier == "vip" else "Premium"
    if not ok:
        return f'❌ {_esc(msg or "Не удалось выдать статус.")}'
    await aio_save_user(found["id"], found)
    return (
        f'✅ <b>Статус {label} выдан!</b>\n\n'
        f'<blockquote>👤 Игрок: <b>{name}</b> (<code>{found["id"]}</code>)\n'
        f'📅 Срок: <b>30 дней</b></blockquote>'
    )


# ── /admin — открыть панель ─────────────────────────────────────────────

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return  # тихо игнорируем, как и остальные админ-команды в проекте
    await state.clear()
    await message.reply(_admin_main_text(), parse_mode="HTML", reply_markup=_admin_main_keyboard())


@dp.callback_query(F.data == "adm_close")
async def cb_admin_close(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("🛠 Админ-панель закрыта. Открыть заново: /admin")
    await call.answer()


@dp.callback_query(F.data == "adm_back")
async def cb_admin_back(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text(_admin_main_text(), parse_mode="HTML", reply_markup=_admin_main_keyboard())
    await call.answer()


# ── Роутер разделов главного меню ───────────────────────────────────────

@dp.callback_query(F.data.startswith("adm_menu:"))
async def cb_admin_menu(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return

    section = call.data.split(":", 1)[1]
    await state.clear()

    if section == "balance":
        await state.set_state(AdminPanel.balance_input)
        await call.message.edit_text(
            "💰 <b>Выдать/снять баланс</b>\n\n"
            "Отправь одним сообщением: <code>юзернейм|id сумма</code>\n"
            "Например: <code>@ivan 500</code> или <code>123456789 -200</code>",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "diamondall":
        await state.set_state(AdminPanel.diamond_all_input)
        await call.message.edit_text(
            "💎 <b>Кристаллы всем игрокам города</b>\n\n"
            "Отправь сумму, например: <code>500</code> или <code>1к</code>",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "status":
        await state.set_state(AdminPanel.status_target_input)
        await call.message.edit_text(
            "👑 <b>Выдать статус VIP/Premium</b>\n\n"
            "Отправь юзернейм или id игрока.",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "updamage":
        await state.set_state(AdminPanel.updamage_target_input)
        await call.message.edit_text(
            "⚔️ <b>Переключить бесконечный урон</b>\n\n"
            "Отправь юзернейм или id игрока.",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "artifacts":
        kb = InlineKeyboardBuilder()
        kb.button(text="💎 Выдать все себе",   callback_data="adm_art_all_self")
        kb.button(text="💎 Выдать все игроку", callback_data="adm_art_all_ask")
        kb.button(text="🎯 Выдать один артефакт", callback_data="adm_art_one_ask")
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text("🎁 <b>Артефакты</b>\n\nВыбери действие.", parse_mode="HTML", reply_markup=kb.as_markup())

    elif section == "checkmine":
        await state.set_state(AdminPanel.checkmine_target_input)
        await call.message.edit_text(
            "⛏ <b>Проверить шахту игрока</b>\n\nОтправь юзернейм или id игрока.",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "deletebd":
        await state.set_state(AdminPanel.deletebd_target_input)
        await call.message.edit_text(
            "🗑 <b>Полное удаление данных игрока</b>\n\n"
            "⚠️ Действие необратимо. Отправь юзернейм или id игрока.",
            parse_mode="HTML", reply_markup=_cancel_kb(),
        )

    elif section == "checks":
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ Создать чек",   callback_data="adm_chk_create")
        kb.button(text="📋 Список чеков", callback_data="adm_chk_list")
        kb.button(text="🗑 Удалить чек",   callback_data="adm_chk_delete")
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text("🎟 <b>Чеки</b>\n\nВыбери действие.", parse_mode="HTML", reply_markup=kb.as_markup())

    elif section == "promos":
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ Создать промокод",   callback_data="adm_pr_create")
        kb.button(text="📋 Список промокодов", callback_data="adm_pr_list")
        kb.button(text="🗑 Удалить промокод",   callback_data="adm_pr_delete")
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text("🏷 <b>Промокоды</b>\n\nВыбери действие.", parse_mode="HTML", reply_markup=kb.as_markup())

    elif section == "clearstats":
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, очистить", callback_data="adm_clearstats_yes")
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text(
            "🧹 <b>Очистка статистики</b>\n\n"
            "Удалит из статистики (/stats) пользователей, которые нажали /start, "
            "но не завершили онбординг. Продолжить?",
            parse_mode="HTML", reply_markup=kb.as_markup(),
        )

    elif section == "clearboosters":
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, очистить", callback_data="adm_clearboosters_yes")
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text(
            "⚡ <b>Очистить ускорители у всех игроков</b>\n\n"
            "Удалит у ВСЕХ игроков ускорители кирки, XP-ускорители, "
            "усилители урона и зелья/яды (инвентарь и активные эффекты).\n"
            "Артефакты, баланс, уровень и статус — не затронет.\n\n"
            "Продолжить?",
            parse_mode="HTML", reply_markup=kb.as_markup(),
        )

    elif section == "broadcast":
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ В меню", callback_data="adm_back")
        kb.adjust(1)
        await call.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Мастер рассылки умеет ждать текст/фото/видео от тебя и работает "
            "через отдельные команды — просто отправь одну из них:\n\n"
            "▶️ Начать: <code>/rass</code>\n"
            "⏹ Отменить: <code>/rass_cancel</code>",
            parse_mode="HTML", reply_markup=kb.as_markup(),
        )

    await call.answer()


# ── Баланс ───────────────────────────────────────────────────────────────

@dp.message(StateFilter(AdminPanel.balance_input))
async def admin_input_balance(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").strip().split()
    if len(parts) != 2:
        await message.reply(
            "❌ Формат: <code>юзернейм|id сумма</code>\nНапример: <code>@ivan 500</code>",
            parse_mode="HTML",
        )
        return
    target_raw = parts[0].lstrip("@")
    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("❌ Сумма должна быть целым числом.", parse_mode="HTML")
        return
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return
    await state.clear()
    text = await _do_add_balance(found, amount)
    await message.reply(text, parse_mode="HTML", reply_markup=_back_kb())


# ── Кристаллы всем ────────────────────────────────────────────────────────

@dp.message(StateFilter(AdminPanel.diamond_all_input))
async def admin_input_diamond_all(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    amount = _parse_amount((message.text or "").strip())
    if amount is None or amount == 0:
        await message.reply("❌ Не удалось распознать сумму.", parse_mode="HTML")
        return
    await state.clear()
    from city import aio_add_crystals_to_all
    count = await aio_add_crystals_to_all(amount)
    sign = "+" if amount > 0 else ""
    await message.reply(
        f"💎 <b>Кристаллы начислены!</b>\n"
        f"Всем игрокам города ({count}) выдано <b>{sign}{amount}</b> кристаллов.",
        parse_mode="HTML", reply_markup=_back_kb(),
    )


# ── Статус VIP/Premium ────────────────────────────────────────────────────

@dp.message(StateFilter(AdminPanel.status_target_input))
async def admin_input_status_target(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    if not target_raw:
        await message.reply("❌ Отправь юзернейм или id.", parse_mode="HTML")
        return
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return
    await state.update_data(target_uid=found["id"])
    await state.set_state(AdminPanel.status_pick_tier)
    name = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    kb = InlineKeyboardBuilder()
    kb.button(text="👑 VIP",     callback_data="adm_status_pick:vip")
    kb.button(text="⭐ Premium", callback_data="adm_status_pick:premium")
    kb.button(text="❌ Отмена",  callback_data="adm_back")
    kb.adjust(2, 1)
    await message.reply(f"👤 Игрок: <b>{name}</b>\nВыбери статус:", parse_mode="HTML", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("adm_status_pick:"), StateFilter(AdminPanel.status_pick_tier))
async def cb_admin_status_pick(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    tier  = call.data.split(":", 1)[1]
    fdata = await state.get_data()
    target_uid = fdata.get("target_uid")
    await state.clear()

    found = await aio_get_user(target_uid) if target_uid else None
    if not found:
        await call.message.edit_text("❌ Запрос устарел, повтори через /admin.", reply_markup=_back_kb())
        await call.answer()
        return

    text = await _do_getstatus(found, tier)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=_back_kb())
    await call.answer()


# ── Бесконечный урон ───────────────────────────────────────────────────────

@dp.message(StateFilter(AdminPanel.updamage_target_input))
async def admin_input_updamage(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return
    await state.clear()
    text = await _do_updamage(found)
    await message.reply(text, parse_mode="HTML", reply_markup=_back_kb())


# ── Артефакты ────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_art_all_self")
async def cb_art_all_self(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    uid  = call.from_user.id
    data = await aio_get_user(uid)
    if not data:
        await call.answer("Сначала напиши /start.", show_alert=True)
        return
    text = await _do_getallart(uid, data)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=_back_kb())
    await call.answer()


@dp.callback_query(F.data == "adm_art_all_ask")
async def cb_art_all_ask(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.artifact_all_target)
    await call.message.edit_text("💎 Отправь юзернейм или id игрока.", parse_mode="HTML", reply_markup=_cancel_kb())
    await call.answer()


@dp.message(StateFilter(AdminPanel.artifact_all_target))
async def admin_input_artifact_all(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return
    await state.clear()
    text = await _do_getallart(found["id"], found)
    await message.reply(text, parse_mode="HTML", reply_markup=_back_kb())


@dp.callback_query(F.data == "adm_art_one_ask")
async def cb_art_one_ask(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.giveart_target_input)
    await call.message.edit_text(
        "🎯 Отправь юзернейм или id игрока, которому выдать артефакт.",
        parse_mode="HTML", reply_markup=_cancel_kb(),
    )
    await call.answer()


@dp.message(StateFilter(AdminPanel.giveart_target_input))
async def admin_input_giveart_target(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return

    from shop import _ARTIFACT_POOL
    await state.update_data(target_uid=found["id"])
    await state.set_state(AdminPanel.giveart_pick)

    kb = InlineKeyboardBuilder()
    for a in _ARTIFACT_POOL:
        kb.button(text=f'{a["name"]} · ×{a["multiplier"]}', callback_data=f'adm_giveart_pick:{a["key"]}')
    kb.button(text="❌ Отмена", callback_data="adm_back")
    kb.adjust(2)

    name = _esc(found.get("first_name") or found.get("username") or str(found["id"]))
    await message.reply(f"👤 Игрок: <b>{name}</b>\nВыбери артефакт:", parse_mode="HTML", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("adm_giveart_pick:"), StateFilter(AdminPanel.giveart_pick))
async def cb_admin_giveart_pick(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    key   = call.data.split(":", 1)[1]
    fdata = await state.get_data()
    target_uid = fdata.get("target_uid")
    await state.clear()

    found = await aio_get_user(target_uid) if target_uid else None
    if not found:
        await call.message.edit_text("❌ Запрос устарел, повтори через /admin.", reply_markup=_back_kb())
        await call.answer()
        return

    from shop import _ARTIFACT_POOL
    art = next((a for a in _ARTIFACT_POOL if a["key"] == key), None)
    if not art:
        await call.answer("❌ Артефакт не найден.", show_alert=True)
        return

    text = await _do_giveart(target_uid, found, art)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=_back_kb())
    await call.answer()


# ── Проверка шахты ────────────────────────────────────────────────────────

@dp.message(StateFilter(AdminPanel.checkmine_target_input))
async def admin_input_checkmine(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return
    await state.clear()
    text = _do_checkmine_text(found["id"], found)
    await message.reply(text, parse_mode="HTML", reply_markup=_back_kb())


# ── Удаление игрока (переиспользует уже готовое подтверждение delbd_yes/no) ─

@dp.message(StateFilter(AdminPanel.deletebd_target_input))
async def admin_input_deletebd(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    target_raw = (message.text or "").strip().lstrip("@")
    found = await aio_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(f"❌ Пользователь <code>{_esc(target_raw)}</code> не найден в базе.", parse_mode="HTML")
        return

    uid = found["id"]
    if uid in ADMIN_IDS:
        await message.reply("❌ Нельзя удалить данные администратора этой командой.", parse_mode="HTML")
        return

    await state.clear()
    name = _esc(found.get("first_name") or found.get("username") or str(uid))
    _pending_delete_bd[message.from_user.id] = uid

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить всё", callback_data=f"delbd_yes:{uid}")
    kb.button(text="❌ Отмена", callback_data="delbd_no")
    kb.adjust(1)

    await message.reply(
        f'⚠️ <b>ВНИМАНИЕ — ПОЛНОЕ УДАЛЕНИЕ ДАННЫХ</b>\n\n'
        f'<blockquote>Игрок: <b>{name}</b> (<code>{uid}</code>)\n\n'
        f'Будут стёрты <b>все</b> данные: баланс, шахта, кирки, питомцы, '
        f'оружие/бои, статус, инвентарь, достижения и весь прогресс.\n'
        f'Игрок начнёт игру полностью заново, как новый пользователь.\n\n'
        f'<b>Это действие необратимо!</b></blockquote>',
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


# ── Чеки ─────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_chk_create")
async def cb_chk_create(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.check_create_input)
    await call.message.edit_text(
        "➕ <b>Создать чек</b>\n\nОтправь: <code>сумма кол-во</code>\nНапример: <code>10000 10</code>",
        parse_mode="HTML", reply_markup=_cancel_kb(),
    )
    await call.answer()


@dp.callback_query(F.data == "adm_chk_delete")
async def cb_chk_delete(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.check_delete_input)
    await call.message.edit_text("🗑 <b>Удалить чек</b>\n\nОтправь код чека.", parse_mode="HTML", reply_markup=_cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "adm_chk_list")
async def cb_chk_list(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    items = await list_checks()
    if not items:
        await call.message.edit_text("📭 Чеков нет.", parse_mode="HTML", reply_markup=_back_kb())
        await call.answer()
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{c["code"]}</code> — {coin} {format_amount(c["amount"])} · [{c["uses_left"]}/{c["uses_total"]}]'
        for c in items
    ]
    await call.message.edit_text(
        f'<b>📋 Чеки ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML", reply_markup=_back_kb(),
    )
    await call.answer()


@dp.message(StateFilter(AdminPanel.check_create_input))
async def admin_input_check_create(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").strip().split()
    if len(parts) != 2:
        await message.reply("❌ Формат: <code>сумма кол-во</code>\nПример: <code>10000 10</code>", parse_mode="HTML")
        return
    try:
        amount = int(parts[0])
        uses   = int(parts[1])
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    await state.clear()
    bot_me = await bot.get_me()
    code   = await create_check(amount, uses)
    link   = f"https://t.me/{bot_me.username}?start=check_{code}"
    coin   = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    await message.reply(
        f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Чек создан!</b>\n\n'
        f'<blockquote>'
        f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
        f'<tg-emoji emoji-id="5330320040883411678">🎁</tg-emoji> <b>Активаций:</b> {uses}\n'
        f'<tg-emoji emoji-id="5444856076954520455">🔗</tg-emoji> <b>Код:</b> <code>{code}</code>'
        f'</blockquote>\n\n'
        f'<b><tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji>Ссылка:</b> {link}',
        parse_mode="HTML", disable_web_page_preview=True, reply_markup=_back_kb(),
    )


@dp.message(StateFilter(AdminPanel.check_delete_input))
async def admin_input_check_delete(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    code = (message.text or "").strip()
    if not code:
        await message.reply("❌ Отправь код чека.", parse_mode="HTML")
        return
    await state.clear()
    ok = await delete_check(code)
    await message.reply("✅ Чек удалён." if ok else "❌ Чек не найден.", parse_mode="HTML", reply_markup=_back_kb())


# ── Промокоды ────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_pr_create")
async def cb_pr_create(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.promo_create_input)
    await call.message.edit_text(
        "➕ <b>Создать промокод</b>\n\nОтправь: <code>название сумма кол-во</code>\n"
        "Например: <code>stars 1000 10</code>",
        parse_mode="HTML", reply_markup=_cancel_kb(),
    )
    await call.answer()


@dp.callback_query(F.data == "adm_pr_delete")
async def cb_pr_delete(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminPanel.promo_delete_input)
    await call.message.edit_text("🗑 <b>Удалить промокод</b>\n\nОтправь название промокода.", parse_mode="HTML", reply_markup=_cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "adm_pr_list")
async def cb_pr_list(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    items = await list_promos()
    if not items:
        await call.message.edit_text("📭 Промокодов нет.", parse_mode="HTML", reply_markup=_back_kb())
        await call.answer()
        return
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    lines = [
        f'<code>{p["name"]}</code> — {coin} {format_amount(p["amount"])} · [{p["uses_left"]}/{p["uses_total"]}]'
        for p in items
    ]
    await call.message.edit_text(
        f'<b>📋 Промокоды ({len(items)}):</b>\n\n' + "\n".join(lines),
        parse_mode="HTML", reply_markup=_back_kb(),
    )
    await call.answer()


@dp.message(StateFilter(AdminPanel.promo_create_input))
async def admin_input_promo_create(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").strip().split()
    if len(parts) != 3:
        await message.reply(
            "❌ Формат: <code>название сумма кол-во</code>\nПример: <code>stars 1000 10</code>",
            parse_mode="HTML",
        )
        return
    name, amount_s, uses_s = parts
    try:
        amount = int(amount_s)
        uses   = int(uses_s)
    except ValueError:
        await message.reply("❌ Сумма и кол-во — целые числа.", parse_mode="HTML")
        return
    if amount <= 0 or uses <= 0:
        await message.reply("❌ Сумма и кол-во должны быть > 0.", parse_mode="HTML")
        return

    await state.clear()
    ok, reason = await create_promo(name, amount, uses)
    coin = '<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji>'
    if ok:
        await message.reply(
            f'<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Промокод создан!</b>\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5444856076954520455">🎁</tg-emoji> <b>Код:</b> <code>{_esc(name)}</code>\n'
            f'{coin} <b>Сумма:</b> {format_amount(amount)}\n'
            f'<tg-emoji emoji-id="5330320040883411678">🎟</tg-emoji> <b>Активаций:</b> {uses}'
            f'</blockquote>',
            parse_mode="HTML", reply_markup=_back_kb(),
        )
    else:
        await message.reply(f'❌ Промокод <code>{_esc(name)}</code> уже существует.', parse_mode="HTML", reply_markup=_back_kb())


@dp.message(StateFilter(AdminPanel.promo_delete_input))
async def admin_input_promo_delete(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    pname = (message.text or "").strip()
    if not pname:
        await message.reply("❌ Отправь название промокода.", parse_mode="HTML")
        return
    await state.clear()
    ok = await delete_promo(pname)
    await message.reply("✅ Промокод удалён." if ok else "❌ Промокод не найден.", parse_mode="HTML", reply_markup=_back_kb())


# ── Очистка статистики ────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_clearstats_yes")
async def cb_clearstats_yes(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    removed = await aio_clear_unregistered()
    await call.message.edit_text(
        f'🧹 <b>Очистка завершена.</b>\n\n'
        f'<blockquote>Удалено незавершённых регистраций: <b>{removed}</b></blockquote>',
        parse_mode="HTML", reply_markup=_back_kb(),
    )
    await call.answer()


# ── Очистка ускорителей/зелий/усилителей у всех игроков ─────────────────

@dp.callback_query(F.data == "adm_clearboosters_yes")
async def cb_clearboosters_yes(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    affected = await aio_clear_all_boosters()
    await call.message.edit_text(
        f'⚡ <b>Ускорители очищены.</b>\n\n'
        f'<blockquote>Затронуто игроков: <b>{affected}</b></blockquote>',
        parse_mode="HTML", reply_markup=_back_kb(),
    )
    await call.answer()


# Ловит клики по кнопкам панели, когда FSM-состояние уже не совпадает
# (например, админ отменил шаг или заново открыл /admin, а на экране
# осталась старая клавиатура) — просто просим открыть панель заново,
# а не оставляем кнопку "молчащей". Тот же приём, что и cb_case_admin_stale
# в main.py. ВАЖНО: должен идти ПОСЛЕДНИМ в списке приоритизации среди
# "adm_*"-хендлеров, чтобы не перехватывать уже обработанные выше клики.
@dp.callback_query(F.data.startswith("adm_"))
async def cb_admin_stale(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    await call.answer("⌛️ Кнопка устарела, открой панель заново: /admin", show_alert=True)


# ── Списки хендлеров для приоритизации (см. main.py) ────────────────────
# main.py импортирует эти списки и передаёт их в _prioritize_message_handlers /
# _prioritize_callback_handlers, чтобы наши хендлеры проверялись раньше
# глобального перехватчика голого текста и общего callback-роутера из
# mainhelp.py (см. подробное объяснение в шапке этого блока).

ADMIN_PANEL_MESSAGE_HANDLERS = [
    admin_input_balance,
    admin_input_diamond_all,
    admin_input_status_target,
    admin_input_updamage,
    admin_input_artifact_all,
    admin_input_giveart_target,
    admin_input_checkmine,
    admin_input_deletebd,
    admin_input_check_create,
    admin_input_check_delete,
    admin_input_promo_create,
    admin_input_promo_delete,
]

ADMIN_PANEL_CALLBACK_HANDLERS = [
    cb_admin_close,
    cb_admin_back,
    cb_admin_menu,
    cb_art_all_self,
    cb_art_all_ask,
    cb_art_one_ask,
    cb_admin_status_pick,
    cb_admin_giveart_pick,
    cb_chk_create,
    cb_chk_delete,
    cb_chk_list,
    cb_pr_create,
    cb_pr_delete,
    cb_pr_list,
    cb_clearstats_yes,
    # Эти два были определены раньше в этом файле (см. /deletebd выше) —
    # без приоритизации их тоже перехватывал бы общий callback-роутер
    # mainhelp.py, потому что их callback_data не начинается на
    # "city_"/"crystop_". Добавляем их сюда же, чтобы /deletebd и кнопка
    # "🗑 Удалить игрока" в панели гарантированно работали.
    cb_deletebd_confirm,
    cb_deletebd_cancel,
    # Общий "устарело" fallback для adm_* — обязательно последним в списке.
    cb_admin_stale,
]
