#!/usr/bin/env python3
"""
Разовая миграция: сжимает раздутые инвентари (boosters_inventory,
xp_inventory, enh_inventory) всех пользователей в tgstellar.db,
складывая одинаковые предметы (одинаковый "key") в одну запись
с полем "count" вместо десятков/сотен/тысяч отдельных записей.

ВАЖНО: останови бота перед запуском (systemctl stop / tmux kill),
чтобы не было гонки записи в БД.

Использование:
    python3 compact_inventories.py /root/Miner/tgstellar.db
"""

import sqlite3
import json
import sys
import shutil
from datetime import datetime


INV_KEYS = ("boosters_inventory", "xp_inventory", "enh_inventory")


def compact_inventory_list(inv: list) -> list:
    """Складывает одинаковые предметы (по полю key) в одну запись с count."""
    if not inv:
        return inv
    stacks: dict = {}
    order: list = []
    for item in inv:
        k = item.get("key")
        if k is None:
            # предмет без key (не должно случаться) — оставляем как есть
            order.append(("__raw__", item))
            continue
        if k not in stacks:
            # берём первый экземпляр как образец полей
            sample = {kk: vv for kk, vv in item.items() if kk not in ("instance_id", "count")}
            sample["instance_id"] = f"stack_{k}"
            sample["count"] = 0
            stacks[k] = sample
            order.append(("key", k))
        stacks[k]["count"] += item.get("count", 1)

    result = []
    seen_keys = set()
    for tag, val in order:
        if tag == "__raw__":
            result.append(val)
        else:
            if val not in seen_keys:
                result.append(stacks[val])
                seen_keys.add(val)
    return result


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 compact_inventories.py /root/Miner/tgstellar.db")
        sys.exit(1)

    db_path = sys.argv[1]

    # Бэкап перед миграцией — обязательно
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Бэкап создан: {backup_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT uid, data_json FROM users")
    rows = cur.fetchall()
    print(f"Всего пользователей: {len(rows)}")

    total_before = 0
    total_after = 0
    changed = 0

    for uid, data_json in rows:
        size_before = len(data_json)
        total_before += size_before

        try:
            data = json.loads(data_json)
        except json.JSONDecodeError:
            print(f"  ⚠️  uid={uid}: битый JSON, пропускаю")
            total_after += size_before
            continue

        touched = False
        for inv_key in INV_KEYS:
            inv = data.get(inv_key)
            if inv:
                new_inv = compact_inventory_list(inv)
                if len(new_inv) != len(inv):
                    data[inv_key] = new_inv
                    touched = True

        new_json = json.dumps(data, ensure_ascii=False)
        size_after = len(new_json)
        total_after += size_after

        if touched:
            cur.execute("UPDATE users SET data_json = ? WHERE uid = ?", (new_json, uid))
            changed += 1
            if size_before - size_after > 100_000:
                print(f"  uid={uid}: {size_before:,} -> {size_after:,} байт "
                      f"(-{size_before - size_after:,})")

    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    print(f"\nГотово.")
    print(f"Пользователей изменено: {changed} из {len(rows)}")
    print(f"Общий размер data_json: {total_before:,} -> {total_after:,} байт")
    print(f"Сэкономлено: {total_before - total_after:,} байт "
          f"({(total_before - total_after) / max(total_before,1) * 100:.1f}%)")
    print(f"\nЕсли что-то пошло не так — восстанови бэкап:")
    print(f"  cp {backup_path} {db_path}")


if __name__ == "__main__":
    main()
