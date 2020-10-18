from contextlib import contextmanager

import psycopg2.extras
import psycopg2.pool
import psycopg2

from ..enip_common.config import POSTGRES_URL, POSTGRES_RO_URL


@contextmanager
def get_cursor():
    with psycopg2.connect(POSTGRES_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cursor:
            yield cursor


@contextmanager
def get_ro_cursor():
    with psycopg2.connect(POSTGRES_RO_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cursor:
            yield cursor
