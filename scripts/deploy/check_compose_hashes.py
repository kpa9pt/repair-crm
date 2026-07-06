import sys
import json


def main():
    print("🔍 Checking compose hashes vs state...", file=sys.stderr)

    # Загружаем свежие хеши
    with open("current_hashes.json") as f:
        current = json.load(f)
    print(f"   Current hashes: {len(current)} services", file=sys.stderr)

    # Загружаем state
    with open("state.json") as f:
        state = json.load(f)
    print(
        f"   State hashes: {len(state.get('services', {}))} services", file=sys.stderr
    )

    changed = []
    for service, new_hash in current.items():
        if not new_hash:
            continue
        old_hash = state.get("services", {}).get(service, {}).get("compose_hash", "")
        if old_hash != new_hash:
            print(
                f"   🔄 {service}: "
                f"{old_hash[:8] if old_hash else 'empty'} → "
                f"{new_hash[:8]}...",
                file=sys.stderr,
            )
            changed.append(service)
        else:
            print(f"   ✅ {service}: unchanged", file=sys.stderr)

    print(f"✅ Changed services: {changed}", file=sys.stderr)
    print(json.dumps(changed))


if __name__ == "__main__":
    main()
