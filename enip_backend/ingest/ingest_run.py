from datetime import datetime, timezone, timedelta

WAYPOINT_INTERVAL = timedelta(minutes=30)


def get_waypoint_for_dt(dt):
    """
    Rounds down to the nearest WAYPOINT_INTERVAL
    From: https://stackoverflow.com/a/50268328
    """
    rounded = dt - (dt - datetime.min.replace(tzinfo=timezone.utc)) % WAYPOINT_INTERVAL
    return rounded


def insert_ingest_run(cursor):
    # Find the most recent ingest
    cursor.execute("SELECT MAX(waypoint_dt) FROM ingest_run")
    last_waypoint = cursor.fetchone()[0]

    print(f"Previous waypoint: {last_waypoint}")

    # Determine if this run is a new waypoint -- if there are no runs for
    # the current waypoint
    now = datetime.now(tz=timezone.utc)
    current_waypoint = get_waypoint_for_dt(now)
    print(f"Current waypoint: {current_waypoint}")

    if not last_waypoint or (current_waypoint > last_waypoint):
        print("  -> This ingest run will be a new waypoint")
        waypoint_dt = current_waypoint
    else:
        print("  -> This ingest run is not a new waypoint")
        waypoint_dt = None

    # Insert a record for this ingest
    cursor.execute(
        "INSERT INTO ingest_run (ingest_dt, waypoint_dt) VALUES (now(), %s) RETURNING ingest_id",
        (waypoint_dt,),
    )
    return cursor.fetchone()[0]

