import os
from contextlib import contextmanager
from typing import Any, Iterable

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_cursor(commit: bool = False):
    """Короткоживущее соединение на один вызов — подходит для serverless.
    Используйте pooled-connection строку Neon (хост с суффиксом -pooler),
    иначе можно быстро упереться в лимит одновременных подключений Postgres."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def query_all(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with get_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Iterable[Any] = ()) -> dict | None:
    """Для INSERT/UPDATE/DELETE. Если запрос содержит RETURNING — вернёт строку результата."""
    with get_cursor(commit=True) as cur:
        cur.execute(sql, params)
        if cur.description:
            row = cur.fetchone()
            return dict(row) if row else None
        return None
