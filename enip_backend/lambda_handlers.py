import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from .enip_common import config
from .export.run import export_all_states, export_national, get_latest_ingest
from .ingest.run import ingest_all

if config.SENTRY_DSN:
    sentry_sdk.init(
        config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        integrations=[AwsLambdaIntegration()],
    )


def run(event, context):
    ingest_id, ingest_dt, ingest_data = ingest_all()
    export_national(
        ingest_id, ingest_dt, ingest_dt.strftime("%Y%m%d%H%M%S"), ingest_data
    )


def run_states(event, context):
    ingest_id, ingest_dt = get_latest_ingest()
    export_all_states(ingest_id, ingest_dt, ingest_dt.strftime("%Y%m%d%H%M%S"))


if __name__ == "__main__":
    run(None, None)
    run_states(None, None)
