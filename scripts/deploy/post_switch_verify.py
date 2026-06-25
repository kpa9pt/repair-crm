import json
import sys
import time
import os
import base64
import subprocess
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


def wait_health(container, port, health, retries=30, delay=2):

    for i in range(retries):

        if healthcheck(container, port, health):
            return True

        print(
            f"retry: {i + 1}/{retries}",
            file=sys.stderr,
        )

        time.sleep(delay)

    return False


def main():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    result = {
        "passed": [],
        "failed": [],
    }

    for service in deploy_plan:

        print(
            f"🔍 post-switch verify: {service}",
            file=sys.stderr,
        )

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        print(
            f"phase 1 smoke: {service}",
            file=sys.stderr,
        )

        if not wait_health(container, port, health):
            result["failed"].append(service)
            continue

        print(
            f"phase 2 soak sleep: {service}",
            file=sys.stderr,
        )

        time.sleep(60)

        print(
            f"phase 3 soak verify: {service}",
            file=sys.stderr,
        )

        if wait_health(container, port, health):
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
