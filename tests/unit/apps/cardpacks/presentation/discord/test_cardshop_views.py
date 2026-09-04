import discord

from kletserbot.apps.cardpacks.application.dto.available_card_set_dto import (
    AvailableCardSetDto,
)
from kletserbot.apps.cardpacks.application.dto.cardshop_dto import (
    CardshopDto,
    CardshopProductDto,
)
from kletserbot.apps.cardpacks.presentation.discord.cardshop_views import (
    CardshopLaunchView,
    CardshopPrivateView,
)


def cardshop() -> CardshopDto:
    return CardshopDto(
        point_balance=1_000,
        products=(
            CardshopProductDto(
                set_id="sv3pt5",
                set_name="Scarlet & Violet 151",
                description="De moderne, special 151 set",
                price=400,
                pack_image_asset="card-pack-image-151.webp",
                owned_quantity=2,
            ),
            CardshopProductDto(
                set_id="base1",
                set_name="Base Set",
                description="De nostalgische base set",
                price=600,
                pack_image_asset="card-pack-image-baseset.jpg",
                owned_quantity=1,
            ),
        ),
    )


def test_public_cardshop_launcher_is_persistent_and_never_shows_balance() -> None:
    view = CardshopLaunchView(  # type: ignore[arg-type]
        object(),
        available_sets=(
            AvailableCardSetDto(
                set_id="base1",
                set_name="Base Set",
                shop_price=600,
                shop_description="De nostalgische base set",
                pack_image_asset="card-pack-image-baseset.jpg",
            ),
        ),
    )

    component_ids = {
        component.custom_id
        for component in view.walk_children()
        if isinstance(component, discord.ui.Button)
    }
    rendered_text = "\n".join(
        component.content
        for component in view.walk_children()
        if isinstance(component, discord.ui.TextDisplay)
    )

    assert view.is_persistent() is True
    assert component_ids == {"cardshop:open", "cardshop:daily"}
    assert "**Jouw saldo:**" not in rendered_text
    assert "Base Set" in rendered_text
    assert "600 punten" in rendered_text
    assert [file.filename for file in view.pack_image_files()] == [
        "card-pack-image-baseset-shop-thumbnail.png"
    ]
    assert any(isinstance(component, discord.ui.Container) for component in view.children)
    assert any(isinstance(component, discord.ui.Thumbnail) for component in view.walk_children())


def test_private_cardshop_shows_owner_balance_and_purchase_controls() -> None:
    view = CardshopPrivateView(
        owner_user_id=123,
        cardpack_service=object(),  # type: ignore[arg-type]
        cardshop=cardshop(),
    )

    rendered_text = "\n".join(
        component.content
        for component in view.walk_children()
        if isinstance(component, discord.ui.TextDisplay)
    )
    component_ids = {
        component.custom_id
        for component in view.walk_children()
        if isinstance(component, discord.ui.Button)
    }

    assert view.owner_user_id == 123
    assert "# Packs kopen" in rendered_text
    assert "1,000 punten" in rendered_text
    assert "• **Scarlet & Violet 151:** 2 pack(s)" in rendered_text
    assert "cardshop:purchase" in component_ids
