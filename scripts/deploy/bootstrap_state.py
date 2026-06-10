import json
import os
import requests

OWNER = "kpa9pt"

SERVICES = [
    "gateway",
    "nginx",
    "certbot",
    "migrations",
]

TOKEN = os.environ["GHCR_READ_TOKEN"]

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN))
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None)

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

    print(f"\n--- SERVICE: {service} ---")
    print("URL:", url)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500])

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions))

    for version in versions:
        # ❗ оставили как у тебя было (НЕ трогаем логику)
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "deploy_id": DEPLOY_ID,
    "services": {
        "gateway": {
            "strategy": "blue-green",
            "active": "blue",
        }
    },
}

gateway_image = latest_image("gateway")

state["services"]["gateway"]["blue"] = {"image": gateway_image}
state["services"]["gateway"]["green"] = {"image": gateway_image}

for service in [
    "nginx",
    "certbot",
    "migrations",
]:
    state["services"][service] = {
        "strategy": "single",
        "image": latest_image(service),
    }

print(json.dumps(state, indent=2))
