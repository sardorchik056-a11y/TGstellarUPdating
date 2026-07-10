# ============================================================
#  lang.py  —  Переводы TGStellar (ru / en)
#  Использование: from lang import t
#  t(lang, "key") → строка на нужном языке
# ============================================================

_STRINGS: dict[str, dict[str, str]] = {

    # ── Выбор языка при старте ──
    "lang_btn_ru": {
        "ru": "🇷🇺 Русский",
        "en": "🇷🇺 Русский",
    },
    "lang_btn_en": {
        "ru": "🇬🇧 English",
        "en": "🇬🇧 English",
    },
    "lang_set_ru": {
        "ru": "🇷🇺 Язык установлен: Русский",
        "en": "🇷🇺 Language set: Russian",
    },
    "lang_set_en": {
        "ru": "🇬🇧 Language set: English",
        "en": "🇬🇧 Language set: English",
    },

    # ── Приветствие ──
    "welcome": {
        "ru": (
            '<blockquote><b><tg-emoji emoji-id="5197288647275071607">🎟</tg-emoji>TGStellar</b> — '
            '<b>современная игровая зона, где ты можешь отвлечься от повседневных забот и полностью погрузиться в атмосферу спокойствия и развлечений.</b></blockquote>\n\n'
            '<blockquote><b><tg-emoji emoji-id="5222079954421818267">🎟</tg-emoji>Это пространство, где время проходит незаметно, а каждая деталь делает игру комфортной и увлекательной</b></blockquote>\n\n'
            '<tg-emoji emoji-id="5357069174512303778">🎟</tg-emoji><b><a href="https://t.me/l0xgenl">Тех. поддержка</a> | <a href="https://t.me/tgstellarnews">Новости</a> | <a href="https://t.me/tgstellarchat">Наш чат</a></b>'
        ),
        "en": (
            '<blockquote><b><tg-emoji emoji-id="5197288647275071607">🎟</tg-emoji>TGStellar</b> — '
            '<b>a modern gaming zone where you can escape from everyday worries and dive into an atmosphere of calm and entertainment.</b></blockquote>\n\n'
            '<blockquote><b><tg-emoji emoji-id="5222079954421818267">🎟</tg-emoji>A space where time flies by and every detail makes the game comfortable and exciting</b></blockquote>\n\n'
            '<tg-emoji emoji-id="5357069174512303778">🎟</tg-emoji><b><a href="https://t.me/l0xgenl">Support</a> | <a href="https://t.me/tgstellarnews">News</a> | <a href="https://t.me/tgstellarchat">Chat</a></b>'
        ),
    },

    # ── Главное меню — кнопки ──
    "btn_profile":  {"ru": "Профиль",    "en": "Profile"},
    "btn_stats":    {"ru": "Статистика", "en": "Statistics"},
    "btn_cases":    {"ru": "Кейсы",      "en": "Cases"},
    "btn_mine":     {"ru": " Шахта ",   "en": " Mine "},
    "btn_hunt":     {"ru": "Охота",      "en": "Hunt"},
    "btn_status":   {"ru": "Статус",     "en": "Status"},
    "btn_pets":     {"ru": "Питомцы",    "en": "Pets"},
    "btn_leaders":  {"ru": "Лидеры",     "en": "Leaders"},
    "btn_settings": {"ru": "Настройки",  "en": "Settings"},
    "btn_back":     {"ru": "Назад",      "en": "Back"},
    "btn_forward":  {"ru": "Вперёд",     "en": "Forward"},
    "btn_inventory":{"ru": "Инвентарь",  "en": "Inventory"},

    # ── Настройки ──
    "settings_title": {
        "ru": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji> <b>НАСТРОЙКИ</b>',
        "en": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji> <b>SETTINGS</b>',
    },
    "settings_subtitle": {
        "ru": "<b>Здесь можно сменить язык бота и быстро перейти в наш чат, канал или поддержку.</b>",
        "en": "<b>Here you can change the bot language and quickly jump to our chat, channel or support.</b>",
    },
    "settings_language": {
        "ru": '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>Текущий язык — Русский 🇷🇺</b>',
        "en": '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>Current language — English 🇬🇧</b>',
    },
    "settings_lang_hint": {
        "ru": "Сменить язык можно в любой момент кнопкой ниже",
        "en": "You can change the language anytime using the button below",
    },
    "settings_links_title": {
        "ru": '<tg-emoji emoji-id="5271604874419647061">📢</tg-emoji> <b>Полезные ссылки</b>',
        "en": '<tg-emoji emoji-id="5271604874419647061">📢</tg-emoji> <b>Useful links</b>',
    },
    "settings_chat_desc": {
        "ru": '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> <b>Чат</b> — общайся с другими игроками',
        "en": '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> <b>Chat</b> — talk with other players',
    },
    "settings_channel_desc": {
        "ru": '<tg-emoji emoji-id="5424818078833715060">📢</tg-emoji> <b>Канал</b> — новости и обновления проекта',
        "en": '<tg-emoji emoji-id="5424818078833715060">📢</tg-emoji> <b>Channel</b> — news and project updates',
    },
    "settings_support_desc": {
        "ru": '<tg-emoji emoji-id="5357069174512303778">🛠</tg-emoji> <b>Поддержка</b> — помощь от администрации',
        "en": '<tg-emoji emoji-id="5357069174512303778">🛠</tg-emoji> <b>Support</b> — help from the admin team',
    },
    "btn_chat":     {"ru": "Чат",      "en": "Chat"},
    "btn_channel":  {"ru": "Канал",    "en": "Channel"},
    "btn_support":  {"ru": "Поддержка","en": "Support"},
    "btn_language": {"ru": "Язык",     "en": "Language"},

    # ── Выбор языка (из настроек) ──
    "lang_choose": {
        "ru": (
            '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>ВЫБОР ЯЗЫКА</b>\n\n'
            '<blockquote><b>Выбери язык интерфейса бота:</b>\n'
            '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>Текущий язык — Русский 🇷🇺</b></blockquote>\n\n'
            '<b>Все тексты, кнопки и уведомления будут отображаться на выбранном языке</b>'
        ),
        "en": (
            '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>LANGUAGE SELECTION</b>\n\n'
            '<blockquote><b>Choose the bot interface language:</b>\n'
            '<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>Current language — English 🇬🇧</b></blockquote>\n\n'
            '<b>All texts, buttons and notifications will be shown in the selected language</b>'
        ),
    },

    # ── Статистика ──
    "stats_title_online": {
        "ru": "Онлайн",
        "en": "Online",
    },
    "stats_title_users": {
        "ru": "Пользователи",
        "en": "Users",
    },
    "stats_5min":  {"ru": "За 5 минут",  "en": "Last 5 minutes"},
    "stats_24h":   {"ru": "За 24 часа",  "en": "Last 24 hours"},
    "stats_week":  {"ru": "За неделю",   "en": "Last week"},
    "stats_month": {"ru": "За месяц",    "en": "Last month"},
    "stats_total": {"ru": "Всего",       "en": "Total"},

    # ── Магазин ──
    "shop_title": {
        "ru": '<blockquote><tg-emoji emoji-id="5406683434124859552">🛒</tg-emoji> <b>МАГАЗИН</b>\n\n<b>Выбери категорию:</b></blockquote>',
        "en": '<blockquote><tg-emoji emoji-id="5406683434124859552">🛒</tg-emoji> <b>SHOP</b>\n\n<b>Choose a category:</b></blockquote>',
    },
    "btn_shop_cases": {"ru": "Кейсы", "en": "Cases"},

    # ── Общие ──
    "in_development": {
        "ru": "📝 Раздел в разработке...",
        "en": "📝 Section in development...",
    },
    "unknown_cmd": {
        "ru": "❓ Неизвестная команда",
        "en": "❓ Unknown command",
    },
}


