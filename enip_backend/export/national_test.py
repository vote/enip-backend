import json
from datetime import datetime, timezone

import pytest

from . import structs
from .helpers import Calls, Comments, HistoricalResults, SQLRecord
from .national import NationalDataExporter

mock_calls: Calls = {}
mock_comments: Comments = {}
mock_historicals: HistoricalResults = {}


@pytest.fixture(autouse=True)
def init_mocks(mocker):
    global mock_calls
    global mock_comments
    global mock_historicals

    mock_calls = {"P": {}, "S": {}}
    mock_comments = {"P": {}, "S": {}, "H": {}, "N": {"N": []}}
    mock_historicals = {}

    mock_load_calls = mocker.patch("enip_backend.export.national.load_calls")
    mock_load_calls.return_value = mock_calls

    mock_load_comments = mocker.patch("enip_backend.export.national.load_comments")
    mock_load_comments.return_value = mock_comments

    mock_load_historicals = mocker.patch(
        "enip_backend.export.national.load_historicals"
    )
    mock_load_historicals.return_value = mock_historicals


@pytest.fixture
def exporter():
    return NationalDataExporter(
        "test_run", datetime(2020, 11, 3, 8, 0, 0, tzinfo=timezone.utc)
    )


def assert_result(actual, expected):
    # We make assertions using the JSON representation
    # because that prints much better in pytest
    assert json.loads(actual.json()) == json.loads(expected.json())


# Helpers for constructing results
def state_summary(state, summary):
    r = structs.NationalData()
    r.state_summaries[state] = summary

    return r


def national_summary(summary, *state_summaries):
    r = structs.NationalData()
    r.national_summary = summary

    for summary_struct in state_summaries:
        for state, summary in summary_struct.state_summaries.items():
            r.state_summaries[state] = summary

    return r


# National result
def test_national_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="US",
                    fipscode="12345",
                    level="national",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=538,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                )
            ]
        ),
        structs.NationalData(
            national_summary=structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=12345,
                        pop_pct=0.234,
                        elect_won=0,
                    )
                )
            )
        ),
    )


# ME statewide (ignore)
def test_statewide_me_prez_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="ME",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=2,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                )
            ]
        ),
        structs.NationalData(),
    )


# ME at large
def test_atlarge_me_prez_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="ME",
                    fipscode="12345",
                    level="district",
                    reportingunitname="At Large",
                    officeid="P",
                    seatnum=None,
                    party="GOP",
                    first="Donald",
                    last="Trump",
                    electtotal=2,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                )
            ]
        ),
        structs.NationalData(
            state_summaries={
                "ME": structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=12345,
                            pop_pct=0.234,
                        )
                    )
                )
            }
        ),
    )


# ME-01
def test_me_01_prez_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="ME",
                    fipscode="12345",
                    level="district",
                    reportingunitname="District 1",
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=1,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                )
            ]
        ),
        state_summary(
            "ME-01",
            structs.PresidentialCDSummary(
                P=structs.StateSummaryPresident(
                    dem=structs.StateSummaryCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=12345,
                        pop_pct=0.234,
                    )
                )
            ),
        ),
    )


# NE-02 winner call, published
def test_me_01_prez_call_published(exporter):
    mock_calls["P"]["ME-01"] = True

    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="US",
                    fipscode="12345",
                    level="national",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=538,
                    votecount=67890,
                    votepct=0.567,
                    winner=False,
                ),
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="ME",
                    fipscode="12345",
                    level="district",
                    reportingunitname="District 1",
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=1,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=67890,
                        pop_pct=0.567,
                        elect_won=1,
                    )
                )
            ),
            state_summary(
                "ME-01",
                structs.PresidentialCDSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                        winner=structs.Party.DEM,
                    )
                ),
            ),
        ),
    )


# NE-02 winner call, unpublished
def test_me_01_prez_call_unpublished(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="US",
                    fipscode="12345",
                    level="national",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=538,
                    votecount=67890,
                    votepct=0.567,
                    winner=False,
                ),
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="ME",
                    fipscode="12345",
                    level="district",
                    reportingunitname="District 1",
                    officeid="P",
                    seatnum=None,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=1,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=67890,
                        pop_pct=0.567,
                    )
                )
            ),
            state_summary(
                "ME-01",
                structs.PresidentialCDSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                    )
                ),
            ),
        ),
    )


