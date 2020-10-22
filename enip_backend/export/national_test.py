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
    mock_calls = {"P": {}, "S": {}}
    mock_comments = {"P": {}, "S": {}, "H": {}}
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

# NE-02 winner call, published
# NE-02 winner call, unpublished

# state result

# state winner call, published
# state winner call, unpublished

# senate result

# GA-S senate result

# sente winner call, published
# senate winner call, unpublished

# house result
# house at large result

# house winner call

# historicals
# oth candidate + historicals
# multiple dems + historicals
# multiple gop + historicals

# presidential winner

# presidential commentary
# senate commentary
# GA-S commentary
# house commentary
# house at large commentary
