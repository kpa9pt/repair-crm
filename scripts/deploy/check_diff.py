import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")
    state = load("state.json")

    deploy_plan = []

    for service in changes.keys():

        service_state = state["services"].get(service)

        if not service_state:
            print(
                f"skip {service}: not found in state",
                file=sys.stderr,
            )
            continue

        if service_state.get("strategy") != "blue-green":
            print(
                f"skip {service}: strategy={service_state.get('strategy')}",
                file=sys.stderr,
            )
            continue

        deploy_plan.append(service)

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()
