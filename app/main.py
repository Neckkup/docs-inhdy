"""เว็บจัดการเอกสาร docs.inhdy.com — login, สั่งเผยแพร่ artifact, ดูรายการเอกสาร

งานหนัก (ดึง artifact, แปลง, deploy) ทำโดย worker/worker.py บนเครื่อง host
แอปนี้แค่เขียนคิวลง SQLite แล้วอ่านสถานะกลับมา
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from common import DEFAULT_FORMAT, DOMAIN, FORMATS, LINK_RE, name_problem

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("DB_PATH", "/data/app.db"))
SITES = Path(os.environ.get("SITES_DIR", "/srv/sites"))
SECRET = os.environ.get("APP_SECRET", "").encode()
APP_ORIGIN = os.environ.get("APP_ORIGIN", "https://docs.app.inhdy.com")
AI_ENABLED = bool(os.environ.get("LITELLM_MODEL") or os.environ.get("LITELLM_ENABLED"))
COOKIE = "__Host-docs_session"
NAME_RE_USER = re.compile(r"^[a-z0-9._-]{2,32}$")
SESSION_TTL = 14 * 24 * 3600

if len(SECRET) < 32:
    raise SystemExit("ต้องตั้ง APP_SECRET (อย่างน้อย 32 ตัวอักษร) ใน .env")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
tpl = Jinja2Templates(directory=HERE / "templates")
tpl.env.globals.update(DOMAIN=DOMAIN, FORMATS=FORMATS, AI_ENABLED=AI_ENABLED)

TH = timezone(timedelta(hours=7))   # เวลาไทย (ไม่มี DST)


def th_time(utc: str | None) -> str:
    """'2026-11-17 07:21:27' (UTC จาก SQLite) -> '17/11/2026 14:21'"""
    if not utc:
        return ""
    try:
        dt = datetime.strptime(utc, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return utc
    return dt.astimezone(TH).strftime("%d/%m/%Y %H:%M")


tpl.env.filters["th"] = th_time


# ---------------------------------------------------------------- db
@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


with db() as _c:
    _c.executescript((HERE / "schema.sql").read_text())


# ---------------------------------------------------------------- passwords (stdlib scrypt)
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(got.hex(), h)
    except ValueError:
        return False


# ---------------------------------------------------------------- sessions (HMAC-signed cookie)
def _sign(data: str) -> str:
    return hmac.new(SECRET, data.encode(), hashlib.sha256).hexdigest()


def make_session(user_id: int, pw_hash: str) -> str:
    # ผูกกับ hash รหัสผ่าน: เปลี่ยนรหัสผ่าน = session เก่าใช้ไม่ได้
    exp = int(time.time()) + SESSION_TTL
    body = f"{user_id}.{exp}.{_sign(pw_hash)[:16]}"
    return f"{body}.{_sign(body)}"


def current_user(request: Request):
    raw = request.cookies.get(COOKIE, "")
    parts = raw.split(".")
    if len(parts) != 4:
        return None
    body, sig = ".".join(parts[:3]), parts[3]
    if not hmac.compare_digest(_sign(body), sig) or int(parts[1]) < time.time():
        return None
    with db() as con:
        u = con.execute("SELECT * FROM users WHERE id = ?", (int(parts[0]),)).fetchone()
    if not u or not hmac.compare_digest(_sign(u["pw_hash"])[:16], parts[2]):
        return None
    return u


def csrf_token(request: Request) -> str:
    return _sign("csrf:" + request.cookies.get(COOKIE, ""))[:32]


def require_user(request: Request):
    u = current_user(request)
    if not u:
        raise HTTPException(303, headers={"Location": "/login"})
    return u


def check_post(request: Request, token: str):
    # ซับโดเมน *.docs.inhdy.com เป็น "same-site" กับแอปนี้ SameSite จึงกันไม่พอ: ตรวจ Origin + token
    origin = request.headers.get("origin")
    if origin and origin != APP_ORIGIN:
        raise HTTPException(403, "origin ไม่ถูกต้อง")
    if not hmac.compare_digest(token or "", csrf_token(request)):
        raise HTTPException(403, "ฟอร์มหมดอายุ ลองโหลดหน้าใหม่")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "frame-ancestors 'none'; form-action 'self'")
    return resp


# ---------------------------------------------------------------- login
_fails: dict[str, list[float]] = {}


def _throttled(key: str) -> bool:
    now = time.time()
    _fails[key] = [t for t in _fails.get(key, []) if now - t < 900]
    return len(_fails[key]) >= 8


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", 303)
    return tpl.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    origin = request.headers.get("origin")
    if origin and origin != APP_ORIGIN:
        raise HTTPException(403)
    ip = request.client.host if request.client else "?"
    key = f"{ip}|{username.lower()}"
    if _throttled(key):
        return tpl.TemplateResponse(request, "login.html",
                                    {"error": "ลองผิดหลายครั้งเกินไป รอ 15 นาที"}, status_code=429)
    with db() as con:
        u = con.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if not u or not check_password(password, u["pw_hash"]):
        _fails.setdefault(key, []).append(time.time())
        return tpl.TemplateResponse(request, "login.html",
                                    {"error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, status_code=401)
    _fails.pop(key, None)
    resp = RedirectResponse("/", 303)
    resp.set_cookie(COOKIE, make_session(u["id"], u["pw_hash"]), max_age=SESSION_TTL,
                    httponly=True, secure=True, samesite="lax", path="/")
    return resp


@app.post("/logout")
def logout(request: Request, csrf: str = Form("")):
    check_post(request, csrf)
    resp = RedirectResponse("/login", 303)
    resp.delete_cookie(COOKIE, path="/", secure=True, httponly=True)
    return resp


# ---------------------------------------------------------------- projects
def _title_of(name: str) -> str | None:
    try:
        head = (SITES / name / "index.html").read_text(encoding="utf-8", errors="replace")[:20000]
    except OSError:
        return None
    m = re.search(r"<title>([^<]*)</title>", head, re.I)
    return m.group(1).strip() if m else None


def list_projects():
    with db() as con:
        rows = {r["name"]: dict(r) for r in con.execute(
            "SELECT p.*, u.username AS owner FROM projects p LEFT JOIN users u ON u.id = p.owner_id")}
    out = []
    for d in sorted(SITES.iterdir()) if SITES.exists() else []:
        if not d.is_dir() or d.name.startswith((".", "_")) or name_problem(d.name):
            continue
        r = rows.get(d.name, {"name": d.name, "owner": None, "owner_id": None, "kind": None,
                              "format": None, "source_url": None})
        r["title"] = _title_of(d.name) or r.get("title") or d.name
        r["mtime"] = datetime.fromtimestamp(d.stat().st_mtime, TH).strftime("%d/%m/%Y %H:%M")
        r["mtime_sort"] = d.stat().st_mtime
        out.append(r)
    out.sort(key=lambda r: r["mtime_sort"], reverse=True)
    return out


def can_manage(user, name: str) -> bool:
    """เจ้าของหรือแอดมินเท่านั้นที่ทับ/ลบโปรเจกต์ที่มีอยู่ได้ (โปรเจกต์เก่าที่ไม่มีเจ้าของ = แอดมิน)"""
    if user["is_admin"]:
        return True
    with db() as con:
        r = con.execute("SELECT owner_id FROM projects WHERE name = ?", (name,)).fetchone()
    return bool(r and r["owner_id"] == user["id"])


def name_status(user, name: str) -> dict:
    if p := name_problem(name):
        return {"ok": False, "msg": p}
    exists = (SITES / name).is_dir()
    with db() as con:
        pending = con.execute(
            "SELECT 1 FROM jobs WHERE name = ? AND status IN ('queued','running','review','approved')",
            (name,)).fetchone()
    if pending:
        return {"ok": False, "msg": "มีงานของชื่อนี้กำลังทำอยู่"}
    if exists and not can_manage(user, name):
        return {"ok": False, "msg": "ชื่อนี้ถูกใช้แล้ว"}
    if exists:
        return {"ok": True, "update": True, "msg": "มีอยู่แล้ว — จะอัปเดตทับของเดิม"}
    return {"ok": True, "update": False, "msg": "ว่าง ใช้ได้"}


# ---------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request, name: str = "", link: str = ""):
    user = require_user(request)
    with db() as con:
        jobs = con.execute(
            "SELECT j.*, u.username FROM jobs j JOIN users u ON u.id = j.user_id "
            "ORDER BY j.id DESC LIMIT 15").fetchall()
    return tpl.TemplateResponse(request, "home.html", {
        "user": user, "csrf": csrf_token(request), "projects": list_projects(),
        "jobs": jobs, "prefill_name": name, "prefill_link": link, "error": None,
        "can_manage": lambda n: can_manage(user, n),
    })


@app.get("/api/name")
def api_name(request: Request, name: str):
    user = require_user(request)
    return name_status(user, name.strip().lower())


@app.post("/publish")
def publish(request: Request, csrf: str = Form(""), link: str = Form(...), name: str = Form(...),
            format: str = Form("auto")):
    user = require_user(request)
    check_post(request, csrf)
    link, name = link.strip(), name.strip().lower()
    err = None
    if not LINK_RE.match(link):
        err = "ลิงก์ต้องเป็น https://claude.ai/artifact/…"
    elif format not in FORMATS or (format == "ai" and not AI_ENABLED):
        err = "รูปแบบไม่ถูกต้อง"
    elif not (st := name_status(user, name))["ok"]:
        err = f"ซับโดเมน: {st['msg']}"
    if err:
        with db() as con:
            jobs = con.execute("SELECT j.*, u.username FROM jobs j JOIN users u ON u.id = j.user_id "
                               "ORDER BY j.id DESC LIMIT 15").fetchall()
        return tpl.TemplateResponse(request, "home.html", {
            "user": user, "csrf": csrf_token(request), "projects": list_projects(), "jobs": jobs,
            "prefill_name": name, "prefill_link": link, "error": err,
            "can_manage": lambda n: can_manage(user, n)}, status_code=400)
    with db() as con:
        cur = con.execute("INSERT INTO jobs (user_id, action, name, source_url, format) "
                          "VALUES (?, 'publish', ?, ?, ?)", (user["id"], name, link, format))
    return RedirectResponse(f"/jobs/{cur.lastrowid}", 303)


@app.post("/delete")
def delete(request: Request, csrf: str = Form(""), name: str = Form(...)):
    user = require_user(request)
    check_post(request, csrf)
    if name_problem(name) or not (SITES / name).is_dir() or not can_manage(user, name):
        raise HTTPException(403, "ลบโปรเจกต์นี้ไม่ได้")
    with db() as con:
        cur = con.execute("INSERT INTO jobs (user_id, action, name) VALUES (?, 'delete', ?)",
                          (user["id"], name))
    return RedirectResponse(f"/jobs/{cur.lastrowid}", 303)


def _job(user, job_id: int):
    with db() as con:
        j = con.execute("SELECT j.*, u.username FROM jobs j JOIN users u ON u.id = j.user_id "
                        "WHERE j.id = ?", (job_id,)).fetchone()
    if not j:
        raise HTTPException(404)
    return j


def _job_json(j) -> dict:
    return {"id": j["id"], "status": j["status"], "kind": j["kind"], "title": j["title"],
            "log": j["log"], "warnings": json.loads(j["warnings"] or "[]"),
            "url": f"https://{j['name']}.{DOMAIN}/" if j["action"] == "publish" else None}


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: int):
    user = require_user(request)
    j = _job(user, job_id)
    return tpl.TemplateResponse(request, "job.html", {
        "user": user, "csrf": csrf_token(request), "job": j, "data": _job_json(j),
        "mine": j["user_id"] == user["id"] or user["is_admin"]})


@app.get("/api/jobs/{job_id}")
def job_api(request: Request, job_id: int):
    user = require_user(request)
    return JSONResponse(_job_json(_job(user, job_id)))


@app.post("/jobs/{job_id}/{decision}")
def job_decide(request: Request, job_id: int, decision: str, csrf: str = Form("")):
    user = require_user(request)
    check_post(request, csrf)
    j = _job(user, job_id)
    if j["user_id"] != user["id"] and not user["is_admin"]:
        raise HTTPException(403)
    new = {"approve": "approved", "cancel": "cancelled"}.get(decision)
    if not new:
        raise HTTPException(404)
    with db() as con:
        # cancel ได้ทั้งตอนรอคิวและตอนรอตรวจ, approve ได้เฉพาะตอนรอตรวจ
        allowed = ("review",) if new == "approved" else ("queued", "review")
        con.execute(f"UPDATE jobs SET status = ?, updated_at = datetime('now') WHERE id = ? "
                    f"AND status IN ({','.join('?' * len(allowed))})", (new, job_id, *allowed))
    return RedirectResponse(f"/jobs/{job_id}", 303)


@app.get("/healthz")
def healthz():
    return {"ok": True}


# พิมพ์ DEFAULT_FORMAT ไว้ให้ template ใช้อธิบาย "อัตโนมัติ"
tpl.env.globals["DEFAULT_FORMAT"] = DEFAULT_FORMAT
