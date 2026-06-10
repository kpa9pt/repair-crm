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

gateway = state["services"]["gateway"]

active = gateway["active"]
inactive = "green" if active == "blue" else "blue"


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service == "gateway":
        # обновляем только inactive сторону
        gateway[inactive]["image"] = build_image(service, sha)
    else:
        state["services"][service]["image"] = build_image(service, sha)


print(json.dumps(state, indent=2))
