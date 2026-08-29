"""
Проверка всех custom-emoji ID из hunt.py через Telegram Bot API.

Как использовать:
1. Положи этот файл рядом с hunt.py (или поправь HUNT_PY_PATH ниже).
2. Впиши свой токен бота в BOT_TOKEN (тот же, что в основном коде бота).
3. Запусти: python3 check_emoji_ids.py
4. Скрипт найдёт все числовые ID в кавычках длиной 15-20 цифр по всему
   файлу (и в _E{}, и в SWORD_EMOJIS{}, и в POTION-словарях, и просто
   в коде), спросит Telegram через getCustomEmojiStickers, какие из них
   существуют, и выведет список тех, что НЕ существуют — это и есть
   причина DOCUMENT_INVALID.

Ничего никуда не отправляет и не меняет — только читает и проверяет.
"""

import re
import sys
import time
import urllib.request
import json

HUNT_PY_PATH = "hunt.py"          # путь к твоему файлу
BOT_TOKEN = "8693034024:AAEjOqhChUGq8IvZHYIOw2-RcfJLSyK7ZBI"   # токен бота (как в основном коде)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/getCustomEmojiStickers"
BATCH_SIZE = 100  # лимит Telegram на один вызов


def extract_ids(path: str):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # все числа длиной 15-20 цифр в кавычках — это и есть custom-emoji ID
    ids = re.findall(r'"(\d{15,20})"', text)
    return sorted(set(ids))


def check_batch(ids_batch):
    payload = json.dumps({"custom_emoji_ids": ids_batch}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    found_ids = {sticker["custom_emoji_id"] for sticker in data["result"]}
    return found_ids


def main():
    if "ВСТАВЬ_СЮДА_ТОКЕН" in BOT_TOKEN:
        print("!! Сначала впиши свой BOT_TOKEN в начале файла.")
        sys.exit(1)

    all_ids = extract_ids(HUNT_PY_PATH)
    print(f"Найдено {len(all_ids)} уникальных ID в {HUNT_PY_PATH}\n")

    existing = set()
    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i : i + BATCH_SIZE]
        existing |= check_batch(batch)
        time.sleep(0.3)  # на всякий случай, чтобы не упереться в rate limit

    missing = [eid for eid in all_ids if eid not in existing]

    print(f"Существуют в Telegram: {len(existing)}")
    print(f"НЕ существуют (битые):  {len(missing)}\n")

    if missing:
        print("=== БИТЫЕ ID (замени их на None или на реальные) ===")
        for eid in missing:
            print(f"  {eid}")
    else:
        print("Все ID в порядке — проблема не в списке ID, а где-то ещё "
              "(например, ID собирается динамически, или ошибка вообще "
              "не про custom-emoji).")


if __name__ == "__main__":
    main()
