import json
import os.path

with open(os.path.join(os.path.dirname(__file__), "national.schema.json")) as f:
    national_schema = json.load(f)
