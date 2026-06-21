from tools.validate_resources import (
    validate_resource_record,
    validate_resources,
    validate_url,
    validation_summary,
)


VALID_TRACKS = {"SQL", "GenAI and RAG", "Data Analysis"}


def valid_record() -> dict[str, object]:
    return {
        "id": "promptingguide_ai",
        "title": "Prompt Engineering Guide",
        "track": "GenAI and RAG",
        "type": "guide",
        "language": "en",
        "cost": "free",
        "url": "https://www.promptingguide.ai/",
        "related_hubml_modules": ["Theory"],
        "expected_output": ["note"],
    }


def test_validate_url_rejects_missing_scheme_and_placeholders() -> None:
    assert validate_url("www.promptingguide.ai")
    assert validate_url("https://example.com/resource")
    assert validate_url("https://docs.example.org/TODO")
    assert validate_url("https://docs.example.org/<topic>")


def test_valid_resource_has_no_errors() -> None:
    errors = validate_resources([valid_record()], VALID_TRACKS)

    assert errors == []


def test_missing_required_field_names_resource_and_field() -> None:
    record = valid_record()
    record.pop("title")

    errors = validate_resources([record], VALID_TRACKS)

    assert "FAIL promptingguide_ai: missing required field 'title'" in errors


def test_enum_error_lists_allowed_values() -> None:
    record = valid_record()
    record["cost"] = "gratis"

    errors = validate_resources([record], VALID_TRACKS)

    assert "FAIL promptingguide_ai: cost 'gratis' not in {free,freemium,paid}" in errors


def test_duplicate_id_is_rejected() -> None:
    errors = validate_resources([valid_record(), valid_record()], VALID_TRACKS)

    assert "FAIL promptingguide_ai: duplicate id 'promptingguide_ai'" in errors


def test_orphan_track_is_rejected() -> None:
    record = valid_record()
    record["track"] = "GenAI"

    errors = validate_resources([record], VALID_TRACKS)

    assert "FAIL promptingguide_ai: track 'GenAI' not in coverage_matrix" in errors


def test_list_fields_must_be_lists() -> None:
    record = valid_record()
    record["expected_output"] = "note"

    errors = validate_resource_record(record, index=0, seen_ids=set(), valid_tracks=VALID_TRACKS)

    assert "FAIL promptingguide_ai: expected_output must be a list" in errors


def test_validation_summary_counts_records_and_tracks() -> None:
    first = valid_record()
    second = valid_record()
    second["id"] = "practice_window_functions"
    second["track"] = "SQL"

    assert validation_summary([first, second]) == "resources OK: 2 records, 2 tracks covered"
