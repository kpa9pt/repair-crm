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
    deploy_plan = json.loads(os.environ["DEPLOY_PLAN"])

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]

        inactive = "green" if active == "blue" else "blue"

        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{inactive}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {container} healthy")
                ok = True
                break

            print(f"retry {i}")
            time.sleep(2)

        if not ok:
            print(f"❌ {container} failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
