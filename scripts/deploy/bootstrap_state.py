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

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    versions = response.json()

    for version in versions:
        tags = version["metadata"]["container"]["tags"]

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]

            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "active": "blue",
    "stable": "blue",
}

gateway_image = latest_image("gateway")

state["gateway-blue"] = gateway_image
state["gateway-green"] = gateway_image

for service in [
    "nginx",
    "certbot",
    "migrations",
]:
    state[service] = latest_image(service)

print(json.dumps(state, indent=2))
