"""Trade WebSocket handlers for Claw Service Hub.

Handles WebSocket message processing for:
- Listing management (create, query, cancel, update price)
- Bid management (create, accept)
- Negotiation management (offer, counter, accept)
- Transaction management (create, query)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection
    from server.trade.listing import ListingManager
    from server.trade.bid import BidManager
    from server.trade.negotiation import NegotiationManager
    from server.trade.transaction import TransactionManager


class TradeHandler:
    """Trade message handler"""

    def __init__(
        self,
        listing_mgr: "ListingManager",
        bid_mgr: "BidManager",
        negotiation_mgr: "NegotiationManager",
        transaction_mgr: "TransactionManager",
        client_websockets: Dict[str, Any],
    ):
        self.listing_mgr = listing_mgr
        self.bid_mgr = bid_mgr
        self.negotiation_mgr = negotiation_mgr
        self.transaction_mgr = transaction_mgr
        self.client_websockets = client_websockets

    async def handle_listing_create(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理创建挂牌"""
        # 验证必填字段
        required_fields = ["listing_id", "title", "price"]
        missing = [f for f in required_fields if not message.get(f)]
        if missing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": f"Missing required fields: {missing}",
                "details": "listing_id, title, and price are required"
            }))
            return

        price = message.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number"
            }))
            return

        listing_id = message.get("listing_id")
        listing = {
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "title": message.get("title"),
            "description": message.get("description"),
            "price": price,
            "category": message.get("category", "service"),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.listing_mgr._listings[listing_id] = listing
        await websocket.send(json.dumps({
            "type": "listing_created",
            "listing_id": listing_id,
            "status": "active",
        }))
        print(f"[Server] Listing created: {listing_id} by {listing['agent_id']}")

    async def handle_listing_query(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理查询挂牌"""
        request_id = message.get("request_id")
        category = message.get("category")
        listings = [l for l in self.listing_mgr._listings.values() if l.get("status") == "active"]
        if category:
            listings = [l for l in listings if l.get("category") == category]
        await websocket.send(json.dumps({
            "type": "listing_query_response",
            "request_id": request_id,
            "listings": listings,
            "total": len(listings),
        }))
        print(f"[Server] Listing query: {len(listings)} results")

    async def handle_bid_create(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理创建出价"""
        # 验证必填字段
        required_fields = ["bid_id", "listing_id", "price"]
        missing = [f for f in required_fields if not message.get(f)]
        if missing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": f"Missing required fields: {missing}",
                "details": "bid_id, listing_id, and price are required"
            }))
            return

        bid_id = message.get("bid_id")
        listing_id = message.get("listing_id")
        listing = self.listing_mgr._listings.get(listing_id)

        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed"
            }))
            return

        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot bid on inactive listing"
            }))
            return

        price = message.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number"
            }))
            return

        bid = {
            "bid_id": bid_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.bid_mgr._bids[bid_id] = bid
        # 通知挂牌所有者
        owner_ws = self.client_websockets.get(listing.get("agent_id"))
        if owner_ws:
            await owner_ws.send(json.dumps({"type": "bid_received", "bid": bid}))
        await websocket.send(json.dumps({"type": "bid_created", "bid_id": bid_id}))
        print(f"[Server] Bid created: {bid_id} for listing {listing_id}")

    async def handle_bid_accept(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理接受出价"""
        bid_id = message.get("bid_id")
        if not bid_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_BID_ID",
                "message": "Missing bid_id",
                "details": "bid_id is required"
            }))
            return

        bid = self.bid_mgr._bids.get(bid_id)
        if not bid:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "BID_NOT_FOUND",
                "message": f"Bid not found: {bid_id}",
                "details": "The bid does not exist or has expired"
            }))
            return

        if bid.get("status") != "pending":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "BID_NOT_PENDING",
                "message": f"Bid is not pending: {bid.get('status')}",
                "details": "This bid has already been processed"
            }))
            return

        bid["status"] = "accepted"
        listing_id = bid["listing_id"]
        listing = self.listing_mgr._listings.get(listing_id)
        if listing:
            listing["status"] = "sold"
            # 创建交易记录
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            transaction = {
                "transaction_id": transaction_id,
                "listing_id": listing_id,
                "buyer_id": bid.get("agent_id"),
                "seller_id": listing.get("agent_id"),
                "price": bid.get("price"),
                "type": "bid",
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.transaction_mgr._transactions[transaction_id] = transaction
            print(f"[Server] Transaction created from bid: {transaction_id}")

        # 通知出价者
        bidder_ws = self.client_websockets.get(bid.get("agent_id"))
        if bidder_ws:
            await bidder_ws.send(json.dumps({"type": "bid_accepted", "bid_id": bid_id}))
        await websocket.send(json.dumps({"type": "bid_accept_response", "bid_id": bid_id, "status": "accepted"}))
        print(f"[Server] Bid accepted: {bid_id}")

    async def handle_negotiation_offer(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理议价出价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")
        listing_id = message.get("listing_id")

        # 验证 listing_id
        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return

        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return

        # 验证价格
        price = message.get("price")
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return

        # 检查 listing 状态
        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot make offer on inactive listing",
                "request_id": request_id
            }))
            return

        offer = {
            "offer_id": offer_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "type": "offer",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.negotiation_mgr._offers[offer_id] = offer
        # 通知挂牌所有者
        owner_ws = self.client_websockets.get(listing.get("agent_id"))
        if owner_ws:
            await owner_ws.send(json.dumps({"type": "negotiation_received", "offer": offer}))
        await websocket.send(json.dumps({"type": "negotiation_sent", "offer_id": offer_id, "request_id": request_id}))
        print(f"[Server] Negotiation offer: {offer_id}")

    async def handle_negotiation_counter(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理议价还价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")
        original_offer = self.negotiation_mgr._offers.get(offer_id)
        if not original_offer:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "OFFER_NOT_FOUND",
                "message": f"Offer not found: {offer_id}",
                "details": "The original offer ID does not exist or has expired",
                "request_id": request_id
            }))
            return

        # 验证价格
        price = message.get("price")
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return

        # 验证 listing_id
        listing_id = message.get("listing_id")
        if not listing_id or listing_id not in self.listing_mgr._listings:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing ID does not exist",
                "request_id": request_id
            }))
            return

        # 使用客户端提供的 offer_id 作为 counter 的 ID
        counter_id = offer_id

        counter = {
            "offer_id": counter_id,
            "listing_id": listing_id,
            "agent_id": message.get("agent_id"),
            "price": price,
            "type": "counter",
            "parent_offer_id": offer_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 如果已存在相同 ID 的 offer，先删除旧的
        if counter_id in self.negotiation_mgr._offers:
            del self.negotiation_mgr._offers[counter_id]

        self.negotiation_mgr._offers[counter_id] = counter

        # 通知原始出价者
        original_agent = original_offer.get("agent_id")
        original_ws = self.client_websockets.get(original_agent)
        if original_ws:
            await original_ws.send(json.dumps({
                "type": "negotiation_counter",
                "offer": counter,
                "parent_offer_id": offer_id
            }))

        await websocket.send(json.dumps({
            "type": "negotiation_counter_sent",
            "offer_id": counter_id,
            "parent_offer_id": offer_id,
            "request_id": request_id
        }))
        print(f"[Server] Negotiation counter: {counter_id} (parent: {offer_id})")

    async def handle_negotiation_accept(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理接受议价"""
        request_id = message.get("request_id")
        offer_id = message.get("offer_id")
        if not offer_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_OFFER_ID",
                "message": "Missing offer_id",
                "details": "offer_id is required",
                "request_id": request_id
            }))
            return

        offer = self.negotiation_mgr._offers.get(offer_id)
        if not offer:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "OFFER_NOT_FOUND",
                "message": f"Offer not found: {offer_id}",
                "details": "The offer does not exist or has expired",
                "request_id": request_id
            }))
            return

        if offer.get("status") != "pending":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "OFFER_NOT_PENDING",
                "message": f"Offer is not pending: {offer.get('status')}",
                "details": "This offer has already been processed",
                "request_id": request_id
            }))
            return

        offer["status"] = "accepted"
        listing_id = offer["listing_id"]
        listing = self.listing_mgr._listings.get(listing_id)
        if listing:
            listing["status"] = "sold"
            # 创建交易记录
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            transaction = {
                "transaction_id": transaction_id,
                "listing_id": listing_id,
                "buyer_id": offer.get("agent_id"),
                "seller_id": listing.get("agent_id"),
                "price": offer.get("price"),
                "type": "negotiation",
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.transaction_mgr._transactions[transaction_id] = transaction
            print(f"[Server] Transaction created from negotiation: {transaction_id}")

        # 通知出价者
        offer_agent = offer.get("agent_id")
        offer_ws = self.client_websockets.get(offer_agent)
        if offer_ws:
            await offer_ws.send(json.dumps({"type": "negotiation_accepted", "offer_id": offer_id}))
        await websocket.send(json.dumps({
            "type": "negotiation_accept_response",
            "offer_id": offer_id,
            "status": "accepted",
            "request_id": request_id
        }))
        print(f"[Server] Negotiation accepted: {offer_id}")

    async def handle_listing_cancel(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理取消挂牌"""
        request_id = message.get("request_id")
        listing_id = message.get("listing_id")

        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return

        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return

        # 验证权限
        if listing.get("agent_id") != client_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "details": "Only the listing owner can cancel this listing",
                "request_id": request_id
            }))
            return

        # 检查挂牌状态
        if listing.get("status") == "sold":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_ALREADY_SOLD",
                "message": "Listing already sold",
                "details": "Cannot cancel a listing that has been sold",
                "request_id": request_id
            }))
            return

        # 取消挂牌
        listing["status"] = "cancelled"
        listing["cancelled_at"] = datetime.now(timezone.utc).isoformat()

        await websocket.send(json.dumps({
            "type": "listing_cancelled",
            "listing_id": listing_id,
            "status": "cancelled",
            "request_id": request_id
        }))
        print(f"[Server] Listing cancelled: {listing_id}")

    async def handle_listing_update_price(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理修改挂牌价格"""
        request_id = message.get("request_id")
        listing_id = message.get("listing_id")
        new_price = message.get("price")

        if not listing_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_ID",
                "message": "Missing listing_id",
                "details": "listing_id is required",
                "request_id": request_id
            }))
            return

        if new_price is None or not isinstance(new_price, (int, float)) or new_price <= 0:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "INVALID_PRICE",
                "message": "Invalid price value",
                "details": "Price must be a positive number",
                "request_id": request_id
            }))
            return

        listing = self.listing_mgr._listings.get(listing_id)
        if not listing:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_FOUND",
                "message": f"Listing not found: {listing_id}",
                "details": "The listing does not exist or has been removed",
                "request_id": request_id
            }))
            return

        # 验证权限
        if listing.get("agent_id") != client_id:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "details": "Only the listing owner can update the price",
                "request_id": request_id
            }))
            return

        # 检查挂牌状态
        if listing.get("status") != "active":
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "LISTING_NOT_ACTIVE",
                "message": f"Listing is not active: {listing.get('status')}",
                "details": "Cannot update price of inactive listing",
                "request_id": request_id
            }))
            return

        old_price = listing.get("price")
        listing["price"] = new_price
        listing["updated_at"] = datetime.now(timezone.utc).isoformat()

        await websocket.send(json.dumps({
            "type": "listing_price_updated",
            "listing_id": listing_id,
            "old_price": old_price,
            "new_price": new_price,
            "status": "active",
            "request_id": request_id
        }))
        print(f"[Server] Listing price updated: {listing_id} ({old_price} -> {new_price})")

    async def handle_listing_cancel_batch(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理批量下架"""
        request_id = message.get("request_id")
        listing_ids = message.get("listing_ids", [])

        if not listing_ids:
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_LISTING_IDS",
                "message": "Missing listing_ids",
                "details": "listing_ids is required and must not be empty",
                "request_id": request_id
            }))
            return

        results = []
        for listing_id in listing_ids:
            listing = self.listing_mgr._listings.get(listing_id)
            if not listing:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing not found"
                })
                continue

            # 验证权限
            if listing.get("agent_id") != client_id:
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Permission denied"
                })
                continue

            # 检查状态
            if listing.get("status") == "sold":
                results.append({
                    "listing_id": listing_id,
                    "status": "error",
                    "reason": "Listing already sold"
                })
                continue

            # 取消挂牌
            listing["status"] = "cancelled"
            listing["cancelled_at"] = datetime.now(timezone.utc).isoformat()
            results.append({
                "listing_id": listing_id,
                "status": "cancelled"
            })

        success_count = sum(1 for r in results if r["status"] == "cancelled")
        await websocket.send(json.dumps({
            "type": "listing_cancelled_batch",
            "results": results,
            "total": len(listing_ids),
            "success_count": success_count,
            "request_id": request_id
        }))
        print(f"[Server] Batch cancel: {success_count}/{len(listing_ids)} listings cancelled")

    async def handle_transaction_create(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理创建交易记录"""
        transaction_id = message.get("transaction_id")
        listing_id = message.get("listing_id")
        buyer_id = message.get("buyer_id")
        seller_id = message.get("seller_id")
        price = message.get("price")

        if not all([transaction_id, listing_id, buyer_id, seller_id, price]):
            await websocket.send(json.dumps({
                "type": "error",
                "error_code": "MISSING_FIELDS",
                "message": "Missing required fields",
                "details": "transaction_id, listing_id, buyer_id, seller_id, and price are required"
            }))
            return

        transaction = {
            "transaction_id": transaction_id,
            "listing_id": listing_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "price": price,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.transaction_mgr._transactions[transaction_id] = transaction

        await websocket.send(json.dumps({
            "type": "transaction_created",
            "transaction_id": transaction_id,
            "status": "completed"
        }))
        print(f"[Server] Transaction created: {transaction_id}")

    async def handle_transaction_query(self, websocket: "ServerConnection", client_id: str, message: dict):
        """处理查询交易记录"""
        request_id = message.get("request_id")
        query_type = message.get("query_type", "all")
        agent_id = message.get("agent_id")

        transactions = []

        for txn in self.transaction_mgr._transactions.values():
            if query_type == "bought":
                if agent_id and txn.get("buyer_id") == agent_id:
                    transactions.append(txn)
                elif not agent_id and txn.get("buyer_id") == client_id:
                    transactions.append(txn)
            elif query_type == "sold":
                if agent_id and txn.get("seller_id") == agent_id:
                    transactions.append(txn)
                elif not agent_id and txn.get("seller_id") == client_id:
                    transactions.append(txn)
            else:
                if agent_id:
                    if txn.get("buyer_id") == agent_id or txn.get("seller_id") == agent_id:
                        transactions.append(txn)
                else:
                    if txn.get("buyer_id") == client_id or txn.get("seller_id") == client_id:
                        transactions.append(txn)

        # 计算总消费/收入
        total_spent = sum(t.get("price", 0) for t in transactions if t.get("buyer_id") == (agent_id or client_id))
        total_earned = sum(t.get("price", 0) for t in transactions if t.get("seller_id") == (agent_id or client_id))

        await websocket.send(json.dumps({
            "type": "transaction_query_response",
            "request_id": request_id,
            "transactions": transactions,
            "total": len(transactions),
            "total_spent": total_spent,
            "total_earned": total_earned,
            "query_type": query_type
        }))
        print(f"[Server] Transaction query: {len(transactions)} records for {agent_id or client_id}")
