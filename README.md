# Election Night Integrity Project Backend

This is the backend for the [Election Night Integrity Project](https://2020.dataforprogress.org/), built by [Data for Progress](https://www.dataforprogress.org/) and [VoteAmerica](https://www.voteamerica.com/).

The job of the backend is to:
- Ingest data from the AP Elections API, historical data sources, and live commentary spreadsheets and write it to a Postgres database
- Export data from the Postgres database to populate static JSON files in S3 that are consumed by the frontend.

## Dev environment

1. To spin up a Postgres database for development, run `docker-compose up`.
2. Then, migrate your database with `scripts/migrate-db.sh`. You can connect with
`scripts/psql.sh`.
3. Copy `.env.example` to `.env` and fill in your AP API key.

## Ingest

The ingester is responsible for importing all of our data sources into Postgres.

You can then run the ingester with: `pipenv run python -m enip_backend.ingest`.

