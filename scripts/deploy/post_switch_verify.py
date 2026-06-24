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

        print(f"🔍 post-switch verify: {service}", file=sys.stderr)

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(30):

            if healthcheck(container, port, health):
                ok = True
                break

            print(
                f"retry {service}: {i + 1}/30",
                file=sys.stderr,
            )

            time.sleep(2)

        if ok:
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
