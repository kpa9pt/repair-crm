import json


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")

    deploy_plan = list(changes.keys())

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()