def t(lang: str, key: str) -> str:
    """Получить строку по языку. Если нет — fallback на ru."""
    lang = lang if lang in ("ru", "en") else "ru"
    entry = _STRINGS.get(key)
    if entry is None:
        return key  # fallback — сам ключ
    return entry.get(lang) or entry.get("ru") or key


def get_lang(data: dict) -> str:
    """Получить язык из данных пользователя."""
    return data.get("lang", "ru")


# ── Профиль ──
_STRINGS.update({
    "profile_rank":    {"ru": "Ранг",           "en": "Rank"},
    "profile_status":  {"ru": "Статус",         "en": "Status"},
    "profile_days":    {"ru": "Дней в проекте", "en": "Days in project"},
    "profile_level":   {"ru": "Уровень",        "en": "Level"},
    "profile_xp":      {"ru": "Опыт",           "en": "XP"},
    "profile_balance": {"ru": "Баланс",         "en": "Balance"},
    "profile_anon":    {"ru": "Аноним",         "en": "Anonymous"},

    "rank_novice":  {"ru": "Новичок", "en": "Novice"},
    "rank_skilled": {"ru": "Опытный", "en": "Skilled"},
    "rank_pro":     {"ru": "Профи",   "en": "Pro"},
    "rank_master":  {"ru": "Мастер",  "en": "Master"},
    "rank_expert":  {"ru": "Эксперт", "en": "Expert"},
    "rank_elite":   {"ru": "Элита",   "en": "Elite"},
    "rank_legend":  {"ru": "Легенда", "en": "Legend"},

    "boost_pickaxe":   {"ru": "Кирка",      "en": "Pickaxe"},
    "boost_xp":        {"ru": "XP",         "en": "XP"},
    "boost_enhancer":  {"ru": "Усилитель",  "en": "Enhancer"},
    "boost_active":    {"ru": "Активные бусты", "en": "Active boosts"},
    "boost_on":        {"ru": "на",         "en": "for"},
})

