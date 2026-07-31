from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "tracerelay"
PROHIBITED_IMPORT_ROOTS = {
    "agents",
    "anthropic",
    "autogen",
    "crewai",
    "langchain",
    "langgraph",
    "openai",
}


def test_package_identity() -> None:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    try:
        import tracerelay

        assert tracerelay.__version__ == "1.0.0.dev0"
    finally:
        sys.path.pop(0)
        sys.modules.pop("tracerelay", None)


def test_minimal_package_configuration() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["requires-python"] == ">=3.13,<3.14"
    assert pyproject["project"]["dependencies"] == []
    assert pyproject["project"]["optional-dependencies"] == {
        "test": ["pytest==9.1.1"]
    }
    assert "package-data" not in pyproject["tool"]["setuptools"]


def test_retired_contract_bootstrap_is_absent() -> None:
    retired_directories = [
        REPOSITORY_ROOT / "implementation",
        REPOSITORY_ROOT / "requirements",
        PACKAGE_ROOT / "assets",
        REPOSITORY_ROOT / "tests" / "contract",
        REPOSITORY_ROOT / "docs" / "archive",
    ]
    remaining_files = [
        file
        for directory in retired_directories
        if directory.exists()
        for file in directory.rglob("*")
        if file.is_file() and "__pycache__" not in file.parts
    ]
    assert remaining_files == []
    assert not (PACKAGE_ROOT / "_build_identity.json").exists()


def test_production_has_no_agent_or_model_framework_import() -> None:
    failures: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".", maxsplit=1)[0] in PROHIBITED_IMPORT_ROOTS:
                    failures.append(f"{path.name}: {name}")
    assert failures == []


def test_repository_text_is_utf8_lf_only() -> None:
    ignored_parts = {
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "build",
        "build-check",
        "dist",
    }
    binary_suffixes = {".bin", ".pyd", ".pyc", ".whl", ".zip"}
    failures: list[str] = []
    for path in sorted(REPOSITORY_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPOSITORY_ROOT)
        if any(
            part in ignored_parts or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        if path.suffix.lower() in binary_suffixes:
            continue
        data = path.read_bytes()
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            failures.append(f"{relative.as_posix()}: {error}")
            continue
        if b"\r" in data:
            failures.append(f"{relative.as_posix()}: contains CR byte")
    assert failures == []
