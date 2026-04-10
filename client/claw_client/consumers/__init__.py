"""Service consumers for Claw Service Hub.

服务消费者客户端，用于发现和调用服务。
"""

from .skill_query import SkillQueryClient

__all__ = [
    "SkillQueryClient",
]
