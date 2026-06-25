import json
import os

SERVICES = ["gateway", "migrations", "nginx", "certbot", "watchdog"]

github_sha = os.environ.get("GITHUB_SHA", "")

manifest = {}

for service in SERVICES:
    changed = os.environ.get(f"CHANGED_{service.upper()}", "false")

    if changed == "true":
        manifest[service] = github_sha

print(json.dumps(manifest))
