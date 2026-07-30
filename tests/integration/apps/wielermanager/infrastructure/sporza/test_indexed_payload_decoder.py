import pytest

from kletserbot.apps.wielermanager.infrastructure.sporza.indexed_payload_decoder import (
    IndexedPayloadDecoder,
)
from kletserbot.shared.application.exceptions import InvalidExternalResponseError


def indexed_payload() -> list[object]:
    return [
        {"_1": 2},
        "route",
        {"_3": 4},
        "data",
        {"_5": 6},
        "miniCompetition",
        {"_7": 8},
        "members",
        [9],
        {"_10": 11, "_12": 13, "_14": 15},
        "teamName",
        "Fast Team",
        "points",
        100,
        "rank",
        1,
    ]


def test_decoder_resolves_indexed_dictionary_keys() -> None:
    decoded = IndexedPayloadDecoder().decode(indexed_payload())

    members = decoded["route"]["data"]["miniCompetition"]["members"]
    assert members == [{"teamName": "Fast Team", "points": 100, "rank": 1}]


def test_decoder_rejects_out_of_range_reference() -> None:
    with pytest.raises(InvalidExternalResponseError):
        IndexedPayloadDecoder().decode([{"_1": 99}, "route"])
