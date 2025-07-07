from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime, timedelta
from logger import log
import hashlib

app = FastAPI()

short_urls = {}
click_stats = {}

class ShortenRequest(BaseModel):
    url: HttpUrl
    validity: Optional[int] = 30

class ShortenResponse(BaseModel):
    shortLink: str
    expiry: datetime

def generate_shortcode(url: str) -> str:
    hash_input = (url + str(datetime.utcnow().timestamp())).encode()
    full_hash = hashlib.sha256(hash_input).hexdigest()
    return full_hash[:6]

@app.post("/shorturls", response_model=ShortenResponse, status_code=201)
async def create_short_url(data: ShortenRequest, request: Request):
    try:
        shortcode = generate_shortcode(str(data.url))
        while shortcode in short_urls:
            shortcode = generate_shortcode(str(data.url))

        expiry = datetime.utcnow() + timedelta(minutes=data.validity or 30)

        short_urls[shortcode] = {
            "url": str(data.url),
            "created": datetime.utcnow(),
            "expiry": expiry,
            "clicks": 0
        }

        return {
            "shortLink": f"http://{request.client.host}:{request.url.port}/{shortcode}",
            "expiry": expiry
        }

    except Exception as e:
        await log("backend", "fatal", "handler", f"Unexpected error in create_short_url: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/{shortcode}")
async def redirect_to_url(shortcode: str, request: Request):
    try:
        entry = short_urls.get(shortcode)
        if not entry:
            await log("backend", "error", "route", f"Shortcode not found: {shortcode}")
            raise HTTPException(status_code=404, detail="Shortcode not found")

        if datetime.utcnow() > entry["expiry"]:
            await log("backend", "warn", "route", f"Shortcode expired: {shortcode}")
            raise HTTPException(status_code=410, detail="Shortcode expired")

        entry["clicks"] += 1
        click_stats.setdefault(shortcode, []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "referer": str(request.headers.get("referer", "unknown")),
            "ip": request.client.host
        })

        return RedirectResponse(url=entry["url"])

    except HTTPException as http_ex:
        raise http_ex  # Already logged
    except Exception as e:
        await log("backend", "fatal", "route", f"Unexpected error in redirect: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/shorturls/stats/{shortcode}")
async def get_url_stats(shortcode: str):
    try:
        entry = short_urls.get(shortcode)
        if not entry:
            await log("backend", "error", "repository", f"Stats not found: {shortcode}")
            raise HTTPException(status_code=404, detail="Shortcode not found")

        return {
            "url": entry["url"],
            "created": entry["created"],
            "expiry": entry["expiry"],
            "clicks": entry["clicks"],
            "interactions": click_stats.get(shortcode, [])
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        await log("backend", "fatal", "repository", f"Unexpected error in stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
