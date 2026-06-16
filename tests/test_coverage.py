from tools.check_coverage import (
    SourceItem,
    classify_topic_coverage,
    evaluate_topic,
    pattern_hits,
)


def test_pattern_hits_are_case_insensitive() -> None:
    text = "Pandas DataFrame and GROUPBY practice"

    assert pattern_hits(text, ["dataframe", "groupby", "missing"]) == ["dataframe", "groupby"]


def test_classification_states() -> None:
    assert classify_topic_coverage(False, False, False, False, False) == "missing"
    assert classify_topic_coverage(True, False, False, False, False) == "theory_only"
    assert classify_topic_coverage(False, True, False, False, False) == "practice_only"
    assert classify_topic_coverage(True, True, False, False, False, theory_quality=80) == "covered"
    assert classify_topic_coverage(True, True, False, False, False, theory_quality=20) == "partial"


def test_evaluate_topic_combines_theory_and_tasks() -> None:
    topic = {
        "id": "data.pandas",
        "title": "Pandas",
        "track": "Data Analysis",
        "level": "beginner",
        "required": True,
        "expected_note_patterns": ["pandas", "dataframe"],
        "expected_task_tags": ["analysis_3_pandas"],
        "expected_practice_patterns": ["eda"],
        "expected_project_types": ["eda notebook"],
    }
    theory = [
        SourceItem(
            kind="theory",
            path="02_Data_Analysis/Pandas/01_Pandas_Basics.md",
            title="Pandas Basics",
            text="DataFrame read_csv groupby",
            quality_score=80,
        )
    ]
    tasks = [
        SourceItem(
            kind="mentor_task",
            path="analysis_3_pandas.ipynb",
            title="Task",
            text="analysis_3_pandas df_events",
        )
    ]

    result = evaluate_topic(topic, theory, [], tasks, [], [])

    assert result["status"] == "covered"
    assert result["evidence_counts"]["theory"] == 1
    assert result["evidence_counts"]["mentor_tasks"] == 1
