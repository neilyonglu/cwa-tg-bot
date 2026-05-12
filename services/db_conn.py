import os
from contextlib import contextmanager
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


@contextmanager
def _db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
