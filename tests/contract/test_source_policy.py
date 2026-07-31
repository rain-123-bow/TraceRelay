from __future__ import annotations

import ast
import json
from pathlib import Path

from contract_authority import (
    IMPLEMENTATION_MANIFEST_SHA256,
    IMPLEMENTATION_SNAPSHOT_ID,
    PACKAGE_ROOT,
    REPOSITORY_ROOT,
    REQUIREMENT_MANIFEST_SHA256,
    REQUIREMENT_SNAPSHOT_ID,
)


PROHIBITED_AI_IMPORT_ROOTS = {
    "agents",
    "anthropic",
    "autogen",
    "crewai",
    "langchain",
    "langgraph",
    "openai",
}
VALID_PHASES = {f"TR-I{index:02d}" for index in range(13)} | {"TR-I00R"}
IGNORED_PARTS = {
    ".git",
    ".hypothesis",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}
BINARY_SUFFIXES = {".bin", ".pyd", ".pyc", ".whl", ".zip"}


def _production_python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _inventory_matches(entry: dict[str, object], relative_path: str) -> bool:
    reserved_path = str(entry["reserved_path"])
    if entry["kind"] == "file":
        return relative_path == reserved_path
    return (
        relative_path == reserved_path
        or relative_path.startswith(f"{reserved_path}/")
    )


def _repository_product_files() -> list[str]:
    product_files: list[str] = []
    for path in sorted(REPOSITORY_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPOSITORY_ROOT)
        if any(
            part in IGNORED_PARTS or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        product_files.append(relative.as_posix())
    return product_files


def test_production_has_no_ai_or_agent_framework_import() -> None:
    failures: list[str] = []
    for path in _production_python_files():
        for imported in _imports(path):
            if imported.split(".", maxsplit=1)[0] in PROHIBITED_AI_IMPORT_ROOTS:
                failures.append(f"{path.relative_to(REPOSITORY_ROOT)} -> {imported}")
    assert failures == []


def test_production_import_boundaries() -> None:
    failures: list[str] = []
    for path in _production_python_files():
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        for imported in _imports(path):
            if imported == "tests" or imported.startswith("tests."):
                failures.append(f"{relative} imports {imported}")
            if relative.startswith("runtime/") and (
                imported == "tracerelay.verifier"
                or imported.startswith("tracerelay.verifier.")
            ):
                failures.append(f"{relative} imports {imported}")
            if relative.startswith("verifier/") and (
                imported == "tracerelay.runtime"
                or imported.startswith("tracerelay.runtime.")
            ):
                failures.append(f"{relative} imports {imported}")
    assert failures == []


def test_source_inventory_has_unambiguous_ownership() -> None:
    inventory_path = (
        REPOSITORY_ROOT / "implementation" / "source-inventory.v1.json"
    )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["schema_version"] == "tracerelay.source_inventory.v1"
    assert inventory["rule"] == (
        "Only the primary phase may create or modify the reserved path unless "
        "a later phase is explicitly listed in later_modification_phases."
    )
    assert inventory["authority"] == {
        "requirement_snapshot_id": REQUIREMENT_SNAPSHOT_ID,
        "requirement_manifest_sha256": REQUIREMENT_MANIFEST_SHA256,
        "implementation_snapshot_id": IMPLEMENTATION_SNAPSHOT_ID,
        "implementation_manifest_sha256": IMPLEMENTATION_MANIFEST_SHA256,
        "phase_dag_sha256": (
            "1e3ba36f4dffe726708a7a21a97262e548868b5c6fa3872eeb799c6f5bbbc5f7"
        ),
    }
    entries = inventory["entries"]
    reserved_paths = [entry["reserved_path"] for entry in entries]
    assert len(reserved_paths) == len(set(reserved_paths))
    assert entries
    for entry in entries:
        assert entry["reserved_path"]
        assert not Path(entry["reserved_path"]).is_absolute()
        assert ".." not in Path(entry["reserved_path"]).parts
        assert entry["primary_phase"] in VALID_PHASES
        assert entry["owner"]
        assert entry["kind"] in {"file", "directory"}
        later_phases = entry["later_modification_phases"]
        assert len(later_phases) == len(set(later_phases))
        assert all(phase in VALID_PHASES for phase in later_phases)
        assert entry["primary_phase"] not in later_phases

    by_path = {entry["reserved_path"]: entry for entry in entries}
    assert by_path["src/tracerelay/_winatomic.c"]["primary_phase"] == "TR-I01"
    assert by_path["src/tracerelay/runtime/coordinator.py"] == {
        "reserved_path": "src/tracerelay/runtime/coordinator.py",
        "kind": "file",
        "primary_phase": "TR-I03",
        "later_modification_phases": ["TR-I05"],
        "owner": "startup_coordinator",
    }
    assert by_path["src/tracerelay/entrypoints/start.py"] == {
        "reserved_path": "src/tracerelay/entrypoints/start.py",
        "kind": "file",
        "primary_phase": "TR-I03",
        "later_modification_phases": ["TR-I05"],
        "owner": "startup_entrypoint",
    }
    assert (
        by_path["src/tracerelay/runtime/ipc_authority.py"]["primary_phase"]
        == "TR-I05"
    )
    assert (
        by_path["src/tracerelay/protocol/bootstrap.py"]["primary_phase"]
        == "TR-I05"
    )
    assert (
        by_path["src/tracerelay/platform/windows/process.py"]["primary_phase"]
        == "TR-I05"
    )
    assert (
        by_path["tools/certification"]["primary_phase"]
        == "TR-I12"
    )


def test_source_inventory_covers_every_current_product_file_once() -> None:
    inventory = json.loads(
        (
            REPOSITORY_ROOT
            / "implementation"
            / "source-inventory.v1.json"
        ).read_text(encoding="utf-8")
    )
    failures: dict[str, list[str]] = {}
    for relative_path in _repository_product_files():
        matches = [
            entry["reserved_path"]
            for entry in inventory["entries"]
            if _inventory_matches(entry, relative_path)
        ]
        if len(matches) != 1:
            failures[relative_path] = matches
    assert failures == {}


def test_i00r_contains_no_i01_runtime_implementation() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in _production_python_files()
    }
    assert observed == {"src/tracerelay/__init__.py"}
    assert not (PACKAGE_ROOT / "_winatomic.c").exists()


def test_repository_text_is_utf8_lf_only() -> None:
    failures: list[str] = []
    for path in sorted(REPOSITORY_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPOSITORY_ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        data = path.read_bytes()
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            failures.append(f"{relative.as_posix()}: invalid UTF-8: {error}")
            continue
        if b"\r" in data:
            failures.append(f"{relative.as_posix()}: contains CR byte")
    assert failures == []