# ── Шахта ──
_STRINGS.update({
    # Главный экран шахты
    "mine_title":        {"ru": "Шахта",             "en": "Mine"},
    "mine_selected":     {"ru": "Выбрано",           "en": "Selected"},
    "mine_duration":     {"ru": "Длительность",      "en": "Duration"},
    "mine_inventory_lbl":{"ru": "Инвентарь",         "en": "Inventory"},
    "mine_press_start":  {
        "ru": 'Нажми <tg-emoji emoji-id="5906727823355156804">🎟</tg-emoji> <b>Запустить</b> чтобы начать добычу!',
        "en": 'Press <tg-emoji emoji-id="5906727823355156804">🎟</tg-emoji> <b>Start</b> to begin mining!',
    },
    "mine_campaigns":    {"ru": "Кампаний",          "en": "Campaigns"},
    "mine_progress":     {"ru": "Прогресс",          "en": "Progress"},
    "mine_finished":     {
        "ru": '<tg-emoji emoji-id="5206607081334906820">🎟</tg-emoji> <b>Добыча завершена!</b>',
        "en": '<tg-emoji emoji-id="5206607081334906820">🎟</tg-emoji> <b>Mining complete!</b>',
    },
    "mine_running":      {
        "ru": '<tg-emoji emoji-id="5341498088408234504">🎟</tg-emoji> <b>Идёт добыча...</b>',
        "en": '<tg-emoji emoji-id="5341498088408234504">🎟</tg-emoji> <b>Mining in progress...</b>',
    },

    # Кнопки шахты
    "mine_btn_start":    {"ru": "Запустить",         "en": "Start"},
    "mine_btn_collect":  {"ru": "Забрать добычу",    "en": "Collect loot"},
    "mine_btn_refresh":  {"ru": "Обновить",          "en": "Refresh"},
    "mine_btn_partial":  {"ru": "Забрать",           "en": "Collect"},
    "mine_btn_sell":     {"ru": "Продать",           "en": "Sell"},
    "mine_btn_inv":      {"ru": "Инвентарь",         "en": "Inventory"},
    "mine_btn_workshop": {"ru": "Мастерская",        "en": "Workshop"},
    "mine_btn_duration": {"ru": "Длительность",      "en": "Duration"},

    # Инвентарь руд
    "mine_inv_empty":    {"ru": "Инвентарь пуст",   "en": "Inventory empty"},
    "mine_inv_more":     {"ru": "...и ещё",         "en": "...and more"},
    "mine_inv_total":    {"ru": "Итого",             "en": "Total"},

    # Продажа
    "mine_sell_title":   {"ru": "Продажа",          "en": "Sell"},
    "mine_sell_empty":   {"ru": "Инвентарь пуст — нечего продавать!", "en": "Inventory is empty — nothing to sell!"},
    "mine_sell_prompt":  {"ru": "Запусти шахту и накопи руды.", "en": "Start mining to collect ores."},
    "mine_sell_prices":  {"ru": "Цены скупщика:",   "en": "Buyer prices:"},
    "mine_sell_balance": {"ru": "Баланс",           "en": "Balance"},
    "mine_sell_total":   {"ru": "Итого к продаже",  "en": "Total to sell"},
    "mine_sell_all_btn": {"ru": "Продать всё",      "en": "Sell all"},
    "mine_sell_nothing": {"ru": "Нечего продавать!","en": "Nothing to sell!"},
    "mine_sell_success": {"ru": "Успешно!",         "en": "Success!"},
    "mine_sell_earned":  {"ru": "Итого получено",   "en": "Total earned"},
    "mine_balance_lbl":  {"ru": "Баланс",           "en": "Balance"},

    # Мастерская
    "mine_workshop_title":   {"ru": "Мастерская",       "en": "Workshop"},
    "mine_workshop_balance": {"ru": "Баланс",           "en": "Balance"},
    "mine_workshop_selected":{"ru": "Выбрано",          "en": "Selected"},
    "mine_workshop_page":    {"ru": "Страница",         "en": "Page"},
    "mine_workshop_choose":  {"ru": "Выберите товар ниже:", "en": "Choose an item below:"},

    # Карточка кирки
    "mine_pick_name":        {"ru": "Название",         "en": "Name"},
    "mine_pick_tier":        {"ru": "Тир",              "en": "Tier"},
    "mine_pick_per5":        {"ru": "Каждые 5 мин",     "en": "Every 5 min"},
    "mine_pick_prices":      {"ru": "Цены",             "en": "Prices"},
    "mine_pick_for_coins":   {"ru": "За монеты",        "en": "For coins"},
    "mine_pick_for_stars":   {"ru": "За звёзды",        "en": "For stars"},
    "mine_pick_unavail":     {"ru": "недоступно",       "en": "unavailable"},
    "mine_pick_free":        {"ru": "Бесплатно",        "en": "Free"},
    "mine_pick_stars_unit":  {"ru": "звёзд",            "en": "stars"},
    "mine_pick_status":      {"ru": "Статус",           "en": "Status"},
    "mine_pick_selected":    {"ru": "✅Выбрано",         "en": "✅ Selected"},
    "mine_pick_not_active":  {"ru": "🔘(не активна)",   "en": "🔘 (not active)"},
    "mine_pick_for_stars_st":{"ru": "⭐за звёзды",      "en": "⭐ for stars"},
    "mine_pick_not_bought":  {"ru": "❌Не куплена",     "en": "❌ Not purchased"},

    # Кнопки карточки кирки
    "mine_pick_btn_active":  {"ru": "Уже активна",      "en": "Already active"},
    "mine_pick_btn_select":  {"ru": "Выбрать",          "en": "Select"},
    "mine_pick_btn_no_coins":{"ru": "Монеты недоступны","en": "Coins unavailable"},

    # Длительность — список
    "mine_dur_title":        {"ru": "Длительность сессии",  "en": "Session Duration"},
    "mine_dur_active":       {"ru": "Активна",          "en": "Active"},
    "mine_dur_unlocked":     {"ru": "Открыто",          "en": "Unlocked"},
    "mine_dur_choose":       {"ru": "Выберите для подробностей:", "en": "Select for details:"},

    # Длительность — карточка
    "mine_dur_card_title":   {"ru": "Длительность —",   "en": "Duration —"},
    "mine_dur_session":      {"ru": "Время сессии",     "en": "Session time"},
    "mine_dur_price":        {"ru": "Цена",             "en": "Price"},
    "mine_dur_status":       {"ru": "Статус",           "en": "Status"},
    "mine_dur_free":         {"ru": "Бесплатно",        "en": "Free"},
    "mine_dur_status_active":{"ru": "✅ Активна",       "en": "✅ Active"},
    "mine_dur_status_owned": {"ru": "🔘(не активна)",  "en": "🔘 (not active)"},
    "mine_dur_status_none":  {"ru": "❌Не куплена",    "en": "❌ Not purchased"},
    "mine_dur_btn_active":   {"ru": "Уже активна",     "en": "Already active"},
    "mine_dur_btn_select":   {"ru": "Выбрать",         "en": "Select"},

    # Результат добычи
    "mine_collect_title":    {"ru": "Результат добычи", "en": "Mining result"},
    "mine_collect_campaigns":{"ru": "Кампаний",        "en": "Campaigns"},
    "mine_collect_nothing":  {"ru": "Ничего не нашли 😔", "en": "Nothing found 😔"},
    "mine_collect_done":     {"ru": "✅ Сессия завершена!", "en": "✅ Session complete!"},
    "mine_collect_running":  {"ru": "⏳ Шахта работает. Осталось:", "en": "⏳ Mine is running. Time left:"},
    "mine_booster_active":   {"ru": "Ускоритель",      "en": "Booster"},
    "mine_booster_active_sfx":{"ru": "активен",        "en": "active"},

    # Сообщения логики (call.answer)
    "mine_already_running":  {"ru": "⛏️ Шахта уже работает!",          "en": "⛏️ Mine is already running!"},
    "mine_start_first":      {"ru": "Сначала запусти шахту!",           "en": "Start the mine first!"},
    "mine_no_campaigns":     {"ru": "⏳ Ещё ни одной кампании не завершено!", "en": "⏳ No campaigns completed yet!"},

    # Покупка / выбор кирки
    "pick_unknown":          {"ru": "❌ Неизвестная кирка.",            "en": "❌ Unknown pickaxe."},
    "pick_stars_only":       {"ru": "❌ Эта кирка покупается только за звёзды Telegram!", "en": "❌ This pickaxe is only available for Telegram Stars!"},
    "pick_already_owned":    {"ru": "У тебя уже есть эта кирка!",      "en": "You already own this pickaxe!"},
    "pick_free_ok":          {"ru": "✅ Получена {name} (бесплатно)!",  "en": "✅ Got {name} (free)!"},
    "pick_no_coins":         {"ru": "❌ Недостаточно монет! Нужно: {cost}", "en": "❌ Not enough coins! Need: {cost}"},
    "pick_bought":           {"ru": "✅ Куплена {name}! Потрачено: {cost}", "en": "✅ Bought {name}! Spent: {cost}"},
    "pick_not_owned":        {"ru": "❌ Сначала купи эту кирку!",       "en": "❌ Buy this pickaxe first!"},
    "pick_no_change_mining": {"ru": "❌ Нельзя менять кирку во время добычи!", "en": "❌ Cannot change pickaxe during mining!"},
    "pick_selected":         {"ru": "✅ Выбрана {name}",               "en": "✅ Selected {name}"},
    "pick_premium_thanks":   {"ru": "⭐ <b>Спасибо за поддержку!</b>", "en": "⭐ <b>Thank you for your support!</b>"},
    "pick_premium_got":      {"ru": "Получена кирка <b>{name}</b> за {stars} звёзд", "en": "Received pickaxe <b>{name}</b> for {stars} stars"},
    "pick_premium_hits":     {"ru": "ударов за кампанию",              "en": "hits per campaign"},

    # Покупка / выбор длительности
    "dur_unknown":           {"ru": "❌ Неизвестная длительность.",     "en": "❌ Unknown duration."},
    "dur_already_owned":     {"ru": "Уже куплено!",                    "en": "Already purchased!"},
    "dur_no_coins":          {"ru": "❌ Недостаточно монет! Нужно: {cost}", "en": "❌ Not enough coins! Need: {cost}"},
    "dur_bought":            {"ru": "✅ Открыто: {label}! Потрачено: {cost}", "en": "✅ Unlocked: {label}! Spent: {cost}"},
    "dur_not_owned":         {"ru": "❌ Сначала купи эту длительность!", "en": "❌ Buy this duration first!"},
    "dur_no_change_mining":  {"ru": "❌ Нельзя менять длительность во время добычи!", "en": "❌ Cannot change duration during mining!"},
    "dur_selected":          {"ru": "✅ Выбрана длительность: {label}", "en": "✅ Duration selected: {label}"},
})

