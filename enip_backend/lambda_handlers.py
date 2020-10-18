from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from .enip_common import config
from .export.run import export_all_states, export_national
from .ingest.apapi import ingest_ap
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
    ingest_dt = datetime.now(tz=timezone.utc)
    ap_data = ingest_ap(
        cursor=None, ingest_id=-1, save_to_db=False, return_levels={"county"}
    )
    export_all_states(ap_data, ingest_dt)


if __name__ == "__main__":
    run(None, None)
    run_states(None, None)
