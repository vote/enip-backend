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


# Helpers for constructing SQLRecords
def default_name(party, first, last):
    if party == "Dem":
        return (first or "Joe", last or "Biden")
    elif party == "GOP":
        return (first or "Donald", last or "Trump")
    else:
        return (first or "Foo", last or "Barson")


def res_p_national(
    party,
    votecount,
    votepct,
    winner=False,
    first=None,
    last=None,
    ingest_id="test_run",
    elex_id="test_elex",
):
    first, last = default_name(party, first, last)

    return SQLRecord(
        ingest_id=ingest_id,
        elex_id=elex_id,
        statepostal="US",
        fipscode="12345",
        level="national",
        reportingunitname=None,
        officeid="P",
        seatnum=None,
        party=party,
        first=first,
        last=last,
        electtotal=538,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_p_state(
    state,
    party,
    votecount,
    votepct,
    electtotal=10,
    winner=False,
    first=None,
    last=None,
    ingest_id="test_run",
    elex_id="test_elex",
):
    first, last = default_name(party, first, last)

    return SQLRecord(
        ingest_id=ingest_id,
        elex_id=elex_id,
        statepostal=state,
        fipscode="12345",
        level="state",
        reportingunitname=None,
        officeid="P",
        seatnum=None,
        party=party,
        first=first,
        last=last,
        electtotal=electtotal,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_p_district(
    state,
    reportingunitname,
    party,
    votecount,
    votepct,
    electtotal=1,
    winner=False,
    first=None,
    last=None,
    ingest_id="test_run",
    elex_id="test_elex",
):
    first, last = default_name(party, first, last)

    return SQLRecord(
        ingest_id=ingest_id,
        elex_id=elex_id,
        statepostal=state,
        fipscode="12345",
        level="district",
        reportingunitname=reportingunitname,
        officeid="P",
        seatnum=None,
        party=party,
        first=first,
        last=last,
        electtotal=electtotal,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_s(
    state,
    party,
    first,
    last,
    votecount,
    votepct,
    winner=False,
    ingest_id="test_run",
    elex_id="test_elex",
):
    seatnum = None
    if state == "GA-S":
        state = "GA"
        seatnum = 2

    return SQLRecord(
        ingest_id=ingest_id,
        elex_id=elex_id,
        statepostal=state,
        fipscode="12345",
        level="state",
        reportingunitname=None,
        officeid="S",
        seatnum=seatnum,
        party=party,
        first=first,
        last=last,
        electtotal=1,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_h(
    state,
    seatnum,
    party,
    first,
    last,
    votecount,
    votepct,
    winner=False,
    ingest_id="test_run",
    elex_id="test_elex",
):
    return SQLRecord(
        ingest_id=ingest_id,
        elex_id=elex_id,
        statepostal=state,
        fipscode="12345",
        level="state",
        reportingunitname=None,
        officeid="H",
        seatnum=seatnum,
        party=party,
        first=first,
        last=last,
        electtotal=1,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


# National result
def test_national_result(exporter):
    assert_result(
        exporter.run_export([res_p_national("Dem", votecount=12345, votepct=0.234)]),
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
        exporter.run_export([res_p_state("ME", "Dem", votecount=12345, votepct=0.234)]),
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
        exporter.run_export([res_p_district("ME", "District 1", "Dem", 12345, 0.234)]),
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
    mock_calls["P"]["NE-02"] = True

    assert_result(
        exporter.run_export(
            [
                res_p_national("Dem", votecount=67890, votepct=0.567),
                res_p_district(
                    "NE",
                    "District 2",
                    "Dem",
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
                "NE-02",
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


# ME-01 winner call, unpublished
def test_me_01_prez_call_unpublished(exporter):
    assert_result(
        exporter.run_export(
            [
                res_p_national("Dem", votecount=67890, votepct=0.567),
                res_p_district(
                    "ME",
                    "District 1",
                    "Dem",
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
            [res_p_state("CA", "Lib", votecount=12345, votepct=0.234)],
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
    mock_calls["P"]["UT"] = True

    assert_result(
        exporter.run_export(
            [
                res_p_national("GOP", votecount=67890, votepct=0.567),
                res_p_national("Lib", votecount=123, votepct=0.123),
                res_p_state(
                    "CA",
                    "GOP",
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                    electtotal=55,
                ),
                res_p_state(
                    "UT", "Lib", votecount=123, votepct=0.123, winner=True, electtotal=6
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
                    ),
                    oth=structs.NationalSummaryPresidentCandidateUnnamed(
                        pop_vote=123, pop_pct=0.123, elect_won=6,
                    ),
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
            state_summary(
                "UT",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        oth=structs.StateSummaryCandidateUnnamed(
                            pop_vote=123, pop_pct=0.123,
                        ),
                        winner=structs.Party.OTHER,
                    )
                ),
            ),
        ),
    )


# state winner call, unpublished
def test_state_prez_call_unpublished(exporter):
    mock_calls["P"]["UT"] = True

    assert_result(
        exporter.run_export(
            [
                res_p_national("GOP", votecount=67890, votepct=0.567,),
                res_p_state(
                    "CA",
                    "GOP",
                    electtotal=55,
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
                res_p_state("UT", "GOP", electtotal=6, votecount=456, votepct=0.456,),
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
            state_summary(
                "UT",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=456,
                            pop_pct=0.456,
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
            [res_s("MA", "Grn", "Howie", "Hawkins", votecount=12345, votepct=0.234,),],
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
                res_s(
                    "GA-S", "Dem", "Raphael", "Warnock", votecount=12345, votepct=0.234,
                ),
            ],
        ),
        state_summary(
            "GA-S",
            structs.SenateSpecialSummary(
                S=structs.StateSummaryCongressionalResult(
                    dem=structs.StateSummaryCandidateNamed(
                        first_name="Raphael",
                        last_name="Warnock",
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
                res_s(
                    "NE",
                    "GOP",
                    "Ben",
                    "Sasse",
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
    mock_calls["S"]["MA"] = True

    assert_result(
        exporter.run_export(
            [
                res_s(
                    "NE",
                    "GOP",
                    "Ben",
                    "Sasse",
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
                res_s("MA", "Dem", "Ed", "Markey", votecount=12345, votepct=0.234),
            ],
        ),
        national_summary(
            structs.NationalSummary(),
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
            state_summary(
                "MA",
                structs.StateSummary(
                    S=structs.StateSummaryCongressionalResult(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Ed",
                            last_name="Markey",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                    )
                ),
            ),
        ),
    )


# house result
def test_state_house_result(exporter):
    assert_result(
        exporter.run_export(
            [res_h("GA", 4, "Dem", "Hank", "Johnson", votecount=12345, votepct=0.234)],
        ),
        state_summary(
            "GA",
            structs.StateSummary(
                H={
                    "04": structs.StateSummaryCongressionalResult(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Hank",
                            last_name="Johnson",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                    )
                }
            ),
        ),
    )


# house at large result
def test_state_house_at_large_result(exporter):
    assert_result(
        exporter.run_export(
            [res_h("AK", 1, "GOP", "Don", "Young", votecount=12345, votepct=0.234)],
        ),
        state_summary(
            "AK",
            structs.StateSummary(
                H={
                    "AL": structs.StateSummaryCongressionalResult(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Don",
                            last_name="Young",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                    )
                }
            ),
        ),
    )


# house winner call
def test_state_house_at_large_call(exporter):
    assert_result(
        exporter.run_export(
            [
                res_h(
                    "AK",
                    1,
                    "Dem",
                    "Alyse",
                    "Galvin",
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
                res_h(
                    "OH",
                    3,
                    "Dem",
                    "Joyce",
                    "Beatty",
                    votecount=12345,
                    votepct=0.234,
                    winner=True,
                ),
                res_h(
                    "OH",
                    1,
                    "Ind",
                    "Kiumars",
                    "Kiani",
                    votecount=123,
                    votepct=0.12,
                    winner=True,
                ),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                H=structs.NationalSummaryWinnerCount(
                    dem=structs.NationalSummaryWinnerCountEntry(won=2),
                    oth=structs.NationalSummaryWinnerCountEntry(won=1),
                )
            ),
            state_summary(
                "AK",
                structs.StateSummary(
                    H={
                        "AL": structs.StateSummaryCongressionalResult(
                            dem=structs.StateSummaryCandidateNamed(
                                first_name="Alyse",
                                last_name="Galvin",
                                pop_vote=12345,
                                pop_pct=0.234,
                            ),
                            winner=structs.Party.DEM,
                        )
                    }
                ),
            ),
            state_summary(
                "OH",
                structs.StateSummary(
                    H={
                        "01": structs.StateSummaryCongressionalResult(
                            oth=structs.StateSummaryCandidateUnnamed(
                                first_name="Kiumars",
                                last_name="Kiani",
                                pop_vote=123,
                                pop_pct=0.12,
                            ),
                            winner=structs.Party.OTHER,
                        ),
                        "03": structs.StateSummaryCongressionalResult(
                            dem=structs.StateSummaryCandidateNamed(
                                first_name="Joyce",
                                last_name="Beatty",
                                pop_vote=12345,
                                pop_pct=0.234,
                            ),
                            winner=structs.Party.DEM,
                        ),
                    }
                ),
            ),
        ),
    )


# historicals, national-level
def test_historical_national_counts(exporter):
    mock_historicals["test_dem"] = {"A": 1, "B": 2}
    mock_historicals["test_gop"] = {"B": 10, "C": 20}
    mock_historicals["test_lib"] = {"C": 100, "D": 200}

    assert_result(
        exporter.run_export(
            [
                res_p_national(
                    "Dem", votecount=12345, votepct=0.234, elex_id="test_dem"
                ),
                res_p_national(
                    "GOP", votecount=67890, votepct=0.567, elex_id="test_gop"
                ),
                res_p_national("Lib", votecount=123, votepct=0.012, elex_id="test_lib"),
            ],
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=12345,
                        pop_pct=0.234,
                        elect_won=0,
                        pop_vote_history={"A": 1, "B": 2},
                    ),
                    gop=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Donald",
                        last_name="Trump",
                        pop_vote=67890,
                        pop_pct=0.567,
                        elect_won=0,
                        pop_vote_history={"B": 10, "C": 20},
                    ),
                    oth=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Jo",
                        last_name="Jorgensen",
                        pop_vote=123,
                        pop_pct=0.012,
                        elect_won=0,
                        pop_vote_history={"C": 100, "D": 200},
                    ),
                )
            )
        ),
    )


# multiple gop + historicals
def test_historical_senate_counts(exporter):
    mock_historicals["test_loeffler"] = {"A": 1, "B": 2}
    mock_historicals["test_collins"] = {"B": 10, "C": 20}
    mock_historicals["test_hazel"] = {"C": 100, "D": 200}

    assert_result(
        exporter.run_export(
            [
                res_s(
                    "GA-S",
                    "GOP",
                    "Kelly",
                    "Loeffler",
                    elex_id="test_loeffler",
                    votecount=789,
                    votepct=0.4,
                ),
                res_s(
                    "GA-S",
                    "GOP",
                    "Doug",
                    "Collins",
                    elex_id="test_collins",
                    votecount=456,
                    votepct=0.3,
                ),
                res_s(
                    "GA-S",
                    "Lib",
                    "Shane",
                    "Hazel",
                    elex_id="test_hazel",
                    votecount=123,
                    votepct=0.2,
                ),
            ],
        ),
        state_summary(
            "GA-S",
            structs.SenateSpecialSummary(
                S=structs.StateSummaryCongressionalResult(
                    gop=structs.StateSummaryCandidateNamed(
                        first_name="Kelly",
                        last_name="Loeffler",
                        pop_vote=789,
                        pop_pct=0.4,
                        pop_vote_history={"A": 1, "B": 2},
                    ),
                    oth=structs.StateSummaryCandidateUnnamed(
                        pop_vote=123 + 456,
                        pop_pct=0.2 + 0.3,
                        pop_vote_history={"B": 10, "C": 20 + 100, "D": 200},
                    ),
                    multiple_gop=True,
                )
            ),
        ),
    )


# multiple dem + historicals
def test_historical_house_counts(exporter):
    mock_historicals["test_pelosi"] = {"A": 1, "B": 2}
    mock_historicals["test_buttar"] = {"B": 10, "C": 20}

    assert_result(
        exporter.run_export(
            [
                res_h(
                    "CA",
                    12,
                    "Dem",
                    "Nancy",
                    "Pelosi",
                    votecount=789,
                    votepct=0.4,
                    elex_id="test_pelosi",
                ),
                res_h(
                    "CA",
                    12,
                    "Dem",
                    "Shahid",
                    "Buttar",
                    votecount=456,
                    votepct=0.3,
                    elex_id="test_buttar",
                ),
            ],
        ),
        state_summary(
            "CA",
            structs.StateSummary(
                H={
                    "12": structs.StateSummaryCongressionalResult(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Nancy",
                            last_name="Pelosi",
                            pop_vote=789,
                            pop_pct=0.4,
                            pop_vote_history={"A": 1, "B": 2},
                        ),
                        oth=structs.StateSummaryCandidateUnnamed(
                            pop_vote=456,
                            pop_pct=0.3,
                            pop_vote_history={"B": 10, "C": 20},
                        ),
                        multiple_dem=True,
                    )
                }
            ),
        ),
    )


# presidential winner
def test_call_winner_dem(exporter):
    mock_calls["P"]["CA"] = True
    mock_calls["P"]["MA"] = True
    mock_calls["P"]["WA"] = True

    assert_result(
        exporter.run_export(
            [
                res_p_national("Dem", 123, 0.123),
                res_p_national("GOP", 456, 0.456),
                res_p_state("CA", "Dem", 111, 0.111, electtotal=200, winner=True),
                res_p_state("MA", "Dem", 222, 0.222, electtotal=70, winner=True),
                res_p_state("WA", "GOP", 333, 0.333, electtotal=200, winner=True),
                res_p_state("WY", "GOP", 444, 0.444, electtotal=70, winner=True),
            ]
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=123,
                        pop_pct=0.123,
                        elect_won=270,
                    ),
                    gop=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Donald",
                        last_name="Trump",
                        pop_vote=456,
                        pop_pct=0.456,
                        elect_won=200,
                    ),
                    winner=structs.Party.DEM,
                )
            ),
            state_summary(
                "CA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=111,
                            pop_pct=0.111,
                        ),
                        winner=structs.Party.DEM,
                    ),
                ),
            ),
            state_summary(
                "MA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=222,
                            pop_pct=0.222,
                        ),
                        winner=structs.Party.DEM,
                    ),
                ),
            ),
            state_summary(
                "WA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=333,
                            pop_pct=0.333,
                        ),
                        winner=structs.Party.GOP,
                    ),
                ),
            ),
            state_summary(
                "WY",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=444,
                            pop_pct=0.444,
                        ),
                    ),
                ),
            ),
        ),
    )


def test_call_winner_gop(exporter):
    mock_calls["P"]["CA"] = True
    mock_calls["P"]["MA"] = True
    mock_calls["P"]["WA"] = True
    mock_calls["P"]["WY"] = True

    assert_result(
        exporter.run_export(
            [
                res_p_national("Dem", 123, 0.123),
                res_p_national("GOP", 456, 0.456),
                res_p_state("CA", "Dem", 111, 0.111, electtotal=200, winner=False),
                res_p_state("MA", "Dem", 222, 0.222, electtotal=70, winner=True),
                res_p_state("WA", "GOP", 333, 0.333, electtotal=200, winner=True),
                res_p_state("WY", "GOP", 444, 0.444, electtotal=70, winner=True),
            ]
        ),
        national_summary(
            structs.NationalSummary(
                P=structs.NationalSummaryPresident(
                    dem=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Joe",
                        last_name="Biden",
                        pop_vote=123,
                        pop_pct=0.123,
                        elect_won=70,
                    ),
                    gop=structs.NationalSummaryPresidentCandidateNamed(
                        first_name="Donald",
                        last_name="Trump",
                        pop_vote=456,
                        pop_pct=0.456,
                        elect_won=270,
                    ),
                    winner=structs.Party.GOP,
                )
            ),
            state_summary(
                "CA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=111,
                            pop_pct=0.111,
                        ),
                    ),
                ),
            ),
            state_summary(
                "MA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=222,
                            pop_pct=0.222,
                        ),
                        winner=structs.Party.DEM,
                    ),
                ),
            ),
            state_summary(
                "WA",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=333,
                            pop_pct=0.333,
                        ),
                        winner=structs.Party.GOP,
                    ),
                ),
            ),
            state_summary(
                "WY",
                structs.StateSummary(
                    P=structs.StateSummaryPresident(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=444,
                            pop_pct=0.444,
                        ),
                        winner=structs.Party.GOP,
                    ),
                ),
            ),
        ),
    )