# state result
def test_state_prez_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="CA",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="Lib",
                    first="Jo",
                    last="Jorgensen",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                ),
            ],
        ),
        state_summary(
            "CA",
            structs.StateSummary(
                P=structs.StateSummaryPresident(
                    oth=structs.StateSummaryCandidateUnnamed(
                        pop_vote=12345, pop_pct=0.234,
                    ),
                )
            ),
        ),
    )


# state winner call, published
def test_state_prez_call_published(exporter):
    mock_calls["P"]["CA"] = True

    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="US",
                    fipscode="12345",
                    level="national",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="GOP",
                    first="Donald",
                    last="Trump",
                    electtotal=538,
                    votecount=67890,
                    votepct=0.567,
                    winner=False,
                ),
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="CA",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="GOP",
                    first="Donald",
                    last="Trump",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    gop=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Donald",
                        last_name="Trump",
                        pop_vote=67890,
                        pop_pct=0.567,
                        elect_won=55,
                    )
                )
            ),
            state_summary(
                "CA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                        winner=structs.Party.GOP,
                    )
                ),
            ),
        ),
    )


# state winner call, unpublished
def test_state_prez_call_unpublished(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="US",
                    fipscode="12345",
                    level="national",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="GOP",
                    first="Donald",
                    last="Trump",
                    electtotal=538,
                    votecount=67890,
                    votepct=0.567,
                    winner=False,
                ),
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="CA",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="P",
                    seatnum=None,
                    party="GOP",
                    first="Donald",
                    last="Trump",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    gop=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Donald",
                        last_name="Trump",
                        pop_vote=67890,
                        pop_pct=0.567,
                    )
                )
            ),
            state_summary(
                "CA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                    )
                ),
            ),
        ),
    )


# senate result
def test_state_senate_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="MA",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="S",
                    seatnum=None,
                    party="Grn",
                    first="Howie",
                    last="Hawkins",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                ),
            ],
        ),
        state_summary(
            "MA",
            structs.StateSummary(
                S=structs.StateSummaryCongressionalResult(
                    oth=structs.StateSummaryCandidateUnnamed(
                        pop_vote=12345, pop_pct=0.234,
                    ),
                )
            ),
        ),
    )


# GA-S senate result
def test_ga_special_senate_result(exporter):
    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="GA",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="S",
                    seatnum=2,
                    party="Dem",
                    first="Joe",
                    last="Biden",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=False,
                ),
            ],
        ),
        state_summary(
            "GA-S",
            structs.SenateSpecialSummary(
                S=structs.StateSummaryCongressionalResult(
                    dem=structs.StateSummaryCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=12345,
                        pop_pct=0.234,
                    ),
                )
            ),
        ),
    )


# sente winner call, published
def test_senate_winner_call_published(exporter):
    mock_calls["S"]["NE"] = True

    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="NE",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="S",
                    seatnum=None,
                    party="GOP",
                    first="Ben",
                    last="Sasse",
                    electtotal=1,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                S=structs.NationalSummaryWinnerCount(
                    gop=structs.NationalSummaryWinnerCountEntry(won=1)
                )
            ),
            state_summary(
                "NE",
                structs.StateSummary(
                    S=structs.StateSummaryCongressionalResult(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Ben",
                            last_name="Sasse",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                        winner=structs.Party.GOP,
                    )
                ),
            ),
        ),
    )


# senate winner call, unpublished
def test_senate_winner_call_unpublished(exporter):
    mock_calls["S"]["NE"] = False

    assert_result(
        exporter.run_export(
            [
                SQLRecord(
                    ingest_id="test_run",
                    elex_id="test_elex",
                    statepostal="NE",
                    fipscode="12345",
                    level="state",
                    reportingunitname=None,
                    officeid="S",
                    seatnum=None,
                    party="GOP",
                    first="Ben",
                    last="Sasse",
                    electtotal=1,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
            ],
        ),
        state_summary(
            "NE",
            structs.StateSummary(
                S=structs.StateSummaryCongressionalResult(
                    gop=structs.StateSummaryCandidateNamed(
                        first_name="Ben",
                        last_name="Sasse",
                        pop_vote=12345,
                        pop_pct=0.234,
                    ),
                )
            ),
        ),
    )


# house result
# house at large result

# house winner call

# historicals
# oth candidate + historicals
# multiple dems + historicals
# multiple gop + historicals

# presidential winner
# counting multiple senate winners

# presidential commentary
# senate commentary
# GA-S commentary
# house commentary
# house at large commentary
# national commentary
