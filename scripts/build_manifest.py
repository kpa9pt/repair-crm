import json
import os
from shared.service_registry import get_services

github_sha = os.environ.get("GITHUB_SHA", "")
changed_services_json = os.environ.get("CHANGED_SERVICES", "[]")

try:
    changed_services = json.loads(changed_services_json)
except json.JSONDecodeError:
    changed_services = []

manifest = {}

for service in get_services():
    if service in changed_services:
        manifest[service] = github_sha

print(json.dumps(manifest))
