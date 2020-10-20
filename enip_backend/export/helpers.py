from datetime import datetime
from typing import Any, Dict, Generator, List, NamedTuple, Optional, Union

from ..enip_common.config import HISTORICAL_START
from ..enip_common.pg import get_cursor, get_ro_cursor
from . import structs

SQLRecord = NamedTuple(
    "SQLRecord",
    [
        ("ingest_id", int),
        ("elex_id", str),
        ("statepostal", str),
        ("fipscode", str),
        ("level", str),
        ("reportingunitname", Optional[str]),
        ("officeid", str),
        ("seatnum", Optional[int]),
        ("party", str),
        ("first", str),
        ("last", str),
        ("electtotal", int),
        ("votecount", int),
        ("votepct", float),
        ("winner", bool),
    ],
)


def sqlrecord_from_dict(dict: Dict[str, Any]) -> SQLRecord:
    return SQLRecord(
        ingest_id=int(dict["ingest_id"]),
        elex_id=str(dict["elex_id"]),
        statepostal=str(dict["statepostal"]),
        fipscode=str(dict["fipscode"]),
        level=str(dict["level"]),
        reportingunitname=str(dict["reportingunitname"])
        if dict["reportingunitname"] is not None
        else None,
        officeid=str(dict["officeid"]),
        seatnum=int(dict["seatnum"]) if dict["seatnum"] is not None else None,
        party=str(dict["party"]),
        first=str(dict["first"]),
        last=str(dict["last"]),
        electtotal=int(dict["electtotal"]),
        votecount=int(dict["votecount"]),
        votepct=float(dict["votepct"]),
        winner=bool(dict["winner"]),
    )


# map of (elex id -> { waypoint_dt -> count})
HistoricalResults = Dict[str, Dict[str, int]]


def handle_candidate_results(
    data: Union[
        structs.NationalSummaryPresident,
        structs.StateSummaryPresident,
        structs.StateSummaryCongressionalResult,
        structs.CountyCongressionalResult,
        structs.CountyPresidentialResult,
    ],
    named_candidate_factory: Any,
    record: SQLRecord,
    historical_counts: HistoricalResults,
) -> None:
    """
    Helper function that adds a result to dem/gop/other. This function:

    - Populates the GOP/Dem candidate if there isn't already one
    - If there's already a GOP/Dem candidate, or if this record is for
        a third-party candidate, adds the results to the "other" bucket
    - Gets the historical vote counts and populates those as well
    """
    party = structs.Party.from_ap(record.party)
    if party == structs.Party.GOP:
        if data.gop:
            # There is already a GOP candidate. We process in order of number
            # of votes, so this is a secondary GOP candidate
            if hasattr(data, "multiple_gop"):
                data.multiple_gop = True
        else:
            # This is the leading GOP candidate
            data.gop = named_candidate_factory(
                first_name=record.first,
                last_name=record.last,
                pop_vote=record.votecount,
                pop_pct=record.votepct,
                pop_vote_history=historical_counts.get(record.elex_id, {}),
            )
            return
    elif party == structs.Party.DEM:
        if data.dem:
            # There is already a Dem candidate. We process in order of number
            # of votes, so this is a secondary Dem candidate
            if hasattr(data, "multiple_dem"):
                data.multiple_dem = True
        else:
            # This is the leading Dem candidate
            data.dem = named_candidate_factory(
                first_name=record.first,
                last_name=record.last,
                pop_vote=record.votecount,
                pop_pct=record.votepct,
                pop_vote_history=historical_counts.get(record.elex_id, {}),
            )
            return

    # Third-party candidate or non-leading gop/dem
    data.oth.pop_vote += record.votecount
    data.oth.pop_pct += record.votepct

    # Merge the candidate's historical counts into the overall historical
    # counts
    for datetime_str, count in historical_counts.get(record.elex_id, {}).items():
        if datetime_str in data.oth.pop_vote_history:
            data.oth.pop_vote_history[datetime_str] += count
        else:
            data.oth.pop_vote_history[datetime_str] = count


