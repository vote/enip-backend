from datetime import datetime
from enum import Enum
from typing import Any, Optional, NamedTuple, Union, cast, Dict, Tuple, List

from ..enip_common.pg import get_cursor
from ..enip_common.states import DISTRICTS_BY_STATE, AT_LARGE_HOUSE_STATES

from . import structs
from .helpers import (
    SQLRecord,
    HistoricalResults,
    handle_candidate_results,
    load_election_results,
    load_historicals,
)


class StateDataExporter:
    data: structs.StateData

    def __init__(self, ingest_run_id: str, ingest_run_dt: datetime, statecode: str):
        self.ingest_run_id = ingest_run_id
        self.ingest_run_dt = ingest_run_dt
        self.historical_counts: HistoricalResults = {}
        self.data = structs.StateData()

        self.state = statecode

    def record_county_presidential_result(self, record: SQLRecord) -> None:
        """
        Records a "county"-level presidential result.
        """
        state = record.statepostal

        # Initialize the state summary
        if state not in self.data.state_summaries:
            self.data.state_summaries[state] = structs.StateSummary()

        # Initialize the county
        county = record.fipscode
        if county not in self.data.state_summaries[state].counties:
            self.data.state_summaries[state].counties[county] = structs.County()

        # Add the results from this record
        handle_candidate_results(
            self.data.state_summaries[state].counties[county].P,
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

        # Initialize the state summary
        if state not in self.data.state_summaries:
            self.data.state_summaries[state] = structs.StateSummary()

        # Initialize the county
        county = record.fipscode
        if county not in self.data.state_summaries[state].counties:
            self.data.state_summaries[state].counties[county] = structs.County()

        # Initialize the sentate result
        senate_result = self.data.state_summaries[state].counties[county].S
        if not senate_result:
            # No results for this senate race yet, initialize it
            senate_result = structs.CountyCongressionalResult()
            self.data.state_summaries[state].counties[county].S = senate_result

        # Add the results from this record
        handle_candidate_results(
            senate_result,
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

        # Initialize the state summary
        if state not in self.data.state_summaries:
            self.data.state_summaries[state] = structs.StateSummary()

        # Initialize the county
        county = record.fipscode
        if county not in self.data.state_summaries[state].counties:
            self.data.state_summaries[state].couznties[county] = structs.County()

        # Initialize the house result
        house_results = self.data.state_summaries[state].counties[county].H
        if seat not in house_results:
            house_results[seat] = structs.CountyCongressionalResult()

        # Add the results from this record
        handle_candidate_results(
            house_results[seat],
            structs.StateSummaryCandidateNamed,
            record,
            self.historical_counts,
        )

    def get_filters(self) -> Tuple[str, List[Any]]:
        """
        Returns the election filters for this export.
        Should return (sql, params)
        """
        return "level IN ('national', 'state', 'district', 'county')", []

    def run_export(self) -> structs.StateData:
        self.data = structs.StateData()

        sql_filter = "level = 'county' AND statepostal = %s"
        filter_params: List[Any] = [self.state]
        self.historical_counts = load_historicals(
            self.ingest_run_dt, sql_filter, filter_params
        )
        for record in load_election_results(
            self.ingest_run_id, sql_filter, filter_params
        ):
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

        return self.data
