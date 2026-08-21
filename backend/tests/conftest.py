from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.config import Settings

BASE_IRI = "https://example.org/kg/"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def settings(data_dir: Path) -> Settings:
    return Settings(base_iri=BASE_IRI, data_dir=data_dir)


@pytest.fixture
def runtime(settings: Settings):
    from ontoforge.runtime import Runtime

    created = Runtime.create(settings)
    try:
        yield created
    finally:
        created.close()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
