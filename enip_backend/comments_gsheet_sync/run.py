from datetime import datetime

import psycopg2
from pytz import timezone

from ..enip_common.config import COMMENTS_GSHEET_ID, POSTGRES_URL
from ..enip_common.gsheets import get_gsheets_client, get_worksheet_data

RANGE = ("A", "H")

# TODO: finalize headers with @jasonkb
TIMESTAMP_HEADER = "Timestamp"
NAME_HEADER = "Your name (e.g. Luke Kastel)"
OFFICE_HEADER = "Office (P for President, S for Senate, H for House)"
PRESIDENT_HEADER = "Choose presidential electoral vote unit (56 choices: 50 states + DC + ME-01, ME-02, NE-01, NE-02, NE-03)"
SENATE_HEADER = "Choose Senate race (35 choices: 34 states + Georgia special)"
HOUSE_HEADER = "Choose House district"
TITLE_HEADER = "Title"
BODY_HEADER = "Body"

WORKSHEET_TITLE = "Form Responses 1"

# TODO: check with @jasonkb that this is the correct timezone
TS_TZ = timezone("US/Eastern")
TS_FMT = "%m/%d/%Y %H:%M:%S"


def _get(row, header, validate_truthy=True):
    val = row[header].value
    if validate_truthy and not val:
        raise Exception(f"Missing value for {header}")
    return val


def _map_sheet_row_to_db(r):
    office = _get(r, OFFICE_HEADER)
    race = None
    if office == "P":
        race = _get(r, PRESIDENT_HEADER)
    elif office == "S":
        race = _get(r, SENATE_HEADER)
    elif office == "H":
        race = _get(r, HOUSE_HEADER)
    else:
        raise Exception("Office id must be P, S, or H")
    ts = datetime.strptime(_get(r, TIMESTAMP_HEADER), TS_FMT)
    return {
        "ts": TS_TZ.localize(ts),
        "submitted_by": _get(r, NAME_HEADER),
        "office_id": office,
        "race": race,
        "title": _get(r, TITLE_HEADER),
        "body": _get(r, BODY_HEADER),
    }


def sync_comments_gsheet():
    client = get_gsheets_client()
    sheet = client.open_by_key(COMMENTS_GSHEET_ID)
    data = get_worksheet_data(sheet.worksheet_by_title(WORKSHEET_TITLE), RANGE)
    print("Syncing comments gsheet")
    # TODO: this fails fast if any of the rows is invalid, we might want to skip instead
    db_rows = [_map_sheet_row_to_db(row) for row in data]

    insert_stmt = """
    INSERT INTO comments (ts, submitted_by, office_id, race, title, body) 
    VALUES  (%(ts)s, %(submitted_by)s, %(office_id)s, %(race)s, %(title)s, %(body)s)
    """
    with psycopg2.connect(POSTGRES_URL) as conn, conn.cursor() as cursor:
        cursor.execute("DELETE FROM comments")
        cursor.executemany(insert_stmt, db_rows)
    print("Comments sync complete")


if __name__ == "__main__":
    sync_comments_gsheet()
