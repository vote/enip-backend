import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from .enip_common import config
from .export.run import export_all
from .ingest.run import ingest_all

if config.SENTRY_DSN:
    sentry_sdk.init(
        config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        integrations=[AwsLambdaIntegration()],
    )


def run(event, context):
    ingest_id, ingest_dt = ingest_all()
    export_all(ingest_id, ingest_dt)
