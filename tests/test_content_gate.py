from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_theory_notes import scan_vault
from tools.check_content_gate import (
    DEFAULT_MATRIX,
    DEFAULT_PRACTICE_DIR,
    DEFAULT_RESOURCES,
    DEFAULT_TASKS,
    build_content_gate_payload,
    evaluate_topic_gate,
    load_json,
    load_matrix,
    load_practice_items,
    load_task_items,
)


REGISTERED_URL = "https://pandas.pydata.org/docs/user_guide/index.html"
UNREGISTERED_URL = "https://not-registered.example.org/pandas"


def topic() -> dict[str, object]:
    return {
        "id": "da.pandas_basics",
        "title": "Pandas Basics",
        "track": "Data Analysis",
        "required": True,
        "expected_note_patterns": ["pandas basics"],
        "expected_task_tags": ["pandas"],
        "expected_practice_patterns": ["pandas practice"],
    }


def audit_note(
    *,
    score: int = 80,
    has_sources: bool = True,
    ai_dump: bool = False,
) -> dict[str, object]:
    return {
        "relative_path": "02_Data_Analysis/Pandas/01_Pandas_Basics.md",
        "section": "Data Analysis",
        "title": "Pandas Basics",
        "quality_score": score,
        "has_sources_section": has_sources,
        "likely_ai_dump_or_placeholder": ai_dump,
    }


def write_note(vault: Path, body: str) -> None:
    note_path = vault / "02_Data_Analysis" / "Pandas" / "01_Pandas_Basics.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(body, encoding="utf-8")


def resources(url: str = REGISTERED_URL) -> list[dict[str, object]]:
    return [
        {
            "id": "pandas_user_guide",
            "title": "Pandas User Guide",
            "track": "Data Analysis",
            "type": "docs",
            "language": "en",
            "cost": "free",
            "url": url,
        }
    ]


def practice_items() -> list[dict[str, object]]:
    return [
        {
            "id": "practice/pandas_practice.md",
            "title": "Pandas practice",
            "text": "pandas practice groupby dataframe",
        }
    ]


def checkable_tasks() -> list[dict[str, object]]:
    return [
        {
            "id": "analysis_3_pandas__cell_10",
            "title": "Pandas task",
            "text": "analysis_3_pandas dataframe pandas",
            "has_asserts": True,
        }
    ]


def test_topic_passes_all_definition_of_done_rules(tmp_path: Path) -> None:
    write_note(
        tmp_path,
        f"# Pandas Basics\n\n## Sources\n\nOfficial docs: {REGISTERED_URL}\n",
    )

    result = evaluate_topic_gate(
        topic(),
        notes=[audit_note()],
        vault=tmp_path,
        registered_urls={REGISTERED_URL},
        practice_items=practice_items(),
        task_items=[],
        threshold=70,
    )

    assert result["status"] == "PASS"
    assert result["rules"]["rule1_note_quality"]["passed"] is True
    assert result["rules"]["rule2_ai_dump_flag"]["passed"] is True
    assert result["rules"]["rule3_sources"]["registered_url_count"] == 1
    assert result["rules"]["rule4_practice_or_task"]["practice_count"] == 1


def test_rule3_fails_when_sources_header_has_no_url(tmp_path: Path) -> None:
    write_note(tmp_path, "# Pandas Basics\n\n## Sources\n\nSource: needs review\n")

    result = evaluate_topic_gate(
        topic(),
        notes=[audit_note()],
        vault=tmp_path,
        registered_urls={REGISTERED_URL},
        practice_items=practice_items(),
        task_items=[],
        threshold=70,
    )

    assert result["status"] == "FAIL"
    assert result["rules"]["rule3_sources"]["passed"] is False
    assert "0 registered URLs" in result["rules"]["rule3_sources"]["detail"]
    assert "rule3" in result["failed_rules"]


def test_rule3_fails_when_url_is_not_registered(tmp_path: Path) -> None:
    write_note(
        tmp_path,
        f"# Pandas Basics\n\n## Sources\n\nUseful link: {UNREGISTERED_URL}\n",
    )

    result = evaluate_topic_gate(
        topic(),
        notes=[audit_note()],
        vault=tmp_path,
        registered_urls={REGISTERED_URL},
        practice_items=practice_items(),
        task_items=[],
        threshold=70,
    )

    assert result["status"] == "FAIL"
    assert result["rules"]["rule3_sources"]["passed"] is False
    assert result["rules"]["rule3_sources"]["registered_url_count"] == 0


def test_rule2_fails_when_note_is_marked_ai_dump_or_placeholder(tmp_path: Path) -> None:
    write_note(
        tmp_path,
        f"# Pandas Basics\n\n## Sources\n\nOfficial docs: {REGISTERED_URL}\n",
    )

    result = evaluate_topic_gate(
        topic(),
        notes=[audit_note(ai_dump=True)],
        vault=tmp_path,
        registered_urls={REGISTERED_URL},
        practice_items=practice_items(),
        task_items=[],
        threshold=70,
    )

    assert result["status"] == "FAIL"
    assert result["rules"]["rule2_ai_dump_flag"]["passed"] is False
    assert "rule2" in result["failed_rules"]


