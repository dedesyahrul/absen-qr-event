import io
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import List

import qrcode
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal, check_database, get_db, init_database
from .models import AttendanceLog, Event, Participant, Table, User, Vendor
from .security import create_token, decode_token, hash_password, verify_password

settings = get_settings()
app = FastAPI(title="Gatherly — Event Registration & Check-in API", version="2.0.0")
_origins = settings.cors_origin_list
_is_wildcard = _origins == ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=not _is_wildcard, allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer(auto_error=False)

# ─── Pydantic Schemas ──────────────────────────────────────────────────────────

class LoginInput(BaseModel):
    email: str
    password: str

class EventInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = ""
    event_date: str
    start_time: str = "08:00"
    end_time: str = "17:00"
    location: str = ""
    status: str = "active"

class VendorInput(BaseModel):
    company_name: str = Field(min_length=2, max_length=180)
    category: str = "General"
    contact_name: str = ""
    phone: str = ""
    email: str = ""

class ParticipantInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    vendor_id: int | None = None
    table_id: int | None = None
    seat_number: str | None = None
    position: str = ""
    phone: str = ""
    email: str = ""

class ScanInput(BaseModel):
    token: str = Field(min_length=4)
    notes: str = ""

class ManualCheckinInput(BaseModel):
    participant_id: int
    notes: str = ""

class UndoCheckinInput(BaseModel):
    participant_id: int
    notes: str = ""

class TableInput(BaseModel):
    table_number: str = Field(min_length=1, max_length=20)
    table_label: str = ""
    capacity: int = 8
    zone: str = "Regular"

class TableBulkInput(BaseModel):
    prefix: str = Field(min_length=1, max_length=10)
    count: int = Field(ge=1, le=100)
    capacity: int = 8
    zone: str = "Regular"

class SeatAssignInput(BaseModel):
    table_id: int | None = None
    seat_number: str | None = None

class ImportConfirmInput(BaseModel):
    rows: list[dict]
    duplicate_action: str = "skip"

class UserInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=100)
    role: str = "operator"

class UserUpdateInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    role: str = "operator"
    is_active: bool = True

class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=100)

class EventCopyInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    event_date: str
    copy_vendors: bool = True
    copy_tables: bool = True
    copy_participants: bool = False
    status: str = "active"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    is_active: bool = True

# ─── Helpers ────────────────────────────────────────────────────────────────────

def serialize_event(event: Event, db: Session) -> dict:
    total = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event.id)) or 0
    checked = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event.id, Participant.check_in_at.is_not(None))) or 0
    return {"id": event.id, "name": event.name, "description": event.description, "event_date": event.event_date, "start_time": event.start_time, "end_time": event.end_time, "location": event.location, "status": event.status, "total_participants": total, "checked_in": checked}


def serialize_participant(item: Participant, db: Session) -> dict:
    vendor = db.get(Vendor, item.vendor_id) if item.vendor_id else None
    table = db.get(Table, item.table_id) if item.table_id else None
    return {
        "id": item.id, "name": item.name, "position": item.position,
        "phone": item.phone, "email": item.email, "qr_token": item.qr_token,
        "attendance_status": item.attendance_status,
        "check_in_at": item.check_in_at, "check_in_method": item.check_in_method,
        "check_out_at": item.check_out_at,
        "vendor_id": item.vendor_id, "company_name": vendor.company_name if vendor else "Unassigned",
        "table_id": item.table_id,
        "table_number": table.table_number if table else None,
        "table_zone": table.zone if table else None,
        "seat_number": item.seat_number,
    }


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_token(credentials.credentials)
        user = db.get(User, int(payload["sub"]))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return user


ROLE_HIERARCHY = {"superadmin": 4, "admin": 3, "operator": 2, "viewer": 1}

def require_role(minimum_role: str):
    def checker(user: User = Depends(current_user)):
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_level < required_level:
            raise HTTPException(status_code=403, detail="Akses ditolak. Role tidak mencukupi.")
        return user
    return checker


def generate_qr_image(token: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def safe_filename(name: str) -> str:
    safe = re.sub(r'[^\w\s-]', '', name.strip())
    safe = re.sub(r'[\s]+', '_', safe)
    return safe or "item"


def _styled_workbook(title: str, headers: list[str]) -> tuple[Workbook, any]:
    wb = Workbook()
    ws = wb.active
    ws.title = title
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="102A43", end_color="102A43", fill_type="solid")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    return wb, ws


def _wb_to_bytes(wb: Workbook) -> io.BytesIO:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─── Startup / Seed ────────────────────────────────────────────────────────────

import time

