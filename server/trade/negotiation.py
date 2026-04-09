"""Negotiation management for Claw Service Hub.

Handles offer, counter-offer, and acceptance.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Offer:
    """议价实体"""

    def __init__(
        self,
        offer_id: str,
        listing_id: str,
        agent_id: str,
        price: float,
        offer_type: str = "offer",  # offer, counter
        status: str = "pending",
        parent_offer_id: str = None,
        created_at: str = "",
    ):
        self.offer_id = offer_id
        self.listing_id = listing_id
        self.agent_id = agent_id
        self.price = price
        self.type = offer_type
        self.status = status  # pending, accepted, rejected
        self.parent_offer_id = parent_offer_id
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "offer_id": self.offer_id,
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "price": self.price,
            "type": self.type,
            "status": self.status,
            "parent_offer_id": self.parent_offer_id,
            "created_at": self.created_at,
        }


class NegotiationManager:
    """议价管理器"""

    def __init__(self):
        self._offers: Dict[str, Offer] = {}  # offer_id -> Offer

    def make_offer(self, data: dict) -> Offer:
        """发起议价"""
        offer = Offer(
            offer_id=data.get("offer_id", f"offer_{uuid.uuid4().hex[:12]}"),
            listing_id=data.get("listing_id", ""),
            agent_id=data.get("agent_id", ""),
            price=float(data.get("price", 0)),
            type="offer",
            status="pending",
        )
        self._offers[offer.offer_id] = offer
        return offer

    def make_counter(self, offer_id: str, data: dict) -> tuple[Optional[Offer], str]:
        """还价

        Returns:
            (counter_offer, error_message)
        """
        original_offer = self._offers.get(offer_id)
        if not original_offer:
            return None, "Offer not found"

        counter_id = offer_id  # Use same ID for easier tracking
        counter = Offer(
            offer_id=counter_id,
            listing_id=data.get("listing_id", original_offer.listing_id),
            agent_id=data.get("agent_id", ""),
            price=float(data.get("price", 0)),
            type="counter",
            status="pending",
            parent_offer_id=offer_id,
        )

        # Replace if exists
        self._offers[counter_id] = counter
        return counter, ""

    def accept_offer(self, offer_id: str) -> tuple[bool, str]:
        """接受议价

        Returns:
            (success, error_message)
        """
        offer = self._offers.get(offer_id)
        if not offer:
            return False, "Offer not found"

        if offer.status != "pending":
            return False, f"Offer is not pending: {offer.status}"

        offer.status = "accepted"
        return True, ""

    def reject_offer(self, offer_id: str) -> tuple[bool, str]:
        """拒绝议价"""
        offer = self._offers.get(offer_id)
        if not offer:
            return False, "Offer not found"

        offer.status = "rejected"
        return True, ""

    def get_offer(self, offer_id: str) -> Optional[Offer]:
        """获取议价"""
        return self._offers.get(offer_id)

    def get_offers_by_listing(self, listing_id: str) -> List[Offer]:
        """获取指定挂牌的所有议价"""
        return [o for o in self._offers.values() if o.listing_id == listing_id]

    def get_offers_by_agent(self, agent_id: str) -> List[Offer]:
        """获取指定代理的所有议价"""
        return [o for o in self._offers.values() if o.agent_id == agent_id]


# 全局单例
_negotiation_manager = None


def get_negotiation_manager() -> NegotiationManager:
    """获取议价管理器单例"""
    global _negotiation_manager
    if _negotiation_manager is None:
        _negotiation_manager = NegotiationManager()
    return _negotiation_manager
