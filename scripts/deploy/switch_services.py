import json
import sys
import os
import base64
from pathlib import Path


def main():
    # Получаем base64 из переменной окружения
    plan = os.environ.get("DEPLOY_PLAN", "")
    deploy_plan_str = base64.b64decode(plan).decode()
    deploy_plan = json.loads(deploy_plan_str)

    if not deploy_plan:
        print("no changes")
        sys.exit(0)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:
        active = state["services"][service]["active"]
        new = "green" if active == "blue" else "blue"

        state["services"][service]["active"] = new

        print(f"🔁 {service}: {active} → {new}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()
