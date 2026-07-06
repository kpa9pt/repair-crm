import json
import sys
import os
import base64
import subprocess
from pathlib import Path
import asyncio  # ← ДОБАВИТЬ


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]
    return subprocess.run(cmd).returncode == 0


async def wait_health_async(container, port, health, retries=30, delay=2):
    """Асинхронная версия wait_health"""
    for i in range(retries):
        # healthcheck синхронный, запускаем в отдельном потоке
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, healthcheck, container, port, health)
        if ok:
            return True
        print(f"retry: {i + 1}/{retries}", file=sys.stderr)
        await asyncio.sleep(delay)
    return False


async def check_service(service: str, state: dict) -> dict:
    """Проверка одного сервиса (smoke + soak)"""
    print(f"🔍 post-switch verify: {service}", file=sys.stderr)

    s = state["services"][service]
    active = s["active"]
    port = s.get("port", 8000)
    health = s.get("healthcheck", "/health")
    container = f"{service}-{active}"

    # Phase 1: Smoke test
    print(f"phase 1 smoke: {service}", file=sys.stderr)
    if not await wait_health_async(container, port, health):
        return {"service": service, "status": "failed"}

    # Phase 2: Soak sleep (для всех сервисов одновременно!)
    print(f"phase 2 soak sleep: {service} (60s)", file=sys.stderr)
    # Ждем 60 секунд, но это ожидание будет параллельным для всех сервисов
    # ⚠️ ДОБАВИТЬ ЭТУ СТРОКУ!
    await asyncio.sleep(60)  # ← ВОТ ОНА

    # Phase 3: Soak verify
    print(f"phase 3 soak verify: {service}", file=sys.stderr)
    if await wait_health_async(container, port, health):
        return {"service": service, "status": "passed"}
    else:
        return {"service": service, "status": "failed"}


async def main_async():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        state = json.load(f)

    # Запускаем проверку всех сервисов параллельно
    tasks = [check_service(service, state) for service in deploy_plan]
    results = await asyncio.gather(*tasks)

    # Собираем результат
    passed = [r["service"] for r in results if r["status"] == "passed"]
    failed = [r["service"] for r in results if r["status"] == "failed"]

    print(json.dumps({"passed": passed, "failed": failed}))


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
