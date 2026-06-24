# ============================================================
#  duel.py  —  Раздел Дуэлей TGStellar
#  Заглушка: UI, тексты, клавиатуры.
#  Боевая логика подключается позже.
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Эмодзи ──────────────────────────────────────────────────
EMOJI_BACK         = "5252272671669706296"
EMOJI_DUEL_MAIN    = "5424972470023104089"   # ⚔️  (hunt, подходит для дуэлей)
EMOJI_SEARCH       = "5440539497383087970"   # 🔎
EMOJI_INVITE       = "5332724926216428039"   # 👥  (друзья/пригласить)
EMOJI_EQUIP        = "5445221832074483553"   # 🎒  (инвентарь/экипировка)
EMOJI_SKILLS       = "5224607267797606837"   # 🔮  (навыки)
EMOJI_STATS_DUEL   = "5231200819986047254"   # 📊  (характеристики)


# ── Текст главного экрана ────────────────────────────────────

def duel_main_text() -> str:
    return (
        '<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>ДУЭЛИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        'Испытай себя в бою один на один.\n'
        'Собери снаряжение, прокачай навыки\n'
        'и докажи, кто сильнейший в TGStellar.'
        '</blockquote>'
    )


# ── Клавиатура главного экрана ───────────────────────────────

def duel_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=" Поиск противника",
            callback_data="duel_search",
            icon_custom_emoji_id=EMOJI_SEARCH,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=" Пригласить на поединок",
            callback_data="duel_invite",
            icon_custom_emoji_id=EMOJI_INVITE,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=" Экипировка",
            callback_data="duel_equip",
            icon_custom_emoji_id=EMOJI_EQUIP,
        ),
        InlineKeyboardButton(
            text=" Навыки",
            callback_data="duel_skills",
            icon_custom_emoji_id=EMOJI_SKILLS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=" Характеристики",
            callback_data="duel_charstats",
            icon_custom_emoji_id=EMOJI_STATS_DUEL,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_menu",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()


# ── Заглушки подразделов ─────────────────────────────────────

def duel_soon_text(section: str) -> str:
    labels = {
        "search":    "Поиск противника",
        "invite":    "Пригласить на поединок",
        "equip":     "Экипировка",
        "skills":    "Навыки",
        "charstats": "Характеристики",
    }
    name = labels.get(section, section)
    return (
        f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>{name}</b>\n\n'
        '<blockquote>🚧 Раздел в разработке.\nСкоро будет доступен!</blockquote>'
    )


def duel_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="duel_main",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()
