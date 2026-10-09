"""Manual demo data seeder for production-safe verification.

This module is intentionally never imported by the application startup hook.
Run it explicitly with: python -m app.seed
"""

import argparse
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy import delete, select

from .database import SessionLocal, init_database
from .models import AttendanceLog, Event, Participant, Table, User, Vendor


SEED_EVENT_NAME = "Vendor Partnership Summit 2026"
SEED_DESCRIPTION = "Annual partner gathering 2026. [seed:vendor-partnership-2026]"
LEGACY_EVENT_NAME = "[DEMO SEED] Vendor Gathering Verification"


def find_demo_event(db):
    return db.scalar(select(Event).where(Event.description == SEED_DESCRIPTION))


def find_legacy_demo_event(db):
    return db.scalar(select(Event).where(Event.name == LEGACY_EVENT_NAME))


def remove_demo_data(db) -> bool:
    event = find_demo_event(db) or find_legacy_demo_event(db)
    if not event:
        return False

    db.execute(delete(AttendanceLog).where(AttendanceLog.event_id == event.id))
    db.execute(delete(Participant).where(Participant.event_id == event.id))
    db.execute(delete(Vendor).where(Vendor.event_id == event.id))
    db.execute(delete(Table).where(Table.event_id == event.id))
    db.delete(event)
    return True


def seed_demo_data(db) -> bool:
    existing = find_demo_event(db) or find_legacy_demo_event(db)
    if existing:
        remove_demo_data(db)

    event = Event(
        name=SEED_EVENT_NAME,
        description=SEED_DESCRIPTION,
        event_date="2026-11-21",
        start_time="08:00",
        end_time="17:00",
        location="Grand Ballroom, The Langham Jakarta",
        status="active",
    )
    db.add(event)
    db.flush()

    vendors = [
        Vendor(event_id=event.id, company_name="Karya Nusantara Sejahtera", category="Strategic Partner", contact_name="Dina Prameswari", phone="0215551201", email="dina.prameswari@example.invalid"),
        Vendor(event_id=event.id, company_name="Orbit Supply Indonesia", category="Supply Chain", contact_name="Raka Wijaya", phone="0215551202", email="raka.wijaya@example.invalid"),
        Vendor(event_id=event.id, company_name="Mitra Komunika Digital", category="Technology", contact_name="Sari Anggraini", phone="0215551203", email="sari.anggraini@example.invalid"),
        Vendor(event_id=event.id, company_name="Aruna Logistik Mandiri", category="Logistics", contact_name="Fajar Nugroho", phone="0215551204", email="fajar.nugroho@example.invalid"),
    ]
    db.add_all(vendors)
    db.flush()

    tables = [
        Table(event_id=event.id, table_number="A1", table_label="VIP Table 1", capacity=8, zone="VIP"),
        Table(event_id=event.id, table_number="A2", table_label="VIP Table 2", capacity=8, zone="VIP"),
        Table(event_id=event.id, table_number="B1", table_label="Regular Table 1", capacity=10, zone="Regular"),
        Table(event_id=event.id, table_number="B2", table_label="Regular Table 2", capacity=10, zone="Regular"),
        Table(event_id=event.id, table_number="B3", table_label="Regular Table 3", capacity=10, zone="Regular"),
    ]
    db.add_all(tables)
    db.flush()

    group_management = token_urlsafe(24)
    group_operations = token_urlsafe(24)
    people = [
        ("Nadia Prameswari", "Head of Partnership", "nadia.prameswari@example.invalid", "0812100101", 0, 0, "1", group_management, "Dewi Lestari", True),
        ("Rizky Aditya", "Partnership Manager", "rizky.aditya@example.invalid", "0812100102", 0, 0, "2", group_management, "Dewi Lestari", True),
        ("Sinta Maharani", "Finance Director", "sinta.maharani@example.invalid", "0812100103", 0, 0, "3", group_management, None, False),
        ("Bagas Wicaksono", "Operations Manager", "bagas.wicaksono@example.invalid", "0812100104", 1, 1, "1", group_operations, "Andi Saputra", True),
        ("Putri Ananda", "Procurement Lead", "putri.ananda@example.invalid", "0812100105", 1, 1, "2", group_operations, "Andi Saputra", True),
        ("Dimas Setiawan", "Chief Executive Officer", "dimas.setiawan@example.invalid", "0812100106", 2, 2, "1", None, None, True),
        ("Ayu Kartika", "Corporate Secretary", "ayu.kartika@example.invalid", "0812100107", 2, 2, "2", None, None, False),
        ("Fajar Nugroho", "Logistics Coordinator", "fajar.nugroho@example.invalid", "0812100108", 3, 2, "3", None, None, True),
        ("Maya Sari", "Technology Partnership Lead", "maya.sari@example.invalid", "0812100109", 2, 3, "1", None, None, False),
        ("Hendra Kurniawan", "Regional Sales Director", "hendra.kurniawan@example.invalid", "0812100110", 3, 3, "2", None, None, False),
    ]
    checked_at = datetime.now(timezone.utc) - timedelta(minutes=12)
    db_user = db.scalar(select(User).where(User.is_active.is_(True)).order_by(User.id))
    participants = []
    for name, position, email, phone, vendor_index, table_index, seat, group_token, attended_by, checked_in in people:
        participant = Participant(
            event_id=event.id,
            vendor_id=vendors[vendor_index].id,
            table_id=tables[table_index].id,
            seat_number=seat,
            name=name,
            position=position,
            phone=phone,
            email=email,
            qr_token=token_urlsafe(24),
            qr_group_token=group_token,
            attended_by=attended_by if checked_in and attended_by else None,
        )
        if checked_in:
            participant.attendance_status = "checked_in"
            participant.check_in_at = checked_at
            participant.check_in_method = "qr"
            participant.checked_in_by = db_user.id if db_user else None
        participants.append(participant)
    db.add_all(participants)
    db.flush()

    for participant in [p for p in participants if p.check_in_at]:
        db.add(AttendanceLog(
            event_id=event.id,
            participant_id=participant.id,
            action="check_in",
            method="qr",
            result="checked_in",
            scanned_by=db_user.id if db_user else None,
            scanned_at=checked_at,
            notes=(f"Wakil: {participant.attended_by} atas nama {participant.name}" if participant.attended_by else "QR check-in at registration desk"),
        ))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or remove isolated demo data.")
    parser.add_argument("--remove", action="store_true", help="Remove only the marked demo dataset.")
    args = parser.parse_args()

    init_database()
    with SessionLocal() as db:
        changed = remove_demo_data(db) if args.remove else seed_demo_data(db)
        db.commit()

    if args.remove:
        print("Demo dataset removed." if changed else "Demo dataset was not found.")
    else:
        print("Demo dataset created." if changed else "Demo dataset already exists; no changes made.")


if __name__ == "__main__":
    main()
