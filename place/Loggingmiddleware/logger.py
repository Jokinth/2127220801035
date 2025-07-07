# logger.py
import httpx

LOG_API_URL = "http://20.244.56.144/evaluation-service/logs"

VALID_STACKS = {"backend"}
VALID_LEVELS = {"debug", "info", "warn", "error", "fatal"}
VALID_PACKAGES = {
    "cache", "controller", "cron_job", "db", "domain",
    "handler", "repository", "route", "service"
}

async def log(stack: str, level: str, package: str, message: str):
    if stack not in VALID_STACKS:
        print(f"[LOGGING ERROR] Invalid stack: {stack}")
        return
    if level not in VALID_LEVELS:
        print(f"[LOGGING ERROR] Invalid level: {level}")
        return
    if package not in VALID_PACKAGES:
        print(f"[LOGGING ERROR] Invalid package: {package}")
        return

    payload = {
        "stack": stack,
        "level": level,
        "package": package,
        "message": message
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(LOG_API_URL, json=payload)
            if res.status_code != 200:
                print(f"[LOGGING ERROR] API returned {res.status_code}: {res.text}")
            else:
                print("[LOGGING SUCCESS] Log sent successfully.")
    except Exception as e:
        print(f"[LOGGING ERROR] Exception while logging: {e}")