# presidential commentary
def test_prez_commentary(exporter):
    mock_comments["P"]["CA"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 3, 4, tzinfo=timezone.utc),
            author="D",
            title="E",
            body="F",
        ),
    ]

    assert_result(
        exporter.run_export(
            [res_p_state("CA", "Lib", votecount=12345, votepct=0.234)],
        ),
        state_summary(
            "CA",
            structs.StateSummary(
                P=structs.StateSummaryPresident(
                    oth=structs.StateSummaryCandidateUnnamed(
                        pop_vote=12345, pop_pct=0.234,
                    ),
                    comments=[
                        structs.Comment(
                            timestamp=datetime(
                                2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc
                            ),
                            author="A",
                            title="B",
                            body="C",
                        ),
                        structs.Comment(
                            timestamp=datetime(
                                2020, 11, 3, 8, 3, 4, tzinfo=timezone.utc
                            ),
                            author="D",
                            title="E",
                            body="F",
                        ),
                    ],
                ),
            ),
        ),
    )


# senate commentary
def test_senate_commentary(exporter):
    mock_comments["S"]["GA"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
    ]

    assert_result(
        exporter.run_export(
            [res_s("GA", "GOP", "David", "Perdue", votecount=12345, votepct=0.234,),],
        ),
        state_summary(
            "GA",
            structs.StateSummary(
                S=structs.StateSummaryCongressionalResult(
                    gop=structs.StateSummaryCandidateNamed(
                        first_name="David",
                        last_name="Perdue",
                        pop_vote=12345,
                        pop_pct=0.234,
                    ),
                    comments=[
                        structs.Comment(
                            timestamp=datetime(
                                2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc
                            ),
                            author="A",
                            title="B",
                            body="C",
                        ),
                    ],
                )
            ),
        ),
    )


