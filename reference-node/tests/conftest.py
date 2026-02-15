from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_NODE_DIR = ROOT / "reference-node"
if str(REFERENCE_NODE_DIR) not in sys.path:
    sys.path.insert(0, str(REFERENCE_NODE_DIR))


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def manifest_path(repo_root: Path) -> Path:
    return repo_root / "manifest.json"


@pytest.fixture
def schemas_dir(repo_root: Path) -> Path:
    return repo_root / "schemas"


@pytest.fixture
def sample_dir(repo_root: Path) -> Path:
    return repo_root / "reference-node" / "sample_data"
