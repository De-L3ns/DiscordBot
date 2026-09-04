from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CardshopProductDto:
    set_id: str
    set_name: str
    description: str
    price: int
    pack_image_asset: str
    owned_quantity: int


@dataclass(frozen=True, slots=True)
class CardshopDto:
    point_balance: int
    products: tuple[CardshopProductDto, ...]


@dataclass(frozen=True, slots=True)
class PackPurchaseDto:
    set_id: str
    set_name: str
    quantity: int
    total_price: int
    remaining_balance: int


@dataclass(frozen=True, slots=True)
class DailyPointClaimDto:
    was_claimed: bool
    awarded_points: int
    point_balance: int
    next_claim_at_utc: datetime


@dataclass(frozen=True, slots=True)
class PointGrantDto:
    granted_points: int
    point_balance: int


@dataclass(frozen=True, slots=True)
class PointMutationResultDto:
    was_applied: bool
    point_balance: int
