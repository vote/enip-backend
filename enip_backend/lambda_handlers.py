import sentry_sdk

from .enip_common import config


if config.SENTRY_DSN:
    sentry_sdk.init(config.SENTRY_DSN, environment=config.SENTRY_ENVIRONMENT)


def hello(event, context):
    print("Hello ENIP")