@app.on_event("startup")
def startup() -> None:
    retries = 5
    while retries > 0:
        try:
            init_database()
            break
        except Exception as e:
            retries -= 1
            print(f"Database connection failed, retrying... ({retries} left)")
            time.sleep(3)
            
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "admin@example.com")):
            db.add(User(name="Super Admin", email="admin@example.com", password_hash=hash_password("admin123"), role="superadmin"))
        event = db.scalar(select(Event).limit(1))
        if not event:
            event = Event(name="Vendor Gathering 2026", description="Annual partner gathering", event_date="2026-03-12", start_time="08:00", end_time="17:00", location="Grand Ballroom, The Langham Jakarta", status="active")
            db.add(event)
            db.flush()
            vendors = [Vendor(event_id=event.id, company_name="Karya Nusantara", category="Strategic Partner"), Vendor(event_id=event.id, company_name="Orbit Supply Co.", category="Supply Chain"), Vendor(event_id=event.id, company_name="Mitra Komunika", category="Technology"), Vendor(event_id=event.id, company_name="Aruna Logistic", category="Logistics")]
            db.add_all(vendors)
            db.flush()
            tables = [Table(event_id=event.id, table_number=f"A{i}", table_label=f"VIP Table {i}", capacity=8, zone="VIP") for i in range(1, 4)]
            tables += [Table(event_id=event.id, table_number=f"B{i}", table_label=f"Regular Table {i}", capacity=10, zone="Regular") for i in range(1, 4)]
            db.add_all(tables)
            db.flush()
            names = [("Nadia Prameswari", 0), ("Rizky Aditya", 1), ("Sinta Maharani", 2), ("Bagas Wicaksono", 3), ("Dimas Setiawan", 0), ("Putri Ananda", 1)]
            for idx, (name, v) in enumerate(names):
                db.add(Participant(event_id=event.id, vendor_id=vendors[v].id, name=name, position="Vendor representative", qr_token=token_urlsafe(24), table_id=tables[idx % len(tables)].id, seat_number=str(idx + 1)))
        db.commit()

# ─── System ─────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
def health_check() -> dict:
    return {"status": "ok" if check_database() else "degraded", "database": check_database()}

@app.get("/api", tags=["System"])
def api_root() -> dict:
    return {"name": "Gatherly — Event Registration & Check-in API", "version": "2.0.0", "docs": "/docs"}

# ─── Auth ───────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login", tags=["Auth"])
def login(payload: LoginInput, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password tidak valid")
    return {"access_token": create_token(user.id, user.role), "token_type": "bearer", "user": UserOut.model_validate(user)}

@app.get("/api/auth/me", response_model=UserOut, tags=["Auth"])
def me(user: User = Depends(current_user)) -> User:
    return user

# ─── User Management ───────────────────────────────────────────────────────────

@app.get("/api/users", tags=["Users"])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> list[dict]:
    users = db.scalars(select(User).order_by(User.name)).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at} for u in users]

