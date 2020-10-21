import logging

from ..enip_common.pg import get_cursor
from ..enip_common.states import PRESIDENTIAL_REPORTING_UNITS, SENATE_RACES
from .apapi import ingest_ap
from .ingest_run import insert_ingest_run

SAVE_WAYPOINT = "waypoint_15_dt"


def _calls_update_stmt(table):
    return f"""
    INSERT INTO {table} (state, ap_call, ap_called_at)
    VALUES (%s, %s, NOW())
    ON CONFLICT (state) DO UPDATE
    SET (ap_call, ap_called_at) = (
        EXCLUDED.ap_call,
        CASE
            WHEN EXCLUDED.ap_call IS NULL THEN NULL
            ELSE NOW()
        END
    )
    WHERE {table}.ap_call IS DISTINCT FROM EXCLUDED.ap_call OR EXCLUDED.ap_call IS NULL
    """


def update_senate_calls(cursor, ingest_data):
    def extract_state(record):
        if record.statepostal == "GA" and record.seatnum == 2:
            return "GA-S"
        return record.statepostal

    winners = {state: None for state in SENATE_RACES}
    for record in ingest_data:
        if record.officeid == "S" and record.level == "state" and record.winner:
            winners[extract_state(record)] = record.party

    rows = [(k, v) for k, v in winners.items()]
    rows.sort(key=lambda tup: tup[0])
    cursor.executemany(_calls_update_stmt("senate_calls"), rows)


def update_president_calls(cursor, ingest_data):
    def extract_state(record):
        if record.level == "district":
            if record.reportingunitname == "At Large":
                return record.statepostal
            elif record.reportingunitname == "District 1":
                return f"{record.statepostal}-01"
            elif record.reportingunitname == "District 2":
                return f"{record.statepostal}-02"
            elif record.reportingunitname == "District 3":
                return f"{record.statepostal}-03"

        return record.statepostal

    winners = {state: None for state in PRESIDENTIAL_REPORTING_UNITS}
    for record in ingest_data:
        if (
            record.officeid == "P"
            and record.level in ("state", "district")
            and record.winner
        ):
            winners[extract_state(record)] = record.party

    rows = [(k, v) for k, v in winners.items()]
    rows.sort(key=lambda tup: tup[0])
    cursor.executemany(_calls_update_stmt("president_calls"), rows)


def ingest_all(force_save=False):
    with get_cursor() as cursor:
        # Create a record for this ingest run
        ingest_id, ingest_dt, waypoint_names = insert_ingest_run(cursor)
        logging.info(f"Ingest ID: {ingest_id}")

        # Fetch the AP results
        save_to_db = force_save or ("waypoint_15_dt" in waypoint_names)
        ingest_data = ingest_ap(cursor, ingest_id, save_to_db=save_to_db)
        # keep update order the same as calls_gsheet_run:
        # Senate then President, sorted by state
        logging.info("Updating senate calls in db")
        update_senate_calls(cursor, ingest_data)
        logging.info("Updating president calls in db")
        update_president_calls(cursor, ingest_data)
        logging.info("Comitting...")

    logging.info(f"All done! Completed ingest {ingest_id} at {ingest_dt}")
    return ingest_id, ingest_dt, ingest_data


if __name__ == "__main__":
    ingest_all(force_save=True)
