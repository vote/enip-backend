import json
from datetime import datetime, timezone

from ..enip_common.pg import get_ro_cursor
from .run import export_all_states, export_national

# Bulk-exports a range of ingests for testing purposes. Prints out a JSON
# blob describing the exports.
START_TIME = datetime(2020, 10, 15, 16, 0, 0, tzinfo=timezone.utc)
END_TIME = datetime(2020, 10, 15, 18, 0, 0, tzinfo=timezone.utc)


def export_bulk():
    ingests = []
    with get_ro_cursor() as cursor:
        cursor.execute(
            "SELECT ingest_id, ingest_dt FROM ingest_run WHERE ingest_dt >= %s AND ingest_dt <= %s AND waypoint_30_dt IS NOT NULL",
            (START_TIME, END_TIME),
        )

        ingests = [(res.ingest_id, res.ingest_dt) for res in cursor]

    print(f"Running {len(ingests)} exports...")

    summary = []
    for i, (ingest_id, ingest_dt) in enumerate(ingests):
        print(f"[[[ INGEST {i+1} OF {len(ingests)} ]]]")

        summary.append(
            {
                "ingest_dt": ingest_dt.isoformat(),
                "exports": {
                    "national": export_national(
                        ingest_id, ingest_dt, ingest_dt.strftime("%Y%m%d%H%M%S")
                    ),
                    "states": export_all_states(
                        ingest_id, ingest_dt, ingest_dt.strftime("%Y%m%d%H%M%S")
                    ),
                },
            }
        )

    return summary


if __name__ == "__main__":
    out_json = export_bulk()
    with open("./bulk.json", "w") as f:
        json.dump(out_json, f)
