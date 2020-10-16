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
    return export_to_s3(
        ingest_run_id,
        ingest_run_dt,
        json.dumps({"foo": random.randrange(1, 5)}),
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

    if export_national(ingest_run_id, ingest_run_dt):
        print(f"  National export completed WITH new results")
    else:
        print(f"  National export completed WITHOUT new results")


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
