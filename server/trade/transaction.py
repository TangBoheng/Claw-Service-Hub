"""Transaction management for Claw Service Hub.

Handles transaction creation and query.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Transaction:
    """交易记录实体"""

    def __init__(
        self,
        transaction_id: str,
        listing_id: str,
        buyer_id: str,
        seller_id: str,
        price: float,
        txn_type: str = "bid",  # bid, negotiation, direct
        status: str = "completed",
        created_at: str = "",
    ):
        self.transaction_id = transaction_id
        self.listing_id = listing_id
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.price = price
        self.type = txn_type
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "listing_id": self.listing_id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "price": self.price,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at,
        }


class TransactionManager:
    """交易记录管理器"""

    def __init__(self):
        self._transactions: Dict[str, Transaction] = {}  # transaction_id -> Transaction

    def create_transaction(
        self,
        transaction_id: str,
        listing_id: str,
        buyer_id: str,
        seller_id: str,
        price: float,
        txn_type: str = "bid",
    ) -> Transaction:
        """创建交易记录"""
        transaction = Transaction(
            transaction_id=transaction_id,
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            price=price,
            txn_type=txn_type,
            status="completed",
        )
        self._transactions[transaction.transaction_id] = transaction
        return transaction

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """获取交易记录"""
        return self._transactions.get(transaction_id)

    def query_transactions(
        self, agent_id: str = None, query_type: str = "all"
    ) -> tuple[List[Transaction], float, float]:
        """查询交易记录

        Args:
            agent_id: 代理 ID（可选）
            query_type: 查询类型 (all, bought, sold)

        Returns:
            (transactions, total_spent, total_earned)
        """
        transactions = []
        total_spent = 0
        total_earned = 0

        for txn in self._transactions.values():
            include = False

            if query_type == "all":
                if agent_id:
                    include = txn.buyer_id == agent_id or txn.seller_id == agent_id
                else:
                    include = True
            elif query_type == "bought":
                if agent_id:
                    include = txn.buyer_id == agent_id
                else:
                    include = txn.buyer_id == txn.buyer_id  # Always true, filter below
            elif query_type == "sold":
                if agent_id:
                    include = txn.seller_id == agent_id
                else:
                    include = txn.seller_id == txn.seller_id  # Always true, filter below

            if include:
                transactions.append(txn)
                if txn.buyer_id == agent_id:
                    total_spent += txn.price
                if txn.seller_id == agent_id:
                    total_earned += txn.price

        return transactions, total_spent, total_earned

    def get_transactions_by_listing(self, listing_id: str) -> List[Transaction]:
        """获取指定挂牌的交易记录"""
        return [t for t in self._transactions.values() if t.listing_id == listing_id]


# 全局单例
_transaction_manager = None


def get_transaction_manager() -> TransactionManager:
    """获取交易记录管理器单例"""
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = TransactionManager()
    return _transaction_manager
