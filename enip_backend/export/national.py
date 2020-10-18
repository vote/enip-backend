from datetime import datetime
from typing import Any, Iterable, List

from ..enip_common.states import AT_LARGE_HOUSE_STATES, DISTRICTS_BY_STATE
from . import structs
from .helpers import (
    HistoricalResults,
    SQLRecord,
    handle_candidate_results,
    load_election_results,
    load_historicals,
)


class NationalDataExporter:
    def __init__(self, ingest_run_id: str, ingest_run_dt: datetime):
        self.ingest_run_id = ingest_run_id
        self.ingest_run_dt = ingest_run_dt
        self.historical_counts: HistoricalResults = {}
        self.data = structs.NationalData()

    def grant_electoral_votes(self, party: structs.Party, count: int) -> None:
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
        handle_candidate_results(
            self.data.national_summary.P,
            structs.NationalSummaryPresidentCandidateNamed,
            record,
            self.historical_counts,
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
        handle_candidate_results(
            self.data.state_summaries[state].P,
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
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
        handle_candidate_results(
            self.data.state_summaries[state].P,
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
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
        handle_candidate_results(
            state_summary,
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
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
        handle_candidate_results(
            seat_results,
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
        )

        # Handle a winner call
        # For the house, we just use AP results with no editorializing
        if record.winner:
            party = structs.Party.from_ap(record.party)

            # mark them as the winner of the race
            seat_results.winner = party

            # Give the party a win in the national summary
            self.grant_congressional_seat(self.data.national_summary.H, party)

    def run_export(
        self, preloaded_results: Iterable[SQLRecord]
    ) -> structs.NationalData:
        self.data = structs.NationalData()

        sql_filter = "level IN ('national', 'state', 'district')"
        filter_params: List[Any] = []

        self.historical_counts = load_historicals(
            self.ingest_run_dt, sql_filter, filter_params
        )

        def handle_record(record):
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

        if preloaded_results:
            for record in preloaded_results:
                handle_record(record)
        else:
            for record in load_election_results(
                self.ingest_run_id, sql_filter, filter_params
            ):
                handle_record(record)

        # Call the presidential winner
        pres_summary = self.data.national_summary.P
        if pres_summary.dem and pres_summary.dem.elect_won >= 270:
            pres_summary.winner = structs.Party.DEM
        elif pres_summary.gop and pres_summary.gop.elect_won >= 270:
            pres_summary.winner = structs.Party.GOP

        return self.data
