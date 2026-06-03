import json

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

active = state.get("active", "blue")
inactive = "green" if active == "blue" else "blue"


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service == "gateway":
        # обновляем только inactive сторону
        state[f"gateway-{inactive}"] = build_image(service, sha)
    else:
        state[service] = build_image(service, sha)


print(json.dumps(state, indent=2))
