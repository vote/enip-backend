from datetime import datetime, timezone, timedelta

WAYPOINT_INTERVALS = [
    ("waypoint_30_dt", timedelta(minutes=30)),
    ("waypoint_5_dt", timedelta(minutes=5)),
    ("waypoint_10_dt", timedelta(minutes=10)),
    ("waypoint_60_dt", timedelta(minutes=60)),
]


def get_waypoint_for_dt(dt, interval):
    """
    Rounds down to the nearest WAYPOINT_INTERVAL
    From: https://stackoverflow.com/a/50268328
    """
    rounded = dt - (dt - datetime.min.replace(tzinfo=timezone.utc)) % interval
    return rounded


def insert_ingest_run(cursor):
    now = datetime.now(tz=timezone.utc)

    # Find the most recent ingest
    max_sql = ", ".join(
        [
            f"MAX({col_name}) AS waypoint{int(delta.total_seconds())}"
            for col_name, delta in WAYPOINT_INTERVALS
        ]
    )

    cursor.execute(f"SELECT {max_sql} FROM ingest_run")

    waypoint_dts = []
    for (last_waypoint, (col_name, interval)) in zip(
        cursor.fetchone(), WAYPOINT_INTERVALS
    ):
        print(f"{col_name}")
        print(f"  Previous waypoint: {last_waypoint}")

        # Determine if this run is a new waypoint -- if there are no runs for
        # the current waypoint
        current_waypoint = get_waypoint_for_dt(now, interval)
        print(f"  Current waypoint: {current_waypoint}")

        if not last_waypoint or (current_waypoint > last_waypoint):
            print(f"    -> This ingest run will be a new waypoint for {col_name}")
            waypoint_dt = current_waypoint
        else:
            print(f"    -> This ingest run is not a new waypoint for {col_name}")
            waypoint_dt = None

        waypoint_dts.append(waypoint_dt)

    # Insert a record for this ingest
    waypoint_cols = ", ".join(col_name for col_name, delta in WAYPOINT_INTERVALS)
    waypoint_placeholders = ", ".join("%s" for col_name, delta in WAYPOINT_INTERVALS)
    cursor.execute(
        f"INSERT INTO ingest_run (ingest_dt, {waypoint_cols}) VALUES (now(), {waypoint_placeholders}) RETURNING ingest_id, ingest_dt",
        waypoint_dts,
    )
    res = cursor.fetchone()
    return res[0], res[1]

