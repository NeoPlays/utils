from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from scanner import scan_ips
from storage import (
    get_all,
    get_config,
    save_config,
    update_ip_meta,
    update_scan_results,
)

scheduler = BackgroundScheduler()


def run_scan():
    cfg = get_config()
    ips = []
    for r in cfg.get("ranges", []):
        if r.get("base"):
            ips += [f"{r['base']}.{i}" for i in range(r["start"], r["end"] + 1)]
    if not ips:
        return
    results = scan_ips(ips)
    update_scan_results(results)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_scan, "cron", hour=3, minute=0, id="daily_scan")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="IP Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="/static"), name="static")


@app.get("/", response_class=FileResponse)
def index():
    return FileResponse("/static/index.html")


@app.get("/api/data")
def api_data():
    return get_all()


class RangeItem(BaseModel):
    base: str
    start: int
    end: int


class ConfigPayload(BaseModel):
    ranges: list[RangeItem]


@app.post("/api/config")
def api_config(payload: ConfigPayload):
    save_config([r.model_dump() for r in payload.ranges])
    return {"ok": True}


@app.post("/api/scan")
def api_scan():
    cfg = get_config()
    ips = []
    for r in cfg.get("ranges", []):
        if r.get("base"):
            ips += [f"{r['base']}.{i}" for i in range(r["start"], r["end"] + 1)]
    if not ips:
        raise HTTPException(400, "No IP ranges configured")
    results = scan_ips(ips)
    update_scan_results(results)
    return get_all()


class MetaPayload(BaseModel):
    comment: str | None = None
    label: str | None = None


@app.patch("/api/ip/{ip}")
def api_update_ip(ip: str, payload: MetaPayload):
    ip = ip.replace("-", ".")  # allow dashes in URL path
    update_ip_meta(ip, payload.comment, payload.label)
    return {"ok": True}
