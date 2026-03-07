"""
Ingest the policies Kaggle dataset into the policy system.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from backend.admin import access_service, document_service
from backend.db.models import Document, Role, RoleType
from backend.db.session import get_session

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

ROLES = [
    # IT Security
    {"role_name": "IT Security Users",    "role_type": RoleType.FUNCTIONAL,     "domain": "IT Security"},
    {"role_name": "IT Security Auditors", "role_type": RoleType.DOMAIN_AUDITOR, "domain": "IT Security"},
    # Compliance
    {"role_name": "Compliance Users",     "role_type": RoleType.FUNCTIONAL,     "domain": "Compliance"},
    {"role_name": "Compliance Auditors",  "role_type": RoleType.DOMAIN_AUDITOR, "domain": "Compliance"},
    # Healthcare
    {"role_name": "Healthcare Users",     "role_type": RoleType.FUNCTIONAL,     "domain": "Healthcare"},
    {"role_name": "Healthcare Auditors",  "role_type": RoleType.DOMAIN_AUDITOR, "domain": "Healthcare"},
]

# ---------------------------------------------------------------------------
# Text file → role mapping (data/uploads/*.txt)
# Keys are file stems (exact, case-sensitive). Values are role_name strings
# that must already exist in the database.
# ---------------------------------------------------------------------------

TEXT_FILE_ROLES: dict[str, list[str]] = {
    "finance_compliance": ["finance", "finance_auditor"],
    "it_security_policy": ["it_eng",  "it_auditor"],
}

SKIP_FILES = {"sample.txt"}

# ---------------------------------------------------------------------------
# Policy → role mapping
# Keys are substrings of PDF filenames (case-insensitive match).
# Values are lists of role_name strings from ROLES above.
# A policy with multiple roles is visible to users in ANY of those roles.
# ---------------------------------------------------------------------------

POLICY_ROLES: dict[str, list[str]] = {
    # ── IT Security ──────────────────────────────────────────────────────
    "Acceptable Use Policy":            ["IT Security Users", "IT Security Auditors"],
    "Access Control Policy":            ["IT Security Users", "IT Security Auditors"],
    "Backup and Recovery Policy":       ["IT Security Users", "IT Security Auditors"],
    "Change Management Policy":         ["IT Security Users", "IT Security Auditors",
                                         "Compliance Users",  "Compliance Auditors"],
    "Data Center Security Policy":      ["IT Security Users", "IT Security Auditors"],
    "Encryption Policy":                ["IT Security Users", "IT Security Auditors"],
    "Firewall Management Policy":       ["IT Security Users", "IT Security Auditors"],
    "Incident Response Policy":         ["IT Security Users", "IT Security Auditors"],
    "Incident Reporting Procedures":    ["IT Security Users", "IT Security Auditors"],
    "Internet Usage Policy":            ["IT Security Users", "IT Security Auditors"],
    "Log Management Policy":            ["IT Security Users", "IT Security Auditors"],
    "Malware Protection Policy":        ["IT Security Users", "IT Security Auditors"],
    "Mobile Device Management Policy":  ["IT Security Users", "IT Security Auditors"],
    "Network Security Policy":          ["IT Security Users", "IT Security Auditors"],
    "Password Management Policy":       ["IT Security Users", "IT Security Auditors"],
    "Remote Access Policy":             ["IT Security Users", "IT Security Auditors"],
    "Role-Based Security Training":     ["IT Security Users", "IT Security Auditors"],
    "Security Awareness Training":      ["IT Security Users", "IT Security Auditors"],
    "Security Events Monitoring":       ["IT Security Users", "IT Security Auditors"],
    "Threat Intelligence":              ["IT Security Users", "IT Security Auditors"],
    "Vulnerability Management":         ["IT Security Users", "IT Security Auditors",
                                         "Compliance Users",  "Compliance Auditors"],

    # ── Compliance ───────────────────────────────────────────────────────
    "Asset Management Policy":          ["Compliance Users", "Compliance Auditors"],
    "Audit and Monitoring Policy":      ["Compliance Users", "Compliance Auditors"],
    "Australian Privacy Principles":    ["Compliance Users", "Compliance Auditors"],
    "Business Continuity":              ["Compliance Users", "Compliance Auditors"],
    "Compliance Management Policy":     ["Compliance Users", "Compliance Auditors"],
    "Data Breach Response Policy":      ["Compliance Users", "Compliance Auditors",
                                         "IT Security Users", "IT Security Auditors"],
    "Data Classification Policy":       ["Compliance Users", "Compliance Auditors"],
    "Data Protection Policy":           ["Compliance Users", "Compliance Auditors"],
    "Data Retention":                   ["Compliance Users", "Compliance Auditors"],
    "GDPR Compliance Policy":           ["Compliance Users", "Compliance Auditors"],
    "Information Security Policy":      ["Compliance Users", "Compliance Auditors",
                                         "IT Security Users", "IT Security Auditors"],
    "Policy Review":                    ["Compliance Users", "Compliance Auditors"],
    "Privacy Policy":                   ["Compliance Users", "Compliance Auditors"],
    "Regulatory Compliance Policy":     ["Compliance Users", "Compliance Auditors"],
    "Risk Management Policy":           ["Compliance Users", "Compliance Auditors"],
    "Third-Party Risk Management":      ["Compliance Users", "Compliance Auditors"],

    # ── Healthcare ───────────────────────────────────────────────────────
    "Ambulance Patient":                ["Healthcare Users", "Healthcare Auditors"],
    "Employee Onboarding":              ["Healthcare Users", "Healthcare Auditors"],
    "Equipment Disposal Policy":        ["Healthcare Users", "Healthcare Auditors"],
    "Facility Security Policy":         ["Healthcare Users", "Healthcare Auditors"],
    "Patient Booking":                  ["Healthcare Users", "Healthcare Auditors"],
    "Patient Consent":                  ["Healthcare Users", "Healthcare Auditors"],
    "Patient Data Privacy":             ["Healthcare Users", "Healthcare Auditors"],
    "Pharmacy Medication":              ["Healthcare Users", "Healthcare Auditors"],
    "Telehealth Security Policy":       ["Healthcare Users", "Healthcare Auditors"],
    "Visitor Management Policy":        ["Healthcare Users", "Healthcare Auditors"],
}


def resolve_roles(filename: str) -> list[str]:
    """Return the role_names for a given PDF filename using substring matching."""
    stem = Path(filename).stem.lower()
    for key, roles in POLICY_ROLES.items():
        if key.lower() in stem:
            return roles
    # Fallback: all three domains (broad policies)
    print(f"  [warn] No explicit mapping for '{filename}' — assigning to all domains")
    return [r["role_name"] for r in ROLES]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(dry_run: bool, force: bool) -> None:
    print("── Step 1: Locate PDFs ───────────────────────────────────────────")
    uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
    pdfs = sorted(uploads_dir.glob("*.pdf"))
    print(f"  Found {len(pdfs)} PDFs at {uploads_dir}")

    print("\n── Step 2: Upsert roles ──────────────────────────────────────────")
    role_map: dict[str, Role] = {}
    async with get_session() as session:
        for r in ROLES:
            result = await session.execute(
                select(Role).where(Role.role_name == r["role_name"])
            )
            role = result.scalar_one_or_none()
            if role is None:
                role = Role(**r)
                session.add(role)
                await session.flush()
                print(f"  Created: {r['role_name']}")
            else:
                print(f"  Exists:  {r['role_name']}")
            role_map[r["role_name"]] = role

    print("\n── Step 3 & 4: Register documents + assign access ───────────────")
    doc_records: list[tuple[Path, str, list[str]]] = []  # (path, doc_id, role_ids)
    async with get_session() as session:
        # Resolve admin user for uploaded_by
        from backend.db.models import User  # noqa: PLC0415
        admin_result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        admin = admin_result.scalar_one_or_none()
        if admin is None:
            print("  ERROR: admin@example.com not found — run seed_db.py first")
            sys.exit(1)

        for pdf in pdfs:
            title = pdf.stem
            # Idempotent: skip if title already registered
            existing = (await session.execute(
                select(Document).where(Document.title == title)
            )).scalar_one_or_none()

            if existing is not None:
                doc = existing
                print(f"  Exists:   {title}")
            else:
                doc = await document_service.register_document(
                    session,
                    title=title,
                    storage_uri=str(pdf),
                    uploaded_by=admin.user_id,
                )
                print(f"  Registered: {title}")

            # Resolve and assign role access
            role_names = resolve_roles(pdf.name)
            role_ids = [role_map[name].role_id for name in role_names if name in role_map]
            await access_service.set_document_access(session, doc.doc_id, role_ids)

            doc_records.append((pdf, str(doc.doc_id), role_ids))

    print(f"\n  Registered {len(doc_records)} PDF documents with role access")

    print("\n── Step 3b: Register text files from data/uploads/ ─────────────")
    uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
    txt_files = sorted(f for f in uploads_dir.glob("*.txt") if f.name not in SKIP_FILES)
    print(f"  Found {len(txt_files)} text file(s) (skipping: {SKIP_FILES})")

    async with get_session() as session:
        from backend.db.models import User  # noqa: PLC0415

        admin_result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        admin = admin_result.scalar_one_or_none()
        if admin is None:
            print("  ERROR: admin@example.com not found — run seed_db.py first")
            sys.exit(1)

        for txt in txt_files:
            stem = txt.stem
            role_names = TEXT_FILE_ROLES.get(stem)
            if role_names is None:
                print(f"  [warn] No mapping for '{txt.name}' — skipping")
                continue

            # Look up roles from DB by exact role_name
            role_ids = []
            for rname in role_names:
                result = await session.execute(select(Role).where(Role.role_name == rname))
                role = result.scalar_one_or_none()
                if role is None:
                    print(f"  [warn] Role '{rname}' not found in DB — skipping")
                else:
                    role_ids.append(role.role_id)

            existing = (await session.execute(
                select(Document).where(Document.title == stem)
            )).scalar_one_or_none()

            if existing is not None:
                doc = existing
                print(f"  Exists:     {stem}")
            else:
                doc = await document_service.register_document(
                    session,
                    title=stem,
                    storage_uri=str(txt),
                    uploaded_by=admin.user_id,
                )
                print(f"  Registered: {stem}")

            await access_service.set_document_access(session, doc.doc_id, role_ids)
            doc_records.append((txt, str(doc.doc_id), role_ids))

    if dry_run:
        print("\n── Dry-run mode: skipping ChromaDB ingestion ─────────────────────")
        print("  Remove --dry-run and ensure Ollama is running to embed documents.")
        return

    print("\n── Step 5: Ingest into ChromaDB (embed + store) ─────────────────")
    from backend.ingestion.pipeline import ingest_document  # noqa: PLC0415
    from backend.llm.factory import get_llm_provider        # noqa: PLC0415
    from backend.rag.factory import get_rag_provider        # noqa: PLC0415

    rag = get_rag_provider()
    llm = get_llm_provider()

    total_chunks = 0
    for i, (pdf, doc_id, role_ids) in enumerate(doc_records, 1):
        role_id_strs = [str(r) for r in role_ids]
        try:
            result = ingest_document(
                file_path=pdf,
                doc_id=doc_id,
                allowed_roles=role_id_strs,
                rag_provider=rag,
                llm_provider=llm,
                title=pdf.stem,
                replace_existing=force,
            )
            total_chunks += result["chunk_count"]
            print(f"  [{i:02d}/{len(doc_records)}] {pdf.stem[:55]:<55} "
                  f"{result['chunk_count']:>4} chunks  {result['page_count']:>3} pages")
        except Exception as exc:
            print(f"  [{i:02d}/{len(doc_records)}] ERROR {pdf.name}: {exc}")

    print(f"\n  Done. {total_chunks} total chunks stored in ChromaDB.")
    print("  Restart the API (uvicorn) to reload the ChromaDB index into memory.")
    print("  The system is ready — start the API and query away.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Register in Postgres only; skip ChromaDB embedding (no Ollama required)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-embed documents already present in ChromaDB",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, force=args.force))
