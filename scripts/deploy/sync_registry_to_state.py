# scripts/deploy/sync_registry_to_state.py
import json
import yaml


def sync_registry_to_state():
    # Загружаем registry
    with open("service-registry.yml") as f:
        registry = yaml.safe_load(f)

    # Загружаем state
    with open("state.json") as f:
        state = json.load(f)

    # Проходим по всем сервисам в registry
    for service_name, config in registry["services"].items():
        if service_name not in state["services"]:
            print(f"🆕 Adding new service: {service_name}")

            strategy = config.get("strategy", "single")

            if strategy == "blue-green":
                state["services"][service_name] = {
                    "strategy": "blue-green",
                    "active": "blue",
                    "port": config.get("port", 8000),
                    "healthcheck": config.get("healthcheck", "/health"),
                    "rollback_locked": False,
                    "compose_hash": "",
                    "blue": {"image": ""},
                    "green": {"image": ""},
                }
            else:
                state["services"][service_name] = {
                    "strategy": "single",
                    "image": "",
                    "rollback_locked": False,
                    "compose_hash": "",
                }

    # Сохраняем state
    with open("state.json", "w") as f:
        json.dump(state, f, indent=2)

    print("✅ State synced with registry")


if __name__ == "__main__":
    sync_registry_to_state()
