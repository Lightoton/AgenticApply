import pytest

def test_database_url_tracking(in_memory_db):
    test_url = "https://example.com/jobs/12345"

    assert not in_memory_db.is_url_seen(test_url)
    assert in_memory_db.get_all_seen_urls() == set()

    in_memory_db.mark_url_seen(test_url)

    assert in_memory_db.is_url_seen(test_url)
    assert test_url in in_memory_db.get_all_seen_urls()

    # Second mark should be idempotent (INSERT OR IGNORE)
    in_memory_db.mark_url_seen(test_url)
    assert len(in_memory_db.get_all_seen_urls()) == 1

def test_database_company_tracking(in_memory_db):
    company = "Acme Corp GmbH"

    assert not in_memory_db.is_company_seen(company)
    assert not in_memory_db.is_company_seen("acme corp gmbh")

    in_memory_db.mark_company_seen(company)

    # Check case-insensitivity and whitespace normalization
    assert in_memory_db.is_company_seen("  ACME CORP GMBH  ")
    assert in_memory_db.is_company_seen("acme corp gmbh")

def test_database_role_tracking_and_agency_allowlist(in_memory_db):
    agency = "epunkt GmbH"
    role1 = "Senior Python Developer (m/w/d)"
    role2 = "Junior AI Engineer (all genders)"

    assert in_memory_db.is_agency(agency) is True
    assert in_memory_db.is_agency("Acme Private Corp") is False

    # Mark first role from agency
    assert not in_memory_db.is_role_seen(agency, role1)
    in_memory_db.mark_role_seen(agency, role1)
    assert in_memory_db.is_role_seen(agency, role1)

    # Agency should allow different role without collision
    assert not in_memory_db.is_role_seen(agency, role2)
    in_memory_db.mark_role_seen(agency, role2)
    assert in_memory_db.is_role_seen(agency, role2)
