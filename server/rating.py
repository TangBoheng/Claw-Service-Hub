"""Rating Manager - 服务评分管理"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Rating:
    """评分记录"""
    
    def __init__(
        self,
        service_id: str,
        score: int,
        comment: str = "",
        tags: List[str] = None,
        user_id: str = None
    ):
        self.id = f"rating_{uuid.uuid4().hex[:12]}"
        self.service_id = service_id
        self.score = score  # 0-5
        self.comment = comment
        self.tags = tags or []
        self.user_id = user_id
        self.created_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "score": self.score,
            "comment": self.comment,
            "tags": self.tags,
            "user_id": self.user_id,
            "created_at": self.created_at
        }


class RatingManager:
    """评分管理器"""
    
    def __init__(self):
        self._ratings: Dict[str, List[Rating]] = {}  # service_id -> [ratings]
    
    async def add_rating(
        self,
        service_id: str,
        score: int,
        comment: str = "",
        tags: List[str] = None,
        user_id: str = None
    ) -> Rating:
        """添加评分"""
        if score < 0 or score > 5:
            raise ValueError("Score must be between 0 and 5")
        
        rating = Rating(
            service_id=service_id,
            score=score,
            comment=comment,
            tags=tags,
            user_id=user_id
        )
        
        if service_id not in self._ratings:
            self._ratings[service_id] = []
        
        self._ratings[service_id].append(rating)
        return rating
    
    def get_ratings(self, service_id: str) -> List[Rating]:
        """获取服务评分列表"""
        return self._ratings.get(service_id, [])
    
    def get_stats(self, service_id: str) -> dict:
        """获取评分统计"""
        ratings = self.get_ratings(service_id)
        
        if not ratings:
            return {
                "service_id": service_id,
                "total": 0,
                "average": 0,
                "distribution": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            }
        
        total = len(ratings)
        score_sum = sum(r.score for r in ratings)
        average = score_sum / total if total > 0 else 0
        
        distribution = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        for r in ratings:
            distribution[str(r.score)] = distribution.get(str(r.score), 0) + 1
        
        return {
            "service_id": service_id,
            "total": total,
            "average": round(average, 2),
            "distribution": distribution
        }


# 全局单例
_rating_manager = None

def get_rating_manager() -> RatingManager:
    """获取评分管理器单例"""
    global _rating_manager
    if _rating_manager is None:
        _rating_manager = RatingManager()
    return _rating_manager