import os
import psycopg2.pool
import psycopg2.extras

from contextlib import contextmanager

from ..enip_common.config import POSTGRES_URL

# Psycopg2's connection pool closes connections that are returned until it's
# back to the minimum (unlike a typical connection pool, which leaves
# connections open for re-use). So we keep the minimum pretty high -- only one
# execution should be running at a time so having 50 connections isn't a big
# deal.
pool = psycopg2.pool.ThreadedConnectionPool(50, 250, POSTGRES_URL)


@contextmanager
def get_cursor():
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor) as cursor:
                yield cursor
    finally:
        pool.putconn(conn)
