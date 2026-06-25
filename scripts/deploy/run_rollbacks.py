import json
import os
import base64
import subprocess


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    failed = decision.get("failed", [])

    if not failed:
        print("✅ no rollback required")
        return

    server_user = os.environ["SERVER_USER"]
    server_ip = os.environ["SERVER_IP"]

    for service in failed:

        print(f"🔄 rollback: {service}")

        subprocess.run(
            [
                "ssh",
                f"{server_user}@{server_ip}",
                f"ROLLBACK_SERVICE={service} python3 -",
            ],
            stdin=open("scripts/rollback.py", "rb"),
            check=True,
        )

    print("✅ rollback engine finished")


if __name__ == "__main__":
    main()
