import csv
import io

from elex.api.models import Election

from ..enip_common.config import AP_API_KEY, ELECTION_DATE, INGEST_TEST_DATA
from ..export.helpers import sqlrecord_from_dict

OFFICE_IDS = ["P", "S", "H"]
RETURN_LEVELS = {"national", "state", "district"}


def ingest_ap(cursor, ingest_id, save_to_db):
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
    return_data = []

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

            if save_to_db:
                writer.writerow(row.values())

            if row["level"] in RETURN_LEVELS:
                return_data.append(sqlrecord_from_dict(row))
            n_rows += 1

    process_election_results(election_ru.results)
    process_election_results(election_district.results, ["district"])

    print(f"Got {n_rows} rows from the AP")

    if save_to_db:
        # Run the COPY command to insert the rows
        print(f"Writing {n_rows} rows to Postgres...")

        csv_file.seek(0)

        cursor.copy_expert(
            sql=f"COPY ap_result ({','.join(column_headers)}) FROM stdin WITH DELIMITER AS ','  CSV HEADER;",
            file=csv_file,
        )

    print(
        f"Done with ingest of AP data! Returning {len(return_data)} data points for national export"
    )

    return return_data
