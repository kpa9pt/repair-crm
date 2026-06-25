import json
import os

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"

DEPLOY_ID = os.getenv("DEPLOY_ID")


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

state["deploy_id"] = DEPLOY_ID


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service not in state["services"]:
        state["services"][service] = {"strategy": "single", "rollback_locked": False}

    service_state = state["services"][service]

    image = build_image(service, sha)

    if service_state["strategy"] == "blue-green":

        active = service_state["active"]
        inactive = "green" if active == "blue" else "blue"

        service_state[inactive]["image"] = image

    else:

        service_state["image"] = image


print(json.dumps(state, indent=2))
