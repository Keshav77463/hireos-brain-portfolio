"""CSV contract, business consistency and API shell checks; database access is forbidden."""

import csv
import io
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.ask.citation_validator import validate_citations
from app.ingest.operational import parse_operational
from app.ingest.service import MAX_BYTES

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "temporary"


def fixture_rows():
    with (ROOT / "tenant_a" / "operations_a.csv").open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def encode(rows):
    result = io.StringIO()
    writer = csv.DictWriter(result, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return result.getvalue().encode("utf-8")


@pytest.mark.parametrize("tenant,size", [("a", 30), ("b", 5), ("c", 7)])
def test_agreed_fixture_contract(tenant, size):
    data = (ROOT / f"tenant_{tenant}" / f"operations_{tenant}.csv").read_bytes()
    rows = parse_operational(data)
    assert len(rows) == size
    assert list(type(rows[0]).model_fields) == (
        "submission_id,job_id,client_name,specialty,candidate_ref,submitted_at,status,"
        "rejection_reason,interview_id,interviewed_at,start_id,started_at,updated_at"
    ).split(",")
    assert all(row.specialty == "ICU RN" for row in rows)
    assert all(row.updated_at >= row.submitted_at for row in rows)
    assert all(row.start_id is None or row.interview_id is not None for row in rows)


@pytest.mark.parametrize(
    "column", ["recruiter_id", "sourcing_channel", "acls_verified", "interview_outcome"]
)
def test_removed_columns_are_rejected(column):
    rows = fixture_rows()
    for row in rows:
        row[column] = "unused"
    with pytest.raises(HTTPException, match="Required CSV columns"):
        parse_operational(encode(rows))


@pytest.mark.parametrize(
    "problem",
    [
        "invalid_status",
        "missing_rejection_reason",
        "partial_interview",
        "partial_start",
        "early_interview",
        "early_start",
        "old_update",
        "interviewed_without_event",
        "started_without_event",
        "missing_timezone",
        "duplicate_submission",
        "duplicate_outcome",
        "inconsistent_job",
        "unexpected_tenant",
        "missing_column",
        "identifier_with_spaces",
    ],
)
def test_rejects_invalid_csv_before_database_access(problem):
    rows = fixture_rows()
    if problem == "invalid_status":
        rows[-1]["status"] = "made_up"
    elif problem == "missing_rejection_reason":
        rows[-1]["status"] = "rejected"
    elif problem == "partial_interview":
        rows[-1]["interview_id"] = "INT-PARTIAL"
    elif problem == "partial_start":
        rows[-1]["start_id"] = "START-PARTIAL"
    elif problem == "early_interview":
        rows[0]["interviewed_at"] = "2026-05-01T00:00:00Z"
    elif problem == "early_start":
        rows[0]["started_at"] = "2026-05-11T00:00:00Z"
    elif problem == "old_update":
        rows[0]["updated_at"] = "2026-05-01T00:00:00Z"
    elif problem == "interviewed_without_event":
        rows[-1]["status"] = "interviewed"
    elif problem == "started_without_event":
        rows[-1]["status"] = "started"
    elif problem == "missing_timezone":
        rows[0]["submitted_at"] = "2026-05-10T09:00:00"
    elif problem == "duplicate_submission":
        rows.append(dict(rows[0]))
    elif problem == "duplicate_outcome":
        rows[0]["start_id"] = rows[0]["interview_id"]
    elif problem == "inconsistent_job":
        rows[-1]["specialty"] = "ER RN"
    elif problem == "unexpected_tenant":
        for row in rows:
            row["tenant_id"] = "forged"
    elif problem == "missing_column":
        for row in rows:
            row.pop("candidate_ref")
    elif problem == "identifier_with_spaces":
        rows[0]["submission_id"] = "invalid identifier"
    with pytest.raises(HTTPException) as rejected:
        parse_operational(encode(rows))
    assert rejected.value.status_code == 422


def test_valid_rejection_preserves_recorded_reason():
    rows = fixture_rows()
    rows[-1].update(status="rejected", rejection_reason="Client recorded an experience mismatch")
    parsed = parse_operational(encode(rows))
    assert parsed[-1].rejection_reason == "Client recorded an experience mismatch"
    assert parsed[-1].interview_id is None


def test_bom_and_reordered_columns_are_supported():
    rows = [dict(reversed(list(row.items()))) for row in fixture_rows()]
    parsed = parse_operational(b"\xef\xbb\xbf" + encode(rows))
    assert len(parsed) == 30


def test_equivalent_timezone_offsets_have_identical_validated_payloads():
    original = fixture_rows()
    equivalent = [dict(row) for row in original]
    for row in equivalent:
        row["updated_at"] = "2026-07-01T05:30:00+05:30"
    first = parse_operational(encode(original))
    second = parse_operational(encode(equivalent))
    assert [row.model_dump(mode="json") for row in first] == [
        row.model_dump(mode="json") for row in second
    ]


@pytest.mark.parametrize(
    "data", [b"", b"\xff", b"x" * (MAX_BYTES + 1)], ids=["empty", "non_utf8", "oversize"]
)
def test_invalid_upload_sizes_and_encoding(data):
    with pytest.raises(HTTPException) as rejected:
        parse_operational(data)
    assert rejected.value.status_code == 422


def test_row_limit_prevents_unbounded_import():
    template = fixture_rows()[-1]
    rows = [{**template, "submission_id": f"SUB-{number}"} for number in range(5001)]
    with pytest.raises(HTTPException, match="5,000"):
        parse_operational(encode(rows))


def test_csv_cells_must_match_header():
    raw = encode(fixture_rows())
    lines = raw.split(b"\r\n")
    lines[-2] += b",unexpected"
    with pytest.raises(HTTPException, match="cells"):
        parse_operational(b"\r\n".join(lines))


def test_page_shell_and_openapi_expose_new_schema(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "13-column CSV" in response.text
    assert 'value="operational"' in response.text
    assert 'value="combined"' not in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.post("/api/ask", json={"question": "Show conversion"}).status_code == 401


def test_citations_cannot_reference_unauthorized_ids():
    with pytest.raises(ValueError):
        validate_citations(
            [{"text": "An unsupported claim", "citations": ["another-tenant:record"]}],
            [{"id": "authorized:record"}],
        )
