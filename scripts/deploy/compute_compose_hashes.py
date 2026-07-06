import sys
from pathlib import Path
import json
import yaml
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Сервисы, которые НЕ должны быть в state (инфраструктурные)
IGNORE_SERVICES = ["postgres"]

# Blue-green сервисы: какие compose-сервисы объединять в один state-сервис
BLUE_GREEN_MAP = {
    "gateway": ["gateway-blue", "gateway-green"],
    "auth": ["auth-blue", "auth-green"],
}


def get_service_hash(service_name: str, compose_data: dict) -> str:
    """
    Вычисляет хеш для сервиса.
    Если сервис в BLUE_GREEN_MAP — объединяет хеши всех его частей.
    """
    print(f"🔍 Computing hash for {service_name}...", file=sys.stderr)

    # Проверяем, является ли сервис blue-green
    if service_name in BLUE_GREEN_MAP:
        # Хешируем все части blue-green сервиса
        parts = BLUE_GREEN_MAP[service_name]
        combined_hash = hashlib.sha256()

        for part in parts:
            section = compose_data.get("services", {}).get(part, {})
            if not section:
                print(f"⚠️  Part {part} not found for {service_name}", file=sys.stderr)
                continue
            section_str = yaml.dump(section, default_flow_style=False, sort_keys=True)
            combined_hash.update(section_str.encode())

        hash_val = combined_hash.hexdigest()
        print(
            f"   ✅ {service_name} (combined from {parts}): {hash_val[:8]}...",
            file=sys.stderr,
        )
        return hash_val

    else:
        # Обычный сервис — хешируем одну секцию
        section = compose_data.get("services", {}).get(service_name, {})
        if not section:
            print(f"⚠️  Empty section for {service_name}", file=sys.stderr)
            return ""
        section_str = yaml.dump(section, default_flow_style=False, sort_keys=True)
        hash_val = hashlib.sha256(section_str.encode()).hexdigest()
        print(f"   ✅ {service_name}: {hash_val[:8]}...", file=sys.stderr)
        return hash_val


def main():
    print("📊 Computing compose hashes for ALL services...", file=sys.stderr)

    # Загружаем docker-compose.yml как Python dict
    with open("docker-compose.yml") as f:
        compose_data = yaml.safe_load(f)

    # Все сервисы из compose
    all_services = list(compose_data.get("services", {}).keys())

    # Фильтруем инфраструктурные сервисы
    all_services = [s for s in all_services if s not in IGNORE_SERVICES]

    print(f"   Found compose services: {all_services}", file=sys.stderr)

    # Определяем, какие state-сервисы нужно хешировать
    # 1. Все обычные сервисы (которые не в BLUE_GREEN_MAP)
    # 2. Blue-green сервисы (из ключей BLUE_GREEN_MAP)
    state_services = set()

    for service in all_services:
        # Проверяем, не является ли этот сервис частью blue-green
        is_part_of_bg = False
        for bg_service, parts in BLUE_GREEN_MAP.items():
            if service in parts:
                state_services.add(bg_service)
                is_part_of_bg = True
                break

        if not is_part_of_bg:
            # Это обычный сервис
            state_services.add(service)

    print(f"   State services to hash: {sorted(state_services)}", file=sys.stderr)

    hashes = {}
    for service in sorted(state_services):
        h = get_service_hash(service, compose_data)
        if h:
            hashes[service] = h
        else:
            print(f"⚠️  No hash for {service}", file=sys.stderr)
            hashes[service] = ""

    print(f"✅ Hashes computed: {len(hashes)} state services", file=sys.stderr)
    print(json.dumps(hashes))


if __name__ == "__main__":
    main()
