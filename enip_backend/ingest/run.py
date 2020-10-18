from ..enip_common.pg import get_cursor
from .apapi import ingest_ap
from .ingest_run import insert_ingest_run

SAVE_WAYPOINT = "waypoint_15_dt"


def ingest_all(force_save=False):
    with get_cursor() as cursor:
        # Create a record for this ingest run
        ingest_id, ingest_dt, waypoint_names = insert_ingest_run(cursor)
        print(f"Ingest ID: {ingest_id}")

        # Fetch the AP results
        save_to_db = force_save or ("waypoint_15_dt" in waypoint_names)
        ingest_data = ingest_ap(cursor, ingest_id, save_to_db=save_to_db)

        print("Comitting...")

    print(f"All done! Completed ingest {ingest_id} at {ingest_dt}")
    return ingest_id, ingest_dt, ingest_data


if __name__ == "__main__":
    ingest_all(force_save=True)
