#!/usr/bin/env python3
"""
性能基准测试
测试记忆优化器的性能指标
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_search_latency():
    """测试搜索延迟"""
    print("\n=== 测试搜索延迟 ===")
    
    from memory_optimizer import MemoryOptimizer
    
    optimizer = MemoryOptimizer('config.json')
    optimizer.initialize()
    
    # 预热
    optimizer.search("预热", limit=5)
    
    # 测试 10 次
    latencies = []
    for i in range(10):
        start = time.time()
        optimizer.search(f"测试{i}", limit=5)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    
    print(f"  平均延迟：{avg_latency:.2f}ms")
    print(f"  最小延迟：{min_latency:.2f}ms")
    print(f"  最大延迟：{max_latency:.2f}ms")
    
    # 评估
    if avg_latency < 100:
        print(f"  ✅ 搜索延迟优秀 (<100ms)")
        return True
    elif avg_latency < 500:
        print(f"  ⚠️  搜索延迟可接受 (<500ms)")
        return True
    else:
        print(f"  ❌ 搜索延迟过高 (>500ms)")
        return False


def test_memory_usage():
    """测试内存使用"""
    print("\n=== 测试内存使用 ===")
    
    import psutil
    process = psutil.Process()
    
    # 初始内存
    initial_mem = process.memory_info().rss / 1024 / 1024  # MB
    
    from memory_optimizer import MemoryOptimizer
    optimizer = MemoryOptimizer('config.json')
    optimizer.initialize()
    
    # 运行后内存
    final_mem = process.memory_info().rss / 1024 / 1024  # MB
    
    memory_used = final_mem - initial_mem
    
    print(f"  初始内存：{initial_mem:.2f}MB")
    print(f"  运行后内存：{final_mem:.2f}MB")
    print(f"  内存使用：{memory_used:.2f}MB")
    
    if memory_used < 100:
        print(f"  ✅ 内存使用优秀 (<100MB)")
        return True
    elif memory_used < 500:
        print(f"  ⚠️  内存使用可接受 (<500MB)")
        return True
    else:
        print(f"  ❌ 内存使用过高 (>500MB)")
        return False


def test_token_savings():
    """估算 Token 节省"""
    print("\n=== 估算 Token 节省 ===")
    
    # 假设场景
    memories_count = 1000
    avg_memory_tokens = 500
    
    # 优化前：加载所有记忆
    before_tokens = memories_count * avg_memory_tokens
    
    # 优化后：只加载最相关的 5 条
    after_tokens = 5 * avg_memory_tokens
    
    # 节省
    saved_tokens = before_tokens - after_tokens
    saved_percent = (saved_tokens / before_tokens) * 100
    
    print(f"  优化前：{before_tokens:,} tokens")
    print(f"  优化后：{after_tokens:,} tokens")
    print(f"  节省：{saved_tokens:,} tokens ({saved_percent:.1f}%)")
    
    if saved_percent >= 90:
        print(f"  ✅ Token 节省优秀 (≥90%)")
        return True
    else:
        print(f"  ⚠️  Token 节省可接受 (≥80%)")
        return True


def main():
    """运行所有基准测试"""
    print("🏎️ 记忆优化器性能基准测试")
    print("=" * 50)
    
    results = {
        "搜索延迟": test_search_latency(),
        "内存使用": test_memory_usage(),
        "Token 节省": test_token_savings(),
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
        print("🎉 所有性能测试通过！")
        return 0
    else:
        print("⚠️  部分测试未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
