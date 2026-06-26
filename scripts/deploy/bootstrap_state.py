import sys
from pathlib import Path
import json
import os
import requests
from shared.service_registry import get_services, get_service_config, is_blue_green


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Добавляем корень проекта в PYTHONPATH

OWNER = "kpa9pt"

TOKEN = os.environ.get("GHCR_READ_TOKEN")
if not TOKEN:
    print("ERROR: GHCR_READ_TOKEN not set", file=sys.stderr)
    sys.exit(1)

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN), file=sys.stderr)
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None, file=sys.stderr)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

DEPLOY_ID = os.getenv("DEPLOY_ID", "bootstrap")


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    print(f"\n--- SERVICE: {service} ---", file=sys.stderr)
    print("URL:", url, file=sys.stderr)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code, file=sys.stderr)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500], file=sys.stderr)

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions), file=sys.stderr)

    for version in versions:
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags, file=sys.stderr)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


# Создаем state
state = {"deploy_id": DEPLOY_ID, "services": {}}

for service in get_services():
    cfg = get_service_config(service)
    image = latest_image(service)

    if is_blue_green(service):
        state["services"][service] = {
            "strategy": "blue-green",
            "active": "blue",
            "port": cfg.get("port", 8000),
            "healthcheck": cfg.get("healthcheck", "/health"),
            "rollback_locked": False,
            "blue": {"image": image},
            "green": {"image": image},
        }
    else:
        state["services"][service] = {
            "strategy": "single",
            "image": image,
            "rollback_locked": False,
        }

print(json.dumps(state, indent=2))
