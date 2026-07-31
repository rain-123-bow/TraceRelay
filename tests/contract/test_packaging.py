from __future__ import annotations

import json
import re
import tomllib

from contract_authority import (
    BUILD_TEST_LOCK_SHA256,
    DIRECT_LOCK_SHA256,
    IMPLEMENTATION_MANIFEST_SHA256,
    IMPLEMENTATION_SNAPSHOT_ID,
    PACKAGE_ROOT,
    REPOSITORY_ROOT,
    REQUIREMENT_MANIFEST_SHA256,
    REQUIREMENT_SNAPSHOT_ID,
    REVIEW_SCHEMA_SET_SHA256,
    RUNTIME_SCHEMA_SET_SHA256,
    sha256_bytes,
)


def test_pyproject_freezes_supported_runtime_and_zero_dependencies() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    project = pyproject["project"]
    build_system = pyproject["build-system"]

    assert project["name"] == "TraceRelay"
    assert project["version"] == "1.0.0.dev0"
    assert project["requires-python"] == ">=3.13,<3.14"
    assert project["dependencies"] == []
    assert build_system["requires"] == ["setuptools==83.0.0"]
    assert build_system["build-backend"] == "setuptools.build_meta"
    assert pyproject["tool"]["setuptools"]["include-package-data"] is True
    assert pyproject["tool"]["setuptools"]["package-data"]["tracerelay"] == [
        "_build_identity.json",
        "assets/v1/*.json",
        "assets/v1/*.md",
        "assets/v1/schemas/*.json",
    ]


def test_build_identity_binds_frozen_authorities_without_fake_commit() -> None:
    identity = json.loads(
        (PACKAGE_ROOT / "_build_identity.json").read_text(encoding="utf-8")
    )
    assert identity == {
        "schema_version": "tracerelay.build_identity.v1",
        "package_version": "1.0.0.dev0",
        "source_commit": None,
        "source_repository_state": "UNBORN_MAIN_NO_COMMIT",
        "python_target": "CPython 3.13",
        "platform_target": "Windows 11 x64",
        "requirement_snapshot_id": REQUIREMENT_SNAPSHOT_ID,
        "requirement_manifest_sha256": REQUIREMENT_MANIFEST_SHA256,
        "implementation_snapshot_id": IMPLEMENTATION_SNAPSHOT_ID,
        "implementation_manifest_sha256": IMPLEMENTATION_MANIFEST_SHA256,
        "runtime_schema_set_sha256": RUNTIME_SCHEMA_SET_SHA256,
        "review_schema_set_sha256": REVIEW_SCHEMA_SET_SHA256,
        "build_test_lock_sha256": BUILD_TEST_LOCK_SHA256,
    }


