from environs import Env

env = Env()
env.read_env()

POSTGRES_URL = env("POSTGRES_URL")
AP_API_KEY = env("AP_API_KEY")
INGEST_TEST_DATA = env.bool("INGEST_TEST_DATA")
ELECTION_DATE = env("ELECTION_DATE")
