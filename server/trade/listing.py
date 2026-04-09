"""Listing management for Claw Service Hub.

Handles listing creation, query, cancellation, and price updates.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection


class Listing:
    """挂牌实体"""

    def __init__(
        self,
        listing_id: str,
        agent_id: str,
        title: str,
        description: str = "",
        price: float = 0,
        category: str = "service",
        status: str = "active",
        created_at: str = "",
        updated_at: str = "",
        cancelled_at: str = "",
    ):
        self.listing_id = listing_id
        self.agent_id = agent_id
        self.title = title
        self.description = description
        self.price = price
        self.category = category
        self.status = status  # active, sold, cancelled
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at
        self.cancelled_at = cancelled_at

    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cancelled_at": self.cancelled_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Listing":
        return cls(
            listing_id=data.get("listing_id", ""),
            agent_id=data.get("agent_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            price=data.get("price", 0),
            category=data.get("category", "service"),
            status=data.get("status", "active"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            cancelled_at=data.get("cancelled_at", ""),
        )


class ListingManager:
    """挂牌管理器"""

    def __init__(self):
        self._listings: Dict[str, Listing] = {}  # listing_id -> Listing

    def create_listing(self, data: dict) -> Listing:
        """创建挂牌"""
        listing = Listing(
            listing_id=data.get("listing_id", f"listing_{uuid.uuid4().hex[:12]}"),
            agent_id=data.get("agent_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            price=float(data.get("price", 0)),
            category=data.get("category", "service"),
            status="active",
        )
        self._listings[listing.listing_id] = listing
        return listing

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """获取挂牌"""
        return self._listings.get(listing_id)

    def query_listings(self, category: str = None, status: str = "active") -> List[Listing]:
        """查询挂牌"""
        results = list(self._listings.values())

        if status:
            results = [l for l in results if l.status == status]

        if category:
            results = [l for l in results if l.category == category]

        return results

    def cancel_listing(self, listing_id: str, agent_id: str) -> tuple[bool, str]:
        """取消挂牌

        Returns:
            (success, error_message)
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return False, "Listing not found"

        if listing.agent_id != agent_id:
            return False, "Permission denied"

        if listing.status == "sold":
            return False, "Listing already sold"

        listing.status = "cancelled"
        listing.cancelled_at = datetime.now(timezone.utc).isoformat()
        return True, ""

    def update_price(
        self, listing_id: str, agent_id: str, new_price: float
    ) -> tuple[bool, str, float]:
        """更新挂牌价格

        Returns:
            (success, error_message, old_price)
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return False, "Listing not found", 0

        if listing.agent_id != agent_id:
            return False, "Permission denied", 0

        if listing.status != "active":
            return False, "Listing is not active", 0

        old_price = listing.price
        listing.price = new_price
        listing.updated_at = datetime.now(timezone.utc).isoformat()
        return True, "", old_price

    def batch_cancel(self, listing_ids: List[str], agent_id: str) -> List[dict]:
        """批量取消挂牌"""
        results = []

        for listing_id in listing_ids:
            listing = self._listings.get(listing_id)
            if not listing:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing not found"
                })
                continue

            if listing.agent_id != agent_id:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Permission denied"
                })
                continue

            if listing.status == "sold":
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing already sold"
                })
                continue

            listing.status = "cancelled"
            listing.cancelled_at = datetime.now(timezone.utc).isoformat()
            results.append({
                "listing_id": listing_id,
                "status": "cancelled"
            })

        return results


# 全局单例
_listing_manager = None


def get_listing_manager() -> ListingManager:
    """获取挂牌管理器单例"""
    global _listing_manager
    if _listing_manager is None:
        _listing_manager = ListingManager()
    return _listing_manager