# ── Питомцы ──
_STRINGS.update({
    "pets_title":         {"ru": "ПИТОМЦЫ",              "en": "PETS"},
    "pets_count":         {"ru": "Твои питомцы",         "en": "Your pets"},
    "pets_none":          {"ru": "У тебя пока нет питомцев.", "en": "You don't have any pets yet."},
    "pets_none_hint":     {"ru": "Купи первого — и он начнёт приносить монеты!", "en": "Buy your first one — and it will start bringing coins!"},
    "pets_notify_hint":   {"ru": "Каждая выплата сопровождается сообщением от питомца.", "en": "Every payout comes with a message from your pet."},
    "pets_btn_back":      {"ru": "Назад",                "en": "Back"},
    "pets_btn_buy":       {"ru": "Купить",               "en": "Buy"},

    "pet_owned":          {"ru": "Питомец у тебя есть!",  "en": "You own this pet!"},
    "pet_not_owned":      {"ru": "Не куплен",             "en": "Not purchased"},
    "pet_ready":          {"ru": "Готов к выплате прямо сейчас!", "en": "Ready to pay out right now!"},
    "pet_next_payout":    {"ru": "Следующая выплата через:", "en": "Next payout in:"},
    "pet_feature":        {"ru": "Особенность:",          "en": "Feature:"},
    "pet_income_label":   {"ru": "Доход каждые 12 часов:", "en": "Income every 12 hours:"},
    "pet_price_label":    {"ru": "Цена:",                 "en": "Price:"},

    "pet_not_found":      {"ru": "❌ Питомец не найден.", "en": "❌ Pet not found."},
    "pet_already_owned":  {"ru": "❌ Этот питомец уже у тебя есть!", "en": "❌ You already own this pet!"},
    "pet_no_coins":       {"ru": "❌ Недостаточно монет! Нужно: {cost}", "en": "❌ Not enough coins! Need: {cost}"},
    "pet_bought_title":   {"ru": "{name} теперь твой питомец!", "en": "{name} is now your pet!"},
    "pet_bought_hint":    {"ru": "Он уже отправился в шахту и скоро принесёт первые монеты.", "en": "It has already headed to the mine and will bring the first coins soon."},
    "pet_bought_timer":   {"ru": "Первая выплата через 12 часов.", "en": "First payout in 12 hours."},
    "pet_income_msg":     {"ru": "Принёс тебе: +{amount}", "en": "Brought you: +{amount}"},
})

# ── Рефералы ──
_STRINGS.update({
    # Главный экран
    "refs_title":           {"ru": "Реферальная программа",     "en": "Referral Program"},
    "refs_rewards_title":   {"ru": "Награды",                   "en": "Rewards"},
    "refs_reward_normal":   {"ru": "Обычный игрок",             "en": "Regular player"},
    "refs_reward_premium":  {"ru": "Игрок с Telegram Premium",  "en": "Player with Telegram Premium"},
    "refs_stats_title":     {"ru": "Твоя статистика",           "en": "Your statistics"},
    "refs_total":           {"ru": "Приглашено всего",          "en": "Total invited"},
    "refs_premium_count":   {"ru": "Из них с Premium",          "en": "With Premium"},
    "refs_earned":          {"ru": "Заработано монет",          "en": "Coins earned"},
    "refs_link_hint":       {"ru": "Нажми, чтобы скопировать, или отправь друзьям кнопкой ниже", "en": "Tap to copy or share with friends using the button below"},
    # Кнопки
    "refs_btn_share":       {"ru": "Поделиться ссылкой",        "en": "Share link"},
    "refs_btn_list":        {"ru": "Мои рефералы",              "en": "My referrals"},
    # Список рефералов
    "refs_list_title":      {"ru": "Мои рефералы",              "en": "My Referrals"},
    "refs_list_invited":    {"ru": "Всего приглашено",          "en": "Total invited"},
    "refs_list_premium":    {"ru": "С Telegram Premium",        "en": "With Telegram Premium"},
    "refs_list_earned":     {"ru": "Заработано всего",          "en": "Total earned"},
    "refs_list_empty":      {"ru": "Здесь появятся игроки, приглашённые тобой.", "en": "Players you invite will appear here."},
    "refs_list_empty_hint": {"ru": "Поделись своей ссылкой — и список начнёт заполняться!", "en": "Share your link — and the list will start filling up!"},
    "refs_list_more":       {"ru": "...и ещё",                  "en": "...and"},
    "refs_list_more_sfx":   {"ru": "рефералов",                 "en": "more referrals"},
    "refs_list_pending":    {"ru": "ожидает проверки",          "en": "pending"},
    "refs_list_rewarded":   {"ru": "награда начислена",         "en": "reward granted"},
    # Уведомления
    "refs_notif_normal":    {"ru": "Новый реферал!",            "en": "New referral!"},
    "refs_notif_premium":   {"ru": "Premium-реферал!",          "en": "Premium referral!"},
    # Капча
    "captcha_blocked":      {"ru": "Вы заблокированы на {min} мин!", "en": "You are blocked for {min} min!"},
})

# ── Топ рефереров ──
_STRINGS.update({
    "reftop_title":          {"ru": "Топ рефереров",            "en": "Top Referrers"},
    "reftop_btn":             {"ru": "Топ рефереров",            "en": "Top Referrers"},
    "reftop_period_today":    {"ru": "Сегодня",                  "en": "Today"},
    "reftop_period_week":     {"ru": "Неделя",                   "en": "Week"},
    "reftop_period_alltime":  {"ru": "Всё время",                "en": "All Time"},
    "reftop_col_invited":     {"ru": "приглашено",               "en": "invited"},
    "reftop_empty_title":     {"ru": "Пока никто не приглашал друзей",  "en": "No one has invited friends yet"},
    "reftop_empty_hint":      {"ru": "Стань первым — поделись своей ссылкой!", "en": "Be the first — share your link!"},
    "reftop_not_in_top":      {"ru": "Тебя нет в топ-{size}",     "en": "You are not in the top {size}"},
    "reftop_not_in_top_hint": {"ru": "Приглашай друзей — и попадёшь в список!", "en": "Invite friends — and you'll make the list!"},
    "reftop_your_rank":       {"ru": "Твоё место",                "en": "Your rank"},
})

