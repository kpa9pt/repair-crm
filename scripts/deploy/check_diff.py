import json
import sys

STATE_FILE = "state.json"


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def main():
    state = load_state()

    gateway = state["services"]["gateway"]

    active = gateway["active"]
    target = "green" if active == "blue" else "blue"

    active_image = gateway[active]["image"]
    target_image = gateway[target]["image"]

    changed = active_image != target_image

    result = {
        "changed": changed,
        "active": active,
        "target": target,
        "active_image": active_image,
        "target_image": target_image,
    }

    # GitHub Actions output
    print(f"changed={str(changed).lower()}")

    # (опционально debug)
    print(json.dumps(result, indent=2), file=sys.stderr)

    if changed:
        sys.exit(0)
    else:
        # важно: НЕ fail job, просто signal
        sys.exit(0)


if __name__ == "__main__":
    main()
