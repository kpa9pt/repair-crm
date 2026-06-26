import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    with open("current_hashes.json") as f:
        current = json.load(f)

    with open("state.json") as f:
        state = json.load(f)

    for service, new_hash in current.items():
        if service in state.get("services", {}):
            state["services"][service]["compose_hash"] = new_hash

    with open("state.json", "w") as f:
        json.dump(state, f, indent=2)

    print("✅ Compose hashes updated in state.json")


if __name__ == "__main__":
    main()
