import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import ApprovedFact, BrandRule

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "demo" / "sample_brand_rules.json"


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Demo data file not found: {DATA_FILE}")

    Base.metadata.create_all(bind=engine)
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    added_rules = 0
    added_facts = 0

    with SessionLocal() as db:
        for item in data.get("rules", []):
            exists = db.scalar(select(BrandRule).where(BrandRule.rule_code == item["rule_code"]))
            if exists:
                continue
            record = dict(item)
            record["effective_date"] = parse_date(record.get("effective_date"))
            db.add(BrandRule(**record))
            added_rules += 1

        for item in data.get("facts", []):
            exists = db.scalar(select(ApprovedFact).where(ApprovedFact.fact_code == item["fact_code"]))
            if exists:
                continue
            record = dict(item)
            record["valid_from"] = parse_date(record.get("valid_from"))
            record["valid_until"] = parse_date(record.get("valid_until"))
            db.add(ApprovedFact(**record))
            added_facts += 1

        db.commit()

    print(f"Brand: {data.get('brand_name', 'Demo brand')}")
    print(f"Added {added_rules} rule(s) and {added_facts} fact(s).")
    print("Existing records were preserved; the seed script is safe to run again.")


if __name__ == "__main__":
    main()
