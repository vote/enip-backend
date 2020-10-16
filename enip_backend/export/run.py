from concurrent.futures import ThreadPoolExecutor
import traceback
import time
import sys
import json
from datetime import datetime
from jsonschema import validate
import random
import sentry_sdk

from ..enip_common.states import STATES
from ..enip_common.pg import get_cursor
from ..enip_common import s3
from ..enip_common.config import CDN_URL

from .national import NationalDataExporter
from .state import StateDataExporter
from .schemas import national_schema, state_schema

THREADS = 26


def export_to_s3(ingest_run_id, ingest_run_dt, json_data, schema, path):
    # Validate
    json_data_parsed = json.loads(json_data)
    validate(instance=json_data_parsed, schema=schema)

    # Write the JSON to s3
    name = f"{path}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{ingest_run_id}.json"
    s3.write_cacheable_json(name, json_data)

    # Load the current latest JSON
    latest_name = f"{path}/latest.json"
    latest_json = s3.read_json(latest_name)

    if latest_json:
        previous_json = s3.read_json(latest_json["path"])
    else:
        previous_json = None

    # Diff
    was_different = previous_json != json_data_parsed

    # Write the new latest JSON
    if was_different:
        last_updated = str(ingest_run_dt)
        new_latest_json = {
            "lastUpdated": str(ingest_run_dt),
            "path": name,
            "cdnUrl": f"{CDN_URL}{name}",
        }
        s3.write_noncacheable_json(latest_name, json.dumps(new_latest_json))

    return was_different


def export_state(ingest_run_id, ingest_run_dt, state_code):
    data = StateDataExporter(ingest_run_id, ingest_run_dt, state_code).run_export()

    return export_to_s3(
        ingest_run_id,
        ingest_run_dt,
        data.json(by_alias=True),
        state_schema,
        f"states/{state_code}",
    )


def export_national(ingest_run_id, ingest_run_dt):
    data = NationalDataExporter(ingest_run_id, ingest_run_dt).run_export()

    return export_to_s3(
        ingest_run_id,
        ingest_run_dt,
        data.json(by_alias=True),
        national_schema,
        "national",
    )


def export_all(ingest_run_id, ingest_run_dt):
    print("Running all exports...")
    any_failed = False
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        ntl_future = executor.submit(export_national, ingest_run_id, ingest_run_dt)
        state_futures = {
            state_code: executor.submit(
                export_state, ingest_run_id, ingest_run_dt, state_code
            )
            for state_code in STATES
        }

        def handle_result(export_name, future):
            try:
                if future.result():
                    print(f"  Export {export_name} completed WITH new results")
                else:
                    print(f"  Export {export_name} completed WITHOUT new results")

            except Exception as e:
                print(f"  Export {export_name} failed")
                traceback.print_exception(*sys.exc_info())

                sentry_sdk.capture_exception(e)
                any_failed = True

        handle_result("NATIONAL", ntl_future)
        for state_code, future in state_futures.items():
            handle_result(state_code, future)

    if any_failed:
        raise RuntimeError("Some exports failed")


if __name__ == "__main__":
    # Get the most recent ingest_run
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT ingest_id, ingest_dt FROM ingest_run ORDER BY ingest_dt DESC LIMIT 1"
        )
        res = cursor.fetchone()

        ingest_id = res.ingest_id
        ingest_dt = res.ingest_dt

    print(f"Exporting ingestion {ingest_id} from {ingest_dt}")
    export_all(ingest_id, ingest_dt)
