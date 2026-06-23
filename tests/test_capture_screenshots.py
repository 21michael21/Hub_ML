from __future__ import annotations

from tools import capture_screenshots


def test_screenshot_targets_include_visual_checkpoint_pages() -> None:
    filenames = {target.filename for target in capture_screenshots.SCREENSHOT_TARGETS}

    assert {
        "home-cockpit.png",
        "tasks-result.png",
        "projects-detail.png",
        "notebook-output.png",
        "portfolio-export.png",
        "interview-arena.png",
        "theory-quality.png",
    }.issubset(filenames)


def test_capture_screenshots_dry_run_lists_targets(capsys) -> None:
    exit_code = capture_screenshots.main_from_args(["--dry-run", "--output-dir", "tmp/screens"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "output_dir=tmp/screens" in output
    assert "home-cockpit.png" in output
    assert "theory-quality.png" in output