@app.post("/api/users", tags=["Users"])
def create_user(payload: UserInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    if db.scalar(select(User).where(User.email == payload.email.lower().strip())):
        raise HTTPException(400, "Email sudah terdaftar")
    if payload.role == "superadmin" and user.role != "superadmin":
        raise HTTPException(403, "Hanya superadmin yang bisa membuat superadmin")
    new_user = User(name=payload.name, email=payload.email.lower().strip(), password_hash=hash_password(payload.password), role=payload.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "name": new_user.name, "email": new_user.email, "role": new_user.role, "is_active": new_user.is_active}

@app.put("/api/users/{user_id}", tags=["Users"])
def update_user(user_id: int, payload: UserUpdateInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    if target.role == "superadmin" and user.role != "superadmin":
        raise HTTPException(403, "Hanya superadmin yang bisa mengubah superadmin")
    if payload.email.lower().strip() != target.email:
        if db.scalar(select(User).where(User.email == payload.email.lower().strip())):
            raise HTTPException(400, "Email sudah terdaftar")
    target.name = payload.name
    target.email = payload.email.lower().strip()
    target.role = payload.role
    target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return {"id": target.id, "name": target.name, "email": target.email, "role": target.role, "is_active": target.is_active}

@app.delete("/api/users/{user_id}", tags=["Users"])
def deactivate_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    if target.id == user.id:
        raise HTTPException(400, "Tidak bisa menonaktifkan diri sendiri")
    if target.role == "superadmin" and user.role != "superadmin":
        raise HTTPException(403, "Hanya superadmin yang bisa menonaktifkan superadmin")
    target.is_active = False
    db.commit()
    return {"detail": "User berhasil dinonaktifkan"}

@app.put("/api/users/{user_id}/reset-password", tags=["Users"])
def reset_user_password(user_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    new_pw = payload.get("new_password", "")
    if len(new_pw) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")
    target.password_hash = hash_password(new_pw)
    db.commit()
    return {"detail": "Password berhasil direset"}

@app.put("/api/auth/password", tags=["Auth"])
def change_password(payload: PasswordChangeInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Password lama tidak valid")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password berhasil diubah"}

# ─── Events CRUD ────────────────────────────────────────────────────────────────

@app.get("/api/events", tags=["Events"])
def list_events(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [serialize_event(e, db) for e in db.scalars(select(Event).order_by(Event.event_date.desc(), Event.id.desc())).all()]

@app.post("/api/events", tags=["Events"])
def create_event(payload: EventInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return serialize_event(event, db)

@app.get("/api/events/{event_id}", tags=["Events"])
def get_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    return serialize_event(event, db)

@app.put("/api/events/{event_id}", tags=["Events"])
def update_event(event_id: int, payload: EventInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return serialize_event(event, db)

@app.delete("/api/events/{event_id}", tags=["Events"])
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    db.delete(event)
    db.commit()
    return {"detail": "Event berhasil dihapus"}

@app.post("/api/events/{event_id}/copy", tags=["Events"])
def copy_event(event_id: int, payload: EventCopyInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    source = db.get(Event, event_id)
    if not source:
        raise HTTPException(404, "Event tidak ditemukan")
    new_event = Event(name=payload.name, description=source.description, event_date=payload.event_date, start_time=source.start_time, end_time=source.end_time, location=source.location, status=payload.status)
    db.add(new_event)
    db.flush()
    vendor_map = {}
    if payload.copy_vendors:
        for v in db.scalars(select(Vendor).where(Vendor.event_id == event_id)).all():
            new_v = Vendor(event_id=new_event.id, company_name=v.company_name, category=v.category, contact_name=v.contact_name, phone=v.phone, email=v.email)
            db.add(new_v)
            db.flush()
            vendor_map[v.id] = new_v.id
    table_map = {}
    if payload.copy_tables:
        for t in db.scalars(select(Table).where(Table.event_id == event_id)).all():
            new_t = Table(event_id=new_event.id, table_number=t.table_number, table_label=t.table_label, capacity=t.capacity, zone=t.zone)
            db.add(new_t)
            db.flush()
            table_map[t.id] = new_t.id
    if payload.copy_participants:
        for p in db.scalars(select(Participant).where(Participant.event_id == event_id)).all():
            db.add(Participant(
                event_id=new_event.id,
                vendor_id=vendor_map.get(p.vendor_id) if p.vendor_id else None,
                table_id=table_map.get(p.table_id) if p.table_id else None,
                seat_number=p.seat_number,
                name=p.name, position=p.position, phone=p.phone, email=p.email,
                qr_token=token_urlsafe(24),
            ))
    db.commit()
    db.refresh(new_event)
    return serialize_event(new_event, db)

@app.get("/api/events/{event_id}/dashboard", tags=["Events"])
def dashboard(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    total = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id)) or 0
    checked = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None))) or 0
    vendors_data = []
    for vendor in db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.company_name)).all():
        vt = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == vendor.id)) or 0
        vc = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == vendor.id, Participant.check_in_at.is_not(None))) or 0
        vendors_data.append({"id": vendor.id, "company_name": vendor.company_name, "category": vendor.category, "total": vt, "checked_in": vc, "rate": round(vc / vt * 100) if vt else 0})
    recent = db.scalars(select(Participant).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None)).order_by(Participant.check_in_at.desc()).limit(8)).all()
    return {"event": serialize_event(event, db), "summary": {"total": total, "checked_in": checked, "remaining": total - checked, "rate": round(checked / total * 100) if total else 0}, "vendors": vendors_data, "recent": [serialize_participant(p, db) for p in recent]}

@app.get("/api/events/{event_id}/stats", tags=["Events"])
def event_stats(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    total = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id)) or 0
    checked = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None))) or 0
    vendor_count = db.scalar(select(func.count(Vendor.id)).where(Vendor.event_id == event_id)) or 0
    table_count = db.scalar(select(func.count(Table.id)).where(Table.event_id == event_id)) or 0
    seated = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id, Participant.table_id.is_not(None))) or 0
    return {"event": serialize_event(event, db), "total_participants": total, "checked_in": checked, "remaining": total - checked, "rate": round(checked / total * 100) if total else 0, "vendor_count": vendor_count, "table_count": table_count, "seated_participants": seated, "unseated_participants": total - seated}

