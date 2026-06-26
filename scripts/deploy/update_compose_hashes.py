import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    print("📝 Updating compose hashes in state...", file=sys.stderr)

    with open("current_hashes.json") as f:
        current = json.load(f)
    print(f"   Current hashes: {len(current)} services", file=sys.stderr)

    with open("state.json") as f:
        state = json.load(f)
    print(f"   State services: {len(state.get('services', {}))}", file=sys.stderr)

    updated = 0
    for service, new_hash in current.items():
        if service in state.get("services", {}):
            old_hash = state["services"][service].get("compose_hash", "")
            state["services"][service]["compose_hash"] = new_hash
            if old_hash != new_hash:
                print(
                    f"   🔄 Updated {service}: "
                    f"{old_hash[:8] if old_hash else 'empty'} → "
                    f"{new_hash[:8]}...",
                    file=sys.stderr,
                )
                updated += 1
        else:
            print(
                f"⚠️  Service {service} not found in state, skipping",
                file=sys.stderr,
            )

    with open("state.json", "w") as f:
        json.dump(state, f, indent=2)

    print(
        f"✅ Compose hashes updated in state.json ({updated} changes)", file=sys.stderr
    )


if __name__ == "__main__":
    main()
