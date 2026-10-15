import os
from pathlib import Path

# Keep test runs isolated from developer data.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path('test.db').absolute()}")

from app.db.init_db import init_db
import pytest

init_db()

@pytest.fixture(autouse=True, scope="session")
def cleanup_test_database():
    yield
    test_db = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    if test_db.exists():
        try:
            test_db.unlink()
        except OSError:
            pass
