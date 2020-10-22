import json

import boto3
import pygsheets
from ddtrace import tracer
from pygsheets.authorization import service_account

from .config import GSHEET_API_CREDENTIALS_SSM_PATH


@tracer.wrap("gsheets.get_gsheets_client", service="gsheets")
def get_gsheets_client():
    """Get a pygsheets client using service account credentials stored in SSM"""
    ssm_param = boto3.client("ssm").get_parameter(
        Name=GSHEET_API_CREDENTIALS_SSM_PATH, WithDecryption=True
    )
    param_value = ssm_param.get("Parameter", {}).get("Value")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(param_value),
        scopes=("https://www.googleapis.com/auth/spreadsheets",),
    )
    return pygsheets.authorize(custom_credentials=credentials)


@tracer.wrap("gsheets.get_worsheet_data", service="gsheets")
def get_worksheet_data(worksheet, data_range, expected_header=None):
    """Read a range of cells from a worksheet into a list of dictionaries
    treating the first row as a header.

    :param worksheet: a pygsheets Worksheet object
    :param data_range: cell range tuple, e.g. ('A', 'D'), ('A1', 'A17')
    :param expected_header: optional, if passed assert that the first row header
           matches the expected_header exactly
    :return: a list of rows as dictionaries, with the header as keys and
            pygsheet Cell objects as values
    """
    sheet_data = worksheet.get_values(*data_range, returnas="cell")
    header = [c.value for c in sheet_data[0]]
    if expected_header and header != expected_header:
        raise Exception(f"Sheet does not have the expected header: {expected_header}")
    return [{header[i]: row[i] for i in range(len(header))} for row in sheet_data[1:]]


@tracer.wrap("gsheets.update_cell", service="gsheets")
def update_cell(cell, value):
    cell.set_value(value)


@tracer.wrap("gsheets.worksheet_by_title", service="gsheets")
def worksheet_by_title(sheet, title):
    return sheet.worksheet_by_title(title)
