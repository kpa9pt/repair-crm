import sys
from pathlib import Path
from shared.service_registry import get_services, get_service_config

sys.path.insert(0, str(Path(__file__).parent.parent))

patterns = set()

for service in get_services():
    cfg = get_service_config(service)
    for path in cfg.get("paths", [f"services/{service}/**"]):
        patterns.add(path)

# Выводим как YAML список для tj-actions/changed-files
for pattern in sorted(patterns):
    print(pattern)
