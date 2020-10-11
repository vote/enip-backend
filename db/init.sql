-- This file initializes the SQL schema.
--
-- It is intended to serve as a migration that brings the database to the
-- latest schema, too: when making changes, don't edit the existing code but
-- rather add additional ALTER TABLE, CREATE TABLE, etc. statements to the
-- bottom of this file and use IF NOT EXISTS to make it idempotent.

-- ingest_runs stores one row for each time we run the ingester.
CREATE TABLE IF NOT EXISTS ingest_run (
  -- A unique ID for the ingestion run
  ingest_id SERIAL PRIMARY KEY,
  -- Timestamp the ingestion started at
  ingest_dt TIMESTAMPTZ NOT NULL,
  -- We provide 30-minute "waypoints" of historical data to the frontend. We
  -- tag the *first* ingest_run of each 30-minute interval with a waypoint_dt
  -- to indicate that data from this ingestion should be used to provide that
  -- historical data.
  waypoint_30_dt TIMESTAMPTZ UNIQUE,
  -- We're not using these waypoints *yet* but we're tracking them anyway
  waypoint_5_dt TIMESTAMPTZ UNIQUE,
  waypoint_10_dt TIMESTAMPTZ UNIQUE,
  waypoint_60_dt TIMESTAMPTZ UNIQUE
);

CREATE INDEX IF NOT EXISTS ingest_run_ingest_dt_idx
  ON ingest_run (ingest_dt);

CREATE INDEX IF NOT EXISTS ingest_run_waypoint_30_dt_idx
  ON ingest_run (waypoint_30_dt);

CREATE INDEX IF NOT EXISTS ingest_run_waypoint_5_dt_idx
  ON ingest_run (waypoint_5_dt);

CREATE INDEX IF NOT EXISTS ingest_run_waypoint_10_dt_idx
  ON ingest_run (waypoint_10_dt);

CREATE INDEX IF NOT EXISTS ingest_run_waypoint_60_dt_idx
  ON ingest_run (waypoint_60_dt);


-- Stores an AP result from an ingestion run
CREATE TABLE IF NOT EXISTS ap_result (
  -- The ID of the ingestion run this result is from
  ingest_id INTEGER NOT NULL REFERENCES ingest_run(ingest_id) ON DELETE CASCADE,

  -- The fields we get from elex
  elex_id TEXT NOT NULL,
  raceid INTEGER,
  racetype TEXT,
  racetypeid TEXT,
  ballotorder INTEGER,
  candidateid INTEGER,
  description TEXT,
  delegatecount INTEGER,
  electiondate DATE,
  electtotal INTEGER,
  electwon INTEGER,
  fipscode TEXT,
  first TEXT,
  incumbent BOOLEAN,
  initialization_data BOOLEAN,
  is_ballot_measure BOOLEAN,
  last TEXT,
  lastupdated TIMESTAMPTZ,
  level TEXT,
  national BOOLEAN,
  officeid TEXT,
  officename TEXT,
  party TEXT,
  polid INTEGER,
  polnum INTEGER,
  precinctsreporting INTEGER,
  precinctsreportingpct DOUBLE PRECISION,
  precinctstotal INTEGER,
  reportingunitid TEXT,
  reportingunitname TEXT,
  runoff BOOLEAN,
  seatname TEXT,
  seatnum INTEGER,
  statename TEXT,
  statepostal TEXT,
  test BOOLEAN,
  uncontested BOOLEAN,
  votecount INTEGER,
  votepct DOUBLE PRECISION,
  winner BOOLEAN,
  PRIMARY KEY (ingest_id, elex_id)
);

CREATE INDEX IF NOT EXISTS ap_result_statepostal_idx
  ON ap_result (statepostal);

CREATE INDEX IF NOT EXISTS ap_result_winner_idx
  ON ap_result (winner);

CREATE INDEX IF NOT EXISTS ap_result_reportingunitid_idx
  ON ap_result (reportingunitid);

CREATE INDEX IF NOT EXISTS ap_result_party_idx
  ON ap_result (party);

CREATE INDEX IF NOT EXISTS ap_result_officeid_idx
  ON ap_result (officeid);

CREATE INDEX IF NOT EXISTS ap_result_level_idx
  ON ap_result (level);

CREATE INDEX IF NOT EXISTS ap_result_lastupdated_idx
  ON ap_result (lastupdated);