# GA-S commentary
def test_senate_special_commentary(exporter):
    mock_comments["S"]["GA-S"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
    ]

    assert_result(
        exporter.run_export(
            [
                res_s(
                    "GA-S", "Dem", "Raphael", "Warnock", votecount=12345, votepct=0.234,
                ),
            ],
        ),
        state_summary(
            "GA-S",
            structs.SenateSpecialSummary(
                S=structs.StateSummaryCongressionalResult(
                    dem=structs.StateSummaryCandidateNamed(
                        first_name="Raphael",
                        last_name="Warnock",
                        pop_vote=12345,
                        pop_pct=0.234,
                    ),
                    comments=[
                        structs.Comment(
                            timestamp=datetime(
                                2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc
                            ),
                            author="A",
                            title="B",
                            body="C",
                        ),
                    ],
                )
            ),
        ),
    )


# house commentary
def test_house_commentary(exporter):
    mock_comments["H"]["GA-04"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
    ]

    assert_result(
        exporter.run_export(
            [res_h("GA", 4, "Dem", "Hank", "Johnson", votecount=12345, votepct=0.234)],
        ),
        state_summary(
            "GA",
            structs.StateSummary(
                H={
                    "04": structs.StateSummaryCongressionalResult(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Hank",
                            last_name="Johnson",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                        comments=[
                            structs.Comment(
                                timestamp=datetime(
                                    2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc
                                ),
                                author="A",
                                title="B",
                                body="C",
                            ),
                        ],
                    )
                }
            ),
        ),
    )


