from pathlib import Path

from core.portfolio.exporter import (
    EXPORT_WARNING,
    extract_markdown_section,
    generate_portfolio_markdown,
    portfolio_export_path,
)


def sample_project() -> dict:
    return {
        "id": "orders_eda_report",
        "title": "Orders EDA Report",
        "goal": "Analyze orders data.",
        "datasets": ["df_orders.csv"],
        "related_dataset_names": ["df_orders.csv"],
        "skills": ["pandas", "visualization"],
        "milestones": [
            {"id": "quality", "title": "Run quality checks", "portfolio_output": "Quality checks table"},
            {"id": "charts", "title": "Create charts", "portfolio_output": "Revenue line chart"},
        ],
        "deliverables": ["Mini report"],
        "portfolio_prompt": "Explain the findings manually.",
        "related_portfolio_templates": [
            {
                "title": "Mini report",
                "what_to_write": "Write real findings.",
                "chart_or_table": "Daily revenue chart.",
                "readme_bullet": "Built an orders EDA report.",
            }
        ],
    }


def sample_card() -> dict:
    return {
        "id": "data_analysis_orders_eda.md",
        "title": "Orders EDA Practice",
        "section": "Data Analysis",
        "difficulty": "easy",
        "est_time": "45 мин",
        "dataset": "df_orders.csv",
        "body": """
## Что сделать

Analyze orders.

## Что положить в портфолио

Mini EDA report with one chart and one limitation.
""",
    }


def test_generate_portfolio_markdown_uses_real_metadata_without_fake_findings() -> None:
    markdown = generate_portfolio_markdown([sample_project()], [sample_card()])

    assert "# ML Learning Portfolio" in markdown
    assert EXPORT_WARNING in markdown
    assert "## Orders EDA Report" in markdown
    assert "df_orders.csv" in markdown
    assert "Daily revenue chart." in markdown
    assert "Fill manually: data quality limits" in markdown
    assert "Built an orders EDA report." in markdown
    assert "## Orders EDA Practice" in markdown
    assert "Mini EDA report with one chart" in markdown


def test_practice_export_can_include_saved_output_record() -> None:
    markdown = generate_portfolio_markdown(
        [],
        [sample_card()],
        {"data_analysis_orders_eda.md": {"artifact": "portfolio/orders.md", "summary": "Finished EDA"}},
    )

    assert "Saved artifact path/link: portfolio/orders.md" in markdown
    assert "Saved note: Finished EDA" in markdown


def test_extract_markdown_section() -> None:
    assert extract_markdown_section(sample_card()["body"], "Что положить в портфолио") == (
        "Mini EDA report with one chart and one limitation."
    )


def test_portfolio_export_path_prefers_readme_then_generated(tmp_path: Path) -> None:
    assert portfolio_export_path(tmp_path) == tmp_path / "README.md"

    (tmp_path / "README.md").write_text("existing", encoding="utf-8")

    assert portfolio_export_path(tmp_path) == tmp_path / "generated_portfolio.md"
