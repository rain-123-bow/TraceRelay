from __future__ import annotations

import hashlib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "tracerelay"
ASSET_ROOT = PACKAGE_ROOT / "assets" / "v1"
SCHEMA_ROOT = ASSET_ROOT / "schemas"
REVIEW_FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "contract" / "fixtures"

REQUIREMENT_SNAPSHOT_ID = "tracerelay-req-b027-48e1910c4369"
REQUIREMENT_MANIFEST_SHA256 = (
    "9f747ab101e7e1d20a9c0c6bc7c2b736921073c71058069fc534793fe73e260e"
)
IMPLEMENTATION_SNAPSHOT_ID = "tracerelay-plan-batch010-bf09efe561ad"
IMPLEMENTATION_MANIFEST_SHA256 = (
    "53c41b92f8374ee43cb67210b8d139f1d39a437b5a445c15046ca61dd254cbb9"
)

REQUIREMENT_ASSETS = {
    "REQUIREMENT_DESIGN_DRAFT.md": (
        80_693,
        "48e1910c43697a60c0a48050be1763be2981633e19dd5e494c3a47a572570ce0",
    ),
    "NORMATIVE_CONTRACTS.md": (
        230_823,
        "33ba2ff66e8b432ab09952cc10873947b921b3f8efec92beb93394febaecdc5f",
    ),
    "support-profile.windows-local-v1.json": (
        23_892,
        "7bf8a619622a602b8a0ed1b01db3a413110fb0f1f5f5f0750d1dfb163eb55229",
    ),
    "reason-exit-catalog.v1.json": (
        454_780,
        "bf310d98eccc1aa390f6057ed3efead18832fff73e32125190af81a2e6496231",
    ),
    "traceability-matrix.v1.json": (
        287_542,
        "fbcf154a254d82d7580a89056a5842ce98bad345fef5a8c513b369c4265fe453",
    ),
}

CONTROL_ASSETS = {
    "SCHEMA_HASHES.json": (
        3_569,
        "f5da3799ae548e8214615ab54187a218811fa00a687e99ae233a0d75e5fa8ca8",
    ),
    "PHASE_DEPENDENCY_DAG.json": (
        10_709,
        "1e3ba36f4dffe726708a7a21a97262e548868b5c6fa3872eeb799c6f5bbbc5f7",
    ),
}

RUNTIME_SCHEMAS = {
    "wire-format.v1.json": (
        31_614,
        "7baa861dc537a649aaeca556f466577ba27c492a1dd1c772f0b36bea9d5bbd75",
    ),
    "record-registry.v1.json": (
        18_285,
        "7b68bb33a4fdd25c3590c55b8f973f7c68e260e115c7ae4b6f0c38d5e9744d7d",
    ),
    "control-registry.v1.json": (
        10_629,
        "e1c6b1ed3133db58b456fd6ebe5c0219f32f21931a335071cc84ce3015eb7ad1",
    ),
    "worker-registry.v1.json": (
        18_871,
        "9dc1868070fad0aedc559965f06d3b01dc86632b4d4f7e5bec9cd248def757bd",
    ),
    "persistent-state.v1.json": (
        58_486,
        "733e24b46d878fd96708789adb958f0e59335f392a722f8d323d1fcbbd9c3892",
    ),
    "report-schema.v1.json": (
        11_176,
        "a64600cffe75572796d0b141fab3be8e68101bfa37e1d0844f640b87d633930a",
    ),
}

GOLDEN_VECTOR_SCHEMA = {
    "golden-vectors.v1.json": (
        22_994,
        "fb89ba99208aa2868d0e86aa8bd166f16247a3a9691bd709282309a9774c2218",
    )
}

RUNTIME_SCHEMA_SET_SHA256 = (
    "479f9667c3e0dfab4ce8bb43f1cd62ec17fdf3bbe63106daa088c6eee0d20dcb"
)
REVIEW_SCHEMA_SET_SHA256 = (
    "2c412b4b08f6780fdd697775e4c578f0317977299b1dde052409a25431f84665"
)
DIRECT_LOCK_SHA256 = (
    "3e31d9b3fb88d44107fc1ebf3ef526f05e8b9d7136209e2ae5049c7c327c5505"
)
BUILD_TEST_LOCK_SHA256 = (
    "34ba47b6ffb3f2c8344bfaca78fec74f0bc5a75616578edd414f6ac702ddc9ab"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_set_digest(entries: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for path, file_sha256 in entries:
        digest.update(path.encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_sha256))
    return digest.hexdigest()
