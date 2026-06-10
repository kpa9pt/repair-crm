import json
import subprocess
import time
import sys

from pathlib import Path

STATE_FILE = Path.home() / "repair-crm" / "state.json"
NGINX_CONTAINER = "nginx"


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def opposite(active: str) -> str:
    if active == "blue":
        return "green"
    return "blue"


def service_name(slot: str) -> str:
    return f"gateway-{slot}"


def wait_health(container: str, retries=30, delay=2):
    print(f"⏳ Waiting health: {container}")

    for i in range(retries):
        try:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import urllib.request;"
                        "urllib.request.urlopen("
                        "'http://localhost:8000/health', timeout=2"
                        ")"
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ health OK")
            return True

        except subprocess.CalledProcessError:
            print(f"retry {i + 1}/{retries}")
            time.sleep(delay)

    return False


def reload_nginx():
    print("🔁 reloading nginx")
    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "nginx", "-s", "reload"],
        check=True,
    )


def main():
    state = load_state()

    active = state.get("active", "blue")
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    subprocess.run(["docker", "compose", "up", "-d", service_name(target)], check=True)

    # 2. healthcheck
    if not wait_health(target_container):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    print("✅ rollback completed")


if __name__ == "__main__":
    main()
