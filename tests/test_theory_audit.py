from pathlib import Path

from tools.audit_theory_notes import build_summary, scan_vault


def test_scan_vault_ignores_hidden_folders_and_collects_metrics(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "workspace.md").write_text("# Hidden\n", encoding="utf-8")
    (vault / "ml").mkdir()
    (vault / "ml" / "model_eval.md").write_text(
        """---
title: Model Evaluation
tags: [ml, metrics]
---

# Model Evaluation

## Examples

```python
print("auc")
```

## Sources

- https://scikit-learn.org/

[[Metrics]]
""",
        encoding="utf-8",
    )

    notes = scan_vault(vault)

    assert len(notes) == 1
    note = notes[0]
    assert note["relative_path"] == "ml/model_eval.md"
    assert note["section"] == "Ml"
    assert note["title"] == "Model Evaluation"
    assert note["code_block_count"] == 1
    assert note["wiki_link_count"] == 1
    assert note["external_link_count"] == 1
    assert note["tag_count"] == 2
    assert note["has_examples"] is True
    assert note["has_sources_section"] is True


def test_build_summary_flags_weak_notes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "placeholder.md").write_text(
        """---
title: Placeholder
status: draft
---

TODO
""",
        encoding="utf-8",
    )

    notes = scan_vault(vault)
    summary = build_summary(notes)

    assert summary["total_notes"] == 1
    assert summary["weakest_notes"][0]["likely_thin_note"] is True
    assert summary["weakest_notes"][0]["likely_ai_dump_or_placeholder"] is True
    assert summary["average_quality_score"] < 70
