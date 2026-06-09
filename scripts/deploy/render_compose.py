import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

active = state.get("active", "blue")
inactive = "green" if active == "blue" else "blue"

blue_green = {"gateway"}

yaml = ["services:"]

# gateway blue/green
if "gateway-blue" in state:
    yaml.append("  gateway-blue:")
    yaml.append(f"    image: {state['gateway-blue']}")

if "gateway-green" in state:
    yaml.append("  gateway-green:")
    yaml.append(f"    image: {state['gateway-green']}")

# остальные сервисы
for service, image in state.items():

    if service in ["active", "gateway-blue", "gateway-green", "stable"]:
        continue

    yaml.append(f"  {service}:")
    yaml.append(f"    image: {image}")

print("\n".join(yaml))
