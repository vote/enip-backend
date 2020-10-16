from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from humps import camelize

from typing import Dict, Optional, List, Union


def to_camel(string):
    return camelize(string)


# From: https://medium.com/analytics-vidhya/camel-case-models-with-fast-api-and-pydantic-5a8acb6c0eee
class CamelModel(BaseModel):
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class Party(str, Enum):
    DEM = "dem"
    GOP = "gop"
    OTHER = "oth"

    @classmethod
    def from_ap(cls, str):
        if str.lower() == "dem":
            return cls.DEM

        if str.lower() == "gop":
            return cls.GOP

        return cls.OTHER


class Comment(CamelModel):
    timestamp: datetime
    author: str
    title: str
    body: str


class NationalSummaryPresidentCandidateNamed(CamelModel):
    first_name: str
    last_name: str
    pop_vote: int
    pop_pct: float
    elect_won: int = 0
    pop_vote_history: Dict[str, int] = {}


class NationalSummaryPresidentCandidateUnnamed(CamelModel):
    pop_vote: int = 0
    pop_pct: float = 0
    elect_won: int = 0
    pop_vote_history: Dict[str, int] = {}


class NationalSummaryPresident(CamelModel):
    dem: Optional[NationalSummaryPresidentCandidateNamed] = None
    gop: Optional[NationalSummaryPresidentCandidateNamed] = None
    oth: NationalSummaryPresidentCandidateUnnamed = Field(
        default_factory=NationalSummaryPresidentCandidateUnnamed
    )
    winner: Optional[Party]


class NationalSummaryWinnerCountEntry(CamelModel):
    won: int = 0


class NationalSummaryWinnerCount(CamelModel):
    dem: NationalSummaryWinnerCountEntry = Field(
        default_factory=NationalSummaryWinnerCountEntry
    )
    gop: NationalSummaryWinnerCountEntry = Field(
        default_factory=NationalSummaryWinnerCountEntry
    )
    oth: NationalSummaryWinnerCountEntry = Field(
        default_factory=NationalSummaryWinnerCountEntry
    )


class StateSummaryCandidateNamed(CamelModel):
    first_name: str
    last_name: str
    pop_vote: int
    pop_pct: float
    pop_vote_history: Dict[str, int] = {}


class StateSummaryCandidateUnnamed(CamelModel):
    pop_vote: int = 0
    pop_pct: float = 0
    pop_vote_history: Dict[str, int] = {}


class StateSummaryPresident(CamelModel):
    dem: Optional[StateSummaryCandidateNamed] = None
    gop: Optional[StateSummaryCandidateNamed] = None
    oth: StateSummaryCandidateUnnamed = Field(
        default_factory=StateSummaryCandidateUnnamed
    )
    winner: Optional[Party] = None
    comments: List[Comment] = []


class StateSummaryCongressionalResult(CamelModel):
    dem: Optional[StateSummaryCandidateNamed] = None
    gop: Optional[StateSummaryCandidateNamed] = None
    oth: StateSummaryCandidateUnnamed = Field(
        default_factory=StateSummaryCandidateUnnamed
    )
    multiple_dem: bool = False
    multiple_gop: bool = False
    winner: Optional[Party] = None
    comments: List[Comment] = []


class StateSummary(CamelModel):
    P: StateSummaryPresident = Field(default_factory=StateSummaryPresident)
    S: Optional[StateSummaryCongressionalResult] = None
    H: Dict[str, StateSummaryCongressionalResult] = {}


class PresidentialCDSummary(CamelModel):
    P: StateSummaryPresident = Field(default_factory=StateSummaryPresident)


class SenateSpecialSummary(CamelModel):
    S: Optional[StateSummaryCongressionalResult] = None


class NationalSummary(CamelModel):
    P: NationalSummaryPresident = Field(default_factory=NationalSummaryPresident)
    S: NationalSummaryWinnerCount = Field(default_factory=NationalSummaryWinnerCount)
    H: NationalSummaryWinnerCount = Field(default_factory=NationalSummaryWinnerCount)


class NationalData(CamelModel):
    national_summary: NationalSummary = Field(default_factory=NationalSummary)
    state_summaries: Dict[
        str, Union[StateSummary, PresidentialCDSummary, SenateSpecialSummary]
    ] = {}


class CountyCongressionalResult(CamelModel):
    dem: Optional[StateSummaryCandidateNamed] = None
    gop: Optional[StateSummaryCandidateNamed] = None
    oth: StateSummaryCandidateUnnamed = Field(
        default_factory=StateSummaryCandidateUnnamed
    )
    multiple_dem: bool = False
    multiple_gop: bool = False


class CountyPresidentialResult(CamelModel):
    dem: Optional[StateSummaryCandidateNamed] = None
    gop: Optional[StateSummaryCandidateNamed] = None
    oth: StateSummaryCandidateUnnamed = Field(
        default_factory=StateSummaryCandidateUnnamed
    )


class County(CamelModel):
    P: CountyPresidentialResult = Field(default_factory=CountyPresidentialResult)
    S: Dict[str, CountyCongressionalResult] = {}
    H: Dict[str, CountyCongressionalResult] = {}


class StateData(CamelModel):
    counties: Dict[str, County] = {}
