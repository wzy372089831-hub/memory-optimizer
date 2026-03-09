#!/usr/bin/env python3
"""
集成测试脚本
测试 MemoryOptimizer 主类的完整功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta


def test_initialize():
    """测试初始化"""
    print("\n=== 测试初始化 ===")
    
    try:
        from memory_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer('config.json')
        optimizer.initialize()
        
        assert optimizer.connector is not None, "连接器未初始化"
        assert optimizer.tiering is not None, "分级模块未初始化"
        assert optimizer.searcher is not None, "搜索模块未初始化"
        assert optimizer.cleanup is not None, "清理模块未初始化"
        
        print("  ✅ 所有模块初始化成功")
        return True
    except Exception as e:
        print(f"  ❌ 初始化失败：{e}")
        return False


def test_get_stats():
    """测试统计功能"""
    print("\n=== 测试统计功能 ===")
    
    try:
        from memory_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer('config.json')
        optimizer.initialize()
        
        stats = optimizer.get_stats()
        
        assert 'hot' in stats, "缺少 hot 统计"
        assert 'warm' in stats, "缺少 warm 统计"
        assert 'cold' in stats, "缺少 cold 统计"
        assert 'total' in stats, "缺少 total 统计"
        
        print(f"  ✅ 统计功能正常：{stats}")
        return True
    except Exception as e:
        print(f"  ❌ 统计功能失败：{e}")
        return False


def test_search():
    """测试搜索功能"""
    print("\n=== 测试搜索功能 ===")
    
    try:
        from memory_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer('config.json')
        optimizer.initialize()
        
        results = optimizer.search("测试", limit=5)
        
        assert isinstance(results, list), "搜索结果应为列表"
        
        print(f"  ✅ 搜索功能正常：{len(results)} 条结果")
        return True
    except Exception as e:
        print(f"  ❌ 搜索功能失败：{e}")
        return False


def test_cleanup():
    """测试清理功能"""
    print("\n=== 测试清理功能 ===")
    
    try:
        from memory_optimizer import MemoryOptimizer
        
        optimizer = MemoryOptimizer('config.json')
        optimizer.initialize()
        
        result = optimizer.cleanup_old_memories(days=30, dry_run=True)
        
        assert 'archived' in result, "缺少 archived 字段"
        assert 'deleted' in result, "缺少 deleted 字段"
        
        print(f"  ✅ 清理功能正常：{result}")
        return True
    except Exception as e:
        print(f"  ❌ 清理功能失败：{e}")
        return False


def main():
    """运行所有集成测试"""
    print("🧪 记忆优化器集成测试")
    print("=" * 50)
    
    results = {
        "初始化": test_initialize(),
        "统计功能": test_get_stats(),
        "搜索功能": test_search(),
        "清理功能": test_cleanup(),
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
        print("🎉 所有集成测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
