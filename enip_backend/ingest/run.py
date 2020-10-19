import logging

from ..enip_common.pg import get_cursor
from .apapi import ingest_ap
from .ingest_run import insert_ingest_run

SAVE_WAYPOINT = "waypoint_15_dt"


def _calls_update_stmt(table):
    return f"""
    INSERT INTO {table} (state, ap_call, ap_called_at)
    VALUES (%s, %s, NOW())
    ON CONFLICT (state) DO UPDATE
    SET (ap_call, ap_called_at) = (EXCLUDED.ap_call, NOW())
    WHERE {table}.ap_call != EXCLUDED.ap_call
    """


def update_senate_calls(cursor, ingest_data):
    def extract_state(record):
        if record.statepostal == "GA" and record.seatnum == 2:
            return "GA-S"
        return record.statepostal

    winners = [
        (extract_state(record), record.party)
        for record in ingest_data
        if record.officeid == "S" and record.level == "state" and record.winner
    ]
    cursor.executemany(_calls_update_stmt("senate_calls"), winners)


def update_president_calls(cursor, ingest_data):
    winners = [
        (record.statepostal, record.party)
        for record in ingest_data
        if record.officeid == "P" and record.level == "state" and record.winner
    ]
    cursor.executemany(_calls_update_stmt("president_calls"), winners)


def ingest_all(force_save=False):
    with get_cursor() as cursor:
        # Create a record for this ingest run
        ingest_id, ingest_dt, waypoint_names = insert_ingest_run(cursor)
        logging.info(f"Ingest ID: {ingest_id}")

        # Fetch the AP results
        save_to_db = force_save or ("waypoint_15_dt" in waypoint_names)
        ingest_data = ingest_ap(cursor, ingest_id, save_to_db=save_to_db)
        print("Updating president calls in db")
        update_president_calls(cursor, ingest_data)
        print("Updating senate calls in db")
        update_senate_calls(cursor, ingest_data)
        logging.info("Comitting...")

    logging.info(f"All done! Completed ingest {ingest_id} at {ingest_dt}")
    return ingest_id, ingest_dt, ingest_data


if __name__ == "__main__":
    ingest_all(force_save=True)
