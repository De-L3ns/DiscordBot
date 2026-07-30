import pytest

from kletserbot.domain.cardpacks.pack_configuration import (
    CardFinish,
    CardKind,
    CardSetConfiguration,
    InvalidPackConfigurationError,
    PackSlotConfiguration,
    PackSlotOutcome,
)


def test_slot_rejects_outcome_weights_that_do_not_total_one() -> None:
    with pytest.raises(
        InvalidPackConfigurationError,
        match="slot outcome weights must total 1.0",
    ):
        PackSlotConfiguration(
            outcomes=(
                PackSlotOutcome(
                    card_kind=CardKind.RARITY,
                    eligible_rarities=("Rare",),
                    weight=0.5,
                    finish=CardFinish.HOLO,
                    is_hit=False,
                ),
            ),
            is_hidden=True,
        )


def test_slot_selects_weighted_outcomes_at_literal_boundaries() -> None:
    slot = PackSlotConfiguration(
        outcomes=(
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Common", "Uncommon"),
                weight=0.67,
                finish=CardFinish.REVERSE_HOLO,
                is_hit=False,
            ),
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Illustration Rare",),
                weight=0.33,
                finish=CardFinish.HOLO,
                is_hit=True,
            ),
        ),
        is_hidden=True,
    )

    assert slot.select_outcome(0.6699).is_hit is False
    assert slot.select_outcome(0.67).is_hit is True


def test_card_set_requires_a_pack_image_asset() -> None:
    slot = PackSlotConfiguration(
        outcomes=(
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Common",),
                weight=1.0,
                finish=CardFinish.NORMAL,
                is_hit=False,
            ),
        ),
        is_hidden=False,
    )

    with pytest.raises(
        InvalidPackConfigurationError,
        match="pack image asset must not be empty",
    ):
        CardSetConfiguration(
            set_id="base1",
            name="Base Set",
            pack_image_asset="",
            slots=(slot,),
        )
