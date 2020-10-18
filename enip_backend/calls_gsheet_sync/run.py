import psycopg2

from pytz import timezone

from ..enip_common.config import POSTGRES_URL, CALLS_GSHEET_ID
from ..enip_common.gsheets import get_gsheets_client

DATA_RANGE = ("A", "D")
PUBLISH_DEFAULT_RANGE = ("F1", "G1")

CALLED_AT_TZ = timezone("US/Eastern")
CALLED_AT_FMT = "%m/%d/%Y %H:%M:%S"


def _get_sheet_data(worksheet):
    sheet_data = worksheet.get_values(*DATA_RANGE, returnas='cell')
    header = [c.value for c in sheet_data[0]]
    if header != ["State", "AP Call", "AP Called At (ET)",  "Published?"]:
        raise Exception("Sheet does not have the expected header")
    return [{header[i]: row[i] for i in range(len(header))} for row in sheet_data[1:]]


def _update_calls_sheet_from_db(cursor, table, worksheet):
    cursor.execute(
        f"SELECT state, ap_call, ap_called_at FROM {table} WHERE ap_call IS NOT NULL"
    )
    db_calls_lookup = {r[0]: {"call": r[1], "called_at": r[2]} for r in cursor}
    sheet_data = _get_sheet_data(worksheet)
    # Selectively update cells that don't have the same api calls from the db
    # Note: we intentionally don't insert new rows into the sheet for states
    # that exist in the db but not the sheet. The sheet will need to be seeded
    # with the states we want to report on.
    for row in sheet_data:
        state = row['State'].value
        db_call = db_calls_lookup.get(state)
        if db_call:
            call = db_call["call"]
            ap_call_cell = row["AP Call"]
            if ap_call_cell.value != call:
                print(f"Updating AP Call {state}: {call}")
                ap_call_cell.set_value(call)

            called_at_fmt = db_call["called_at"].astimezone(CALLED_AT_TZ).strftime(CALLED_AT_FMT)
            ap_called_at_cell = row["AP Called At (ET)"]
            if ap_called_at_cell.value != called_at_fmt:
                print(f"Updating AP Called At {state}: {called_at_fmt}")
                ap_called_at_cell.set_value(called_at_fmt)


def _update_db_published_from_sheet(cursor, table, worksheet):
    publish_default_cells = worksheet.get_values(*PUBLISH_DEFAULT_RANGE)[0]
    if publish_default_cells[0] != "Default":
        raise Exception("Worksheet {} does not match the expected format".format(worksheet.title))
    default_is_publish = publish_default_cells[1] == "Publish"

    def handle_published(value):
        if value == "Default":
            return default_is_publish
        return value == "Yes"

    sheet_data = _get_sheet_data(worksheet)
    rows = [(row["State"].value, handle_published(row["Published?"].value))
            for row in sheet_data]
    # Note: published settings are updated for all states in the sheet, even those that don't have calls
    statement = f"""
    INSERT INTO {table} (state, published)
    VALUES (%s, %s)
    ON CONFLICT (state) DO UPDATE
    SET published = EXCLUDED.published
    """
    cursor.executemany(statement, rows)


def import_calls_gsheet():
    client = get_gsheets_client()
    sheet = client.open_by_key(CALLS_GSHEET_ID)
    senate_sheet = sheet.worksheet_by_title("Senate Calls")
    president_sheet = sheet.worksheet_by_title("President Calls")
    with psycopg2.connect(POSTGRES_URL) as conn, conn.cursor() as cur:
        print("Syncing calls from the db to google sheets")
        _update_calls_sheet_from_db(cur, "senate_calls", senate_sheet)
        _update_calls_sheet_from_db(cur, "president_calls", president_sheet)
        print("Syncing publish settings from sheets to the db")
        _update_db_published_from_sheet(cur, "senate_calls", senate_sheet)
        _update_db_published_from_sheet(cur, "president_calls", president_sheet)
    print("Sync complete")


if __name__ == '__main__':
    import_calls_gsheet()
