"""Replace the current event dataset with the real participant list."""

import re
import sys
from pathlib import Path
from secrets import token_urlsafe
from collections import Counter

from sqlalchemy import delete, select

from .database import SessionLocal, init_database
from .models import AttendanceLog, Event, Participant, Table, Vendor


REAL_DATA_DESCRIPTION = "Real participant data imported from docs/all-participants-update-01.md (vendors only)"
LEGACY_REAL_DATA_DESCRIPTIONS = {
    "Real participant data imported from docs/All participants.md",
    "Real participant data imported from docs/all-participants.md",
    "Real participant data imported from docs/all-participants-update.md",
    "Real participant data imported from docs/all-participants-update-01.md",
}
COMPANY_ROW = re.compile(r"^\s*(.*?)\s+-\s+(.+?)\s*$")
PERSON = re.compile(r"(\d+)\.\s*(.*?)(?=\s+\d+\.\s*|$)")
BLANK = re.compile(r"\[?\s*blank\s*\]?|kosong|hanya 1 PIC", re.IGNORECASE)


def parse_markdown(path: Path) -> list[dict]:
    records = []
    table_rows = []
    current_table = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\u2060", "")
        heading = re.match(r"^#{1,3}\s+Meja\s+(\d+)", line, re.IGNORECASE)
        if heading:
            current_table = int(heading.group(1))
            continue
        if not line.startswith("|") or line.startswith("| :") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        value = cells[-1].replace("**", "").replace("_", "").strip()
        table_heading = re.fullmatch(r"Meja\s+(\d+)", value, re.IGNORECASE)
        if table_heading:
            current_table = int(table_heading.group(1))
            continue
        if not current_table:
            continue
        if re.fullmatch(rf"Meja\s+{current_table}", value, re.IGNORECASE):
            continue
        if not value or BLANK.search(value):
            continue
        table_rows.append((current_table, value))

    for table_number, value in table_rows:
        company = COMPANY_ROW.match(value)
        if company:
            company_name = company.group(1).strip()
            people = [match.group(2).strip().strip("/").strip() for match in PERSON.finditer(company.group(2))]
            people = [person for person in people if person and not BLANK.search(person)]
            if people:
                records.append({"table": table_number, "company": company_name, "people": people})
        elif re.match(r"^(?:PT|PERUM)\s+", value, re.IGNORECASE):
            records.append({"table": table_number, "company": value, "people": [f"{value} - Delegasi 1"]})
    return records


def import_real_data(path: Path) -> tuple[int, int, int]:
    records = parse_markdown(path)
    if not records:
        raise RuntimeError(f"No participant records parsed from {path}")
    table_numbers = sorted({record["table"] for record in records})
    if not table_numbers or min(table_numbers) != 1 or max(table_numbers) != 31:
        raise RuntimeError(f"Expected tables from 1 through 31, found {table_numbers}")
    table_numbers = list(range(1, 32))

    with SessionLocal.begin() as db:
        event = db.scalar(select(Event).order_by(Event.id).limit(1))
        if not event:
            raise RuntimeError("No event exists in the database")
        if event.description in LEGACY_REAL_DATA_DESCRIPTIONS:
            participants = db.query(Participant).filter(Participant.event_id == event.id).count()
            vendors = db.query(Vendor).filter(Vendor.event_id == event.id).count()
            tables = db.query(Table).filter(Table.event_id == event.id).count()
            event.description = REAL_DATA_DESCRIPTION
            return participants, vendors, tables

        db.execute(delete(AttendanceLog).where(AttendanceLog.event_id == event.id))
        db.execute(delete(Participant).where(Participant.event_id == event.id))
        db.execute(delete(Vendor).where(Vendor.event_id == event.id))
        db.execute(delete(Table).where(Table.event_id == event.id))

        tables = {
            number: Table(
                event_id=event.id,
                table_number=str(number),
                table_label=f"{'VIP' if number <= 8 else 'Regular'} Table {number}",
                capacity=9,
                zone="VIP" if number <= 8 else "Regular",
            )
            for number in table_numbers
        }
        db.add_all(tables.values())
        db.flush()

        vendors = {}
        for record in records:
            if record["company"] and record["company"] not in vendors:
                vendors[record["company"]] = Vendor(
                    event_id=event.id,
                    company_name=record["company"],
                    category="Vendor",
                    contact_name=record["people"][0],
                )
                db.add(vendors[record["company"]])
        db.flush()

        vendor_counts = Counter(
            record["company"]
            for record in records
            for _ in record["people"]
            if record["company"]
        )
        group_tokens = {
            company: token_urlsafe(24)
            for company, count in vendor_counts.items()
            if count > 1
        }
        participants = []
        for record in records:
            vendor = vendors.get(record["company"])
            for person in record["people"]:
                table_number = record["table"]
                participants.append(
                    Participant(
                        event_id=event.id,
                        vendor_id=vendor.id if vendor else None,
                        table_id=tables[table_number].id,
                        seat_number=None,
                        name=person,
                        position="Vendor PIC" if vendor else "Guest",
                        email="",
                        phone="",
                        qr_token=token_urlsafe(24),
                        qr_group_token=group_tokens.get(record["company"]),
                    )
                )
        db.add_all(participants)

        event.name = "Vendor Gathering 2026"
        event.description = REAL_DATA_DESCRIPTION
        return len(participants), len(vendors), len(tables)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/all-participants-update-01.md")
    if path.is_dir():
        candidates = [path / "All participants.md", path / "docs" / "All participants.md"]
        path = next((candidate for candidate in candidates if candidate.is_file()), path)
    init_database()
    counts = import_real_data(path)
    print(f"Imported {counts[0]} participants, {counts[1]} vendors, {counts[2]} tables.")


if __name__ == "__main__":
    main()
