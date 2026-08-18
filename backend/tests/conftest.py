import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import carregar_params  # noqa: E402


@pytest.fixture(scope="session")
def params():
    return carregar_params()
