"""
记忆分级模块 - HOT/WARM/COLD 三级管理
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MemoryTiering:
    """记忆分级管理器"""
    
    def __init__(self, config: Dict):
        self.config = config['tiering']
        
    def classify(self, memory: Dict) -> str:
        """
        根据访问模式分类记忆
        
        返回：HOT | WARM | COLD
        """
        last_accessed = memory.get('last_accessed')
        access_count_7d = memory.get('access_count_7d', 0)
        
        # 转换为 datetime
        if isinstance(last_accessed, (int, float)):
            last_accessed = datetime.fromtimestamp(last_accessed)
        elif isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed)
            except ValueError:
                return "COLD"
        
        if last_accessed is None:
            return "COLD"
        
        days_since_access = (datetime.now() - last_accessed).days
        hours_since_access = (datetime.now() - last_accessed).total_seconds() / 3600
        
        # HOT 标准：24 小时内访问过 或 7 天内访问 5 次+
        if hours_since_access <= self.config.get('hot_threshold_hours', 24):
            return "HOT"
        if access_count_7d >= 5:
            return "HOT"
            
        # WARM 标准：7 天内访问过
        if days_since_access <= self.config.get('warm_threshold_days', 7):
            return "WARM"
            
        # COLD 标准：超过 7 天未访问
        return "COLD"
        
    def promote(self, memory: Dict, new_tier: str = "HOT"):
        """升级记忆到指定层级"""
        memory['tier'] = new_tier
        memory['access_count'] = memory.get('access_count', 0) + 1
        memory['last_accessed'] = datetime.now()
        print(f"⬆️  记忆已升级到 {new_tier}")
        return memory
        
    def demote(self, memory: Dict, new_tier: str = "COLD"):
        """降级记忆到指定层级"""
        memory['tier'] = new_tier
        print(f"⬇️  记忆已降级到 {new_tier}")
        return memory
        
    def auto_classify_batch(self, memories: List[Dict]) -> Dict[str, int]:
        """
        批量自动分类
        
        返回：{"HOT": 10, "WARM": 50, "COLD": 100}
        """
        stats = {"HOT": 0, "WARM": 0, "COLD": 0}
        
        for memory in memories:
            tier = self.classify(memory)
            memory['tier'] = tier
            stats[tier] += 1
            
        return stats
        
    def get_tier_limits(self, tier: str) -> Dict:
        """获取各层级的容量限制"""
        limits = {
            "HOT": {
                "max_count": self.config.get('hot_max_count', 50),
                "location": "memory_cache",
                "priority": "high"
            },
            "WARM": {
                "max_count": self.config.get('warm_max_count', 500),
                "location": "lancedb_ssd",
                "priority": "medium"
            },
            "COLD": {
                "max_count": float('inf'),
                "location": "object_storage",
                "priority": "low"
            }
        }
        return limits.get(tier, limits["COLD"])


# 测试函数
def test_tiering():
    """测试分级功能"""
    config = {
        "tiering": {
            "hot_threshold_hours": 24,
            "warm_threshold_days": 7,
            "hot_max_count": 50,
            "warm_max_count": 500
        }
    }
    
    tiering = MemoryTiering(config)
    
    # 测试用例
    test_memories = [
        {"id": "1", "last_accessed": datetime.now() - timedelta(hours=1), "access_count_7d": 10},
        {"id": "2", "last_accessed": datetime.now() - timedelta(days=3), "access_count_7d": 2},
        {"id": "3", "last_accessed": datetime.now() - timedelta(days=15), "access_count_7d": 0},
    ]
    
    print("📊 记忆分级测试:")
    for mem in test_memories:
        tier = tiering.classify(mem)
        print(f"  记忆 {mem['id']}: {tier}")
        

if __name__ == "__main__":
    test_tiering()
