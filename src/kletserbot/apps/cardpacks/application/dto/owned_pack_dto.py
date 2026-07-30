from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OwnedPackDto:
    set_id: str
    set_name: str
    quantity: int
    pack_image_asset: str
