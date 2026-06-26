import json
import subprocess
import time
import sys
import os

from pathlib import Path

STATE_FILE = Path(
    os.getenv(
        "STATE_PATH",
        str(Path.home() / "repair-crm" / "state" / "state.json"),
    )
)

WORKDIR = Path(
    os.getenv(
        "WORKDIR",
        str(Path.home() / "repair-crm"),
    )
)

NGINX_CONTAINER = "nginx"

service = os.getenv("ROLLBACK_SERVICE")
if not service:
    raise RuntimeError("ROLLBACK_SERVICE not set")


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
    return f"{service}-{slot}"


def wait_health(container: str, port: int, healthcheck: str, retries=30, delay=2):
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
                        f"'http://localhost:{port}{healthcheck}', timeout=2"
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
        ["docker", "exec", NGINX_CONTAINER, "/scripts/reload.sh"],
        check=True,
    )


def main():
    state = load_state()

    service_state = state["services"][service]

    port = service_state.get("port", 8000)
    healthcheck = service_state.get("healthcheck", "/health")

    if service_state["strategy"] == "single":
        print("single strategy rollback not supported")
        sys.exit(1)

    active = service_state["active"]
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    # Проверяем, существует ли контейнер
    result = subprocess.run(
        ["docker", "inspect", target_container],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Контейнер существует → запускаем
        print(f"📦 Starting existing container: {target_container}")
        subprocess.run(
            ["docker", "start", target_container],
            cwd=WORKDIR,
            check=True,
        )
    else:
        # Контейнера нет → ничего не делаем, ждем что он появится
        print(f"⏳ Container {target_container} does not exist yet, waiting...")
        # Ждем 30 секунд, может деплой его создаст
        time.sleep(30)
        # И пробуем еще раз проверить существование
        result = subprocess.run(
            ["docker", "inspect", target_container],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Container {target_container} still does not exist")
            print("❌ Rollback failed: cannot find container")
            sys.exit(1)
        else:
            subprocess.run(
                ["docker", "start", target_container],
                cwd=WORKDIR,
                check=True,
            )

    # 2. healthcheck
    if not wait_health(
        target_container,
        port,
        healthcheck,
    ):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["services"][service]["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    print("✅ rollback completed")


if __name__ == "__main__":
    main()
