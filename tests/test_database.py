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