# ── Дуэли (интерфейс) ──
_STRINGS.update({
    # Титулы
    "duel_title_weak":            {"ru": "Слабак",              "en": "Weakling"},
    "duel_title_training":        {"ru": "Тренирующийся",       "en": "Trainee"},
    "duel_title_strong":          {"ru": "Сильный",              "en": "Strong"},
    "duel_title_hero":            {"ru": "Герой",                "en": "Hero"},
    "duel_title_invincible":      {"ru": "Непобедимый",          "en": "Invincible"},
    "duel_title_incomparable":    {"ru": "Бесподобный",          "en": "Peerless"},
    "duel_title_death_bringer":   {"ru": "Приносящий гибель",    "en": "Death Bringer"},
    "duel_title_eternal_champion":{"ru": "Вечный победитель",    "en": "Eternal Champion"},

    # Слоты снаряжения
    "duel_slot_helmet": {"ru": "Шлем",      "en": "Helmet"},
    "duel_slot_armor":  {"ru": "Броня",     "en": "Armor"},
    "duel_slot_gloves": {"ru": "Перчатки",  "en": "Gloves"},
    "duel_slot_pants":  {"ru": "Штаны",     "en": "Pants"},
    "duel_slot_boots":  {"ru": "Сапоги",    "en": "Boots"},

    # Главное меню дуэлей
    "duel_main_title":    {"ru": "ДУЭЛИ", "en": "DUELS"},
    "duel_main_title_line": {
        "ru": "Титул — <b>{title}</b>",
        "en": "Title — <b>{title}</b>",
    },
    "duel_main_wl_line": {
        "ru": "Победы: <b>{wins}</b>  Поражения: <b>{losses}</b>",
        "en": "Wins: <b>{wins}</b>  Losses: <b>{losses}</b>",
    },
    "duel_main_desc": {
        "ru": "Испытай себя в бою один на один.\nСобери снаряжение для защиты, купи навыки для урона\nи докажи, кто сильнейший в TGStellar!",
        "en": "Test yourself in one-on-one combat.\nGather gear for defense, buy skills for damage,\nand prove who's the strongest in TGStellar!",
    },
    "duel_btn_search":    {"ru": " Поиск противника", "en": " Find opponent"},
    "duel_btn_challenge": {"ru": " Бросить вызов",     "en": " Send challenge"},
    "duel_btn_equip":     {"ru": " Снаряжение",        "en": " Gear"},
    "duel_btn_skills":    {"ru": " Навыки",            "en": " Skills"},
    "duel_btn_charstats": {"ru": " Характеристики",    "en": " Stats"},

    # Снаряжение — обзор
    "duel_equip_title":   {"ru": "СНАРЯЖЕНИЕ", "en": "GEAR"},
    "duel_equip_hint":    {"ru": "Снаряжение даёт HP и защиту — урон даётся навыками!", "en": "Gear gives HP and defense — damage comes from skills!"},
    "duel_equip_empty":   {"ru": "пусто", "en": "empty"},
    "duel_equip_not_worn":{"ru": "(не надето)", "en": "(not equipped)"},

    # Характеристики
    "duel_stats_title":     {"ru": "ХАРАКТЕРИСТИКИ", "en": "STATS"},
    "duel_stats_hp":        {"ru": "Здоровье",       "en": "Health"},
    "duel_stats_regen":     {"ru": "Регенерация",    "en": "Regeneration"},
    "duel_stats_phys_def":  {"ru": "Физ. защита",    "en": "Phys. defense"},
    "duel_stats_mag_def":   {"ru": "Маг. защита",    "en": "Magic defense"},
    "duel_stats_stamina":   {"ru": "Стойкость",      "en": "Stamina"},
    "duel_stats_hp_per_turn":{"ru": "HP/ход",         "en": "HP/turn"},
    "duel_stats_hp_regen_note": {
        "ru": "⚠️ <b>HP восстанавливается</b> (+{amount} каждые {interval} сек.)\nСледующий тик через <b>{secs} сек.</b>\n<i>Нельзя начать бой пока HP &lt; 100</i>",
        "en": "⚠️ <b>HP is regenerating</b> (+{amount} every {interval} sec.)\nNext tick in <b>{secs} sec.</b>\n<i>You can't start a fight while HP &lt; 100</i>",
    },
    "duel_stats_gear_worn":  {"ru": "надето {count}/5 предм.", "en": "{count}/5 items equipped"},
    "duel_stats_gear_none":  {"ru": "снаряжение не надето",    "en": "no gear equipped"},
    "duel_stats_gear_line":  {"ru": "🎽 <i>Снаряжение: {gear}</i>", "en": "🎽 <i>Gear: {gear}</i>"},
    "duel_stats_skills_line":{"ru": "⚔️ <i>Навыков куплено: {count} шт.</i>", "en": "⚔️ <i>Skills bought: {count}</i>"},
    "duel_stats_footer":     {"ru": "💡 Урон в дуэли зависит от купленных навыков,\nа не от снаряжения!", "en": "💡 Duel damage depends on the skills you've bought,\nnot on your gear!"},

    # Навыки — обзор
    "duel_skills_title":   {"ru": "БОЕВЫЕ НАВЫКИ", "en": "COMBAT SKILLS"},
    "duel_skills_equipped_label": {"ru": "Экипировано:", "en": "Equipped:"},
    "duel_skills_empty_slot":     {"ru": "пусто",        "en": "empty"},
    "duel_skills_hint": {
        "ru": "Экипируй до {max} навыков — только они доступны в бою!",
        "en": "Equip up to {max} skills — only those are usable in battle!",
    },
    "duel_btn_skills_shop": {"ru": "📖 Изучение навыков", "en": "📖 Learn skills"},

    # Карточка навыка — кнопки
    "duel_skill_btn_unequip": {"ru": "Снять из боя", "en": "Unequip from battle"},
    "duel_skill_btn_equip":   {"ru": "Экипировать в бой", "en": "Equip for battle"},
    "duel_skill_btn_slots_full": {
        "ru": "⚠️ Все {max} слотов заняты",
        "en": "⚠️ All {max} slots are full",
    },
    "duel_skill_btn_learn":   {"ru": "📖 Изучить — {price} монет", "en": "📖 Learn — {price} coins"},
    "duel_skill_btn_nofunds": {"ru": "💸 Недостаточно монет", "en": "💸 Not enough coins"},

    # Тосты экипировки/снятия навыка
    "duel_skill_msg_not_owned":         {"ru": "❌ Навык не куплен!", "en": "❌ Skill not purchased!"},
    "duel_skill_msg_already_equipped":  {"ru": "❌ Навык уже экипирован!", "en": "❌ Skill already equipped!"},
    "duel_skill_msg_max_equipped":      {"ru": "❌ Максимум {max} навыков в бою!", "en": "❌ Maximum of {max} skills in battle!"},
    "duel_skill_msg_equipped":          {"ru": "✅ Навык экипирован!", "en": "✅ Skill equipped!"},
    "duel_skill_msg_not_equipped":      {"ru": "❌ Навык не экипирован!", "en": "❌ Skill not equipped!"},
    "duel_skill_msg_unequipped":        {"ru": "✅ Навык снят!", "en": "✅ Skill unequipped!"},

    # Магазин навыков — тосты
    "duel_skill_slots_full_alert": {
        "ru": "⚠️ Все {max} слотов в бою заняты! Сначала снимите один навык.",
        "en": "⚠️ All {max} battle slots are full! Unequip a skill first.",
    },
    "duel_skill_unknown":        {"ru": "Неизвестный навык.", "en": "Unknown skill."},
    "duel_skill_not_enough":     {"ru": "Недостаточно монет! Нужно: {need} | У вас: {have}", "en": "Not enough coins! Needed: {need} | You have: {have}"},
    "duel_skill_already_bought": {"ru": "Навык уже куплен!", "en": "Skill already purchased!"},
    "duel_skill_bought_alert":   {"ru": "✅ Куплен навык: {name}!", "en": "✅ Skill purchased: {name}!"},
    "duel_skill_nofunds_alert":  {"ru": "💸 Недостаточно монет для покупки навыка!", "en": "💸 Not enough coins to buy this skill!"},

    # Приглашение на дуэль (входящий вызов)
    "duel_invite_title":      {"ru": "⚔️ <b>Вызов на дуэль!</b>", "en": "⚔️ <b>Duel challenge!</b>"},
    "duel_invite_player_default": {"ru": "Игрок", "en": "Player"},
    "duel_invite_body":       {
        "ru": "👤 <b>{name}</b> (уровень {lvl}) бросает тебе вызов!\n\n📊 <b>Характеристики противника:</b>",
        "en": "👤 <b>{name}</b> (level {lvl}) is challenging you!\n\n📊 <b>Opponent's stats:</b>",
    },
    "duel_invite_regen_suffix": {"ru": "HP/ход", "en": "HP/turn"},
    "duel_invite_skills_line": {"ru": "⚔️ Навыки: <i>{names}</i>", "en": "⚔️ Skills: <i>{names}</i>"},
    "duel_invite_skills_none": {"ru": "нет", "en": "none"},
    "duel_invite_expiry":     {"ru": "⏳ <i>Вызов действителен 2 минуты</i>", "en": "⏳ <i>Challenge is valid for 2 minutes</i>"},
    "duel_invite_btn_accept": {"ru": "✅ Принять", "en": "✅ Accept"},
    "duel_invite_btn_decline":{"ru": "❌ Отказаться", "en": "❌ Decline"},

    # ── Бой ──
    "duel_battle_already_over":  {"ru": "Бой уже завершён.", "en": "The battle is already over."},
    "duel_battle_you_frozen":    {"ru": "❄️ Ты заморожен и пропускаешь ход!", "en": "❄️ You're frozen and skip this turn!"},
    "duel_battle_on_cooldown":   {"ru": "⏳ Навык на перезарядке ещё {left}с.", "en": "⏳ Skill still on cooldown for {left}s."},
    "duel_battle_title":         {"ru": "БОЙ", "en": "BATTLE"},
    "duel_battle_finished_title":{"ru": "БОЙ ЗАВЕРШЁН", "en": "BATTLE OVER"},
    "duel_battle_draw":          {"ru": "⚔️ <b>Ничья!</b>", "en": "⚔️ <b>Draw!</b>"},
    "duel_battle_you_won":       {"ru": "<b>Ты победил!</b>", "en": "<b>You won!</b>"},
    "duel_battle_you_lost":      {"ru": "💀 <b>Ты проиграл!</b>", "en": "💀 <b>You lost!</b>"},
    "duel_battle_reward_line":   {
        "ru": "\n\n<tg-emoji emoji-id=\"5397916757333654639\">❤️</tg-emoji> <b>+{amount} <tg-emoji emoji-id=\"5199552030615558774\">❤️</tg-emoji></b> <i>(титул врага: {title})</i>",
        "en": "\n\n<tg-emoji emoji-id=\"5397916757333654639\">❤️</tg-emoji> <b>+{amount} <tg-emoji emoji-id=\"5199552030615558774\">❤️</tg-emoji></b> <i>(opponent's title: {title})</i>",
    },
    "duel_battle_your_shield":   {"ru": "🛡️ Твой щит: <b>{hp} HP</b>", "en": "🛡️ Your shield: <b>{hp} HP</b>"},
    "duel_battle_foe_shield":    {"ru": "🛡️ Щит врага: <b>{hp} HP</b>", "en": "🛡️ Enemy's shield: <b>{hp} HP</b>"},
    "duel_battle_you_frozen_note": {"ru": "❄️ <b>Ты заморожен! Следующий ход пропущен.</b>", "en": "❄️ <b>You're frozen! Next turn is skipped.</b>"},
    "duel_battle_foe_frozen_note": {"ru": "❄️ <b>{name} заморожен!</b>", "en": "❄️ <b>{name} is frozen!</b>"},
    "duel_battle_choose_skill":  {"ru": "Выбери навык для атаки:", "en": "Choose a skill to attack:"},
    "duel_battle_surrendered_log": {"ru": "🏳️ {name} сдался.", "en": "🏳️ {name} surrendered."},
    "duel_battle_you_surrendered": {"ru": "Ты сдался.", "en": "You surrendered."},
    "duel_battle_not_in_battle": {"ru": "Ты не в бою!", "en": "You're not in a battle!"},

    # ── Строки лога боя ──
    "duel_log_shield_line":   {"ru": "{name}: {emoji} {skill} → 🛡️ Щит {amount} HP", "en": "{name}: {emoji} {skill} → 🛡️ Shield {amount} HP"},
    "duel_log_damage_line":   {"ru": "{name}: {emoji} {skill} → -{dmg} HP{effect}", "en": "{name}: {emoji} {skill} → -{dmg} HP{effect}"},
    "duel_log_absorbed_suffix": {"ru": " (щит -{n})", "en": " (shield -{n})"},
    "duel_log_frozen_suffix":   {"ru": " ❄️ заморозка!", "en": " ❄️ frozen!"},

    # ── Кнопки боя ──
    "duel_battle_btn_new_search": {"ru": "🔄 Новый поиск", "en": "🔄 New search"},
    "duel_battle_btn_to_menu":    {"ru": "🏠 В меню дуэлей", "en": "🏠 Duel menu"},
    "duel_battle_btn_surrender":  {"ru": "🏳️ Сдаться", "en": "🏳️ Surrender"},
    "duel_battle_sec_short":      {"ru": "с", "en": "s"},

    "duel_hp_too_low_regen":   {"ru": "HP слишком низкий ({hp}/100)! Восстановится через {secs} сек.", "en": "HP too low ({hp}/100)! Will recover in {secs} sec."},
    "duel_hp_too_low_tick":    {"ru": "HP слишком низкий ({hp}/100)! Следующий тик через {secs} сек.", "en": "HP too low ({hp}/100)! Next tick in {secs} sec."},
    "duel_hp_too_low_recover_first": {"ru": "HP слишком низкий ({hp}/100)! Сначала восстановись.", "en": "HP too low ({hp}/100)! Recover first."},
    "duel_search_cancelled_toast": {"ru": "Поиск отменён.", "en": "Search cancelled."},

    "duel_already_in_battle_toast": {"ru": "Ты уже в бою!", "en": "You're already in a battle!"},
    "duel_challenger_in_battle":    {"ru": "❌ Вызывающий уже в другом бою. Вызов отменён.", "en": "❌ The challenger is already in another battle. Challenge cancelled."},
    "duel_challenger_not_found":    {"ru": "❌ Вызывающий не найден.", "en": "❌ Challenger not found."},
    "duel_challenge_expired":       {"ru": "❌ Вызов истёк или уже не действителен.", "en": "❌ The challenge has expired or is no longer valid."},
    "duel_challenger_in_battle_2":  {"ru": "❌ Вызывающий уже в другом бою.", "en": "❌ The challenger is already in another battle."},
    "duel_accepted_battle_started": {"ru": "✅ <b>{name} принял вызов! Бой начался!</b>\n\n", "en": "✅ <b>{name} accepted the challenge! The battle has begun!</b>\n\n"},
    "duel_challenge_cancelled_toast": {"ru": "Вызов отменён.", "en": "Challenge cancelled."},
    "duel_challenge_declined_toast":  {"ru": "Вызов отклонён.", "en": "Challenge declined."},
    "duel_challenge_declined_notify": {"ru": "❌ <b>{name} отклонил твой вызов на дуэль.</b>", "en": "❌ <b>{name} declined your duel challenge.</b>"},

    # Магазин навыков
    "duel_shop_title":  {"ru": "Изучение Навыков", "en": "Learn Skills"},
    "duel_shop_page":   {"ru": "Страница {page}/{total} · ⚔️ в бою: {eq}/{max}", "en": "Page {page}/{total} · ⚔️ equipped: {eq}/{max}"},
    "duel_shop_balance":{"ru": "Баланс: <b>{balance}</b>", "en": "Balance: <b>{balance}</b>"},
    "duel_shop_footer": {"ru": "Нажми навык — купи или экипируй в бой", "en": "Tap a skill — buy it or equip it for battle"},

    # Поиск
    "duel_search_title": {"ru": "ПОИСК ПРОТИВНИКА", "en": "FIND OPPONENT"},
    "duel_search_wait": {
        "ru": "⏳ <b>Ищем соперника...</b>\n\nОжидай — как только найдётся противник,\nбой начнётся автоматически.\n\n<i>Нажми «Проверить» чтобы обновить статус.</i>",
        "en": "⏳ <b>Looking for an opponent...</b>\n\nHang tight — as soon as an opponent is found,\nthe fight will start automatically.\n\n<i>Tap “Check” to refresh the status.</i>",
    },
    "duel_search_idle": {
        "ru": "Нажми <b>«Найти бой»</b> для поиска соперника.\n\nВ бою тебе доступны твои навыки из магазина.\nУрон зависит <b>только от навыков</b> — прокачивай их!\n🔵 Маг. навыки снижаются магической защитой\n💥 Физ. навыки снижаются физической защитой\n🛡️ Щитовые навыки поглощают входящий урон",
        "en": "Tap <b>“Find fight”</b> to look for an opponent.\n\nIn battle you can use the skills you've bought.\nDamage depends <b>only on skills</b> — level them up!\n🔵 Magic skills are reduced by magic defense\n💥 Physical skills are reduced by physical defense\n🛡️ Shield skills absorb incoming damage",
    },
    "duel_btn_search_check": {"ru": "🔄 Проверить",      "en": "🔄 Check"},
    "duel_btn_search_cancel":{"ru": "❌ Отменить поиск", "en": "❌ Cancel search"},
    "duel_btn_search_start": {"ru": "⚔️ Найти бой",      "en": "⚔️ Find fight"},

    # Вызов
    "duel_challenge_title": {"ru": "БРОСИТЬ ВЫЗОВ", "en": "SEND CHALLENGE"},
    "duel_challenge_body": {
        "ru": "Отправь <b>ID</b> или <b>@юзернейм</b> игрока которого хочешь вызвать на дуэль.\n\nПримеры:\n<code>123456789</code>\n<code>@username</code>\n\n⏳ <i>Вызов действует 2 минуты — если противник не ответит, он истечёт.</i>",
        "en": "Send the <b>ID</b> or <b>@username</b> of the player you want to challenge to a duel.\n\nExamples:\n<code>123456789</code>\n<code>@username</code>\n\n⏳ <i>The challenge is valid for 2 minutes — if the opponent doesn't respond, it expires.</i>",
    },
    "duel_challenge_sent_title": {"ru": "⚔️ <b>Вызов отправлен!</b>", "en": "⚔️ <b>Challenge sent!</b>"},
    "duel_challenge_sent_body": {
        "ru": "👤 <b>{name}</b> получил твой вызов.\n⏳ Ожидай ответа — у него есть 2 минуты.",
        "en": "👤 <b>{name}</b> received your challenge.\n⏳ Waiting for a response — they have 2 minutes.",
    },
    "duel_btn_challenge_cancel": {"ru": "❌ Отменить вызов", "en": "❌ Cancel challenge"},

    # Статус HP
    "duel_hp_status": {
        "ru": "⚠️ <b>Твоё HP: {hp}/{hp_max}</b>\nВосстановление: +{amount} HP каждые {interval} сек.\nСледующий тик через <b>{secs} сек.</b>\n<i>Нельзя начать бой пока HP &lt; 100!</i>",
        "en": "⚠️ <b>Your HP: {hp}/{hp_max}</b>\nRegeneration: +{amount} HP every {interval} sec.\nNext tick in <b>{secs} sec.</b>\n<i>You can't start a fight while HP &lt; 100!</i>",
    },

    # Раздел в разработке
    "duel_soon_search":  {"ru": "Поиск противника",         "en": "Find opponent"},
    "duel_soon_invite":  {"ru": "Пригласить на поединок",    "en": "Invite to duel"},
    "duel_soon_skills":  {"ru": "Навыки",                    "en": "Skills"},
    "duel_soon_body":    {"ru": "🚧 Раздел в разработке.\nСкоро будет доступен!", "en": "🚧 This section is under development.\nComing soon!"},

    # Быстрые команды — ошибки
    "duel_cmd_no_hp": {
        "ru": "⚠️ <b>HP слишком низкий!</b>\n\nТвоё HP: <b>{hp}/100</b>\nВосстановится через <b>{secs} сек.</b>\n<i>Нельзя начать бой пока HP &lt; 100</i>",
        "en": "⚠️ <b>HP too low!</b>\n\nYour HP: <b>{hp}/100</b>\nWill recover in <b>{secs} sec.</b>\n<i>You can't start a fight while HP &lt; 100</i>",
    },
    "duel_cmd_already_in_battle": {"ru": "⚔️ <b>Ты уже находишься в бою!</b>", "en": "⚔️ <b>You're already in a battle!</b>"},
    "duel_cmd_invite_usage": {
        "ru": "Ответь на сообщение игрока командой <b>вз</b> (или <b>challenge</b>),\nчтобы бросить ему вызов.\n\nИли напиши: <code>вз @username</code> / <code>вз 123456789</code>\n\n⏳ <i>Вызов действует 2 минуты.</i>",
        "en": "Reply to a player's message with the command <b>challenge</b> (or <b>вз</b>)\nto challenge them.\n\nOr type: <code>challenge @username</code> / <code>challenge 123456789</code>\n\n⏳ <i>The challenge is valid for 2 minutes.</i>",
    },
    "duel_cmd_invite_self":       {"ru": "❌ <b>Нельзя вызвать самого себя!</b>", "en": "❌ <b>You can't challenge yourself!</b>"},
    "duel_cmd_invite_not_found": {"ru": "❌ <b>Игрок не найден.</b> Он должен хотя бы раз написать боту.", "en": "❌ <b>Player not found.</b> They must have messaged the bot at least once."},
    "duel_cmd_invite_in_battle":  {"ru": "❌ <b>Этот игрок уже находится в бою.</b>", "en": "❌ <b>This player is already in a battle.</b>"},
    "duel_cmd_invite_blocked":    {"ru": "❌ Не удалось отправить уведомление <b>{name}</b> — возможно бот заблокирован.", "en": "❌ Couldn't send a notification to <b>{name}</b> — the bot may be blocked."},
    "duel_cmd_invite_limit": {
        "ru": "❌ <b>Лимит вызовов исчерпан!</b>\n\nТы уже вызывал <b>{name}</b> {limit} раз(а) за последние 24 часа.\nПопробуй снова через <b>{wait}</b>.",
        "en": "❌ <b>Challenge limit reached!</b>\n\nYou've already challenged <b>{name}</b> {limit} time(s) in the last 24 hours.\nTry again in <b>{wait}</b>.",
    },
    "duel_hours_short": {"ru": "ч", "en": "h"},
    "duel_mins_short":  {"ru": "мин", "en": "min"},
})

