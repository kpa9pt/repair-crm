import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

yaml = ["services:"]

for service_name, config in state["services"].items():

    strategy = config["strategy"]

    if strategy == "blue-green":

        yaml.append(f"  {service_name}-blue:")
        yaml.append(f"    image: {config['blue']['image']}")

        yaml.append(f"  {service_name}-green:")
        yaml.append(f"    image: {config['green']['image']}")

    elif strategy == "single":

        yaml.append(f"  {service_name}:")
        yaml.append(f"    image: {config['image']}")

print("\n".join(yaml))
