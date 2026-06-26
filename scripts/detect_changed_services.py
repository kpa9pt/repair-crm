import sys
from pathlib import Path
import json
import os
import fnmatch
from shared.service_registry import get_services, get_service_config

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))


def detect_changed_services():
    """Определяет, какие сервисы изменились на основе списка файлов"""
    changed_files = os.environ.get("ALL_CHANGED_FILES", "").split()

    if not changed_files:
        print(json.dumps([]))
        return

    changed_services = []

    for service in get_services():
        cfg = get_service_config(service)
        paths = cfg.get("paths", [f"services/{service}/**"])

        for path in paths:
            # Преобразуем паттерн для fnmatch
            # services/gateway/** → services/gateway/*
            pattern = path.replace("**", "*").rstrip("/")

            for file in changed_files:
                if fnmatch.fnmatch(file, pattern):
                    changed_services.append(service)
                    break

            if service in changed_services:
                break

    # Убираем дубликаты
    changed_services = list(set(changed_services))
    print(json.dumps(changed_services))


if __name__ == "__main__":
    detect_changed_services()
