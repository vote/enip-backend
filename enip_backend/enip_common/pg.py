import os
import psycopg2
from ..enip_common.config import POSTGRES_URL

conn = psycopg2.connect(POSTGRES_URL)
