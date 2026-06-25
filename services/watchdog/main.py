import json
import time
import os
import subprocess


STATE_PATH = os.getenv("STATE_PATH", "/state/state.json")


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def healthcheck(container, port, path):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{path}', timeout=2)"
        ),
    ]
    return subprocess.run(cmd).returncode == 0


def trigger_rollback(service):
    print(f"[WATCHDOG] rollback triggered for {service}")

    subprocess.run(["python", "/scripts/rollback.py", service])


def check_service(service, cfg):
    if cfg.get("strategy") != "blue-green":
        return True

    active = cfg["active"]
    container = f"{service}-{active}"

    port = cfg.get("port", 8000)
    health = cfg.get("healthcheck", "/health")

    retries = 15

    for i in range(retries):
        if healthcheck(container, port, health):
            return True
        time.sleep(2)

    return False


def main():
    while True:
        state = load_state()

        rolled_back_this_cycle = set()

        for service, cfg in state["services"].items():

            if cfg.get("strategy") != "blue-green":
                continue

            if cfg.get("rollback_locked", False):
                print(f"[WATCHDOG] rollback locked → skip {service}")
                continue

            ok = check_service(service, cfg)

            if ok:
                continue

            if service in rolled_back_this_cycle:
                continue

            print(f"[WATCHDOG] service failed → {service}")

            # rollback
            trigger_rollback(service)

            # mark locked immediately
            state["services"][service]["rollback_locked"] = True
            rolled_back_this_cycle.add(service)

            save_state(state)

        time.sleep(60)


if __name__ == "__main__":
    main()
