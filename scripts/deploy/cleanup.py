import json
import os
import base64
import subprocess
from pathlib import Path


def load_state():
    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        return json.load(f)


def load_plan():
    data = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(data).decode())


def main():
    state = load_state()
    deploy_plan = load_plan()

    print("=== CLEANUP START ===")

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"skip unknown service: {service}")
            continue

        svc = state["services"][service]

        if svc["strategy"] == "blue-green":
            active = svc["active"]
            inactive = "green" if active == "blue" else "blue"
            container = f"{service}-{inactive}"

            print(f"stopping {container}")
            subprocess.run(["docker", "stop", container], check=False)

    # ✅ Удаляем только старые/неиспользуемые образы
    print("=== PRUNE unused images (keep containers) ===")
    subprocess.run(["docker", "image", "prune", "-a", "-f"], check=False)

    print("=== CLEANUP DONE ===")


if __name__ == "__main__":
    main()
