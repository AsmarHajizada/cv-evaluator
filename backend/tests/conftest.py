from pathlib import Path

import pytest

from cv_eval.extraction import extract_cv_file
from cv_eval.schemas import CVDocument

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def sample_cv() -> CVDocument:
    return extract_cv_file(EXAMPLES / "cv_ml_engineer.md")


@pytest.fixture(scope="session")
def sample_jd() -> str:
    return (EXAMPLES / "jd_ml_engineer.txt").read_text()
