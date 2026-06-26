import sys
from pathlib import Path
import json
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Сервисы, которые НЕ должны быть в state (инфраструктурные)
IGNORE_SERVICES = ["postgres"]


def get_compose_hash(service: str, compose_data: dict) -> str:
    """Извлекает секцию сервиса из docker-compose.yml и вычисляет хеш"""
    print(f"🔍 Computing hash for {service}...", file=sys.stderr)
    try:
        section = compose_data.get("services", {}).get(service, {})
        if not section:
            print(f"⚠️  Empty section for {service}", file=sys.stderr)
            return ""
        # Превращаем секцию в строку для хеширования
        section_str = yaml.dump(section, default_flow_style=False, sort_keys=True)
        import hashlib

        hash_val = hashlib.sha256(section_str.encode()).hexdigest()
        print(f"   ✅ {service}: {hash_val[:8]}...", file=sys.stderr)
        return hash_val
    except Exception as e:
        print(f"❌ ERROR: Failed to compute hash for {service}: {e}", file=sys.stderr)
        return ""


def main():
    print("📊 Computing compose hashes for ALL services...", file=sys.stderr)

    # Загружаем docker-compose.yml как Python dict
    with open("docker-compose.yml") as f:
        compose_data = yaml.safe_load(f)

    services = list(compose_data.get("services", {}).keys())

    # Фильтруем инфраструктурные сервисы
    services = [s for s in services if s not in IGNORE_SERVICES]

    print(f"   Found services (excluding postgres): {services}", file=sys.stderr)

    hashes = {}
    for service in services:
        h = get_compose_hash(service, compose_data)
        if h:
            hashes[service] = h
        else:
            print(f"⚠️  No hash for {service}", file=sys.stderr)
            hashes[service] = ""

    print(f"✅ Hashes computed: {len(hashes)} services", file=sys.stderr)
    print(json.dumps(hashes))


if __name__ == "__main__":
    main()
