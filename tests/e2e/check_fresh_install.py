"""Fresh-install packaging check.

Not a pytest test (no test_ prefix, not auto-collected) — this creates a
throwaway venv, does a real (non-editable) `pip install .` of the project,
and runs the installed `app-cli` console-script entry point. Catches
pyproject.toml/entry-point/packaging mistakes that `pip install -e .`
would silently paper over.

Run manually or as a CI step:
    python tests/e2e/check_fresh_install.py
"""

import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def venv_bin(venv_dir: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def main() -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="app-cli-fresh-install-"))
    venv_dir = tmp_dir / "venv"
    try:
        print(f"Creating throwaway venv at {venv_dir} ...")
        venv.create(venv_dir, with_pip=True)

        venv_python = venv_bin(venv_dir, "python")

        print("Installing project (non-editable) ...")
        install = subprocess.run(
            [str(venv_python), "-m", "pip", "install", str(PROJECT_ROOT)],
            capture_output=True,
            encoding="utf-8",
        )
        if install.returncode != 0:
            print("FAIL: pip install failed.")
            print(install.stdout)
            print(install.stderr)
            return 1

        app_cli = venv_bin(venv_dir, "app-cli")
        if not app_cli.exists():
            print(f"FAIL: console script not found at {app_cli}")
            return 1

        print("Running installed console script: app-cli hello Tester ...")
        run = subprocess.run(
            [str(app_cli), "hello", "Tester"],
            capture_output=True,
            encoding="utf-8",
        )
        if run.returncode != 0:
            print("FAIL: app-cli hello exited non-zero.")
            print(run.stdout)
            print(run.stderr)
            return 1
        if "Hello, Tester!" not in run.stdout:
            print(f"FAIL: unexpected output: {run.stdout!r}")
            return 1

        print("PASS: fresh install works and console script runs correctly.")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
