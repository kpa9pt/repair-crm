import json
import os
import base64
from pathlib import Path


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in decision["passed"]:

        if service not in state["services"]:
            print(f"⚠️ unknown service: {service}")
            continue

        state["services"][service]["rollback_locked"] = False

        print(f"🔓 rollback unlocked: {service}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()
