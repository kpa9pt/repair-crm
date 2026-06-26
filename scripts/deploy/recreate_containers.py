import json
import os
import base64
import subprocess


def main():
    plan_raw = os.environ.get("COMPOSE_PLAN", "[]")
    deploy_plan = json.loads(base64.b64decode(plan_raw).decode())

    if not deploy_plan:
        print("✅ No compose changes to recreate")
        return

    print(f"🔍 Compose plan: {deploy_plan}")

    for service in deploy_plan:
        print(f"🔄 Processing {service} due to compose changes...")

        # Проверяем, есть ли сервис в state
        with open("state.json") as f:
            state = json.load(f)

        service_state = state.get("services", {}).get(service, {})
        strategy = service_state.get("strategy", "single")

        if strategy == "blue-green":
            # Для blue-green пересоздаем оба контейнера
            containers = [f"{service}-blue", f"{service}-green"]
            print(f"   Blue-green service, recreating: {containers}")
        else:
            containers = [service]
            print(f"   Single service, recreating: {containers}")

        for container in containers:
            print(f"   🔄 Recreating {container}...")
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "--force-recreate", container],
                cwd="/home/deploy/repair-crm",
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"   ✅ {container} recreated")
            else:
                print(f"   ❌ Failed to recreate {container}: {result.stderr}")


if __name__ == "__main__":
    main()
