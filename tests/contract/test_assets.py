from __future__ import annotations

import json
from pathlib import Path

import pytest

from contract_authority import (
    ASSET_ROOT,
    CONTROL_ASSETS,
    GOLDEN_VECTOR_SCHEMA,
    REQUIREMENT_ASSETS,
    REVIEW_FIXTURE_ROOT,
    REVIEW_SCHEMA_SET_SHA256,
    RUNTIME_SCHEMAS,
    RUNTIME_SCHEMA_SET_SHA256,
    SCHEMA_ROOT,
    schema_set_digest,
    sha256_bytes,
)


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        *((Path(name), value) for name, value in REQUIREMENT_ASSETS.items()),
        *((Path(name), value) for name, value in CONTROL_ASSETS.items()),
        *(
            (Path("schemas") / name, value)
            for name, value in RUNTIME_SCHEMAS.items()
        ),
    ],
)
def test_packaged_asset_matches_frozen_bytes(
    relative_path: Path, expected: tuple[int, str]
) -> None:
    asset_path = ASSET_ROOT / relative_path
    data = asset_path.read_bytes()
    expected_bytes, expected_sha256 = expected
    assert len(data) == expected_bytes
    assert sha256_bytes(data) == expected_sha256


@pytest.mark.parametrize(
    "asset_path",
    [
        ASSET_ROOT / name
        for name in REQUIREMENT_ASSETS
        if name.endswith(".json")
    ]
    + [ASSET_ROOT / name for name in CONTROL_ASSETS]
    + [SCHEMA_ROOT / name for name in RUNTIME_SCHEMAS]
    + [REVIEW_FIXTURE_ROOT / "golden-vectors.v1.json"],
)
def test_packaged_json_assets_parse(asset_path: Path) -> None:
    json.loads(asset_path.read_text(encoding="utf-8"))


def test_schema_hash_manifest_matches_runtime_schema_bytes() -> None:
    manifest = json.loads(
        (ASSET_ROOT / "SCHEMA_HASHES.json").read_text(encoding="utf-8")
    )
    declared = manifest["runtime_schema_set"]
    expected_order = [f"schemas/{name}" for name in RUNTIME_SCHEMAS]
    observed_order = [entry["path"] for entry in declared["ordered_entries"]]
    assert observed_order == expected_order

    observed_entries: list[tuple[str, str]] = []
    for entry in declared["ordered_entries"]:
        schema_path = ASSET_ROOT / entry["path"]
        data = schema_path.read_bytes()
        observed_sha256 = sha256_bytes(data)
        assert len(data) == entry["bytes"]
        assert observed_sha256 == entry["sha256"]
        observed_entries.append((entry["path"], observed_sha256))

    observed_set_digest = schema_set_digest(observed_entries)
    assert observed_set_digest == declared["schema_set_sha256"]
    assert observed_set_digest == RUNTIME_SCHEMA_SET_SHA256


def test_review_schema_set_digest_is_reproducible() -> None:
    manifest = json.loads(
        (ASSET_ROOT / "SCHEMA_HASHES.json").read_text(encoding="utf-8")
    )
    declared = manifest["review_schema_set"]
    expected_order = [f"schemas/{name}" for name in RUNTIME_SCHEMAS] + [
        "schemas/golden-vectors.v1.json"
    ]
    observed_order = [entry["path"] for entry in declared["ordered_entries"]]
    assert observed_order == expected_order

    observed_entries: list[tuple[str, str]] = []
    for entry in declared["ordered_entries"]:
        if entry["path"] == "schemas/golden-vectors.v1.json":
            schema_path = REVIEW_FIXTURE_ROOT / "golden-vectors.v1.json"
        else:
            schema_path = ASSET_ROOT / entry["path"]
        data = schema_path.read_bytes()
        observed_sha256 = sha256_bytes(data)
        assert len(data) == entry["bytes"]
        assert observed_sha256 == entry["sha256"]
        observed_entries.append((entry["path"], observed_sha256))

    golden_expected = next(iter(GOLDEN_VECTOR_SCHEMA.values()))
    golden_data = (REVIEW_FIXTURE_ROOT / "golden-vectors.v1.json").read_bytes()
    assert (len(golden_data), sha256_bytes(golden_data)) == golden_expected
    observed_set_digest = schema_set_digest(observed_entries)
    assert observed_set_digest == declared["schema_set_sha256"]
    assert observed_set_digest == REVIEW_SCHEMA_SET_SHA256


def test_package_asset_directory_contains_only_declared_files() -> None:
    observed = {
        path.relative_to(ASSET_ROOT).as_posix()
        for path in ASSET_ROOT.rglob("*")
        if path.is_file()
    }
    expected = set(REQUIREMENT_ASSETS) | set(CONTROL_ASSETS) | {
        f"schemas/{name}" for name in RUNTIME_SCHEMAS
    }
    assert observed == expected