def load_historicals(
    ingest_run_dt: datetime, filter_sql: str, filter_params: List[Any]
) -> HistoricalResults:
    historical_counts: HistoricalResults = {}

    with get_ro_cursor() as cursor:
        # Fetch historical results and produce a map of (elex id -> { waypoint_dt -> count})
        cursor.execute(
            f"""
            SELECT
                -- If the vote count did not change for a particular election
                -- between two waypoints, we don't need to report the intermediate
                -- values. We report only the first value (as per the ORDER BY
                -- below)
                DISTINCT ON (elex_id, votecount)
                ingest_run.waypoint_30_dt,
                ap_result.elex_id,
                ap_result.votecount
            FROM ap_result
            JOIN ingest_run ON ingest_run.ingest_id = ap_result.ingest_id
            WHERE ingest_run.waypoint_30_dt IS NOT NULL
                AND racetypeid = 'G'
                AND ingest_dt < %s
                AND ingest_dt > %s
                AND {filter_sql}
            ORDER BY elex_id, votecount, waypoint_30_dt ASC
            """,
            [ingest_run_dt, HISTORICAL_START] + filter_params,
        )
        for record in cursor:
            if record.elex_id not in historical_counts:
                historical_counts[record.elex_id] = {}
            historical_counts[record.elex_id][
                str(record.waypoint_30_dt)
            ] = record.votecount

    return historical_counts


def load_election_results(
    ingest_run_id: str, filter_sql: str, filter_params: List[Any]
) -> Generator[SQLRecord, None, None]:
    # Use the RW cursor to make sure we have the latest data
    with get_cursor() as cursor:
        # Iterate over every result
        cursor.execute(
            f"""
            SELECT
                ingest_id,

                -- A unique ID for the race that is stable across ingest
                -- runs. Used to correlate current data with historical data.
                elex_id,

                -- The state code for the result
                statepostal,

                -- FIPS code for county-level results
                fipscode,

                -- national, state, or district
                -- district is for ME and NE congressional district presidential results
                level,

                -- For ME and NE districts, this gives us which district
                -- (or "At Large" for statewide seats)
                reportingunitname,

                -- P, S, or H
                officeid,

                -- For house races, which house race. Also for the GA sentate, this
                -- is null for the regular race and 2 for the special. Note that the
                -- AP marks at-large districts as seatnum=1
                seatnum,

                -- Dem, GOP, or one of many others
                party,

                -- Candidate name
                first,
                last,

                -- Electoral votes awarded in this race
                electtotal,

                -- Number of votes cast for this candidate
                votecount,

                -- Percent of votes cast for this candidate
                votepct,

                -- Whether the AP has called the race for this candidate
                winner
            FROM ap_result
            WHERE ingest_id = %s
                AND racetypeid = 'G'
                AND {filter_sql}

            -- Order by votes, descending. This means we can work through the
            -- results in order, and mark the first dem/gop candidate we see as
            -- the leading candidate (and fold other candidates into the "other"
            -- totals)
            ORDER BY votecount DESC
            """,
            [ingest_run_id] + filter_params,
        )

        for record in cursor:
            yield record


Comments = Dict[str, Dict[str, structs.Comment]]


def load_comments() -> Comments:
    comments: Comments = {"P": {}, "S": {}, "H": {}}
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM comments ORDER BY ts DESC")

        for record in cursor:
            office = comments[record.office_id]
            office[record.race] = structs.Comment(
                timestamp=record.ts,
                author=record.submitted_by,
                title=record.title,
                body=record.body,
            )

    return comments


Calls = Dict[str, Dict[str, bool]]


def load_calls() -> Calls:
    calls: Calls = {"P": {}, "S": {}}

    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM senate_calls")
        for record in cursor:
            calls["S"][record.state] = record.published

        cursor.execute("SELECT * FROM president_calls")
        for record in cursor:
            calls["P"][record.state] = record.published

    return calls

