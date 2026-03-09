#!/usr/bin/env python3
"""
记忆优化器使用示例
演示如何使用记忆优化器的各项功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, timedelta
from memory_optimizer import MemoryOptimizer
from memory_tiering import MemoryTiering
from cleanup_scheduler import CleanupScheduler


def example_basic_usage():
    """基础使用示例"""
    print("\n" + "="*60)
    print("示例 1: 基础使用")
    print("="*60)
    
    # 1. 初始化优化器
    optimizer = MemoryOptimizer('config.json')
    
    # 2. 初始化（连接 LanceDB + 加载所有模块）
    optimizer.initialize()

    # 3. 查看统计
    stats = optimizer.get_stats()
    print(f"📊 当前记忆统计：{stats}")

    # 4. 智能搜索
    results = optimizer.search("用户偏好", limit=5)
    print(f"🔍 搜索结果：{len(results)} 条")

    # 5. 清理冷记忆
    cleanup_result = optimizer.cleanup_old_memories(days=30, dry_run=True)
    print(f"🧹 清理预览：{cleanup_result}")


def example_memory_tiering():
    """记忆分级示例"""
    print("\n" + "="*60)
    print("示例 2: 记忆分级")
    print("="*60)
    
    config = {
        "tiering": {
            "hot_threshold_hours": 24,
            "warm_threshold_days": 7,
            "hot_max_count": 50,
            "warm_max_count": 500
        }
    }
    
    tiering = MemoryTiering(config)
    
    # 模拟一些记忆
    memories = [
        {"id": "1", "content": "今天的工作笔记", "last_accessed": datetime.now() - timedelta(hours=2), "access_count_7d": 10},
        {"id": "2", "content": "上周的会议纪要", "last_accessed": datetime.now() - timedelta(days=3), "access_count_7d": 2},
        {"id": "3", "content": "上月的项目文档", "last_accessed": datetime.now() - timedelta(days=20), "access_count_7d": 0},
    ]
    
    # 自动分类
    stats = tiering.auto_classify_batch(memories)
    print(f"📊 记忆分级统计：{stats}")
    
    for mem in memories:
        print(f"  - {mem['content']}: {mem['tier']}")


def example_cleanup():
    """清理调度示例"""
    print("\n" + "="*60)
    print("示例 3: 定期清理")
    print("="*60)
    
    config = {
        "cleanup": {
            "auto_archive": True,
            "archive_path": "~/.openclaw/memory/archive_example",
            "delete_after_days": 90
        }
    }
    
    class MockConnector:
        table = None
    
    scheduler = CleanupScheduler(config, MockConnector())
    
    # 查看归档统计
    stats = scheduler.get_stats()
    print(f"📊 归档统计：{stats}")
    
    # 预览清理
    result = scheduler.auto_archive(days=30, dry_run=True)
    print(f"🧹 清理预览：{result}")


def example_cron_setup():
    """Cron 定时任务配置示例"""
    print("\n" + "="*60)
    print("示例 4: Cron 定时任务配置")
    print("="*60)
    
    print("""
# 添加到 crontab (crontab -e)

# 每天凌晨 3 点自动清理冷记忆
0 3 * * * cd ~/AI/Claude/memory-optimizer && python3 -c "from src.cleanup_scheduler import CleanupScheduler; CleanupScheduler(...).auto_archive(days=30)"

# 每周日凌晨 4 点重建索引
0 4 * * 0 cd ~/AI/Claude/memory-optimizer && python3 -c "from src.memory_optimizer import MemoryOptimizer; m = MemoryOptimizer(); m.initialize()"

# 每小时统计 Token 消耗
0 * * * * cd ~/AI/Claude/memory-optimizer && python3 -c "from src.memory_optimizer import MemoryOptimizer; print(MemoryOptimizer().get_stats())" >> ~/token-stats.log
    """)


def main():
    """运行所有示例"""
    print("🎯 记忆优化器使用示例")
    print("生成时间：2026-03-09")
    
    try:
        example_memory_tiering()  # 不依赖 DB
        example_cleanup()  # 不依赖 DB
        example_cron_setup()  # 纯文本
        
        print("\n" + "="*60)
        print("提示：基础使用示例需要 LanceDB 连接，已跳过")
        print("="*60)
        
        return 0
    except Exception as e:
        print(f"❌ 示例运行失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
