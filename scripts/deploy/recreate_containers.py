import json
import os
import base64
import subprocess


def main():
    plan_raw = os.environ.get("DEPLOY_PLAN", "[]")
    deploy_plan = json.loads(base64.b64decode(plan_raw).decode())

    if not deploy_plan:
        print("No services to recreate")
        return

    for service in deploy_plan:
        print(f"🔄 Recreating {service}...")
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--force-recreate", service],
            cwd="/home/deploy/repair-crm",
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"✅ {service} recreated")
        else:
            print(f"❌ Failed to recreate {service}: {result.stderr}")


if __name__ == "__main__":
    main()
