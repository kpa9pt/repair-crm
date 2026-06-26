import sys
from pathlib import Path
import json
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def get_compose_hash(service: str) -> str:
    """Извлекает секцию сервиса из docker-compose.yml и вычисляет хеш"""
    print(f"🔍 Computing hash for {service}...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["yq", "eval", f".services.{service}", "docker-compose.yml"],
            capture_output=True,
            text=True,
            check=True,
        )
        section = result.stdout
        if not section.strip():
            print(f"⚠️  Empty section for {service}", file=sys.stderr)
            return ""
        hash_result = subprocess.run(
            ["sha256sum"], input=section, capture_output=True, text=True, check=True
        )
        hash_val = hash_result.stdout.split()[0]
        print(f"   ✅ {service}: {hash_val[:8]}...", file=sys.stderr)
        return hash_val
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Failed to compute hash for {service}: {e}", file=sys.stderr)
        return ""


def main():
    print("📊 Computing compose hashes for ALL services...", file=sys.stderr)

    # Получаем все секции из docker-compose.yml
    # Через yq получаем список ключей .services
    result = subprocess.run(
        ["yq", "eval", ".services | keys", "docker-compose.yml"],
        capture_output=True,
        text=True,
        check=True,
    )

    # Парсим список сервисов из вывода yq
    services = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("---"):
            # Убираем кавычки если есть
            service = line.strip('"-')
            if service:
                services.append(service)

    print(f"   Found services: {services}", file=sys.stderr)

    hashes = {}
    for service in services:
        h = get_compose_hash(service)
        if h:
            hashes[service] = h
        else:
            print(f"⚠️  No hash for {service}", file=sys.stderr)
            hashes[service] = ""

    print(f"✅ Hashes computed: {len(hashes)} services", file=sys.stderr)
    print(json.dumps(hashes))


if __name__ == "__main__":
    main()
