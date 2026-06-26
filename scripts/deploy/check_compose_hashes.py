import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    # Загружаем свежие хеши
    with open("current_hashes.json") as f:
        current = json.load(f)

    # Загружаем state
    with open("state.json") as f:
        state = json.load(f)

    changed = []
    for service, new_hash in current.items():
        if not new_hash:
            continue
        old_hash = state.get("services", {}).get(service, {}).get("compose_hash", "")
        if old_hash != new_hash:
            changed.append(service)

    print(json.dumps(changed))


if __name__ == "__main__":
    main()
