#!/usr/bin/env python3
"""
Smart database migration and purge script for AgenticApply.
Removes poisoned, false-rejected, and malformed URL records from seen_urls,
clears recruitment agencies from seen_companies to allow new multi-role postings,
and retains only the 7 genuinely generated application records.
"""

import os
import sqlite3
import sys

# Ensure repository root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import db

VERIFIED_MATCHES = [
    {
        "company": "cloudunify flexco",
        "title": "DevOps / Cloud Engineer",
        "url": "https://www.karriere.at/jobs/10030340",
        "is_agency": False,
    },
    {
        "company": "checkyeti gmbh",
        "title": "Backend Python Engineer",
        "url": "https://www.karriere.at/jobs/10029398",
        "is_agency": False,
    },
    {
        "company": "fabasoft",
        "title": "Software Engineer",
        "url": "https://www.karriere.at/jobs/10034182",
        "is_agency": False,
    },
    {
        "company": "elevenlabs",
        "title": "Applied AI Engineer",
        "url": "https://www.arbeitnow.ch/jobs/companies/elevenlabs/remote-applied-ai-engineer-404690",
        "is_agency": False,
    },
    {
        "company": "weblyzard technology gmbh",
        "title": "AI & Web Engineer",
        "url": "https://www.karriere.at/jobs/10034271",
        "is_agency": False,
    },
    {
        "company": "gitlab",
        "title": "Backend Engineer (Python / AI)",
        "url": "https://www.arbeitnow.co.uk/jobs/companies/gitlab/remote-backend-engineer-pythonai-engineering-agent-foundations-499521",
        "is_agency": False,
    },
    {
        "company": "pmc international gmbh",
        "title": "Senior AI / Software Consultant",
        "url": "https://www.karriere.at/jobs/7894933",
        "is_agency": True,
    },
]


def run_smart_purge():
    db_path = db.db_path
    print(f"Connecting to database at: {db_path}")

    if not os.path.exists(db_path):
        print("Database not found. Nothing to purge.")
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Report stats prior to migration
        pre_urls = cursor.execute("SELECT count(*) FROM seen_urls").fetchone()[0]
        pre_companies = cursor.execute("SELECT count(*) FROM seen_companies").fetchone()[0]
        pre_roles = cursor.execute("SELECT count(*) FROM seen_roles").fetchone()[0]

        print("\n--- Pre-migration Counts ---")
        print(f"seen_urls:      {pre_urls}")
        print(f"seen_companies: {pre_companies}")
        print(f"seen_roles:     {pre_roles}")

        # Purge existing tables
        cursor.execute("DELETE FROM seen_urls")
        cursor.execute("DELETE FROM seen_companies")
        cursor.execute("DELETE FROM seen_roles")

        # Repopulate verified entries
        for match in VERIFIED_MATCHES:
            company = match["company"].strip().lower()
            title = match["title"].strip()
            url = match["url"].strip()

            # Record verified URL
            cursor.execute("INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,))

            # Record verified role in seen_roles
            role_key = db.generate_role_key(company, title)
            cursor.execute(
                "INSERT OR IGNORE INTO seen_roles (dedup_key, company, title) VALUES (?, ?, ?)",
                (role_key, company, title),
            )

            # Record direct employers in seen_companies (agencies omitted to allow multi-role processing)
            if not match["is_agency"] and not db.is_agency(company):
                cursor.execute(
                    "INSERT OR IGNORE INTO seen_companies (company_name) VALUES (?)",
                    (company,),
                )

        conn.commit()

        # Report post-migration stats
        post_urls = cursor.execute("SELECT count(*) FROM seen_urls").fetchone()[0]
        post_companies = cursor.execute("SELECT count(*) FROM seen_companies").fetchone()[0]
        post_roles = cursor.execute("SELECT count(*) FROM seen_roles").fetchone()[0]

        companies = [r[0] for r in cursor.execute("SELECT company_name FROM seen_companies").fetchall()]
        roles = [f"{r[0]} ({r[1]})" for r in cursor.execute("SELECT company, title FROM seen_roles").fetchall()]

        print("\n--- Post-migration Counts ---")
        print(f"seen_urls:      {post_urls} (Retained only generated application targets)")
        print(f"seen_companies: {post_companies} (Direct employers only: {', '.join(companies)})")
        print(f"seen_roles:     {post_roles} (All 7 active positions indexed)")
        print("\nActive Roles in seen_roles:")
        for r in roles:
            print(f"  - {r}")
        print("\n[SUCCESS] Smart database purge completed cleanly.")


if __name__ == "__main__":
    run_smart_purge()