# house at large commentary
def test_house_al_commentar(exporter):
    mock_comments["H"]["AK-AL"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
    ]

    assert_result(
        exporter.run_export(
            [res_h("AK", 1, "GOP", "Don", "Young", votecount=12345, votepct=0.234)],
        ),
        state_summary(
            "AK",
            structs.StateSummary(
                H={
                    "AL": structs.StateSummaryCongressionalResult(
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Don",
                            last_name="Young",
                            pop_vote=12345,
                            pop_pct=0.234,
                        ),
                        comments=[
                            structs.Comment(
                                timestamp=datetime(
                                    2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc
                                ),
                                author="A",
                                title="B",
                                body="C",
                            ),
                        ],
                    )
                }
            ),
        ),
    )


# national commentary
def test_national_commentary(exporter):
    mock_comments["N"]["N"] = [
        structs.Comment(
            timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
            author="A",
            title="B",
            body="C",
        ),
    ]

    assert_result(
        exporter.run_export(
            [res_p_state("CA", "Lib", votecount=12345, votepct=0.234)],
        ),
        national_summary(
            structs.NationalSummary(
                comments=[
                    structs.Comment(
                        timestamp=datetime(2020, 11, 3, 8, 1, 2, tzinfo=timezone.utc),
                        author="A",
                        title="B",
                        body="C",
                    ),
                ]
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
        ),
    )
