from datetime import datetime
from typing import Any, Iterable, List

from ddtrace import tracer

from ..enip_common.states import AT_LARGE_HOUSE_STATES
from . import structs
from .helpers import (
    HistoricalResults,
    SQLRecord,
    handle_candidate_results,
    load_election_results,
    load_historicals,
)


class StateDataExporter:
    data: structs.StateData

    def __init__(self, ingest_run_dt: datetime, statecode: str):
        self.ingest_run_dt = ingest_run_dt
        self.historical_counts: HistoricalResults = {}
        self.data = structs.StateData()

        self.state = statecode

    def record_county_presidential_result(self, record: SQLRecord) -> None:
        """
        Records a "county"-level presidential result.
        """
        # Initialize the county
        county = record.fipscode
        if county not in self.data.counties:
            self.data.counties[county] = structs.County()

        # Add the results from this record
        handle_candidate_results(
            self.data.counties[county].P,
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
        )

    def record_county_senate_result(self, record: SQLRecord) -> None:
        """
        Records a "county"-level senate result.
        """
        state = record.statepostal
        if state == "GA" and record.seatnum == 2:
            # Georgia senate special election
            state = "GA-S"

        # Initialize the county
        county = record.fipscode
        if county not in self.data.counties:
            self.data.counties[county] = structs.County()

        # Initialize the senate result
        if state not in self.data.counties[county].S:
            self.data.counties[county].S[state] = structs.CountyCongressionalResult()

        # Add the results from this record
        handle_candidate_results(
            self.data.counties[county].S[state],
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
        )

    def record_county_house_result(self, record: SQLRecord) -> None:
        """
        Records a "county"-level house result.
        """
        state = record.statepostal
        seat = str(record.seatnum).zfill(2)
        if state in AT_LARGE_HOUSE_STATES:
            seat = "AL"

        # Initialize the county
        county = record.fipscode
        if county not in self.data.counties:
            self.data.counties[county] = structs.County()

        # Initialize the house result
        if seat not in self.data.counties[county].H:
            self.data.counties[county].H[seat] = structs.CountyCongressionalResult()

        # Add the results from this record
        handle_candidate_results(
            self.data.counties[county].H[seat],
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
        )

    def run_export(self, preloaded_results: Iterable[SQLRecord]) -> structs.StateData:
        self.data = structs.StateData()

        sql_filter = "level = 'county' AND statepostal = %s"
        filter_params: List[Any] = [self.state]

        with tracer.trace("enip.export.state.historicals"):
            self.historical_counts = load_historicals(
                self.ingest_run_dt, sql_filter, filter_params
            )

        def handle_record(record):
            if record.officeid == "P":
                self.record_county_presidential_result(record)
            elif record.officeid == "S":
                self.record_county_senate_result(record)
            elif record.officeid == "H":
                self.record_county_house_result(record)
            else:
                raise RuntimeError(
                    f"Uncategorizable result: {record.elex_id} {record.level} {record.officeid}"
                )

        for record in preloaded_results:
            if record.statepostal == self.state:
                handle_record(record)

        return self.data
