import json
from pathlib import Path

import pytest

from kletserbot.domain.cardpacks.pack_configuration import CardKind
from kletserbot.infrastructure.cardpacks.json_card_set_configuration_provider import (
    InvalidCardpackConfigurationFileError,
    JsonCardSetConfigurationProvider,
)

PROJECT_ROOT = Path(__file__).parents[4]
PACKAGED_CONFIG_ROOT = (
    PROJECT_ROOT / "src" / "kletserbot" / "infrastructure" / "cardpacks" / "config"
)


def test_packaged_configuration_loads_151_and_base_set() -> None:
    provider = JsonCardSetConfigurationProvider(
        set_catalog_path=PACKAGED_CONFIG_ROOT / "sets.json",
        pull_rates_path=PACKAGED_CONFIG_ROOT / "pull_rates.json",
    )

    configurations = provider.retrieve_configurations()

    assert [configuration.set_id for configuration in configurations] == [
        "sv3pt5",
        "base1",
    ]
    configuration_151 = configurations[0]
    assert configuration_151.energy_set_id == "sve"
    assert configuration_151.pack_image_asset == "card-pack-image-151.webp"
    assert configuration_151.energy_card_ids == tuple(
        f"sve-{card_number}" for card_number in range(1, 9)
    )
    assert len(configuration_151.slots) == 11
    assert configuration_151.slots[7].outcomes[0].card_kind is CardKind.RARITY
    assert configuration_151.slots[8].outcomes[0].card_kind is CardKind.RARITY
    assert [outcome.weight for outcome in configuration_151.slots[8].outcomes] == [
        0.8839,
        0.085,
        0.0311,
    ]
    assert [outcome.weight for outcome in configuration_151.slots[9].outcomes] == [
        0.7834,
        0.1328,
        0.0644,
        0.0194,
    ]

    base_set = configurations[1]
    assert base_set.energy_set_id == "base1"
    assert base_set.pack_image_asset == "card-pack-image-baseset.jpg"
    assert base_set.energy_card_ids == tuple(
        f"base1-{card_number}" for card_number in range(97, 103)
    )
    assert len(base_set.slots) == 11
    assert [outcome.weight for outcome in base_set.slots[9].outcomes] == [0.67, 0.33]


def test_invalid_set_is_excluded_without_hiding_other_valid_sets(
    tmp_path: Path,
) -> None:
    set_catalog_path = tmp_path / "sets.json"
    pull_rates_path = tmp_path / "pull_rates.json"
    set_catalog_path.write_text(
        json.dumps(
            {
                "pokemonSets": [
                    {
                        "id": "invalid",
                        "name": "Invalid",
                        "packImageAsset": "invalid.jpg",
                        "energySetId": "invalid",
                        "energyCardIds": ["invalid-1"],
                    },
                    {
                        "id": "valid",
                        "name": "Valid",
                        "packImageAsset": "valid.jpg",
                        "energySetId": "valid",
                        "energyCardIds": ["valid-1"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    pull_rates_path.write_text(
        json.dumps(
            {
                "invalid": {
                    "slots": [
                        {
                            "count": 1,
                            "isHidden": False,
                            "outcomes": [
                                {
                                    "cardKind": "rarity",
                                    "eligibleRarities": ["Common"],
                                    "weight": 0.5,
                                    "finish": "normal",
                                    "isHit": False,
                                }
                            ],
                        }
                    ]
                },
                "valid": {
                    "slots": [
                        {
                            "count": 1,
                            "isHidden": False,
                            "outcomes": [
                                {
                                    "cardKind": "rarity",
                                    "eligibleRarities": ["Common"],
                                    "weight": 1.0,
                                    "finish": "normal",
                                    "isHit": False,
                                }
                            ],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    configurations = JsonCardSetConfigurationProvider(
        set_catalog_path,
        pull_rates_path,
    ).retrieve_configurations()

    assert [configuration.set_id for configuration in configurations] == ["valid"]


def test_set_without_pull_rates_is_excluded(tmp_path: Path) -> None:
    set_catalog_path = tmp_path / "sets.json"
    pull_rates_path = tmp_path / "pull_rates.json"
    set_catalog_path.write_text(
        json.dumps(
            {
                "pokemonSets": [
                    {
                        "id": "sv3pt5",
                        "name": "151",
                        "packImageAsset": "151.jpg",
                        "energySetId": "sve",
                        "energyCardIds": ["sve-1"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pull_rates_path.write_text("{}", encoding="utf-8")

    configurations = JsonCardSetConfigurationProvider(
        set_catalog_path,
        pull_rates_path,
    ).retrieve_configurations()

    assert configurations == ()


def test_malformed_json_raises_stable_configuration_error(tmp_path: Path) -> None:
    set_catalog_path = tmp_path / "sets.json"
    pull_rates_path = tmp_path / "pull_rates.json"
    set_catalog_path.write_text("{", encoding="utf-8")
    pull_rates_path.write_text("{}", encoding="utf-8")

    with pytest.raises(
        InvalidCardpackConfigurationFileError,
        match="cardpack configuration is not valid JSON",
    ):
        JsonCardSetConfigurationProvider(
            set_catalog_path,
            pull_rates_path,
        ).retrieve_configurations()
