import json
import logging
import random
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import sentry_sdk
from ddtrace import tracer
from jsonschema import validate
from jsonschema.exceptions import ValidationError

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

    try:
        validate(instance=json_data_parsed, schema=schema)
    except ValidationError as e:
        # Write the invalid JSON to s3 for diagnostics
        failed_cdn_url = "(failed to write to s3)"
        try:
            failed_name = f"{path}/failed/{export_name}_{ingest_run_id}.json"

            s3.write_cacheable_json(failed_name, json_data)
            failed_cdn_url = f"{CDN_URL}{failed_name}"
        except:
            logging.exception("Failed to save invalid JSON to S3")

        error_msg = (
            f"JSON failed schema validation: {e.message} -- logged to {failed_cdn_url}"
        )
        error_data = {
            "validation_message": e.message,
            "validator": e.validator,
            "validator_value": e.validator_value,
            "absolute_schema_path": list(e.absolute_schema_path),
            "bad_json_url": failed_cdn_url,
        }

        with sentry_sdk.configure_scope() as scope:
            scope.set_context("validation_error", error_data)
            sentry_sdk.capture_exception(RuntimeError(error_msg))

        logging.exception(error_msg, extra=error_data)
        raise e

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


@tracer.wrap("enip.export.export_state")
def export_state(ingest_run_dt, state_code, ingest_data):
    with tracer.trace("enip.export.export_state.run_export"):
        data = StateDataExporter(ingest_run_dt, state_code).run_export(ingest_data)

    with tracer.trace("enip.export.export_state.export_to_s3"):
        return export_to_s3(
            0,
            ingest_run_dt,
            data.json(by_alias=True),
            state_schema,
            f"states/{state_code}",
            ingest_run_dt.strftime("%Y%m%d%H%M%S"),
        )


@tracer.wrap("enip.export.export_national")
def export_national(ingest_run_id, ingest_run_dt, export_name, ingest_data=None):
    logging.info("Running national export...")
    with tracer.trace("enip.export.export_ntl.run_export"):
        data = NationalDataExporter(ingest_run_id, ingest_run_dt).run_export(
            ingest_data
        )

    with tracer.trace("enip.export.export_ntl.export_to_s3"):
        was_different, cdn_url = export_to_s3(
            ingest_run_id,
            ingest_run_dt,
            data.json(by_alias=True),
            national_schema,
            "national",
            export_name,
        )

    if was_different:
        logging.info(f"  National export completed WITH new results: {cdn_url}")
    else:
        logging.info(f"  National export completed WITHOUT new results: {cdn_url}")

    return cdn_url


def export_all_states(ap_data, ingest_run_dt):
    logging.info(f"Running all state exports from ingest at {str(ingest_run_dt)}...")
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
                    logging.info(
                        f"  Export {state_code} completed WITH new results: {cdn_url}"
                    )
                else:
                    logging.info(
                        f"  Export {state_code} completed WITHOUT new results: {cdn_url}"
                    )

                results[state_code] = cdn_url

            except Exception as e:
                logging.info(f"  Export {state_code} failed")
                traceback.logging.info_exception(*sys.exc_info())

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
