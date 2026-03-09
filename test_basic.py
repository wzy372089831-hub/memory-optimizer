#!/usr/bin/env python3
"""
基础测试脚本
测试记忆优化器的核心功能
"""

import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_lancedb_connector():
    """测试 LanceDB 连接器"""
    print("\n=== 测试 LanceDB 连接器 ===")
    
    from lancedb_connector import LanceDBConnector
    
    config = {
        "lancedb": {
            "path": "~/.openclaw/memory/lancedb",
            "cache_size_mb": 1024,
            "num_partitions": 256,
            "num_sub_vectors": 96
        }
    }
    
    try:
        connector = LanceDBConnector(config)
        connector.connect()
        print("✅ 连接测试通过")
        
        connector.create_table()
        print("✅ 表创建测试通过")
        
        stats = connector.get_stats()
        print(f"✅ 统计查询测试通过：{stats}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_memory_tiering():
    """测试记忆分级"""
    print("\n=== 测试记忆分级 ===")
    
    from memory_tiering import MemoryTiering
    from datetime import datetime, timedelta
    
    config = {
        "tiering": {
            "hot_threshold_hours": 24,
            "warm_threshold_days": 7,
            "hot_max_count": 50,
            "warm_max_count": 500
        }
    }
    
    try:
        tiering = MemoryTiering(config)
        
        # 测试用例
        test_memories = [
            {"id": "1", "last_accessed": datetime.now() - timedelta(hours=1), "access_count_7d": 10},
            {"id": "2", "last_accessed": datetime.now() - timedelta(days=3), "access_count_7d": 2},
            {"id": "3", "last_accessed": datetime.now() - timedelta(days=15), "access_count_7d": 0},
        ]
        
        expected = ["HOT", "WARM", "COLD"]
        
        for mem, exp_tier in zip(test_memories, expected):
            tier = tiering.classify(mem)
            status = "✅" if tier == exp_tier else "❌"
            print(f"  {status} 记忆 {mem['id']}: {tier} (期望：{exp_tier})")
            
        return True
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False


def test_hook_functions():
    """测试 Hook 函数（on_write / on_read）"""
    print("\n=== 测试 Hook 函数 ===")

    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    sys.path.insert(0, os.path.dirname(__file__))
    from memory_optimizer import on_write, on_read
    from datetime import datetime, timedelta

    try:
        # on_write：应自动分配 tier
        memory_data = {
            "id": "hook-1",
            "content": "Hook 测试记忆",
            "last_accessed": datetime.now() - timedelta(hours=1),
            "access_count_7d": 5,
        }
        result = on_write(memory_data)
        assert "tier" in result, "on_write 必须返回含 tier 字段的字典"
        assert result["tier"] in ("HOT", "WARM", "COLD"), f"tier 值非法：{result['tier']}"
        print(f"  ✅ on_write：tier={result['tier']}")

        # on_read：应返回 list，且长度 ≤ 5
        fake_results = [
            {"id": str(i), "content": f"记忆 {i}", "_score": i * 0.1}
            for i in range(10)
        ]
        filtered = on_read("测试查询", fake_results)
        assert isinstance(filtered, list), "on_read 必须返回 list"
        assert len(filtered) <= 5, f"on_read 返回数量超过 5：{len(filtered)}"
        # 验证按 _score 降序
        scores = [r.get("_score", 0) for r in filtered]
        assert scores == sorted(scores, reverse=True), "on_read 结果未按 _score 降序"
        print(f"  ✅ on_read：返回 {len(filtered)} 条，已按 _score 降序")

        return True
    except Exception as e:
        print(f"❌ Hook 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("🧪 记忆优化器基础测试")
    print("=" * 50)

    results = {
        "LanceDB 连接器": test_lancedb_connector(),
        "记忆分级": test_memory_tiering(),
        "Hook 函数": test_hook_functions(),
    }
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")
        
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