# ─── Vendors CRUD ───────────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/vendors", tags=["Vendors"])
def list_vendors(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [{"id": v.id, "company_name": v.company_name, "category": v.category, "contact_name": v.contact_name, "phone": v.phone, "email": v.email, "participant_count": db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == v.id)) or 0} for v in db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.company_name)).all()]

@app.post("/api/events/{event_id}/vendors", tags=["Vendors"])
def create_vendor(event_id: int, payload: VendorInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    vendor = Vendor(event_id=event_id, **payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, **payload.model_dump(), "participant_count": 0}

@app.put("/api/events/{event_id}/vendors/{vendor_id}", tags=["Vendors"])
def update_vendor(event_id: int, vendor_id: int, payload: VendorInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    vendor = db.scalar(select(Vendor).where(Vendor.id == vendor_id, Vendor.event_id == event_id))
    if not vendor:
        raise HTTPException(404, "Vendor tidak ditemukan")
    for key, value in payload.model_dump().items():
        setattr(vendor, key, value)
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, **payload.model_dump(), "participant_count": db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == vendor.id)) or 0}

@app.delete("/api/events/{event_id}/vendors/{vendor_id}", tags=["Vendors"])
def delete_vendor(event_id: int, vendor_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    vendor = db.scalar(select(Vendor).where(Vendor.id == vendor_id, Vendor.event_id == event_id))
    if not vendor:
        raise HTTPException(404, "Vendor tidak ditemukan")
    db.delete(vendor)
    db.commit()
    return {"detail": "Vendor berhasil dihapus"}

# ─── Tables (Seating) CRUD ─────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/tables", tags=["Seating"])
def list_tables(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    result = []
    for t in db.scalars(select(Table).where(Table.event_id == event_id).order_by(Table.table_number)).all():
        seated = db.scalar(select(func.count(Participant.id)).where(Participant.table_id == t.id)) or 0
        result.append({"id": t.id, "table_number": t.table_number, "table_label": t.table_label, "capacity": t.capacity, "zone": t.zone, "status": t.status, "seated": seated})
    return result

@app.post("/api/events/{event_id}/tables", tags=["Seating"])
def create_table(event_id: int, payload: TableInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    t = Table(event_id=event_id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, **payload.model_dump(), "seated": 0}

@app.post("/api/events/{event_id}/tables/bulk", tags=["Seating"])
def create_tables_bulk(event_id: int, payload: TableBulkInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    tables = []
    for i in range(1, payload.count + 1):
        t = Table(event_id=event_id, table_number=f"{payload.prefix}{i}", table_label=f"{payload.zone} {payload.prefix}{i}", capacity=payload.capacity, zone=payload.zone)
        db.add(t)
        tables.append(t)
    db.commit()
    return [{"id": t.id, "table_number": t.table_number, "table_label": t.table_label, "capacity": t.capacity, "zone": t.zone, "status": t.status, "seated": 0} for t in tables]

@app.put("/api/events/{event_id}/tables/{table_id}", tags=["Seating"])
def update_table(event_id: int, table_id: int, payload: TableInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    t = db.scalar(select(Table).where(Table.id == table_id, Table.event_id == event_id))
    if not t:
        raise HTTPException(404, "Meja tidak ditemukan")
    for key, value in payload.model_dump().items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    seated = db.scalar(select(func.count(Participant.id)).where(Participant.table_id == t.id)) or 0
    return {"id": t.id, "table_number": t.table_number, "table_label": t.table_label, "capacity": t.capacity, "zone": t.zone, "status": t.status, "seated": seated}

@app.delete("/api/events/{event_id}/tables/{table_id}", tags=["Seating"])
def delete_table(event_id: int, table_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    t = db.scalar(select(Table).where(Table.id == table_id, Table.event_id == event_id))
    if not t:
        raise HTTPException(404, "Meja tidak ditemukan")
    db.execute(select(Participant).where(Participant.table_id == table_id))
    for p in db.scalars(select(Participant).where(Participant.table_id == table_id)).all():
        p.table_id = None
        p.seat_number = None
    db.delete(t)
    db.commit()
    return {"detail": "Meja berhasil dihapus"}

# ─── Participants CRUD ──────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/participants", tags=["Participants"])
def list_participants(event_id: int, search: str = Query(""), db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    query = select(Participant).where(Participant.event_id == event_id).order_by(Participant.name)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(Participant.name.ilike(term), Participant.email.ilike(term), Participant.phone.ilike(term)))
    return [serialize_participant(item, db) for item in db.scalars(query.limit(500)).all()]

@app.post("/api/events/{event_id}/participants", tags=["Participants"])
def create_participant(event_id: int, payload: ParticipantInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    if payload.vendor_id and not db.scalar(select(Vendor).where(Vendor.id == payload.vendor_id, Vendor.event_id == event_id)):
        raise HTTPException(400, "Vendor tidak sesuai dengan event")
    if payload.table_id and not db.scalar(select(Table).where(Table.id == payload.table_id, Table.event_id == event_id)):
        raise HTTPException(400, "Meja tidak sesuai dengan event")
    participant = Participant(event_id=event_id, qr_token=token_urlsafe(24), **payload.model_dump())
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return serialize_participant(participant, db)

@app.put("/api/events/{event_id}/participants/{participant_id}", tags=["Participants"])
def update_participant(event_id: int, participant_id: int, payload: ParticipantInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    p = db.scalar(select(Participant).where(Participant.id == participant_id, Participant.event_id == event_id))
    if not p:
        raise HTTPException(404, "Peserta tidak ditemukan")
    for key, value in payload.model_dump().items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return serialize_participant(p, db)

@app.delete("/api/events/{event_id}/participants/{participant_id}", tags=["Participants"])
def delete_participant(event_id: int, participant_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    p = db.scalar(select(Participant).where(Participant.id == participant_id, Participant.event_id == event_id))
    if not p:
        raise HTTPException(404, "Peserta tidak ditemukan")
    db.delete(p)
    db.commit()
    return {"detail": "Peserta berhasil dihapus"}

@app.patch("/api/events/{event_id}/participants/{participant_id}/seat", tags=["Seating"])
def assign_seat(event_id: int, participant_id: int, payload: SeatAssignInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    p = db.scalar(select(Participant).where(Participant.id == participant_id, Participant.event_id == event_id))
    if not p:
        raise HTTPException(404, "Peserta tidak ditemukan")
    if payload.table_id and not db.scalar(select(Table).where(Table.id == payload.table_id, Table.event_id == event_id)):
        raise HTTPException(400, "Meja tidak sesuai dengan event")
    p.table_id = payload.table_id
    p.seat_number = payload.seat_number
    db.commit()
    db.refresh(p)
    return serialize_participant(p, db)

# ─── Attendance ─────────────────────────────────────────────────────────────────

def perform_checkin(event_id: int, participant: Participant, method: str, user: User, notes: str, db: Session) -> dict:
    if participant.event_id != event_id:
        raise HTTPException(400, "Peserta bukan bagian dari event ini")
    now = datetime.now(timezone.utc)
    if participant.check_in_at:
        db.add(AttendanceLog(event_id=event_id, participant_id=participant.id, action="check_in", method=method, result="already_checked_in", scanned_by=user.id, notes=notes))
        db.commit()
        return {"result": "already_checked_in", "participant": serialize_participant(participant, db), "checked_in_at": participant.check_in_at}
    participant.attendance_status = "checked_in"
    participant.check_in_at = now
    participant.check_in_method = method
    participant.checked_in_by = user.id
    db.add(AttendanceLog(event_id=event_id, participant_id=participant.id, action="check_in", method=method, result="checked_in", scanned_by=user.id, notes=notes))
    db.commit()
    db.refresh(participant)
    return {"result": "checked_in", "participant": serialize_participant(participant, db), "checked_in_at": participant.check_in_at}

@app.post("/api/events/{event_id}/attendance/scan", tags=["Attendance"])
def scan(event_id: int, payload: ScanInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event or event.status != "active":
        raise HTTPException(400, "Event tidak aktif")
    participant = db.scalar(select(Participant).where(Participant.event_id == event_id, Participant.qr_token == payload.token).with_for_update())
    if not participant:
        db.add(AttendanceLog(event_id=event_id, action="scan", method="qr", result="invalid_token", scanned_by=user.id, notes=payload.notes))
        db.commit()
        raise HTTPException(404, "QR Code tidak valid atau peserta tidak ditemukan")
    return perform_checkin(event_id, participant, "qr", user, payload.notes, db)

@app.post("/api/events/{event_id}/attendance/manual", tags=["Attendance"])
def manual_checkin(event_id: int, payload: ManualCheckinInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    participant = db.scalar(select(Participant).where(Participant.id == payload.participant_id).with_for_update())
    if not participant:
        raise HTTPException(404, "Peserta tidak ditemukan")
    return perform_checkin(event_id, participant, "manual", user, payload.notes, db)

@app.post("/api/events/{event_id}/attendance/undo", tags=["Attendance"])
def undo_checkin(event_id: int, payload: UndoCheckinInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    p = db.scalar(select(Participant).where(Participant.id == payload.participant_id, Participant.event_id == event_id).with_for_update())
    if not p:
        raise HTTPException(404, "Peserta tidak ditemukan")
    if not p.check_in_at:
        raise HTTPException(400, "Peserta belum check-in")
    p.attendance_status = "not_attended"
    p.check_in_at = None
    p.check_in_method = None
    p.checked_in_by = None
    db.add(AttendanceLog(event_id=event_id, participant_id=p.id, action="undo_check_in", method="manual", result="undo", scanned_by=user.id, notes=payload.notes))
    db.commit()
    db.refresh(p)
    return {"result": "undo_success", "participant": serialize_participant(p, db)}

# ─── Attendance Logs ────────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/attendance-logs", tags=["Attendance"])
def list_attendance_logs(event_id: int, limit: int = Query(100, le=500), db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    logs = db.scalars(select(AttendanceLog).where(AttendanceLog.event_id == event_id).order_by(AttendanceLog.scanned_at.desc()).limit(limit)).all()
    result = []
    for log in logs:
        p = db.get(Participant, log.participant_id) if log.participant_id else None
        scanner = db.get(User, log.scanned_by) if log.scanned_by else None
        result.append({"id": log.id, "action": log.action, "method": log.method, "result": log.result, "scanned_at": log.scanned_at, "notes": log.notes, "participant_name": p.name if p else None, "scanned_by_name": scanner.name if scanner else None})
    return result

# ─── QR Code Generation ────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/participants/qr-all", tags=["QR Code"])
def download_all_qr(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    participants_list = db.scalars(select(Participant).where(Participant.event_id == event_id).order_by(Participant.name)).all()
    if not participants_list:
        raise HTTPException(404, "Belum ada peserta di event ini")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in participants_list:
            img_buffer = generate_qr_image(p.qr_token)
            vendor = db.get(Vendor, p.vendor_id) if p.vendor_id else None
            company = safe_filename(vendor.company_name) if vendor else "Unassigned"
            filename = f"{company}/{safe_filename(p.name)}_{p.id}.png"
            zf.writestr(filename, img_buffer.read())
    zip_buffer.seek(0)
    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="qr_codes_{safe_filename(event.name)}.zip"'})

@app.get("/api/events/{event_id}/participants/{participant_id}/qr", tags=["QR Code"])
def get_participant_qr(event_id: int, participant_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    participant = db.scalar(select(Participant).where(Participant.id == participant_id, Participant.event_id == event_id))
    if not participant:
        raise HTTPException(404, "Peserta tidak ditemukan di event ini")
    buffer = generate_qr_image(participant.qr_token)
    filename = f"qr_{safe_filename(participant.name)}_{participant.id}.png"
    return StreamingResponse(buffer, media_type="image/png", headers={"Content-Disposition": f'inline; filename="{filename}"'})

# ─── Import Excel ───────────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/import/template", tags=["Import/Export"])
def download_import_template(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["nama", "perusahaan", "jabatan", "telepon", "email", "kategori_perusahaan", "nomor_meja", "nomor_kursi"]
    wb, ws = _styled_workbook("Template Import", headers)
    ws.append(["Nadia Prameswari", "PT Karya Nusantara", "Manager", "08123456789", "nadia@example.com", "Strategic Partner", "A1", "1"])
    ws.append(["Rizky Aditya", "PT Orbit Supply", "Staff", "08198765432", "", "Supply Chain", "A1", "2"])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 22
    buf = _wb_to_bytes(wb)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="template_import_peserta.xlsx"'})

@app.post("/api/events/{event_id}/import/preview", tags=["Import/Export"])
async def import_preview(event_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File harus berformat .xlsx")
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content))
        ws = wb.active
    except Exception:
        raise HTTPException(400, "File Excel tidak valid")
    headers_row = [str(cell.value or "").strip().lower() for cell in ws[1]]
    required = {"nama", "perusahaan"}
    if not required.issubset(set(headers_row)):
        raise HTTPException(400, f"Header wajib tidak ditemukan: {required - set(headers_row)}")
    col_map = {h: i for i, h in enumerate(headers_row)}
    rows = []
    errors = []
    existing_vendors = {v.company_name.lower() for v in db.scalars(select(Vendor).where(Vendor.event_id == event_id)).all()}
    existing_tables = {t.table_number.lower() for t in db.scalars(select(Table).where(Table.event_id == event_id)).all()}
    new_vendors = set()
    new_tables = set()
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[col_map.get("nama", 0)]:
            continue
        name = str(row[col_map["nama"]]).strip()
        company = str(row[col_map["perusahaan"]]).strip() if col_map.get("perusahaan") is not None and row[col_map["perusahaan"]] else ""
        if not name:
            errors.append({"row": row_idx, "error": "Nama kosong"})
            continue
        if not company:
            errors.append({"row": row_idx, "error": "Perusahaan kosong"})
            continue
        row_data = {
            "nama": name,
            "perusahaan": company,
            "jabatan": str(row[col_map.get("jabatan", -1)] or "").strip() if col_map.get("jabatan") is not None and len(row) > col_map.get("jabatan", 999) else "",
            "telepon": str(row[col_map.get("telepon", -1)] or "").strip() if col_map.get("telepon") is not None and len(row) > col_map.get("telepon", 999) else "",
            "email": str(row[col_map.get("email", -1)] or "").strip() if col_map.get("email") is not None and len(row) > col_map.get("email", 999) else "",
            "kategori_perusahaan": str(row[col_map.get("kategori_perusahaan", -1)] or "General").strip() if col_map.get("kategori_perusahaan") is not None and len(row) > col_map.get("kategori_perusahaan", 999) else "General",
            "nomor_meja": str(row[col_map.get("nomor_meja", -1)] or "").strip() if col_map.get("nomor_meja") is not None and len(row) > col_map.get("nomor_meja", 999) else "",
            "nomor_kursi": str(row[col_map.get("nomor_kursi", -1)] or "").strip() if col_map.get("nomor_kursi") is not None and len(row) > col_map.get("nomor_kursi", 999) else "",
        }
        # Check for duplicate in DB
        existing = db.scalar(select(Participant).where(Participant.event_id == event_id, func.lower(Participant.name) == name.lower()).join(Vendor, Participant.vendor_id == Vendor.id, isouter=True).where(or_(Vendor.company_name.ilike(company), Participant.vendor_id.is_(None))))
        row_data["is_duplicate"] = existing is not None
        if company.lower() not in existing_vendors:
            new_vendors.add(company)
        if row_data["nomor_meja"] and row_data["nomor_meja"].lower() not in existing_tables:
            new_tables.add(row_data["nomor_meja"])
        rows.append(row_data)
    return {"total_rows": len(rows), "errors": errors, "rows": rows, "new_vendors": sorted(new_vendors), "new_tables": sorted(new_tables)}

@app.post("/api/events/{event_id}/import/confirm", tags=["Import/Export"])
def import_confirm(event_id: int, payload: ImportConfirmInput, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    created = 0
    skipped = 0
    updated = 0
    vendors_created = 0
    tables_created = 0
    for row in payload.rows:
        company = row.get("perusahaan", "")
        vendor = db.scalar(select(Vendor).where(Vendor.event_id == event_id, func.lower(Vendor.company_name) == company.lower())) if company else None
        if company and not vendor:
            vendor = Vendor(event_id=event_id, company_name=company, category=row.get("kategori_perusahaan", "General"))
            db.add(vendor)
            db.flush()
            vendors_created += 1
        table = None
        table_number = row.get("nomor_meja", "")
        if table_number:
            table = db.scalar(select(Table).where(Table.event_id == event_id, func.lower(Table.table_number) == table_number.lower()))
            if not table:
                table = Table(event_id=event_id, table_number=table_number, capacity=8, zone="Regular")
                db.add(table)
                db.flush()
                tables_created += 1
        name = row.get("nama", "")
        if row.get("is_duplicate") and payload.duplicate_action == "skip":
            skipped += 1
            continue
        if row.get("is_duplicate") and payload.duplicate_action == "update":
            existing = db.scalar(select(Participant).where(Participant.event_id == event_id, func.lower(Participant.name) == name.lower()))
            if existing:
                existing.position = row.get("jabatan", existing.position)
                existing.phone = row.get("telepon", existing.phone)
                existing.email = row.get("email", existing.email)
                existing.vendor_id = vendor.id if vendor else existing.vendor_id
                existing.table_id = table.id if table else existing.table_id
                existing.seat_number = row.get("nomor_kursi") or existing.seat_number
                updated += 1
                continue
        p = Participant(
            event_id=event_id,
            vendor_id=vendor.id if vendor else None,
            table_id=table.id if table else None,
            seat_number=row.get("nomor_kursi") or None,
            name=name,
            position=row.get("jabatan", ""),
            phone=row.get("telepon", ""),
            email=row.get("email", ""),
            qr_token=token_urlsafe(24),
        )
        db.add(p)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped, "updated": updated, "vendors_created": vendors_created, "tables_created": tables_created}

# ─── Export Excel ───────────────────────────────────────────────────────────────

@app.get("/api/events/{event_id}/export/participants", tags=["Import/Export"])
def export_participants(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["No", "Nama", "Perusahaan", "Jabatan", "Telepon", "Email", "Meja", "Kursi", "Status", "Waktu Check-in"]
    wb, ws = _styled_workbook("Daftar Peserta", headers)
    for idx, p in enumerate(db.scalars(select(Participant).where(Participant.event_id == event_id).order_by(Participant.name)).all(), 1):
        vendor = db.get(Vendor, p.vendor_id) if p.vendor_id else None
        table = db.get(Table, p.table_id) if p.table_id else None
        ws.append([idx, p.name, vendor.company_name if vendor else "", p.position, p.phone, p.email, table.table_number if table else "", p.seat_number or "", "Hadir" if p.check_in_at else "Belum Hadir", str(p.check_in_at)[:19] if p.check_in_at else ""])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = _wb_to_bytes(wb)
    fn = f"peserta_{safe_filename(event.name)}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{fn}"'})

@app.get("/api/events/{event_id}/export/attendance", tags=["Import/Export"])
def export_attendance(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["No", "Nama", "Perusahaan", "Waktu Check-in", "Metode", "Meja", "Kursi", "Dicatat Oleh"]
    wb, ws = _styled_workbook("Laporan Kehadiran", headers)
    checked = db.scalars(select(Participant).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None)).order_by(Participant.check_in_at)).all()
    for idx, p in enumerate(checked, 1):
        vendor = db.get(Vendor, p.vendor_id) if p.vendor_id else None
        table = db.get(Table, p.table_id) if p.table_id else None
        scanner = db.get(User, p.checked_in_by) if p.checked_in_by else None
        ws.append([idx, p.name, vendor.company_name if vendor else "", str(p.check_in_at)[:19] if p.check_in_at else "", p.check_in_method or "", table.table_number if table else "", p.seat_number or "", scanner.name if scanner else ""])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = _wb_to_bytes(wb)
    fn = f"kehadiran_{safe_filename(event.name)}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{fn}"'})

@app.get("/api/events/{event_id}/export/vendors", tags=["Import/Export"])
def export_vendors(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["No", "Perusahaan", "Kategori", "Kontak", "Telepon", "Email", "Jumlah Peserta", "Hadir", "Rate (%)"]
    wb, ws = _styled_workbook("Daftar Vendor", headers)
    for idx, v in enumerate(db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.company_name)).all(), 1):
        total = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == v.id)) or 0
        checked = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == v.id, Participant.check_in_at.is_not(None))) or 0
        ws.append([idx, v.company_name, v.category, v.contact_name, v.phone, v.email, total, checked, round(checked / total * 100) if total else 0])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = _wb_to_bytes(wb)
    fn = f"vendor_{safe_filename(event.name)}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{fn}"'})

@app.get("/api/events/{event_id}/export/seating", tags=["Import/Export"])
def export_seating(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["Meja", "Label", "Zona", "Kapasitas", "Terisi", "Peserta", "Kursi"]
    wb, ws = _styled_workbook("Layout Meja", headers)
    for t in db.scalars(select(Table).where(Table.event_id == event_id).order_by(Table.table_number)).all():
        seated_list = db.scalars(select(Participant).where(Participant.table_id == t.id).order_by(Participant.seat_number)).all()
        if not seated_list:
            ws.append([t.table_number, t.table_label, t.zone, t.capacity, 0, "", ""])
        for p in seated_list:
            ws.append([t.table_number, t.table_label, t.zone, t.capacity, len(seated_list), p.name, p.seat_number or ""])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = _wb_to_bytes(wb)
    fn = f"seating_{safe_filename(event.name)}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{fn}"'})

@app.get("/api/events/{event_id}/export/audit-log", tags=["Import/Export"])
def export_audit_log(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    headers = ["No", "Waktu", "Aksi", "Metode", "Hasil", "Peserta", "Dicatat Oleh", "Catatan"]
    wb, ws = _styled_workbook("Audit Log", headers)
    for idx, log in enumerate(db.scalars(select(AttendanceLog).where(AttendanceLog.event_id == event_id).order_by(AttendanceLog.scanned_at.desc())).all(), 1):
        p = db.get(Participant, log.participant_id) if log.participant_id else None
        scanner = db.get(User, log.scanned_by) if log.scanned_by else None
        ws.append([idx, str(log.scanned_at)[:19] if log.scanned_at else "", log.action, log.method, log.result, p.name if p else "-", scanner.name if scanner else "-", log.notes])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    buf = _wb_to_bytes(wb)
    fn = f"audit_{safe_filename(event.name)}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{fn}"'})
