import logging
from datetime import datetime, timezone

import sentry_sdk
from ddtrace import patch_all, tracer
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from .enip_common import config
from .export.run import export_all_states, export_national
from .ingest.apapi import ingest_ap
from .calls_gsheet_sync.run import sync_calls_gsheet
from .ingest.run import ingest_all

logging.getLogger().setLevel(logging.INFO)
patch_all()

if config.SENTRY_DSN:
    sentry_sdk.init(
        config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        integrations=[AwsLambdaIntegration()],
    )


def run(event, context):
    with tracer.trace("enip.run_national"):
        with tracer.trace("enip.run_national.ingest"):
            ingest_id, ingest_dt, ingest_data = ingest_all()
        with tracer.trace("enip.run_national.export"):
            export_national(
                ingest_id, ingest_dt, ingest_dt.strftime("%Y%m%d%H%M%S"), ingest_data
            )


def run_states(event, context):
    with tracer.trace("enip.run_states"):
        with tracer.trace("enip.run_states.ingest"):
            ingest_dt = datetime.now(tz=timezone.utc)
            ap_data = ingest_ap(
                cursor=None, ingest_id=-1, save_to_db=False, return_levels={"county"}
            )
        with tracer.trace("enip.run_states.export"):
            export_all_states(ap_data, ingest_dt)


def run_sync_calls_gsheet(event, context):
    sync_calls_gsheet()


if __name__ == "__main__":
    run(None, None)
    run_states(None, None)
    run_sync_calls_gsheet(None, None)
