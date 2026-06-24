import json

STATE_FILE = "state.json"


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def main():
    state = load_state()

    deploy_plan = []

    for service_name, service in state["services"].items():

        if service.get("strategy") != "blue-green":
            continue

        active = service["active"]
        inactive = "green" if active == "blue" else "blue"

        active_image = service[active]["image"]
        inactive_image = service[inactive]["image"]

        if active_image != inactive_image:
            deploy_plan.append(service_name)

    print(json.dumps(deploy_plan, indent=2))


if __name__ == "__main__":
    main()
