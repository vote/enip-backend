import logging

import psycopg2
from dateutil.parser import parse as parse_date
from pytz import timezone

from ..enip_common.config import CALLS_GSHEET_ID, POSTGRES_URL
from ..enip_common.gsheets import (
    get_gsheets_client,
    get_worksheet_data,
    update_cell,
    worksheet_by_title,
)

DATA_RANGE = ("A", "D")
EXPECTED_DATA_HEADER = ["State", "AP Call", "AP Called At (ET)", "Published?"]

PUBLISH_DEFAULT_RANGE = ("F1", "G1")

CALLED_AT_TZ = timezone("US/Eastern")
CALLED_AT_FMT = "%m/%d/%Y %H:%M:%S"


def _update_calls_sheet_from_db(cursor, table, worksheet):
    cursor.execute(f"SELECT state, ap_call, ap_called_at FROM {table}")
    db_calls_lookup = {r[0]: {"call": r[1], "called_at": r[2]} for r in cursor}
    sheet_data = get_worksheet_data(worksheet, DATA_RANGE, EXPECTED_DATA_HEADER)
    # Selectively update cells that don't have the same api calls from the db
    # Note: we intentionally don't insert new rows into the sheet for states
    # that exist in the db but not the sheet. The sheet will need to be seeded
    # with the states we want to report on.
    for row in sheet_data:
        state = row["State"].value
        db_call = db_calls_lookup.get(state)
        if db_call:
            call = db_call["call"] or ""
            ap_call_cell = row["AP Call"]
            if ap_call_cell.value != call:
                logging.info(f"Updating AP Call {state}: {call}")
                update_cell(ap_call_cell, call or "")

            called_at_fmt = (
                db_call["called_at"].astimezone(CALLED_AT_TZ).strftime(CALLED_AT_FMT)
                if db_call["called_at"]
                else ""
            )
            ap_called_at_cell = row["AP Called At (ET)"]

            if (
                ap_called_at_cell.value
                and called_at_fmt
                and parse_date(ap_called_at_cell.value) == parse_date(called_at_fmt)
            ):
                # We compare parsed dates so we're not sensitive to Google Sheets date
                # formatting weirdness
                pass
            elif ap_called_at_cell.value != called_at_fmt:
                logging.info(f"Updating AP Called At {state}: {called_at_fmt}")
                update_cell(ap_called_at_cell, called_at_fmt)


def _update_db_published_from_sheet(cursor, table, worksheet):
    publish_default_cells = worksheet.get_values(*PUBLISH_DEFAULT_RANGE)[0]
    if publish_default_cells[0] != "Default":
        raise Exception(
            "Worksheet {} does not match the expected format".format(worksheet.title)
        )
    default_is_publish = publish_default_cells[1] == "Publish"

    def handle_published(row):
        value = row["Published?"].value
        if value == "Default":
            return default_is_publish
        return value == "Yes"

    sheet_data = get_worksheet_data(worksheet, DATA_RANGE, EXPECTED_DATA_HEADER)
    rows = [
        {"state": row["State"].value, "published": handle_published(row)}
        for row in sheet_data
    ]
    rows.sort(key=lambda r: r["state"])
    statement = f"""
    UPDATE {table}
    SET published = %(published)s
    WHERE state = %(state)s
    """
    cursor.executemany(statement, rows)


def sync_calls_gsheet():
    client = get_gsheets_client()
    sheet = client.open_by_key(CALLS_GSHEET_ID)
    senate_sheet = worksheet_by_title(sheet, "Senate Calls")
    president_sheet = worksheet_by_title(sheet, "President Calls")
    with psycopg2.connect(POSTGRES_URL) as conn, conn.cursor() as cur:
        logging.info("Syncing calls from the db to google sheets")
        _update_calls_sheet_from_db(cur, "senate_calls", senate_sheet)
        _update_calls_sheet_from_db(cur, "president_calls", president_sheet)
        logging.info("Syncing publish settings from sheets to the db")
        # Keep update order the same as ingest:
        # Senate then President, sorted by state
        _update_db_published_from_sheet(cur, "senate_calls", senate_sheet)
        _update_db_published_from_sheet(cur, "president_calls", president_sheet)
    logging.info("Sync complete")


if __name__ == "__main__":
    sync_calls_gsheet()
