import json
import sys
from pathlib import Path


def main():
    deploy_plan = json.loads(sys.argv[1])

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
