import json
import os
import base64
from pathlib import Path


STATE_FILE = Path.home() / "repair-crm" / "state" / "state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def decode_plan():
    raw = os.environ.get("DEPLOY_PLAN", "")
    if not raw:
        return []

    decoded = base64.b64decode(raw).decode()
    return json.loads(decoded)


def main():
    deploy_plan = decode_plan()
    state = load_state()

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"⚠️ skip unknown service {service}")
            continue

        print(f"🔒 lock rollback: {service}")
        state["services"][service]["rollback_locked"] = True

    save_state(state)
    print("✅ rollback locked for planned services")


if __name__ == "__main__":
    main()
