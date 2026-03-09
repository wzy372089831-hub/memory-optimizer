#!/usr/bin/env python3
"""
智能搜索测试脚本
测试向量搜索 + 关键词搜索 + 混合排序功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta


def test_embedding_generator():
    """测试嵌入生成器"""
    print("\n=== 测试 EmbeddingGenerator ===")
    
    try:
        from smart_search import EmbeddingGenerator
        
        embedder = EmbeddingGenerator()
        
        # 测试单条生成
        text = "这是一个测试文本"
        vector = embedder.generate(text)
        
        assert len(vector) == 384, f"向量维度错误：{len(vector)}"
        assert all(isinstance(v, float) for v in vector), "向量元素应为浮点数"
        
        print(f"  ✅ 单条嵌入生成：{len(vector)} 维")
        
        # 测试批量生成
        texts = ["文本 1", "文本 2", "文本 3"]
        vectors = embedder.generate_batch(texts)
        
        assert len(vectors) == 3, f"批量生成数量错误：{len(vectors)}"
        print(f"  ✅ 批量嵌入生成：{len(vectors)} 条")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False


def test_keyword_search():
    """测试关键词搜索"""
    print("\n=== 测试关键词搜索 ===")
    
    try:
        from smart_search import SmartSearch
        
        # Mock 配置和连接器
        config = {"search": {"default_limit": 5}}
        
        class MockConnector:
            table = None
        
        search = SmartSearch(config, MockConnector())
        
        # 测试数据
        test_data = [
            {"id": "1", "content": "Python 编程教程", "metadata": "技术"},
            {"id": "2", "content": "Java 项目笔记", "metadata": "技术"},
            {"id": "3", "content": "Python 数据分析", "metadata": "教程"},
        ]
        
        results = search._keyword_search(test_data, "python")
        
        assert len(results) == 2, f"关键词搜索结果错误：{len(results)}"
        assert all('_score' in r for r in results), "结果应包含_score"
        assert all('_match_type' in r for r in results), "结果应包含_match_type"
        
        print(f"  ✅ 关键词搜索：找到 {len(results)} 条结果")
        for r in results:
            print(f"    - ID {r['id']}: {r['content']} (score={r['_score']:.2f})")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False


def test_merge_results():
    """测试结果合并"""
    print("\n=== 测试结果合并 ===")
    
    try:
        from smart_search import SmartSearch
        
        config = {"search": {"default_limit": 5}}
        
        class MockConnector:
            table = None
        
        search = SmartSearch(config, MockConnector())
        
        # 向量结果
        vector_results = [
            {"id": "1", "_score": 0.9, "_match_type": "vector"},
            {"id": "2", "_score": 0.8, "_match_type": "vector"},
        ]
        
        # 关键词结果
        keyword_results = [
            {"id": "2", "_score": 0.7, "_match_type": "keyword"},
            {"id": "3", "_score": 0.6, "_match_type": "keyword"},
        ]
        
        merged = search._merge_results(vector_results, keyword_results)
        
        assert len(merged) == 3, f"合并结果数量错误：{len(merged)}"
        assert merged[0]['id'] == "1", "第一个结果应为 ID 1"
        assert merged[1]['id'] == "2", "第二个结果应为 ID 2 (向量优先)"
        assert merged[2]['id'] == "3", "第三个结果应为 ID 3"
        
        print(f"  ✅ 结果合并：{len(merged)} 条 (去重后)")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False


def test_relevance_sort():
    """测试相关性排序"""
    print("\n=== 测试相关性排序 ===")
    
    try:
        from smart_search import SmartSearch
        
        config = {"search": {"default_limit": 5}}
        
        class MockConnector:
            table = None
        
        search = SmartSearch(config, MockConnector())
        
        # 测试数据：ID 3 应该排第一 (访问次数最高，且_score 不错)
        test_results = [
            {"id": "1", "_score": 0.7, "access_count": 5, "_match_type": "vector"},
            {"id": "2", "_score": 0.9, "access_count": 10, "_match_type": "vector"},
            {"id": "3", "_score": 0.8, "access_count": 20, "_match_type": "hybrid"},
        ]
        
        sorted_results = search._relevance_sort(test_results, "test")
        
        # 综合评分计算:
        # ID 1: 0.6*0.7 + 0.25*(5/20) + 0.15*0 = 0.42 + 0.0625 + 0 = 0.4825
        # ID 2: 0.6*0.9 + 0.25*(10/20) + 0.15*0 = 0.54 + 0.125 + 0 = 0.665
        # ID 3: 0.6*0.8 + 0.25*(20/20) + 0.15*0.05 = 0.48 + 0.25 + 0.0075 = 0.7375
        # 预期排序：ID 3 > ID 2 > ID 1
        
        assert sorted_results[0]['id'] == "3", f"最相关的应排第一，实际是{sorted_results[0]['id']}"
        
        print(f"  ✅ 相关性排序：正确")
        for r in sorted_results:
            print(f"    - ID {r['id']}: score={r['_score']:.2f}, accesses={r['access_count']}, type={r['_match_type']}")
        
        return True
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("🧪 智能搜索模块测试")
    print("=" * 50)
    
    results = {
        "EmbeddingGenerator": test_embedding_generator(),
        "关键词搜索": test_keyword_search(),
        "结果合并": test_merge_results(),
        "相关性排序": test_relevance_sort(),
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
