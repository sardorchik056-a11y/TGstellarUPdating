# ══════════════════════════════════════════════════════════════════════
#  rass.py — Рассылка (только для ADMIN_IDS)
#
#  Возможности:
#  • HTML-текст с premium emoji (<tg-emoji emoji-id="...">)
#  • Прикреплённое фото или видео
#  • Кнопки с URL (формат «Текст | https://...», каждая на новой строке)
#  • Пошаговый ввод: текст → кнопки → подтверждение → рассылка
#  • Прогресс и итог (доставлено / заблокировали / ошибки)
# ══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto,
    InputMediaVideo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Состояния FSM (uid -> dict) ──────────────────────────────────────
_rass_state: dict[int, dict] = {}

# ── Шаги ─────────────────────────────────────────────────────────────
STEP_TEXT    = "text"
STEP_BUTTONS = "buttons"
STEP_CONFIRM = "confirm"
STEP_SENDING = "sending"


# ─────────────────────────────────────────────────────────────────────
#  Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────

def _parse_buttons(raw: str) -> Optional[list[list[InlineKeyboardButton]]]:
    """
    Парсит кнопки из строки:
        Название | https://link
        Другая   | https://link2
    Возвращает список рядов или None при ошибке формата.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            return None
        parts = line.split("|", 1)
        label = parts[0].strip()
        url   = parts[1].strip()
        if not label:
            return None
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")):
            return None
        rows.append([InlineKeyboardButton(text=label, url=url)])
    return rows or None


def _build_keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*row)
    return builder.as_markup()


def _confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Разослать",
            callback_data="rass_confirm_yes",
            icon_custom_emoji_id="5201691993775818138",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="rass_confirm_no",
        ),
    )
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
#  Публичный API — регистрируется в main.py
# ─────────────────────────────────────────────────────────────────────

def is_in_rass(uid: int) -> bool:
    """Проверяет, находится ли пользователь в процессе рассылки."""
    return uid in _rass_state


async def rass_start(message: Message, admin_ids: set[int]) -> None:
    """Обрабатывает команду /rass."""
    uid = message.from_user.id
    if uid not in admin_ids:
        return

    _rass_state[uid] = {"step": STEP_TEXT}

    await message.answer(
        '📢 <b>Рассылка — шаг 1 из 3</b>\n\n'
        '<blockquote>'
        '<b>Отправь текст сообщения.</b>\n'
        'HTML-разметка поддерживается:\n'
        '• <code>&lt;b&gt;жирный&lt;/b&gt;</code>\n'
        '• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n'
        '• <code>&lt;blockquote&gt;цитата&lt;/blockquote&gt;</code>\n'
        '• <code>&lt;tg-emoji emoji-id="..."&gt;🌟&lt;/tg-emoji&gt;</code>\n'
        '• <code>&lt;a href="..."&gt;ссылка&lt;/a&gt;</code>\n\n'
        '<b>Хочешь прикрепить фото/видео?</b>\n'
        'Пришли медиа с текстом в подписи (caption).'
        '</blockquote>\n\n'
        '<i>Отправь /rass_cancel чтобы отменить.</i>',
        parse_mode="HTML",
    )


async def rass_cancel(message: Message, admin_ids: set[int]) -> None:
    """Обрабатывает /rass_cancel."""
    uid = message.from_user.id
    if uid not in admin_ids:
        return
    if uid in _rass_state:
        del _rass_state[uid]
    await message.answer(
        '❌ <b>Рассылка отменена.</b>',
        parse_mode="HTML",
    )


async def rass_fsm_message(message: Message, admin_ids: set[int]) -> bool:
    """
    FSM-обработчик входящих сообщений.
    Возвращает True если сообщение «съедено» (не нужно передавать дальше).
    """
    uid = message.from_user.id
    if uid not in admin_ids or uid not in _rass_state:
        return False

    state = _rass_state[uid]
    step  = state.get("step")

    # ── Шаг 1: получаем текст / медиа ────────────────────────────────
    if step == STEP_TEXT:
        if message.photo:
            state["media_type"] = "photo"
            state["media_id"]   = message.photo[-1].file_id
            state["text"]       = message.caption or ""
        elif message.video:
            state["media_type"] = "video"
            state["media_id"]   = message.video.file_id
            state["text"]       = message.caption or ""
        elif message.text and not message.text.startswith("/"):
            state["media_type"] = None
            state["media_id"]   = None
            state["text"]       = message.text
        else:
            return False  # команды пропускаем

        state["step"] = STEP_BUTTONS
        await message.answer(
            '📢 <b>Рассылка — шаг 2 из 3</b>\n\n'
            '<blockquote>'
            'Добавь <b>кнопки с ссылками</b> или напиши <b>нет</b>.\n\n'
            'Формат (каждая кнопка — новая строка):\n'
            '<code>Перейти на сайт | https://example.com\n'
            'Наш канал | https://t.me/channel</code>'
            '</blockquote>',
            parse_mode="HTML",
        )
        return True

    # ── Шаг 2: получаем кнопки ───────────────────────────────────────
    if step == STEP_BUTTONS:
        if not message.text:
            await message.answer(
                '⚠️ Отправь кнопки в нужном формате или напиши <b>нет</b>.',
                parse_mode="HTML",
            )
            return True

        txt = message.text.strip().lower()
        if txt in ("нет", "no", "-", "0"):
            state["buttons"] = None
        else:
            rows = _parse_buttons(message.text)
            if rows is None:
                await message.answer(
                    '❌ <b>Неверный формат кнопок.</b>\n\n'
                    'Используй:\n<code>Текст кнопки | https://ссылка</code>\n\n'
                    'Каждая кнопка на новой строке. Или напиши <b>нет</b>.',
                    parse_mode="HTML",
                )
                return True
            state["buttons"] = rows

        state["step"] = STEP_CONFIRM

        # ── Показываем превью ─────────────────────────────────────────
        kbd = _build_keyboard(state["buttons"]) if state["buttons"] else None

        await message.answer(
            '📢 <b>Рассылка — шаг 3 из 3</b>\n\n'
            '<b>Превью сообщения:</b>',
            parse_mode="HTML",
        )

        # Отправляем превью
        try:
            await _send_one(message.bot, uid, state, preview=True)
        except Exception as e:
            await message.answer(
                f'⚠️ Не удалось показать превью: <code>{e}</code>\n'
                f'Проверь HTML-разметку.',
                parse_mode="HTML",
            )
            state["step"] = STEP_TEXT
            state.clear()
            state["step"] = STEP_TEXT
            del _rass_state[uid]
            return True

        from database import aio_get_all_users
        total = len([u for u in await aio_get_all_users() if u.get("onboarded", True)])

        await message.answer(
            f'<blockquote>'
            f'👥 <b>Получателей: {total}</b>\n'
            f'🔘 Кнопок: {"есть (" + str(len(state["buttons"])) + " шт.)" if state["buttons"] else "нет"}'
            f'</blockquote>\n\n'
            f'Начать рассылку?',
            parse_mode="HTML",
            reply_markup=_confirm_keyboard(),
        )
        return True

    return False


async def rass_fsm_callback(call: CallbackQuery, admin_ids: set[int], bot: Bot) -> bool:
    """
    Обрабатывает callback-кнопки подтверждения рассылки.
    Возвращает True если callback «съеден».
    """
    uid = call.from_user.id
    if uid not in admin_ids:
        return False
    if call.data not in ("rass_confirm_yes", "rass_confirm_no"):
        return False

    if uid not in _rass_state:
        await call.answer("Сессия истекла. Запусти /rass заново.", show_alert=True)
        return True

    state = _rass_state[uid]

    if call.data == "rass_confirm_no":
        del _rass_state[uid]
        await call.message.edit_text(
            '❌ <b>Рассылка отменена.</b>',
            parse_mode="HTML",
        )
        await call.answer()
        return True

    # ── Начинаем рассылку ─────────────────────────────────────────────
    state["step"] = STEP_SENDING
    await call.answer("Рассылка запущена!")
    await call.message.edit_text(
        '📢 <b>Рассылка запущена...</b>\n\n'
        'Пожалуйста, подожди.',
        parse_mode="HTML",
    )

    from database import aio_get_all_users
    all_users = await aio_get_all_users()
    recipients = [u for u in all_users if u.get("onboarded", True)]

    ok_count   = 0
    fail_count = 0
    block_count = 0

    progress_msg = call.message
    total = len(recipients)

    for i, u in enumerate(recipients):
        try:
            await _send_one(bot, u["id"], state)
            ok_count += 1
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                block_count += 1
            else:
                fail_count += 1

        # Обновляем прогресс каждые 50 сообщений
        if (i + 1) % 50 == 0 or (i + 1) == total:
            try:
                await progress_msg.edit_text(
                    f'📢 <b>Рассылка...</b>\n\n'
                    f'<blockquote>'
                    f'📨 Отправлено: <b>{i + 1}/{total}</b>\n'
                    f'✅ Доставлено: <b>{ok_count}</b>\n'
                    f'🚫 Заблокировали: <b>{block_count}</b>\n'
                    f'❌ Ошибки: <b>{fail_count}</b>'
                    f'</blockquote>',
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)  # ~20 сообщений/сек — не триггерим flood

    del _rass_state[uid]

    await progress_msg.edit_text(
        '<tg-emoji emoji-id="5201691993775818138">✅</tg-emoji> <b>Рассылка завершена!</b>\n\n'
        f'<blockquote>'
        f'👥 Всего пользователей: <b>{total}</b>\n'
        f'✅ Доставлено: <b>{ok_count}</b>\n'
        f'🚫 Заблокировали бота: <b>{block_count}</b>\n'
        f'❌ Прочие ошибки: <b>{fail_count}</b>'
        f'</blockquote>',
        parse_mode="HTML",
    )
    return True


# ─────────────────────────────────────────────────────────────────────
#  Внутренняя отправка одного сообщения
# ─────────────────────────────────────────────────────────────────────

async def _send_one(bot: Bot, chat_id: int, state: dict, preview: bool = False) -> None:
    """Отправляет одно сообщение согласно state."""
    text       = state.get("text", "")
    media_type = state.get("media_type")
    media_id   = state.get("media_id")
    buttons    = state.get("buttons")

    kbd = _build_keyboard(buttons) if buttons else None

    if media_type == "photo":
        await bot.send_photo(
            chat_id,
            photo=media_id,
            caption=text or None,
            parse_mode="HTML",
            reply_markup=kbd,
        )
    elif media_type == "video":
        await bot.send_video(
            chat_id,
            video=media_id,
            caption=text or None,
            parse_mode="HTML",
            reply_markup=kbd,
        )
    else:
        await bot.send_message(
            chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=kbd,
            disable_web_page_preview=True,
        )
