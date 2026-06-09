import json
import sys

STATE_FILE = "state.json"


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def main():
    state = load_state()

    blue = state["gateway-blue"]
    green = state["gateway-green"]
    active = state.get("active")

    changed = blue != green

    # target логика (на будущее пригодится)
    if active == "blue":
        target = "green"
    else:
        target = "blue"

    result = {
        "changed": changed,
        "active": active,
        "target": target,
        "blue": blue,
        "green": green,
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
