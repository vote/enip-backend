import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from .enip_common import config


if config.SENTRY_DSN:
    sentry_sdk.init(
        config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        integrations=[AwsLambdaIntegration()]
    )


def hello(event, context):
    print("Hello ENIP")
