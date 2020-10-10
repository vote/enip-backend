# Election Night Integrity Project Backend

This is the backend for the [Election Night Integrity Project](https://2020.dataforprogress.org/), built by [Data for Progress](https://www.dataforprogress.org/) and [VoteAmerica](https://www.voteamerica.com/).

The job of the backend is to:
- Ingest data from the AP Elections API, historical data sources, and live commentary spreadsheets and write it to a Postgres database
- Export data from the Postgres database to populate static JSON files in S3 that are consumed by the frontend.
