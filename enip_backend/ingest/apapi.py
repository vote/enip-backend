from elex.api.models import Election
import os
import io
import csv
from datetime import datetime, timedelta, timezone

from ..enip_common.config import AP_API_KEY, INGEST_TEST_DATA, ELECTION_DATE

OFFICE_IDS = ["P", "S", "H"]


def ingest_ap(cursor, ingest_id):
    # Make the API request. We need to request both reporting-unit-level results,
    # which gives us everything except NE/ME congressional districts, and
    # district results for those few results.
    election_ru = Election(
        testresults=INGEST_TEST_DATA,
        resultslevel="ru",
        officeids=OFFICE_IDS,
        setzerocounts=False,
        electiondate=ELECTION_DATE,
        api_key=AP_API_KEY,
    )
    election_district = Election(
        testresults=INGEST_TEST_DATA,
        resultslevel="district",
        officeids=OFFICE_IDS,
        setzerocounts=False,
        electiondate=ELECTION_DATE,
        api_key=AP_API_KEY,
    )

    # Convert the AP results to an in-memory CSV (much faster than a bunch of inserts)
    csv_file = io.StringIO()
    writer = csv.writer(csv_file)
    n_rows = 0
    column_headers = None

    def process_election_results(results, filter_levels=None):
        nonlocal n_rows
        nonlocal column_headers

        for obj in results:
            row = obj.serialize()
            row["ingest_id"] = ingest_id
            row["elex_id"] = row["id"]
            del row["id"]

            if column_headers is None:
                column_headers = row.keys()
                writer.writerow(column_headers)

            if filter_levels and row["level"] not in filter_levels:
                continue

            writer.writerow(row.values())
            n_rows += 1

    process_election_results(election_ru.results)
    process_election_results(election_district.results, ["district"])

    # Run the COPY command to insert the rows
    print(f"Writing {n_rows} rows to Postgres...")

    csv_file.seek(0)

    cursor.copy_expert(
        sql=f"COPY ap_result ({','.join(column_headers)}) FROM stdin WITH DELIMITER AS ','  CSV HEADER;",
        file=csv_file,
    )

    print("Done with ingest of AP data!")
