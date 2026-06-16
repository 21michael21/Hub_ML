from core.tasks.models import (
    dataset_snippet_for_task,
    detect_task_datasets,
    extract_mentor_task_solution_code,
    extract_mentor_task_test_code,
    infer_mentor_task_setup_code,
    normalize_mentor_task,
)
from core.tasks.runner import build_mentor_task_script, classify_task_result


def test_task_normalization_separates_solution_and_tests() -> None:
    raw = {
        "id": "python_3_architecture__cell_48",
        "source_notebook": "python_3_architecture.ipynb",
        "title": "Задание",
        "prompt": "Создайте класс Cell.",
        "starter_code": (
            "class Cell:\n"
            "    pass # это просто затычка, чтобы не было ошибки, можешь удалить\n"
            "    # TODO ваш код здесь\n\n\n"
            "point = Cell(3, 5)\n"
            "assert point.x == 3\n"
            "assert point.y == 5"
        ),
        "tests": ["assert point.x == 3", "assert point.y == 5"],
        "has_asserts": True,
        "confidence": "high",
    }

    task = normalize_mentor_task(raw)

    assert task is not None
    assert "assert point.x" not in task["solution_starter"]
    assert "class Cell" in task["solution_starter"]
    assert "point = Cell(3, 5)" in task["test_code"]
    assert "assert point.y == 5" in task["test_code"]


def test_extract_solution_and_test_code_from_starter() -> None:
    starter = "x = ...\n\nassert x == 42"
    test_code = extract_mentor_task_test_code(starter)
    solution_code = extract_mentor_task_solution_code(starter, test_code)

    assert test_code == "assert x == 42"
    assert solution_code == "x = ..."


def test_build_script_always_appends_official_tests() -> None:
    script = build_mentor_task_script(
        solution_code="x = 1\nassert x == 0",
        test_code="assert x == 1",
        setup_code="seed = 123",
    )

    assert "# --- setup ---\nseed = 123" in script
    assert "# --- solution ---\nx = 1\nassert x == 0" in script
    assert script.rstrip().endswith("# --- tests ---\nassert x == 1")


def test_result_classification() -> None:
    assert classify_task_result({"ok": True, "outputs": []}) == "PASS"
    assert classify_task_result(
        {
            "ok": False,
            "outputs": [{"type": "error", "ename": "AssertionError", "evalue": ""}],
        }
    ) == "FAIL"
    assert classify_task_result(
        {
            "ok": False,
            "outputs": [{"type": "error", "ename": "NameError", "evalue": "x"}],
        }
    ) == "ERROR"
    assert classify_task_result({"timed_out": True, "ok": False}) == "TIMEOUT"
    assert classify_task_result({"ok": False, "error": "KernelBusy", "outputs": []}) == "KERNEL_BUSY"


def test_dataset_snippet_detection_uses_relative_paths() -> None:
    task = {
        "title": "Pandas",
        "prompt": "Загрузите таблицу df_events.csv в переменную df_events_task.",
        "starter_code": "df_events_task = ...",
        "solution_starter": "df_events_task = ...",
        "test_code": "assert rows_count == 378299",
    }

    assert detect_task_datasets(task) == ["df_events.csv"]
    snippet = dataset_snippet_for_task(task)
    assert 'pd.read_csv("datasets/df_events.csv")' in snippet
    assert "/datasets/" not in snippet


def test_dependent_pandas_setup_is_inferred() -> None:
    task = {
        "title": "Фильтрация",
        "prompt": "Оставьте в df_events_task только события и сохраните в screen_views_late.",
        "starter_code": "screen_views_late = ...\n\nassert len(screen_views_late) == 27205",
        "solution_starter": "screen_views_late = ...",
        "test_code": "assert len(screen_views_late) == 27205",
    }

    setup = infer_mentor_task_setup_code(task)

    assert 'pd.read_csv("datasets/df_events.csv")' in setup
    assert "df_events_task =" in setup
    assert "screen_views_late =" not in setup
