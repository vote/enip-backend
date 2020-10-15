from datetime import datetime
from enum import Enum
from typing import Any, Optional, NamedTuple, Union, cast, Dict

from ..enip_common.pg import get_cursor
from ..enip_common.states import DISTRICTS_BY_STATE, AT_LARGE_HOUSE_STATES

from . import structs

SQLRecord = NamedTuple(
    "SQLRecord",
    [
        ("ingest_id", int),
        ("elex_id", str),
        ("statepostal", str),
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


class NationalDataExporter:
    def __init__(self, ingest_run_id: str, ingest_run_dt: datetime):
        self.ingest_run_id = ingest_run_id
        self.ingest_run_dt = ingest_run_dt

        self.data = structs.NationalData()
        self.historical_counts: Dict[str, Dict[str, int]] = {}

    def handle_candidate_results(
        self,
        data: Union[
            structs.NationalSummaryPresident,
            structs.StateSummaryPresident,
            structs.StateSummaryCongressionalResult,
        ],
        named_candidate_factory: Any,
        record: SQLRecord,
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
                    pop_vote_history=self.historical_counts.get(record.elex_id, {}),
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
                    pop_vote_history=self.historical_counts.get(record.elex_id, {}),
                )
                return

        # Third-party candidate or non-leading gop/dem
        data.oth.pop_vote += record.votecount
        data.oth.pop_pct += record.votepct

        # Merge the candidate's historical counts into the overall historical
        # counts
        for datetime_str, count in self.historical_counts.get(
            record.elex_id, {}
        ).items():
            if datetime_str in data.oth.pop_vote_history:
                data.oth.pop_vote_history[datetime_str] += count
            else:
                data.oth.pop_vote_history[datetime_str] = count

    def grant_electoral_votes(self, party: structs.Party, count: int):
        """
        Helper function to add electoral votes to the national summary when
        we've called a state for a candidate
        """
        race = self.data.national_summary.P
        if party == structs.Party.DEM:
            assert race.dem is not None
            race.dem.elect_won += count
        elif party == structs.Party.GOP:
            assert race.gop is not None
            race.gop.elect_won += count
        else:
            race.oth.elect_won += count

    def grant_congressional_seat(
        self, data: structs.NationalSummaryWinnerCount, party: structs.Party
    ):
        """
        Helper function to add one to the senate/house national summary
        """
        if party == structs.Party.DEM:
            data.dem.won += 1
        elif party == structs.Party.GOP:
            data.gop.won += 1
        else:
            data.oth.won += 1

    def record_ntl_result(self, record: SQLRecord) -> None:
        """
        Records a "national"-level result. These results are just the national-level
        results for a presidential candidate
        """
        assert record.officeid == "P"
        assert record.statepostal == "US"

        self.handle_candidate_results(
            self.data.national_summary.P,
            structs.NationalSummaryPresidentCandidateNamed,
            record,
        )

    def record_district_result(self, record: SQLRecord) -> None:
        """
        Records a "district"-level result. These results are presidential results
        for congressional district and at-large NE and ME districts.
        """
        assert record.officeid == "P"

        # map reporting unit name to district to get the effective state name
        # (for NE and ME, we treat NE-1, ME-2, etc. as their own states for
        # the purposes of the presidential)
        if record.reportingunitname == "At Large":
            state = record.statepostal
        elif record.reportingunitname == "District 1":
            state = f"{record.statepostal}-01"
        elif record.reportingunitname == "District 2":
            state = f"{record.statepostal}-02"
        elif record.reportingunitname == "District 3":
            state = f"{record.statepostal}-03"
        else:
            raise RuntimeError(
                f"Invalid {record.statepostal} district: {record.reportingunitname}"
            )

        # Initialize the state summaries
        if state not in self.data.state_summaries:
            if record.reportingunitname == "At Large":
                self.data.state_summaries[state] = structs.StateSummary()
            else:
                self.data.state_summaries[state] = structs.PresidentialCDSummary()

        # Add the results from this record
        self.handle_candidate_results(
            self.data.state_summaries[state].P,
            structs.StateSummaryCandidateNamed,
            record,
        )

        # Handle a winner call
        # TODO: check spreadsheet data for whether we're publishing this call
        if record.winner:
            party = structs.Party.from_ap(record.party)

            # mark them as the winner of the race
            self.data.state_summaries[state].P.winner = party

            # Give the candidate the electoral votes
            self.grant_electoral_votes(party, record.electtotal)

    def record_state_presidential_result(self, record: SQLRecord) -> None:
        """
        Records a "state"-level presidential result.
        """
        state = record.statepostal
        if state in DISTRICTS_BY_STATE:
            # Ignore state-level results for ME and NE -- we use district-level
            # results (with the results for the At Large district reported as the
            # statewide results)
            return

        # Initialize the state summary
        if state not in self.data.state_summaries:
            self.data.state_summaries[state] = structs.StateSummary()

        # Add the results from this record
        self.handle_candidate_results(
            self.data.state_summaries[state].P,
            structs.StateSummaryCandidateNamed,
            record,
        )

        # Handle a winner call
        # TODO: check spreadsheet data for whether we're publishing this call
        if record.winner:
            party = structs.Party.from_ap(record.party)

            # mark them as the winner of the race
            self.data.state_summaries[state].P.winner = party

            # Give the candidate the electoral votes
            self.grant_electoral_votes(party, record.electtotal)

    def record_state_senate_result(self, record: SQLRecord) -> None:
        """
        Records a Senate result
        """
        # Get the effective state name. We treat GA-S as a state for the
        # purposes of the Georgia special election
        state = record.statepostal
        if state == "GA" and record.seatnum == 2:
            # Georgia senate special election
            state = "GA-S"

        # Initialize the state summary, and the senate component of the state
        # summary
        if state not in self.data.state_summaries:
            if state == "GA-S":
                self.data.state_summaries[state] = structs.SenateSpecialSummary()
            else:
                self.data.state_summaries[state] = structs.StateSummary()

        state_summary = self.data.state_summaries[state].S
        if not state_summary:
            # No results for this senate race yet; initialize it
            state_summary = structs.StateSummaryCongressionalResult()

            self.data.state_summaries[state].S = state_summary

        # Add the results from this record
        self.handle_candidate_results(
            state_summary, structs.StateSummaryCandidateNamed, record,
        )

        # Handle a winner call
        # TODO: check spreadsheet data for whether we're publishing this call
        if record.winner:
            party = structs.Party.from_ap(record.party)

            # mark them as the winner of the race
            state_summary.winner = party

            # Give the party a win in the national summary
            self.grant_congressional_seat(self.data.national_summary.S, party)

    def record_state_house_result(self, record: SQLRecord) -> None:
        """
        Records a House result
        """
        # Get the effective seat name. For states with a single seat, we
        # use the designation "AL" (At-Large) instead of a seat number.
        state = record.statepostal
        seat = str(record.seatnum).zfill(2)
        if state in AT_LARGE_HOUSE_STATES:
            seat = "AL"

        # Initialize the state summary, and this house race's summary
        if state not in self.data.state_summaries:
            self.data.state_summaries[state] = structs.StateSummary()

        if seat not in self.data.state_summaries[state].H:
            self.data.state_summaries[state].H[
                seat
            ] = structs.StateSummaryCongressionalResult()

        seat_results = self.data.state_summaries[state].H[seat]

        # Add the results from this record
        self.handle_candidate_results(
            seat_results, structs.StateSummaryCandidateNamed, record,
        )

        # Handle a winner call
        # For the house, we just use AP results with no editorializing
        if record.winner:
            party = structs.Party.from_ap(record.party)

            # mark them as the winner of the race
            seat_results.winner = party

            # Give the party a win in the national summary
            self.grant_congressional_seat(self.data.national_summary.H, party)

    def run_export(self) -> Any:
        # Zero out the data in case this function gets run twice
        self.data = structs.NationalData()
        self.historical_counts = {}

        with get_cursor() as cursor:
            # Fetch historical results and produce a map of (elex id -> { waypoint_dt -> count})
            cursor.execute(
                """
                SELECT
                    ingest_run.waypoint_30_dt,
                    ap_result.elex_id,
                    ap_result.votecount
                FROM ap_result
                JOIN ingest_run ON ingest_run.ingest_id = ap_result.ingest_id
                WHERE ingest_run.waypoint_30_dt IS NOT NULL
                    AND racetypeid = 'G'
                    AND level IN ('national', 'state', 'district')
                    AND ingest_dt < %s
                """,
                (self.ingest_run_dt,),
            )
            for record in cursor:
                if record.elex_id not in self.historical_counts:
                    self.historical_counts[record.elex_id] = {}
                self.historical_counts[record.elex_id][
                    str(record.waypoint_30_dt)
                ] = record.votecount

            # Iterate over every state and national result
            cursor.execute(
                """
                SELECT
                    ingest_id,

                    -- A unique ID for the race that is stable across ingest
                    -- runs. Used to correlate current data with historical data.
                    elex_id,

                    -- The state code for the result
                    statepostal,

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
                AND level IN ('national', 'state', 'district')

                -- Order by votes, descending. This means we can work through the
                -- results in order, and mark the first dem/gop candidate we see as
                -- the leading candidate (and fold other candidates into the "other"
                -- totals)
                ORDER BY votecount DESC
                """,
                (self.ingest_run_id,),
            )

            for record_any in cursor:
                record = cast(SQLRecord, record_any)
                if record.level == "national":
                    self.record_ntl_result(record)
                elif record.level == "district":
                    self.record_district_result(record)
                elif record.level == "state" and record.officeid == "P":
                    self.record_state_presidential_result(record)
                elif record.level == "state" and record.officeid == "S":
                    self.record_state_senate_result(record)
                elif record.level == "state" and record.officeid == "H":
                    self.record_state_house_result(record)
                else:
                    raise RuntimeError(
                        f"Uncategorizable result: {record.elex_id} {record.level} {record.officeid}"
                    )

            # Call the presidential winner
            pres_summary = self.data.national_summary.P
            if pres_summary.dem and pres_summary.dem.elect_won >= 270:
                pres_summary.winner = structs.Party.DEM
            elif pres_summary.gop and pres_summary.gop.elect_won >= 270:
                pres_summary.winner = structs.Party.GOP

        return self.data
