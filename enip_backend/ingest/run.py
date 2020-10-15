from .apapi import ingest_ap
from .ingest_run import insert_ingest_run
from ..enip_common.pg import get_cursor


def ingest_all():
    with get_cursor() as cursor:
        # Create a record for this ingest run
        ingest_id = insert_ingest_run(cursor)
        print(f"Ingest ID: {ingest_id}")

        # Fetch the AP results
        ingest_ap(cursor, ingest_id)

        print("Comitting...")

    print(f"All done! Completed ingest {ingest_id}")


if __name__ == "__main__":
    ingest_all()
