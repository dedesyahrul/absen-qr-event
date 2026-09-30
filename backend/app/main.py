import io
import re
import zipfile
from datetime import datetime, timezone
from secrets import token_urlsafe

import qrcode
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal, check_database, get_db, init_database
from .models import AttendanceLog, Event, Participant, User, Vendor
from .security import create_token, decode_token, hash_password, verify_password

settings = get_settings()
app = FastAPI(title="Absen QR Vendor Gathering API", version="1.0.0")
_origins = settings.cors_origin_list
_is_wildcard = _origins == ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=not _is_wildcard, allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer(auto_error=False)


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
    position: str = ""
    phone: str = ""
    email: str = ""


class ScanInput(BaseModel):
    token: str = Field(min_length=4)
    notes: str = ""


class ManualCheckinInput(BaseModel):
    participant_id: int
    notes: str = ""


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str


def serialize_event(event: Event, db: Session) -> dict:
    total = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event.id)) or 0
    checked = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event.id, Participant.check_in_at.is_not(None))) or 0
    return {"id": event.id, "name": event.name, "description": event.description, "event_date": event.event_date, "start_time": event.start_time, "end_time": event.end_time, "location": event.location, "status": event.status, "total_participants": total, "checked_in": checked}


def serialize_participant(item: Participant, db: Session) -> dict:
    vendor = db.get(Vendor, item.vendor_id) if item.vendor_id else None
    return {"id": item.id, "name": item.name, "position": item.position, "phone": item.phone, "email": item.email, "qr_token": item.qr_token, "attendance_status": item.attendance_status, "check_in_at": item.check_in_at, "check_in_method": item.check_in_method, "vendor_id": item.vendor_id, "company_name": vendor.company_name if vendor else "Unassigned"}


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


@app.on_event("startup")
def startup() -> None:
    init_database()
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "admin@example.com")):
            db.add(User(name="Aditya Rahman", email="admin@example.com", password_hash=hash_password("admin123"), role="admin"))
        event = db.scalar(select(Event).limit(1))
        if not event:
            event = Event(name="Vendor Gathering 2026", description="Annual partner gathering", event_date="2026-03-12", start_time="08:00", end_time="17:00", location="Grand Ballroom, The Langham Jakarta", status="active")
            db.add(event)
            db.flush()
            vendors = [Vendor(event_id=event.id, company_name="Karya Nusantara", category="Strategic Partner"), Vendor(event_id=event.id, company_name="Orbit Supply Co.", category="Supply Chain"), Vendor(event_id=event.id, company_name="Mitra Komunika", category="Technology"), Vendor(event_id=event.id, company_name="Aruna Logistic", category="Logistics")]
            db.add_all(vendors)
            db.flush()
            names = [("Nadia Prameswari", 0), ("Rizky Aditya", 1), ("Sinta Maharani", 2), ("Bagas Wicaksono", 3), ("Dimas Setiawan", 0), ("Putri Ananda", 1)]
            db.add_all([Participant(event_id=event.id, vendor_id=vendors[v].id, name=name, position="Vendor representative", qr_token=token_urlsafe(24)) for name, v in names])
        db.commit()


@app.get("/api/health", tags=["System"])
def health_check() -> dict[str, object]:
    database_ok = check_database()
    return {"status": "ok" if database_ok else "degraded", "database": database_ok}


@app.get("/api", tags=["System"])
def api_root() -> dict[str, str]:
    return {"name": "Absen QR Vendor Gathering API", "docs": "/docs"}


@app.post("/api/auth/login")
def login(payload: LoginInput, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password tidak valid")
    return {"access_token": create_token(user.id, user.role), "token_type": "bearer", "user": UserOut.model_validate(user)}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@app.get("/api/events")
def list_events(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [serialize_event(event, db) for event in db.scalars(select(Event).order_by(Event.event_date.desc(), Event.id.desc())).all()]


@app.post("/api/events")
def create_event(payload: EventInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return serialize_event(event, db)


@app.get("/api/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    return serialize_event(event, db)


@app.get("/api/events/{event_id}/dashboard")
def dashboard(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    total = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id)) or 0
    checked = db.scalar(select(func.count(Participant.id)).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None))) or 0
    vendors = []
    for vendor in db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.company_name)).all():
        vt = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == vendor.id)) or 0
        vc = db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == vendor.id, Participant.check_in_at.is_not(None))) or 0
        vendors.append({"id": vendor.id, "company_name": vendor.company_name, "category": vendor.category, "total": vt, "checked_in": vc, "rate": round(vc / vt * 100) if vt else 0})
    recent = db.scalars(select(Participant).where(Participant.event_id == event_id, Participant.check_in_at.is_not(None)).order_by(Participant.check_in_at.desc()).limit(8)).all()
    return {"event": serialize_event(event, db), "summary": {"total": total, "checked_in": checked, "remaining": total - checked, "rate": round(checked / total * 100) if total else 0}, "vendors": vendors, "recent": [serialize_participant(item, db) for item in recent]}


