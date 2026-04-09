"""Bid management for Claw Service Hub.

Handles bid creation and acceptance.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Bid:
    """出价实体"""

    def __init__(
        self,
        bid_id: str,
        listing_id: str,
        agent_id: str,
        price: float,
        status: str = "pending",
        created_at: str = "",
    ):
        self.bid_id = bid_id
        self.listing_id = listing_id
        self.agent_id = agent_id
        self.price = price
        self.status = status  # pending, accepted, rejected
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "bid_id": self.bid_id,
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "price": self.price,
            "status": self.status,
            "created_at": self.created_at,
        }


class BidManager:
    """出价管理器"""

    def __init__(self):
        self._bids: Dict[str, Bid] = {}  # bid_id -> Bid

    def create_bid(self, data: dict) -> Bid:
        """创建出价"""
        bid = Bid(
            bid_id=data.get("bid_id", f"bid_{uuid.uuid4().hex[:12]}"),
            listing_id=data.get("listing_id", ""),
            agent_id=data.get("agent_id", ""),
            price=float(data.get("price", 0)),
            status="pending",
        )
        self._bids[bid.bid_id] = bid
        return bid

    def get_bid(self, bid_id: str) -> Optional[Bid]:
        """获取出价"""
        return self._bids.get(bid_id)

    def accept_bid(self, bid_id: str) -> tuple[bool, str]:
        """接受出价

        Returns:
            (success, error_message)
        """
        bid = self._bids.get(bid_id)
        if not bid:
            return False, "Bid not found"

        if bid.status != "pending":
            return False, f"Bid is not pending: {bid.status}"

        bid.status = "accepted"
        return True, ""

    def reject_bid(self, bid_id: str) -> tuple[bool, str]:
        """拒绝出价"""
        bid = self._bids.get(bid_id)
        if not bid:
            return False, "Bid not found"

        bid.status = "rejected"
        return True, ""

    def get_bids_by_listing(self, listing_id: str) -> List[Bid]:
        """获取指定挂牌的所有出价"""
        return [b for b in self._bids.values() if b.listing_id == listing_id]


# 全局单例
_bid_manager = None


def get_bid_manager() -> BidManager:
    """获取出价管理器单例"""
    global _bid_manager
    if _bid_manager is None:
        _bid_manager = BidManager()
    return _bid_manager