# ── Дуэли — экран слота экипировки и карточка предмета ──
_STRINGS.update({
    "duel_equip_slot_header": {"ru": "СНАРЯЖЕНИЕ — {label}", "en": "GEAR — {label}"},
    "duel_equip_slot_page": {
        "ru": "Страница {page}/{total} · уровни {start}–{end}",
        "en": "Page {page}/{total} · levels {start}–{end}",
    },
    "duel_equip_slot_hint": {"ru": "Нажми на предмет, чтобы узнать подробности", "en": "Tap an item to see details"},
    "duel_state_worn":         {"ru": "надето",       "en": "equipped"},
    "duel_state_in_inventory": {"ru": "в инвентаре",  "en": "in inventory"},
    "duel_coins_suffix":       {"ru": "монет",        "en": "coins"},

    "duel_item_status_worn":      {"ru": "✅ <b>Надето прямо сейчас</b>", "en": "✅ <b>Currently equipped</b>"},
    "duel_item_status_inventory": {"ru": "📦 <b>Есть в инвентаре</b> — не надето", "en": "📦 <b>In inventory</b> — not equipped"},
    "duel_item_price_line": {
        "ru": '<tg-emoji emoji-id="5278467510604160626">🎒</tg-emoji> <b>Цена: {price} <tg-emoji emoji-id="5199552030615558774">🎒</tg-emoji></b>',
        "en": '<tg-emoji emoji-id="5278467510604160626">🎒</tg-emoji> <b>Price: {price} <tg-emoji emoji-id="5199552030615558774">🎒</tg-emoji></b>',
    },
    "duel_item_deficit": {"ru": "⚠️ <i>Не хватает {deficit} монет</i>", "en": "⚠️ <i>Missing {deficit} coins</i>"},

    "duel_rarity_common":    {"ru": "⬜ Обычный",     "en": "⬜ Common"},
    "duel_rarity_uncommon":  {"ru": "🟩 Необычный",   "en": "🟩 Uncommon"},
    "duel_rarity_rare":      {"ru": "🟦 Редкий",      "en": "🟦 Rare"},
    "duel_rarity_epic":      {"ru": "🟪 Эпический",   "en": "🟪 Epic"},
    "duel_rarity_legendary": {"ru": "🟧 Легендарный", "en": "🟧 Legendary"},
    "duel_rarity_mythic":    {"ru": "🟥 Мифический",  "en": "🟥 Mythic"},
    "duel_rarity_ancient":   {"ru": "🔶 Древний",     "en": "🔶 Ancient"},
    "duel_rarity_relic":     {"ru": "💠 Реликвийный", "en": "💠 Relic"},
    "duel_rarity_absolute":  {"ru": "👑 Абсолютный",  "en": "👑 Absolute"},

    "duel_item_bonus_title": {"ru": "Боевые бонусы (защита и HP):", "en": "Combat bonuses (defense and HP):"},
    "duel_item_dmg_note":    {"ru": "💡 Урон в дуэли даётся навыками, а не снаряжением!", "en": "💡 Duel damage comes from skills, not gear!"},

    "duel_btn_unequip":          {"ru": "Снять",  "en": "Unequip"},
    "duel_btn_equip_item":       {"ru": "Надеть", "en": "Equip"},
    "duel_btn_buy_item":         {"ru": "Купить — {price} монет", "en": "Buy — {price} coins"},
    "duel_btn_not_enough_coins": {"ru": "Недостаточно монет", "en": "Not enough coins"},

    # Алерты (call.answer) для экипировки
    "duel_alert_unknown_item": {"ru": "Неизвестный предмет.", "en": "Unknown item."},
    "duel_alert_not_enough_coins_full": {
        "ru": "Недостаточно монет!\nНужно: {price} | У вас: {balance}",
        "en": "Not enough coins!\nNeed: {price} | You have: {balance}",
    },
    "duel_alert_no_funds_buy":     {"ru": "💸 Недостаточно монет для покупки!", "en": "💸 Not enough coins to buy!"},
    "duel_alert_bought_item":      {"ru": "✅ Куплено: {name}!", "en": "✅ Bought: {name}!"},
    "duel_alert_equip_buy_first":  {"ru": "Сначала купи предмет.", "en": "Buy the item first."},
    "duel_alert_equipped_item":    {"ru": "✅ Надето: {name}!", "en": "✅ Equipped: {name}!"},
    "duel_alert_unequipped_item":  {"ru": "❌ Снято: {name}.", "en": "❌ Unequipped: {name}."},
})
