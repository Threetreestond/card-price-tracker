import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def get_db_connection(data_path: str) -> Generator[sqlite3.Connection]:
    Path(data_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(data_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    with get_db_connection("temporary/test.db") as conn:
        raise ValueError("boom")
