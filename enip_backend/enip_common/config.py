from environs import Env

env = Env()
env.read_env()

POSTGRES_URL = env("POSTGRES_URL")
AP_API_KEY = env("AP_API_KEY")
INGEST_TEST_DATA = env.bool("INGEST_TEST_DATA")
ELECTION_DATE = env("ELECTION_DATE")
SENTRY_DSN = env("SENTRY_DSN", None)
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", "unknown")
S3_BUCKET = env("S3_BUCKET")
S3_PREFIX = env("S3_PREFIX")

CDN_URL = f"https://enip-data.voteamerica.com/{S3_PREFIX}/"
