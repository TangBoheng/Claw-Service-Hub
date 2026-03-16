"""
评分系统
1-10 分制，支持评价和统计
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import uuid


@dataclass
class Rating:
    """评分记录"""
    id: str
    service_id: str
    score: int  # 1-10 分
    comment: str = ""
    tags: List[str] = None  # 评价标签: ["fast", "accurate", "reliable"]
    rated_at: str = ""
    anonymous: bool = True  # 是否匿名
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.rated_at:
            self.rated_at = datetime.now(timezone.utc).isoformat()
        # 验证分数范围
        if not 1 <= self.score <= 10:
            raise ValueError("Score must be between 1 and 10")
    
    def to_dict(self) -> dict:
        return asdict(self)


class RatingManager:
    """
    评分管理器
    
    功能：
    - 提交评分 (1-10 分)
    - 获取服务评分
    - 计算加权平均
    """
    
    def __init__(self):
        self._ratings: Dict[str, List[Rating]] = {}  # service_id -> ratings
        self._cache_path: str = None
    
    def load_from_file(self, path: str):
        """从文件加载评分数据"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                for sid, ratings_list in data.items():
                    self._ratings[sid] = [Rating(**r) for r in ratings_list]
            print(f"[Rating] Loaded {len(self._ratings)} services from {path}")
        except FileNotFoundError:
            print(f"[Rating] No existing ratings file, starting fresh")
        except Exception as e:
            print(f"[Rating] Error loading: {e}")
    
    def save_to_file(self, path: str):
        """保存评分到文件"""
        data = {
            sid: [r.to_dict() for r in ratings] 
            for sid, ratings in self._ratings.items()
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[Rating] Saved ratings to {path}")
    
    async def add_rating(
        self, 
        service_id: str, 
        score: int, 
        comment: str = "",
        tags: List[str] = None,
        anonymous: bool = True
    ) -> Rating:
        """添加评分"""
        rating = Rating(
            id=str(uuid.uuid4())[:8],
            service_id=service_id,
            score=score,
            comment=comment,
            tags=tags or [],
            anonymous=anonymous
        )
        
        if service_id not in self._ratings:
            self._ratings[service_id] = []
        
        self._ratings[service_id].append(rating)
        print(f"[Rating] New rating for {service_id}: {score}/10")
        
        return rating
    
    def get_ratings(self, service_id: str) -> List[Rating]:
        """获取服务的所有评分"""
        return self._ratings.get(service_id, [])
    
    def get_stats(self, service_id: str) -> dict:
        """获取服务评分统计"""
        ratings = self._ratings.get(service_id, [])
        
        if not ratings:
            return {
                "service_id": service_id,
                "count": 0,
                "average": 0.0,
                "min": 0,
                "max": 0,
                "tags": {}
            }
        
        scores = [r.score for r in ratings]
        
        # 统计标签
        tag_counts: Dict[str, int] = {}
        for r in ratings:
            for tag in r.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "service_id": service_id,
            "count": len(ratings),
            "average": round(sum(scores) / len(scores), 2),
            "min": min(scores),
            "max": max(scores),
            "tags": tag_counts,
            "recent": [r.to_dict() for r in ratings[-5:]]
        }
    
    def get_all_stats(self) -> List[dict]:
        """获取所有服务的评分统计"""
        return [
            self.get_stats(sid) 
            for sid in self._ratings.keys()
        ]


# 全局评分管理器
_rating_manager = RatingManager()


def get_rating_manager() -> RatingManager:
    return _rating_manager


def reset_rating_manager():
    """重置全局评分管理器（用于测试）"""
    global _rating_manager
    _rating_manager = RatingManager()