from environs import Env

env = Env()
env.read_env()

POSTGRES_URL = env("POSTGRES_URL")
POSTGRES_RO_URL = env("POSTGRES_RO_URL", POSTGRES_URL)
AP_API_KEY = env("AP_API_KEY")
INGEST_TEST_DATA = env.bool("INGEST_TEST_DATA")
ELECTION_DATE = env("ELECTION_DATE")
SENTRY_DSN = env("SENTRY_DSN", None)
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", "unknown")
S3_BUCKET = env("S3_BUCKET")
S3_PREFIX = env("S3_PREFIX")
HISTORICAL_START = env.datetime("HISTORICAL_START", "2020-10-01T00:00:00Z")
CDN_URL = f"https://enip-data.voteamerica.com/{S3_PREFIX}/"
