from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class SaleItem:
    nft_address: str
    nft_name: str
    collection_address: str
    collection_name: str
    nft_address_b64url: str = ""
    image_url: str = ""


@dataclass
class SaleEvent:
    trace_id: str
    buyer: str
    seller: str
    price_ton: Decimal
    items: List[SaleItem]
