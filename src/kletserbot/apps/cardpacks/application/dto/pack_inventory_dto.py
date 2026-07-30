from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackInventoryDto:
    set_id: str
    quantity: int
