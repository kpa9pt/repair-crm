import json
import sys
import subprocess
import time
import os
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def main():
    # Читаем JSON из stdin
    deploy_plan_str = sys.stdin.read().strip()
    print(f"DEBUG: deploy_plan_str = {repr(deploy_plan_str)}")

    if not deploy_plan_str:
        # Если stdin пустой, пробуем из переменной окружения
        deploy_plan_str = os.environ.get("DEPLOY_PLAN", "")
        print(f"DEBUG: fallback to env = {repr(deploy_plan_str)}")

    deploy_plan = json.loads(deploy_plan_str)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {service} healthy")
                ok = True
                break

            print(f"retry {i}")

            time.sleep(2)

        if not ok:
            print(f"❌ {service} failed")
            sys.exit(1)

    subprocess.run(["docker", "exec", "nginx", "/scripts/reload.sh"], check=True)

    print("🔁 nginx reloaded")


if __name__ == "__main__":
    main()
