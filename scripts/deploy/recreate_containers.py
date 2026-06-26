import json
import os
import sys
import base64
import subprocess
from pathlib import Path


def find_state_file():
    """Ищет state.json в возможных местах"""
    possible_paths = [
        Path("state.json"),  # текущая директория (раннер или корень проекта)
        Path("/home/deploy/repair-crm/state/state.json"),  # абсолютный путь на сервере
        Path.home() / "repair-crm" / "state" / "state.json",  # через home
    ]

    for path in possible_paths:
        if path.exists():
            print(f"✅ Found state.json at: {path}", file=sys.stderr)
            return path

    print(f"❌ state.json not found. Tried: {possible_paths}", file=sys.stderr)
    return None


def main():
    plan_raw = os.environ.get("COMPOSE_PLAN", "[]")
    if not plan_raw:
        print("✅ No COMPOSE_PLAN provided")
        return

    try:
        deploy_plan = json.loads(base64.b64decode(plan_raw).decode())
    except Exception as e:
        print(f"❌ Failed to decode COMPOSE_PLAN: {e}")
        sys.exit(1)

    if not deploy_plan:
        print("✅ No compose changes to recreate")
        return

    print(f"🔍 Compose plan: {deploy_plan}")

    # Ищем state.json
    state_path = find_state_file()
    if not state_path:
        print("❌ Cannot proceed without state.json")
        sys.exit(1)

    with open(state_path) as f:
        state = json.load(f)

    # Путь к docker-compose.yml
    compose_dir = Path("/home/deploy/repair-crm")
    if not compose_dir.exists():
        compose_dir = Path(".")  # fallback

    for service in deploy_plan:
        print(f"🔄 Processing {service} due to compose changes...")

        # Проверяем, есть ли такой сервис в state
        if service in state.get("services", {}):
            strategy = state["services"][service].get("strategy", "single")

            if strategy == "blue-green":
                containers = [f"{service}-blue", f"{service}-green"]
                print(f"   Blue-green service, recreating: {containers}")
            else:
                containers = [service]
                print(f"   Single service, recreating: {containers}")
        else:
            # Возможно, это прямой контейнер (gateway-blue)
            if service in state.get("services", {}):
                containers = [service]
                print(f"   Direct service, recreating: {containers}")
            else:
                print(f"⚠️  Service {service} not found in state, skipping")
                continue

        for container in containers:
            print(f"   🔄 Recreating {container}...")
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "--force-recreate", container],
                cwd=str(compose_dir),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"   ✅ {container} recreated")
            else:
                print(f"   ❌ Failed to recreate {container}: {result.stderr}")


if __name__ == "__main__":
    main()
