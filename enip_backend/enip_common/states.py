STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}

DISTRICTS = {"ME-1", "ME-2", "NE-1", "NE-2", "NE-3"}

DISTRICTS_BY_STATE = {"ME": {"ME-1", "ME-2"}, "NE": {"NE-1", "NE-2", "NE-3"}}

SENATE_SPECIALS = {"GA-S"}

SENATE_SPECIALS_BY_STATE = {"GA": {"GA-S"}}

AT_LARGE_HOUSE_STATES = {"AK", "DE", "MT", "ND", "SD", "VT", "WY"}

ALL_REPORTING_UNITS = STATES | DISTRICTS | SENATE_SPECIALS
