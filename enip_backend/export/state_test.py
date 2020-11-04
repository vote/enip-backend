import json
from datetime import datetime, timezone

import pytest

from . import structs
from .helpers import HistoricalResults, SQLRecord
from .state import StateDataExporter

mock_historicals: HistoricalResults = {}


@pytest.fixture(autouse=True)
def init_mocks(mocker):
    global mock_historicals

    mock_historicals = {}

    mock_load_historicals = mocker.patch("enip_backend.export.state.load_historicals")
    mock_load_historicals.return_value = mock_historicals


def exporter(state):
    return StateDataExporter(datetime(2020, 11, 3, 8, 0, 0, tzinfo=timezone.utc), state)


def assert_result(actual, expected):
    # We make assertions using the JSON representation
    # because that prints much better in pytest
    assert json.loads(actual.json()) == json.loads(expected.json())


# Helpers for constructing SQLRecords
def default_name(party, first, last):
    if party == "Dem":
        return (first or "Joe", last or "Biden")
    elif party == "GOP":
        return (first or "Donald", last or "Trump")
    else:
        return (first or "Foo", last or "Barson")


def res_p(
    state,
    fipscode,
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
        statepostal=state,
        fipscode=fipscode,
        level="county",
        reportingunitname=None,
        officeid="P",
        seatnum=None,
        party=party,
        first=first,
        last=last,
        electtotal=538,
        electwon=0,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_s(
    state,
    fipscode,
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
        fipscode=fipscode,
        level="county",
        reportingunitname=None,
        officeid="S",
        seatnum=seatnum,
        party=party,
        first=first,
        last=last,
        electtotal=538,
        electwon=0,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def res_h(
    state,
    seatnum,
    fipscode,
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
        fipscode=fipscode,
        level="county",
        reportingunitname=None,
        officeid="H",
        seatnum=seatnum,
        party=party,
        first=first,
        last=last,
        electtotal=538,
        electwon=0,
        votecount=votecount,
        votepct=votepct,
        winner=winner,
    )


def test_prez_result():
    mock_historicals["test_dem"] = {"A": 1, "B": 2}
    mock_historicals["test_gop"] = {"B": 10, "C": 20}
    mock_historicals["test_lib"] = {"C": 100, "D": 200}

    assert_result(
        exporter("MA").run_export(
            [
                res_p(
                    "MA",
                    "12345",
                    "Dem",
                    votecount=12345,
                    votepct=0.234,
                    elex_id="test_dem",
                ),
                res_p(
                    "MA",
                    "12345",
                    "GOP",
                    votecount=67890,
                    votepct=0.567,
                    elex_id="test_gop",
                ),
                res_p(
                    "MA",
                    "12345",
                    "Lib",
                    votecount=123,
                    votepct=0.012,
                    elex_id="test_lib",
                ),
            ]
        ),
        structs.StateData(
            counties={
                "12345": structs.County(
                    P=structs.CountyPresidentialResult(
                        dem=structs.StateSummaryCandidateNamed(
                            first_name="Joe",
                            last_name="Biden",
                            pop_vote=12345,
                            pop_pct=0.234,
                            pop_vote_history={"A": 1, "B": 2,},
                        ),
                        gop=structs.StateSummaryCandidateNamed(
                            first_name="Donald",
                            last_name="Trump",
                            pop_vote=67890,
                            pop_pct=0.567,
                            pop_vote_history={"B": 10, "C": 20,},
                        ),
                        oth=structs.StateSummaryCandidateUnnamed(
                            pop_vote=123,
                            pop_pct=0.012,
                            pop_vote_history={"C": 100, "D": 200,},
                        ),
                    )
                )
            }
        ),
    )


def test_senate_result():
    mock_historicals["test_loeffler"] = {"A": 1, "B": 2}
    mock_historicals["test_collins"] = {"B": 10, "C": 20}
    mock_historicals["test_hazel"] = {"C": 100, "D": 200}

    assert_result(
        exporter("GA").run_export(
            [
                res_s(
                    "GA-S",
                    "12345",
                    "GOP",
                    "Kelly",
                    "Loeffler",
                    elex_id="test_loeffler",
                    votecount=789,
                    votepct=0.4,
                ),
                res_s(
                    "GA-S",
                    "12345",
                    "GOP",
                    "Doug",
                    "Collins",
                    elex_id="test_collins",
                    votecount=456,
                    votepct=0.3,
                ),
                res_s(
                    "GA-S",
                    "12345",
                    "Lib",
                    "Shane",
                    "Hazel",
                    elex_id="test_hazel",
                    votecount=123,
                    votepct=0.2,
                ),
                res_s(
                    "GA",
                    "67890",
                    "Dem",
                    "Jon",
                    "Ossof",
                    elex_id="test_ossof",
                    votecount=1,
                    votepct=0.2,
                ),
            ]
        ),
        structs.StateData(
            counties={
                "12345": structs.County(
                    S={
                        "GA-S": structs.CountyCongressionalResult(
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
                        ),
                    }
                ),
                "67890": structs.County(
                    S={
                        "GA": structs.CountyCongressionalResult(
                            dem=structs.StateSummaryCandidateNamed(
                                first_name="Jon",
                                last_name="Ossof",
                                pop_vote=1,
                                pop_pct=0.2,
                            )
                        ),
                    }
                ),
            }
        ),
    )


def test_house_result():
    mock_historicals["test_pelosi"] = {"A": 1, "B": 2}
    mock_historicals["test_buttar"] = {"B": 10, "C": 20}

    assert_result(
        exporter("CA").run_export(
            [
                res_h(
                    "CA",
                    12,
                    "12345",
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
                    "12345",
                    "Dem",
                    "Shahid",
                    "Buttar",
                    votecount=456,
                    votepct=0.3,
                    elex_id="test_buttar",
                ),
            ],
        ),
        structs.StateData(
            counties={
                "12345": structs.County(
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
                )
            }
        ),
    )


def test_house_at_large_result():
    assert_result(
        exporter("AK").run_export(
            [
                res_h(
                    "AK",
                    1,
                    "10002",
                    "GOP",
                    "Don",
                    "Young",
                    votecount=12345,
                    votepct=0.234,
                )
            ],
        ),
        structs.StateData(
            counties={
                "10002": structs.County(
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
                )
            }
        ),
    )
