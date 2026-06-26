import sys
from pathlib import Path
import json
import subprocess
from shared.service_registry import get_services

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def get_compose_hash(service: str) -> str:
    """Извлекает секцию сервиса из docker-compose.yml и вычисляет хеш"""
    try:
        result = subprocess.run(
            ["yq", "eval", f".services.{service}", "docker-compose.yml"],
            capture_output=True,
            text=True,
            check=True,
        )
        section = result.stdout
        if not section.strip():
            return ""
        hash_result = subprocess.run(
            ["sha256sum"], input=section, capture_output=True, text=True, check=True
        )
        return hash_result.stdout.split()[0]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to compute hash for {service}: {e}", file=sys.stderr)
        return ""


def main():
    hashes = {}
    for service in get_services():
        h = get_compose_hash(service)
        if h:
            hashes[service] = h
        else:
            print(f"WARNING: No hash for {service}", file=sys.stderr)
            hashes[service] = ""
    print(json.dumps(hashes))


if __name__ == "__main__":
    main()
