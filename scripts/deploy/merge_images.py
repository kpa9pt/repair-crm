#!/usr/bin/env python3
"""
Скрипт для восстановления потерянных образов из проваленного деплоя.
Логика:
1. Сравнивает images.json (новый) и images.failed.json (бекап)
2. Находит сервисы, которых нет в новом images.json
3. Проверяет state на сервере: если образ в state отличается от бекапного -
    значит образ потерян
4. Мержит потерянные образы в актуальный images.json
"""

import json
import sys
from pathlib import Path


def main():
    print("🔍 Restoring lost images from failed deploy...", file=sys.stderr)

    # Проверяем наличие бекапа
    backup_path = Path("images.failed.json")
    if not backup_path.exists():
        print("✅ No failed deploy backup found", file=sys.stderr)
        return

    # 1. Загружаем бекап
    with open(backup_path) as f:
        backup_images = json.load(f)
    print(f"📦 Backup images: {len(backup_images)} services", file=sys.stderr)
    print(f"   Services: {list(backup_images.keys())}", file=sys.stderr)

    # 2. Загружаем текущий images.json
    current_images = {}
    if Path("images.json").exists():
        with open("images.json") as f:
            current_images = json.load(f)
    print(f"📄 Current images: {len(current_images)} services", file=sys.stderr)

    # 3. Находим сервисы, которые есть в бекапе, но нет в текущем
    lost_services = {}
    for service, image in backup_images.items():
        if service not in current_images:
            lost_services[service] = image
            print(f"   🔄 Lost service detected: {service}", file=sys.stderr)

    if not lost_services:
        print("✅ No lost services to restore", file=sys.stderr)
        return

    # 4. Загружаем state с сервера и проверяем, какие образы реально потеряны
    state_path = Path("state.json")
    if not state_path.exists():
        print("⚠️ state.json not found, restoring all lost services", file=sys.stderr)
        to_merge = lost_services
    else:
        with open(state_path) as f:
            state = json.load(f)

        to_merge = {}

        for service, backup_image in lost_services.items():
            if service not in state.get("services", {}):
                print(f"⚠️ Service {service} not in state, skipping", file=sys.stderr)
                continue

            svc = state["services"][service]
            strategy = svc.get("strategy", "single")

            if strategy == "blue-green":
                active = svc.get("active", "blue")
                inactive = "green" if active == "blue" else "blue"
                current_image = svc.get(inactive, {}).get("image", "")

                if current_image != backup_image:
                    to_merge[service] = backup_image
                    print(
                        f"   ✅ Need restore: {service} (inactive={inactive})",
                        file=sys.stderr,
                    )
                else:
                    print(f"   ✅ Already correct: {service}", file=sys.stderr)

            else:  # single strategy
                current_image = svc.get("image", "")

                if current_image != backup_image:
                    to_merge[service] = backup_image
                    print(f"   ✅ Need restore: {service} (single)", file=sys.stderr)
                else:
                    print(f"   ✅ Already correct: {service}", file=sys.stderr)

    if not to_merge:
        print("✅ No images to restore", file=sys.stderr)
        return

    # 5. Мержим в images.json
    merged = {**current_images, **to_merge}
    with open("images.json", "w") as f:
        json.dump(merged, f, indent=2)

    print(
        f"✅ images.json updated with "
        f"{len(to_merge)} restored services: "
        f"{list(to_merge.keys())}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
