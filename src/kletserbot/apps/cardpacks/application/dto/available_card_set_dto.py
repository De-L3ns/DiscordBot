from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AvailableCardSetDto:
    set_id: str
    set_name: str
    shop_price: int
    shop_description: str
    pack_image_asset: str
