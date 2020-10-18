import json
import random
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import sentry_sdk
from jsonschema import validate

from ..enip_common import s3
from ..enip_common.config import CDN_URL
from ..enip_common.pg import get_ro_cursor
from ..enip_common.states import STATES
from .national import NationalDataExporter
from .schemas import national_schema, state_schema
from .state import StateDataExporter

THREADS = 4


def export_to_s3(ingest_run_id, ingest_run_dt, json_data, schema, path, export_name):
    # Validate
    json_data_parsed = json.loads(json_data)
    validate(instance=json_data_parsed, schema=schema)

    # Write the JSON to s3
    name = f"{path}/{export_name}_{ingest_run_id}.json"
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
    cdn_url = f"{CDN_URL}{name}"
    if was_different:
        str(ingest_run_dt)
        new_latest_json = {
            "lastUpdated": str(ingest_run_dt),
            "path": name,
            "cdnUrl": cdn_url,
        }
        s3.write_noncacheable_json(latest_name, json.dumps(new_latest_json))

    return was_different, cdn_url


def export_state(ingest_run_dt, state_code, ingest_data):
    data = StateDataExporter(ingest_run_dt, state_code).run_export(ingest_data)

    return export_to_s3(
        0,
        ingest_run_dt,
        data.json(by_alias=True),
        state_schema,
        f"states/{state_code}",
        ingest_run_dt.strftime("%Y%m%d%H%M%S"),
    )


def export_national(ingest_run_id, ingest_run_dt, export_name, ingest_data=None):
    print("Running national export...")
    data = NationalDataExporter(ingest_run_id, ingest_run_dt).run_export(ingest_data)

    was_different, cdn_url = export_to_s3(
        ingest_run_id,
        ingest_run_dt,
        data.json(by_alias=True),
        national_schema,
        "national",
        export_name,
    )

    if was_different:
        print(f"  National export completed WITH new results: {cdn_url}")
    else:
        print(f"  National export completed WITHOUT new results: {cdn_url}")

    return cdn_url


def export_all_states(ap_data, ingest_run_dt):
    print(f"Running all state exports from ingest at {str(ingest_run_dt)}...")
    any_failed = False
    results = {}

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        # Do the states in a random order so if the DB is overloaded and we're
        # timing out regularly, we still eventually update all of the states
        # (because if we time out and miss a few states, they'll probably
        # go earlier in the next run)
        states_list = list(STATES)
        random.shuffle(states_list)

        state_futures = {
            state_code: executor.submit(
                export_state, ingest_run_dt, state_code, ap_data
            )
            for state_code in states_list
        }

        for state_code, future in state_futures.items():
            try:
                was_different, cdn_url = future.result()
                if future.result():
                    print(
                        f"  Export {state_code} completed WITH new results: {cdn_url}"
                    )
                else:
                    print(
                        f"  Export {state_code} completed WITHOUT new results: {cdn_url}"
                    )

                results[state_code] = cdn_url

            except Exception as e:
                print(f"  Export {state_code} failed")
                traceback.print_exception(*sys.exc_info())

                sentry_sdk.capture_exception(e)

    if any_failed:
        raise RuntimeError("Some exports failed")

    return results


def get_latest_ingest():
    # Get the most recent ingest_run
    with get_ro_cursor() as cursor:
        cursor.execute(
            "SELECT ingest_id, ingest_dt FROM ingest_run ORDER BY ingest_dt DESC LIMIT 1"
        )
        res = cursor.fetchone()

        return res.ingest_id, res.ingest_dt
