from tools.check_required_topic_sources import (
    REQUIRED_TOPIC_SOURCES,
    check_required_topic_sources,
)


def resource(resource_id: str) -> dict[str, object]:
    return {
        "id": resource_id,
        "title": resource_id.replace("_", " ").title(),
        "url": f"https://example.org/{resource_id}",
        "track": "Interview Prep",
        "type": "guide",
        "language": "en",
        "cost": "free",
    }


def test_required_topic_sources_pass_when_accepted_sources_exist() -> None:
    records = []
    for source_ids in REQUIRED_TOPIC_SOURCES.values():
        records.append(resource(next(iter(source_ids))))

    result = check_required_topic_sources(records)

    assert result.passed is True
    assert result.missing == {}
    assert set(result.found) == set(REQUIRED_TOPIC_SOURCES)


def test_required_topic_sources_fail_when_topic_has_no_accepted_source() -> None:
    records = [
        resource("ml_interviews_book"),
        resource("tech_interview_coding_prep"),
        resource("github_readme_docs"),
    ]

    result = check_required_topic_sources(records)

    assert result.passed is False
    assert result.missing == {"career.resume_remote": sorted(REQUIRED_TOPIC_SOURCES["career.resume_remote"])}


def test_required_topic_sources_ignore_unrelated_sources() -> None:
    records = [resource("unrelated_interview_blog")]

    result = check_required_topic_sources(records)

    assert result.passed is False
    assert len(result.missing) == len(REQUIRED_TOPIC_SOURCES)
