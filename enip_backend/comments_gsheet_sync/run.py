import logging
from itertools import chain
from datetime import datetime

import psycopg2
from pytz import timezone

from ..enip_common.config import COMMENTS_GSHEET_ID, POSTGRES_URL
from ..enip_common.gsheets import (
    get_gsheets_client,
    get_worksheet_data,
    worksheet_by_title,
)

RANGE = ("A", "H")

TIMESTAMP_HEADER = "Timestamp"
NAME_HEADER = "Your name (e.g. Luke Kastel)"
OFFICE_HEADER = "Office (P for President, S for Senate, H for House)"
PRESIDENT_HEADER = "Choose presidential electoral vote unit (56 choices: 50 states + DC + ME-01, ME-02, NE-01, NE-02, NE-03)"
SENATE_HEADER = "Choose Senate race (35 choices: 34 states + Georgia special)"
HOUSE_HEADER = "Choose House district"
TITLE_HEADER = "Title"
BODY_HEADER = "Body"

WORKSHEET_TITLE = "Form Responses 1"

TS_TZ = timezone("US/Eastern")
TS_FMT = "%m/%d/%Y %H:%M:%S"


def _get(row, header, validate_truthy=True):
    val = row[header].value
    if validate_truthy and not val:
        raise Exception(
            f"Missing value for {header} in row {row.get(TIMESTAMP_HEADER)}"
        )
    return val


def _map_sheet_row_to_db(r):
    try:
        office_and_race_list = []
        office = _get(r, OFFICE_HEADER)
        if office == "P":
            office_and_race_list.append((office, _get(r, PRESIDENT_HEADER)))
        elif office == "S":
            office_and_race_list.append((office, _get(r, SENATE_HEADER)))
        elif office == "PS":
            state = _get(r, PRESIDENT_HEADER)
            office_and_race_list.append(("P", state))
            office_and_race_list.append(("S", state))
            if state == "GA":
                office_and_race_list.append(("S", "GA-S"))
        elif office == "H":
            office_and_race_list.append((office, _get(r, HOUSE_HEADER)))
        elif office == "N":
            office_and_race_list.append((office, None))
        else:
            logging.error("Skipping. Office id must be P, S, PS, N or H")

        ts = datetime.strptime(_get(r, TIMESTAMP_HEADER), TS_FMT)
        for (office_id, race) in office_and_race_list:
            yield {
                "ts": TS_TZ.localize(ts),
                "submitted_by": _get(r, NAME_HEADER),
                "office_id": office_id,
                "race": race,
                "title": _get(r, TITLE_HEADER),
                "body": _get(r, BODY_HEADER),
            }
    except Exception as err:
        logging.error("Skipping. Exception: {}".format(err))


def sync_comments_gsheet():
    client = get_gsheets_client()
    sheet = client.open_by_key(COMMENTS_GSHEET_ID)
    data = get_worksheet_data(worksheet_by_title(sheet, WORKSHEET_TITLE), RANGE)
    logging.info("Syncing comments gsheet")
    # TODO: this fails fast if any of the rows is invalid, we might want to skip instead
    db_rows = chain(*[_map_sheet_row_to_db(row) for row in data])

    insert_stmt = """
    INSERT INTO comments (ts, submitted_by, office_id, race, title, body)
    VALUES  (%(ts)s, %(submitted_by)s, %(office_id)s, %(race)s, %(title)s, %(body)s)
    """
    with psycopg2.connect(POSTGRES_URL) as conn, conn.cursor() as cursor:
        cursor.execute("DELETE FROM comments")
        cursor.executemany(insert_stmt, list(db_rows))
    logging.info("Comments sync complete")


if __name__ == "__main__":
    sync_comments_gsheet()
