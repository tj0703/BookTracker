import json
import os
import subprocess
import sys


def run_cli(args, data_dir):
    env = dict(os.environ, APP_CLI_DATA_DIR=str(data_dir))
    return subprocess.run(
        [sys.executable, "-m", "app_cli.cli", *args],
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )


def add_book(data_dir, title, rating=None):
    args = [
        "book",
        "add",
        "--title",
        title,
        "--completed",
        "2026-01-01",
        "--review",
        "Loved it.",
        "--review-date",
        "2026-01-02",
    ]
    if rating is not None:
        args += ["--rating", str(rating)]
    return run_cli(args, data_dir)


def test_help_commands_do_not_error(tmp_path):
    result = run_cli(["--help"], tmp_path)
    assert result.returncode == 0

    result = run_cli(["book", "--help"], tmp_path)
    assert result.returncode == 0

    result = run_cli(["book", "search", "--help"], tmp_path)
    assert result.returncode == 0

    result = run_cli(["book", "search", "title", "--help"], tmp_path)
    assert result.returncode == 0

    result = run_cli(["book", "search", "author", "--help"], tmp_path)
    assert result.returncode == 0


def test_search_title_missing_argument_exits_cleanly(tmp_path):
    result = run_cli(["book", "search", "title"], tmp_path)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_search_author_missing_argument_exits_cleanly(tmp_path):
    result = run_cli(["book", "search", "author"], tmp_path)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_add_persists_across_separate_processes(tmp_path):
    add_result = add_book(tmp_path, "Dune", rating=5)
    assert add_result.returncode == 0
    assert "Added 'Dune'." in add_result.stdout

    list_result = run_cli(["book", "list"], tmp_path)
    assert list_result.returncode == 0
    assert "Dune" in list_result.stdout
    assert "rating: 5/5" in list_result.stdout

    data_file = tmp_path / "books.json"
    assert data_file.exists()
    stored = json.loads(data_file.read_text(encoding="utf-8"))
    assert stored["books"][0]["title"] == "Dune"


def test_invalid_rating_exits_nonzero_with_clean_error(tmp_path):
    result = add_book(tmp_path, "Dune", rating=9)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_invalid_date_exits_nonzero_with_clean_error(tmp_path):
    result = run_cli(
        [
            "book",
            "add",
            "--title",
            "Dune",
            "--completed",
            "not-a-date",
            "--review",
            "Loved it.",
            "--review-date",
            "2026-01-02",
        ],
        tmp_path,
    )
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_non_latin_title_does_not_crash_output(tmp_path):
    # Finna's catalog includes non-Latin titles/authors (Cyrillic, CJK,
    # etc.). Printing them must never crash, even when stdout is piped
    # (as it is here) rather than attached to a real console.
    title = "Достоевский"

    add_result = add_book(tmp_path, title, rating=5)
    assert add_result.returncode == 0
    assert "Traceback" not in add_result.stderr

    list_result = run_cli(["book", "list"], tmp_path)
    assert list_result.returncode == 0
    assert "Traceback" not in list_result.stderr
    assert title in list_result.stdout


def test_recommend_gate_unlocks_after_ten_rated_books_across_processes(tmp_path):
    for i in range(9):
        result = add_book(tmp_path, f"Book {i}", rating=5)
        assert result.returncode == 0

    result = run_cli(["book", "recommend"], tmp_path)
    assert result.returncode == 0
    assert "Rated books: 9/10" in result.stdout

    result = add_book(tmp_path, "Book 9", rating=5)
    assert result.returncode == 0
    assert "Rated books:" not in result.stdout
