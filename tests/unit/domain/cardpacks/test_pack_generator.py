from collections.abc import Sequence

import pytest

from kletserbot.domain.cardpacks.opened_pack import OpenedPack
from kletserbot.domain.cardpacks.pack_configuration import (
    CardFinish,
    CardKind,
    CardSetConfiguration,
    PackSlotConfiguration,
    PackSlotOutcome,
)
from kletserbot.domain.cardpacks.pack_generator import (
    InsufficientCardPoolError,
    PackGenerator,
)
from kletserbot.domain.cardpacks.pokemon_card import PokemonCard


def card(
    card_id: str,
    rarity: str,
    *,
    supertype: str = "Pokémon",
    subtypes: tuple[str, ...] = ("Basic",),
) -> PokemonCard:
    return PokemonCard(
        card_id=card_id,
        name=card_id,
        number=card_id.rsplit("-", maxsplit=1)[-1],
        rarity=rarity,
        supertype=supertype,
        subtypes=subtypes,
        small_image_url=f"https://images.example.test/{card_id}.png",
        large_image_url=f"https://images.example.test/{card_id}_large.png",
    )


def fixed_slot(
    rarity: str,
    *,
    finish: CardFinish = CardFinish.NORMAL,
    is_hidden: bool = False,
    is_hit: bool = False,
) -> PackSlotConfiguration:
    return PackSlotConfiguration(
        outcomes=(
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=(rarity,),
                weight=1.0,
                finish=finish,
                is_hit=is_hit,
            ),
        ),
        is_hidden=is_hidden,
    )


def energy_slot() -> PackSlotConfiguration:
    return PackSlotConfiguration(
        outcomes=(
            PackSlotOutcome(
                card_kind=CardKind.BASIC_ENERGY,
                eligible_rarities=(),
                weight=1.0,
                finish=CardFinish.NORMAL,
                is_hit=False,
            ),
        ),
        is_hidden=False,
    )


def reverse_slot() -> PackSlotConfiguration:
    return PackSlotConfiguration(
        outcomes=(
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Common", "Uncommon"),
                weight=1.0,
                finish=CardFinish.REVERSE_HOLO,
                is_hit=False,
            ),
        ),
        is_hidden=True,
    )


def weighted_slot(
    outcomes: tuple[tuple[str, float, bool], ...],
) -> PackSlotConfiguration:
    return PackSlotConfiguration(
        outcomes=tuple(
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=(rarity,),
                weight=weight,
                finish=CardFinish.HOLO,
                is_hit=is_hit,
            )
            for rarity, weight, is_hit in outcomes
        ),
        is_hidden=True,
    )


def configuration_151() -> CardSetConfiguration:
    return CardSetConfiguration(
        set_id="sv3pt5",
        name="Scarlet & Violet—151",
        pack_image_asset="card-pack-image-151.webp",
        slots=(
            *(fixed_slot("Common") for _ in range(4)),
            *(fixed_slot("Uncommon") for _ in range(3)),
            reverse_slot(),
            weighted_slot(
                (
                    ("Common", 0.8839, False),
                    ("Illustration Rare", 0.0850, True),
                    ("Special Illustration Rare", 0.0311, True),
                )
            ),
            weighted_slot(
                (
                    ("Rare", 0.7834, False),
                    ("Double Rare", 0.1328, True),
                    ("Ultra Rare", 0.0644, True),
                    ("Hyper Rare", 0.0194, True),
                )
            ),
            energy_slot(),
        ),
        energy_card_ids=("energy-1",),
    )


def card_pool() -> tuple[PokemonCard, ...]:
    return (
        *(card(f"common-{index}", "Common") for index in range(1, 6)),
        *(card(f"uncommon-{index}", "Uncommon") for index in range(1, 5)),
        card("ir-1", "Illustration Rare"),
        card("sir-1", "Special Illustration Rare"),
        card("rare-1", "Rare"),
        card("double-rare-1", "Double Rare"),
        card("ultra-rare-1", "Ultra Rare"),
        card("hyper-rare-1", "Hyper Rare"),
        card(
            "energy-1",
            "Common",
            supertype="Energy",
            subtypes=("Basic",),
        ),
    )


def select_first(cards: Sequence[PokemonCard]) -> PokemonCard:
    return cards[0]


def test_generator_builds_eleven_card_151_pack_with_guaranteed_energy() -> None:
    random_values = iter((0.0, 0.0))

    opened_pack = PackGenerator().generate_pack(
        configuration_151(),
        card_pool(),
        lambda: next(random_values),
        select_first,
    )

    assert isinstance(opened_pack, OpenedPack)
    assert len(opened_pack.cards) == 11
    assert [opened.card.rarity for opened in opened_pack.cards[:4]] == [
        "Common",
        "Common",
        "Common",
        "Common",
    ]
    assert opened_pack.cards[10].card.is_basic_energy is True
    assert opened_pack.cards[10].finish is CardFinish.NORMAL


def test_generator_rolls_slot_nine_and_ten_independently() -> None:
    random_values = iter((0.90, 0.90))

    opened_pack = PackGenerator().generate_pack(
        configuration_151(),
        card_pool(),
        lambda: next(random_values),
        select_first,
    )

    assert opened_pack.cards[8].card.rarity == "Illustration Rare"
    assert opened_pack.cards[8].is_hit is True
    assert opened_pack.cards[9].card.rarity == "Double Rare"
    assert opened_pack.cards[9].is_hit is True


def test_generator_avoids_duplicate_normal_common_and_uncommon_cards() -> None:
    opened_pack = PackGenerator().generate_pack(
        configuration_151(),
        card_pool(),
        lambda: 0.0,
        select_first,
    )

    assert len({opened.card.card_id for opened in opened_pack.cards[:4]}) == 4
    assert len({opened.card.card_id for opened in opened_pack.cards[4:7]}) == 3


def test_reverse_finish_can_repeat_a_visible_card() -> None:
    opened_pack = PackGenerator().generate_pack(
        configuration_151(),
        card_pool(),
        lambda: 0.0,
        select_first,
    )

    assert opened_pack.cards[7].card.card_id == opened_pack.cards[0].card.card_id
    assert opened_pack.cards[7].finish is CardFinish.REVERSE_HOLO


def test_generator_rejects_a_pool_with_too_few_common_cards() -> None:
    cards = tuple(
        pokemon_card
        for pokemon_card in card_pool()
        if pokemon_card.card_id not in {"common-4", "common-5"}
    )

    with pytest.raises(
        InsufficientCardPoolError,
        match="slot 4 has no eligible cards",
    ):
        PackGenerator().generate_pack(
            configuration_151(),
            cards,
            lambda: 0.0,
            select_first,
        )


def test_guaranteed_energy_excludes_premium_energy_cards() -> None:
    cards = (
        *card_pool()[:-1],
        card(
            "gold-energy-1",
            "Hyper Rare",
            supertype="Energy",
            subtypes=("Basic",),
        ),
        card_pool()[-1],
    )

    opened_pack = PackGenerator().generate_pack(
        configuration_151(),
        cards,
        lambda: 0.0,
        select_first,
    )

    assert opened_pack.cards[10].card.card_id == "energy-1"
    assert opened_pack.cards[10].card.rarity == "Common"
