import json

import boto3
import pygsheets
from pygsheets.authorization import service_account

from .config import GSHEET_API_CREDENTIALS_SSM_PATH


def get_gsheets_client():
    ssm_param = boto3.client("ssm").get_parameter(
        Name=GSHEET_API_CREDENTIALS_SSM_PATH, WithDecryption=True
    )
    param_value = ssm_param.get("Parameter", {}).get("Value")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(param_value),
        scopes=("https://www.googleapis.com/auth/spreadsheets",)
    )
    return pygsheets.authorize(custom_credentials=credentials)