def test_rule4_accepts_checkable_mentor_task_without_practice(tmp_path: Path) -> None:
    write_note(
        tmp_path,
        f"# Pandas Basics\n\n## Sources\n\nOfficial docs: {REGISTERED_URL}\n",
    )

    result = evaluate_topic_gate(
        topic(),
        notes=[audit_note()],
        vault=tmp_path,
        registered_urls={REGISTERED_URL},
        practice_items=[],
        task_items=checkable_tasks(),
        threshold=70,
    )

    assert result["status"] == "PASS"
    assert result["rules"]["rule4_practice_or_task"]["task_count"] == 1


def test_payload_summarizes_required_failures(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_note(vault, "# Pandas Basics\n\n## Sources\n\nSource: needs review\n")
    audit = {"vault": str(vault), "notes": [audit_note()]}

    payload = build_content_gate_payload(
        topics=[topic()],
        audit=audit,
        resources=resources(),
        practice_items=[],
        task_items=[],
        threshold=70,
    )

    assert payload["summary"]["total_topics"] == 1
    assert payload["summary"]["passed_topics"] == 0
    assert payload["summary"]["failed_topics"] == 1
    assert payload["summary"]["failed_rule_counts"]["rule3"] == 1
    assert payload["summary"]["failed_required_topic_ids"] == ["da.pandas_basics"]


def test_payload_can_be_filtered_to_one_topic(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_note(vault, "# Pandas Basics\n\n## Sources\n\nSource: needs review\n")
    audit = {"vault": str(vault), "notes": [audit_note()]}
    extra_topic = {
        "id": "sql.aggregation_windows",
        "title": "SQL Aggregations and Window Functions",
        "track": "SQL",
        "required": True,
        "expected_note_patterns": ["window function"],
        "expected_task_tags": ["window function"],
        "expected_practice_patterns": ["window function"],
    }

    from tools.check_content_gate import filter_topics

    filtered = filter_topics([topic(), extra_topic], "sql.aggregation_windows")
    payload = build_content_gate_payload(
        topics=filtered,
        audit=audit,
        resources=resources(),
        practice_items=[],
        task_items=[],
        threshold=70,
    )

    assert [item["id"] for item in filtered] == ["sql.aggregation_windows"]
    assert payload["summary"]["total_topics"] == 1
    assert payload["topics"][0]["id"] == "sql.aggregation_windows"


def test_topic_matching_requires_two_hits_for_multi_pattern_topics(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_note(
        vault,
        f"# Pandas Basics\n\n## Sources\n\nOfficial docs: {REGISTERED_URL}\n",
    )
    audit = {"vault": str(vault), "notes": [audit_note()]}
    broad_topic = {
        "id": "python.basics",
        "title": "Python Basics",
        "track": "Python",
        "required": True,
        "expected_note_patterns": ["python", "function", "dict"],
        "expected_task_tags": ["python", "function"],
        "expected_practice_patterns": ["python", "function"],
    }

    payload = build_content_gate_payload(
        topics=[broad_topic],
        audit=audit,
        resources=resources(),
        practice_items=[{"id": "function_only", "title": "Function drill", "text": "function"}],
        task_items=[{"id": "task_function", "title": "Function task", "text": "function", "has_asserts": True}],
        threshold=70,
    )

    result = payload["topics"][0]
    assert result["status"] == "FAIL"
    assert result["rules"]["rule1_note_quality"]["matched_notes"] == 0
    assert result["rules"]["rule4_practice_or_task"]["practice_count"] == 0
    assert result["rules"]["rule4_practice_or_task"]["task_count"] == 0


def test_strict_cli_exits_nonzero_when_required_topic_fails(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_note(vault, "# Pandas Basics\n\n## Sources\n\nSource: needs review\n")

    matrix_path = tmp_path / "matrix.json"
    audit_path = tmp_path / "audit.json"
    resources_path = tmp_path / "resources.json"
    practice_dir = tmp_path / "practice"
    tasks_path = tmp_path / "tasks.json"
    output_dir = tmp_path / "reports"
    practice_dir.mkdir()

    matrix_path.write_text(json.dumps({"topics": [topic()]}), encoding="utf-8")
    audit_path.write_text(json.dumps({"vault": str(vault), "notes": [audit_note()]}), encoding="utf-8")
    resources_path.write_text(json.dumps(resources()), encoding="utf-8")
    tasks_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")

    from tools.check_content_gate import main

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--matrix",
                str(matrix_path),
                "--audit",
                str(audit_path),
                "--resources",
                str(resources_path),
                "--practice-dir",
                str(practice_dir),
                "--tasks",
                str(tasks_path),
                "--output-dir",
                str(output_dir),
                "--strict",
            ]
        )

    assert exc.value.code == 1
    assert (output_dir / "content_gate_report.json").exists()


def test_committed_sample_vault_has_at_least_one_gate_pass_and_fail() -> None:
    sample_vault = Path("tests/fixtures/sample_vault").resolve()
    notes = scan_vault(sample_vault)

    payload = build_content_gate_payload(
        topics=load_matrix(DEFAULT_MATRIX),
        audit={"vault": str(sample_vault), "notes": notes},
        resources=load_json(DEFAULT_RESOURCES),
        practice_items=load_practice_items(DEFAULT_PRACTICE_DIR),
        task_items=load_task_items(DEFAULT_TASKS),
        threshold=70,
    )

    summary = payload["summary"]
    passed_topic_ids = {str(topic["id"]) for topic in payload["topics"] if topic["status"] == "PASS"}
    assert summary["passed_topics"] >= 1
    assert summary["failed_topics"] >= 1
    assert "python.basics" in passed_topic_ids
