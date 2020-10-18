import json
from datetime import datetime

import boto3
import psycopg2
import pygsheets
from pygsheets.authorization import service_account
from pytz import timezone

from ..enip_common.config import POSTGRES_URL, GSHEET_API_CREDENTIALS_SSM_PATH, CALLS_GSHEET_ID

DATA_RANGE = ("A", "D")
PUBLISH_DEFAULT_RANGE = ("F1", "G1")

CALLED_AT_TZ = "US/Eastern"
CALLED_AT_FMT = "%m/%d/%Y %H:%M:%S"


def _get_gsheets_client():
    ssm_param = boto3.client("ssm").get_parameter(
        Name=GSHEET_API_CREDENTIALS_SSM_PATH, WithDecryption=True
    )
    param_value = ssm_param.get("Parameter", {}).get("Value")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(param_value),
        scopes=("https://www.googleapis.com/auth/spreadsheets",)
    )
    return pygsheets.authorize(custom_credentials=credentials)


def _convert_sheet_rows_to_dicts(vals):
    header = vals[0]
    return [{header[i]: row[i] for i in range(len(header))} for row in vals[1:]]


def _handle_ap_called_at(value):
    if not value:
        return None
    return datetime.strptime(value, CALLED_AT_FMT).replace(tzinfo=timezone(CALLED_AT_TZ))


def _process_worksheet(sheet, worksheet_title):
    wks = sheet.worksheet_by_title(worksheet_title)
    publish_default_cells = wks.get_values(*PUBLISH_DEFAULT_RANGE)[0]
    if publish_default_cells[0] != "Default":
        raise Exception("Worksheet {} does not match the expect format", worksheet_title)
    default_is_publish = publish_default_cells[1] == "Publish"

    def _handle_published(value):
        if value == "Default":
            return default_is_publish
        return value == "Yes"

    rows = _convert_sheet_rows_to_dicts(wks.get_values(*DATA_RANGE))
    return [
        {
            # Throw a key error if the sheet does not have the expected headers
            "state": row["State"],
            "ap_call": row["AP Call"] or None,
            "ap_called_at": _handle_ap_called_at(row["AP Called At (ET)"]),
            "published": _handle_published(row["Published?"])
        }
        for row in rows
    ]


def _write_rows_to_db(cursor, table, processed_rows):
    statement = """
    INSERT INTO {table} (state, ap_call, ap_called_at, published)
    VALUES (%(state)s, %(ap_call)s, %(ap_called_at)s, %(published)s)
    ON CONFLICT (state) DO UPDATE
    SET (ap_call, ap_called_at, published) = (EXCLUDED.ap_call, EXCLUDED.ap_called_at, EXCLUDED.published)
    """.format(table=table)
    cursor.executemany(statement, processed_rows)


def import_calls_gsheet():
    client = _get_gsheets_client()
    sheet = client.open_by_key(CALLS_GSHEET_ID)
    senate_data = _process_worksheet(sheet, "Senate Calls")
    president_data = _process_worksheet(sheet, "President Calls")
    with psycopg2.connect(POSTGRES_URL) as conn, conn.cursor() as cur:
        print("Syncing senate data")
        _write_rows_to_db(cur, "senate_calls", senate_data)
        print("Syncing president data")
        _write_rows_to_db(cur, "president_calls", president_data)
    print("Sync complete")


if __name__ == '__main__':
    import_calls_gsheet()