def test_direct_build_test_dependency_lock_is_exact_and_rebased() -> None:
    lock_path = (
        REPOSITORY_ROOT / "requirements" / "build-test-direct.lock"
    )
    lock_data = lock_path.read_bytes()
    assert sha256_bytes(lock_data) == DIRECT_LOCK_SHA256
    lock_text = lock_data.decode("utf-8")
    assert (
        "# Authority: tracerelay-plan-batch010-bf09efe561ad."
        in lock_text
    )
    assert "# Dependency pins are reused unchanged from TR-I00." in lock_text
    lock_lines = [
        line.strip()
        for line in lock_text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lock_lines == [
        "setuptools==83.0.0",
        "build==1.5.0",
        "pytest==9.1.1",
        "hypothesis==6.163.0",
    ]


def test_offline_wheelhouse_manifest_is_closed_and_hash_pinned() -> None:
    manifest = json.loads(
        (
            REPOSITORY_ROOT
            / "requirements"
            / "wheelhouse-manifest.v1.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "tracerelay.wheelhouse_manifest.v1"
    assert manifest["target"] == {
        "implementation": "cp",
        "python_version": "3.13",
        "abi": "cp313",
        "platform": "win_amd64",
    }
    assert manifest["runtime_dependencies"] == []
    assert manifest["resolution_mode"] == "only_binary_no_runtime_dependencies"
    assert manifest["authority"] == {
        "implementation_snapshot_id": IMPLEMENTATION_SNAPSHOT_ID,
        "implementation_manifest_sha256": IMPLEMENTATION_MANIFEST_SHA256,
        "resolution_reused_from_phase": "TR-I00",
        "artifact_bytes_reverified_in_phase": "TR-I00R",
    }
    entries = manifest["artifacts"]
    assert entries
    filenames = [entry["filename"] for entry in entries]
    assert len(filenames) == len(set(filenames))
    for entry in entries:
        assert entry["name"]
        assert entry["version"]
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
        assert entry["role"] in {"direct", "transitive"}
        assert entry["tags"]


def test_complete_lock_and_wheelhouse_manifest_are_the_same_exact_closure() -> None:
    expected_closure = {
        "build": (
            "1.5.0",
            "build-1.5.0-py3-none-any.whl",
            "13f3eecb844759ab66efec90ca17639bbf14dc06cb2fdf37a9010322d9c50a6f",
            ("py3-none-any",),
        ),
        "colorama": (
            "0.4.6",
            "colorama-0.4.6-py2.py3-none-any.whl",
            "4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6",
            ("py2-none-any", "py3-none-any"),
        ),
        "hypothesis": (
            "6.163.0",
            "hypothesis-6.163.0-cp313-cp313-win_amd64.whl",
            "b268211e625cd550e361fc387bf1db5deb1e9cae0ce4041116f0a0aafeef7c06",
            ("cp313-cp313-win_amd64",),
        ),
        "iniconfig": (
            "2.3.0",
            "iniconfig-2.3.0-py3-none-any.whl",
            "f631c04d2c48c52b84d0d0549c99ff3859c98df65b3101406327ecc7d53fbf12",
            ("py3-none-any",),
        ),
        "packaging": (
            "26.2",
            "packaging-26.2-py3-none-any.whl",
            "5fc45236b9446107ff2415ce77c807cee2862cb6fac22b8a73826d0693b0980e",
            ("py3-none-any",),
        ),
        "pluggy": (
            "1.6.0",
            "pluggy-1.6.0-py3-none-any.whl",
            "e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746",
            ("py3-none-any",),
        ),
        "pygments": (
            "2.20.0",
            "pygments-2.20.0-py3-none-any.whl",
            "81a9e26dd42fd28a23a2d169d86d7ac03b46e2f8b59ed4698fb4785f946d0176",
            ("py3-none-any",),
        ),
        "pyproject-hooks": (
            "1.2.0",
            "pyproject_hooks-1.2.0-py3-none-any.whl",
            "9e5c6bfa8dcc30091c74b0cf803c81fdd29d94f01992a7707bc97babb1141913",
            ("py3-none-any",),
        ),
        "pytest": (
            "9.1.1",
            "pytest-9.1.1-py3-none-any.whl",
            "37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c",
            ("py3-none-any",),
        ),
        "setuptools": (
            "83.0.0",
            "setuptools-83.0.0-py3-none-any.whl",
            "29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3",
            ("py3-none-any",),
        ),
        "sortedcontainers": (
            "2.4.0",
            "sortedcontainers-2.4.0-py2.py3-none-any.whl",
            "a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0",
            ("py2-none-any", "py3-none-any"),
        ),
    }
    manifest = json.loads(
        (
            REPOSITORY_ROOT
            / "requirements"
            / "wheelhouse-manifest.v1.json"
        ).read_text(encoding="utf-8")
    )
    observed_manifest = {
        entry["name"].lower().replace("_", "-"): (
            entry["version"],
            entry["filename"],
            entry["sha256"],
            tuple(entry["tags"]),
        )
        for entry in manifest["artifacts"]
    }
    assert observed_manifest == expected_closure

    lock_text = (
        REPOSITORY_ROOT
        / "requirements"
        / "build-test-py313-win-x64.lock"
    ).read_text(encoding="utf-8")
    assert (
        sha256_bytes(lock_text.encode("utf-8"))
        == BUILD_TEST_LOCK_SHA256
    )
    assert (
        "# Authority: tracerelay-plan-batch010-bf09efe561ad."
        in lock_text
    )
    assert (
        "# Dependency pins and wheel bytes are reused unchanged from TR-I00."
        in lock_text
    )
    lock_entries = re.findall(
        r"(?m)^([A-Za-z0-9_-]+)==([^ \\\n]+) \\\n"
        r"    --hash=sha256:([0-9a-f]{64})$",
        lock_text,
    )
    observed_lock = {
        name.lower().replace("_", "-"): (version, sha256)
        for name, version, sha256 in lock_entries
    }
    expected_lock = {
        name: (version, sha256)
        for name, (version, _filename, sha256, _tags) in expected_closure.items()
    }
    assert observed_lock == expected_lock