@app.get("/api/events/{event_id}/vendors")
def list_vendors(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return [{"id": v.id, "company_name": v.company_name, "category": v.category, "contact_name": v.contact_name, "phone": v.phone, "email": v.email, "participant_count": db.scalar(select(func.count(Participant.id)).where(Participant.vendor_id == v.id)) or 0} for v in db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.company_name)).all()]


@app.post("/api/events/{event_id}/vendors")
def create_vendor(event_id: int, payload: VendorInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    vendor = Vendor(event_id=event_id, **payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, **payload.model_dump(), "participant_count": 0}


@app.get("/api/events/{event_id}/participants")
def list_participants(event_id: int, search: str = Query(""), db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    query = select(Participant).where(Participant.event_id == event_id).order_by(Participant.name)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(Participant.name.ilike(term), Participant.email.ilike(term), Participant.phone.ilike(term)))
    return [serialize_participant(item, db) for item in db.scalars(query.limit(200)).all()]


@app.post("/api/events/{event_id}/participants")
def create_participant(event_id: int, payload: ParticipantInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event tidak ditemukan")
    if payload.vendor_id and not db.scalar(select(Vendor).where(Vendor.id == payload.vendor_id, Vendor.event_id == event_id)):
        raise HTTPException(400, "Vendor tidak sesuai dengan event")
    participant = Participant(event_id=event_id, qr_token=token_urlsafe(24), **payload.model_dump())
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return serialize_participant(participant, db)


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


@app.post("/api/events/{event_id}/attendance/scan")
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


@app.post("/api/events/{event_id}/attendance/manual")
def manual_checkin(event_id: int, payload: ManualCheckinInput, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    participant = db.scalar(select(Participant).where(Participant.id == payload.participant_id).with_for_update())
    if not participant:
        raise HTTPException(404, "Peserta tidak ditemukan")
    return perform_checkin(event_id, participant, "manual", user, payload.notes, db)


def generate_qr_image(token: str, participant_name: str, event_name: str) -> io.BytesIO:
    """Generate a QR code image containing the participant token."""
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def safe_filename(name: str) -> str:
    """Create a safe filename from a participant name."""
    safe = re.sub(r'[^\w\s-]', '', name.strip())
    safe = re.sub(r'[\s]+', '_', safe)
    return safe or "participant"


@app.get("/api/events/{event_id}/participants/qr-all", tags=["QR Code"])
def download_all_qr(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Generate QR codes for all participants in the event and return as a ZIP file."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    participants_list = db.scalars(select(Participant).where(Participant.event_id == event_id).order_by(Participant.name)).all()
    if not participants_list:
        raise HTTPException(404, "Belum ada peserta di event ini")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in participants_list:
            img_buffer = generate_qr_image(p.qr_token, p.name, event.name)
            vendor = db.get(Vendor, p.vendor_id) if p.vendor_id else None
            company = safe_filename(vendor.company_name) if vendor else "Unassigned"
            filename = f"{company}/{safe_filename(p.name)}_{p.id}.png"
            zf.writestr(filename, img_buffer.read())
    zip_buffer.seek(0)
    zip_filename = f"qr_codes_{safe_filename(event.name)}.zip"
    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'})


@app.get("/api/events/{event_id}/participants/{participant_id}/qr", tags=["QR Code"])
def get_participant_qr(event_id: int, participant_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Generate and return a QR code PNG image for a single participant."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event tidak ditemukan")
    participant = db.scalar(select(Participant).where(Participant.id == participant_id, Participant.event_id == event_id))
    if not participant:
        raise HTTPException(404, "Peserta tidak ditemukan di event ini")
    buffer = generate_qr_image(participant.qr_token, participant.name, event.name)
    filename = f"qr_{safe_filename(participant.name)}_{participant.id}.png"
    return StreamingResponse(buffer, media_type="image/png", headers={"Content-Disposition": f'inline; filename="{filename}"'})
