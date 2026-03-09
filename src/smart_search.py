"""
智能搜索模块 - 向量 + 关键词 + 时间过滤
"""

import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class EmbeddingGenerator:
    """向量嵌入生成器（优先使用 OpenClaw 配置的模型）"""

    def __init__(self, config: Optional[Dict] = None):
        self._embedding_config = config or {}
        self.model, self.dim = self._resolve_model()
        self._pipeline = None

    # ------------------------------------------------------------------
    # OpenClaw 模型检测
    # ------------------------------------------------------------------

    def _resolve_model(self) -> Tuple[str, int]:
        """
        按优先级解析嵌入模型和维度：
          1. 读取 OpenClaw 配置文件（openclaw_config_paths 列表）
          2. 使用 config.json 中 embedding.fallback_model
          3. 硬编码兜底 all-MiniLM-L6-v2 / 384
        """
        # 1. 尝试从 OpenClaw 配置文件读取
        for raw_path in self._embedding_config.get('openclaw_config_paths', []):
            path = os.path.expanduser(raw_path)
            if not os.path.exists(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    oc_cfg = json.load(f)
                model, dim = self._extract_openclaw_embedding(oc_cfg)
                if model:
                    print(f"✅ 检测到 OpenClaw 嵌入模型：{model}（维度 {dim}）")
                    return model, dim
            except Exception as e:
                print(f"⚠️  读取 OpenClaw 配置失败 {path}：{e}")

        # 2. fallback：config.json 中指定的本地模型
        fallback_model = self._embedding_config.get(
            'fallback_model', 'sentence-transformers/all-MiniLM-L6-v2'
        )
        fallback_dim = self._embedding_config.get('fallback_dim', 384)
        print(f"ℹ️  使用 fallback 嵌入模型：{fallback_model}（维度 {fallback_dim}）")
        return fallback_model, fallback_dim

    @staticmethod
    def _extract_openclaw_embedding(oc_cfg: Dict) -> Tuple[Optional[str], int]:
        """
        从 OpenClaw 配置字典中提取嵌入模型名称和维度。
        支持多种 OpenClaw 配置布局：
          - oc_cfg["embedding"]["model"] / oc_cfg["embedding"]["dim"]
          - oc_cfg["memory"]["embedding_model"] / oc_cfg["memory"]["embedding_dim"]
          - oc_cfg["embedder"]["model_name"]
        """
        # 布局 1: {"embedding": {"model": "...", "dim": N}}
        emb = oc_cfg.get('embedding') or {}
        model = emb.get('model') or emb.get('model_name') or emb.get('name')
        dim = emb.get('dim') or emb.get('dimensions') or emb.get('vector_size')
        if model:
            return model, int(dim) if dim else EmbeddingGenerator._infer_dim(model)

        # 布局 2: {"memory": {"embedding_model": "...", "embedding_dim": N}}
        mem = oc_cfg.get('memory') or {}
        model = mem.get('embedding_model') or mem.get('embedder')
        dim = mem.get('embedding_dim') or mem.get('vector_dim')
        if model:
            return model, int(dim) if dim else EmbeddingGenerator._infer_dim(model)

        # 布局 3: {"embedder": {"model_name": "..."}}
        embedder = oc_cfg.get('embedder') or {}
        model = embedder.get('model_name') or embedder.get('model')
        dim = embedder.get('dim') or embedder.get('dimensions')
        if model:
            return model, int(dim) if dim else EmbeddingGenerator._infer_dim(model)

        return None, 384

    @staticmethod
    def _infer_dim(model: str) -> int:
        """
        根据模型名称推断常见维度（无法确定时返回 0，触发运行时探测）。
        """
        model_lower = model.lower()
        known = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536,
            'all-minilm-l6-v2': 384,
            'all-minilm-l12-v2': 384,
            'all-mpnet-base-v2': 768,
            'bge-small': 512,
            'bge-base': 768,
            'bge-large': 1024,
            'nomic-embed-text': 768,
        }
        for key, dim in known.items():
            if key in model_lower:
                return dim
        return 0  # 未知，后续运行时探测

    def get_dim(self) -> int:
        """返回实际向量维度（若未知则生成一条测试向量探测）"""
        if self.dim:
            return self.dim
        # 运行时探测
        try:
            sample = self.generate("probe")
            self.dim = len(sample)
            print(f"✅ 运行时探测向量维度：{self.dim}")
        except Exception:
            self.dim = 384
            print(f"⚠️  无法探测维度，使用默认值 {self.dim}")
        return self.dim

    # ------------------------------------------------------------------
    # 嵌入生成
    # ------------------------------------------------------------------

    def _get_pipeline(self):
        """懒加载嵌入模型"""
        if self._pipeline is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._pipeline = SentenceTransformer(self.model)
                print(f"✅ 嵌入模型已加载：{self.model}")
            except ImportError:
                print("⚠️  sentence-transformers 未安装，使用备用方案")
                self._pipeline = "dummy"
        return self._pipeline

    def generate(self, text: str) -> List[float]:
        """生成单条文本的向量嵌入"""
        pipeline = self._get_pipeline()
        if pipeline == "dummy":
            return self._dummy_embedding(text)
        embedding = pipeline.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量嵌入"""
        pipeline = self._get_pipeline()
        if pipeline == "dummy":
            return [self._dummy_embedding(t) for t in texts]
        embeddings = pipeline.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def _dummy_embedding(self, text: str) -> List[float]:
        """备用嵌入（固定维度，仅测试用）"""
        import hashlib
        dim = self.dim or 384
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = list(hash_bytes) + [0] * max(0, dim - 32)
        return [float(v) / 256.0 for v in vector[:dim]]


class SmartSearch:
    """智能搜索器（向量搜索 + 关键词过滤 + 时间过滤 + 混合排序）"""

    def __init__(self, config: Dict, connector):
        self.config = config['search']
        self.connector = connector
        self.embedder = EmbeddingGenerator(config.get('embedding', {}))

    def search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        limit: int = 5,
        tier: str = "all",
        since: Optional[datetime] = None,
        min_score: float = 0.6,
    ) -> List[Dict]:
        """
        混合搜索：向量 + 关键词 + 时间

        参数:
            query: 搜索关键词
            query_vector: 查询向量（可选，不传则自动生成）
            limit: 返回数量限制
            tier: 记忆层级过滤 (HOT/WARM/COLD/all)
            since: 时间过滤（只返回此时间之后的记忆）
            min_score: 最低相关性分数

        返回:
            搜索结果列表（含 _score 字段）
        """
        vector_results: List[Dict] = []
        keyword_results: List[Dict] = []

        # 1. 向量搜索
        if self.connector.table is not None:
            # 自动生成查询向量（若未提供）
            vec = query_vector
            if vec is None and query:
                try:
                    vec = self.embedder.generate(query)
                except Exception as e:
                    print(f"⚠️ 向量嵌入生成失败：{e}")

            if vec is not None:
                raw = self.connector.search(vec, limit=limit * 3)
                for r in raw:
                    # LanceDB 返回的 _distance 越小越相似；转换为 [0,1] 分数
                    distance = r.get('_distance', 1.0)
                    score = max(0.0, 1.0 - distance)
                    r['_score'] = score
                    r['_match_type'] = 'vector'
                vector_results = raw

        # 2. 关键词搜索（从 DB 检索，限制最大扫描行数防内存溢出）
        if query and self.connector.table is not None:
            try:
                max_scan = self.config.get('max_keyword_scan', 2000)
                all_rows = self.connector.table.to_pandas().head(max_scan)
                keyword_results = self._keyword_search(all_rows.to_dict('records'), query)
            except Exception as e:
                print(f"⚠️ 关键词搜索失败：{e}")

        # 3. 合并结果（向量结果为主，补充关键词专属命中）
        results = self._merge_results(vector_results, keyword_results)

        # 4. 层级过滤
        if tier != "all":
            results = self._tier_filter(results, tier)

        # 5. 时间过滤
        if since:
            results = self._time_filter(results, since)

        # 6. 相关性分数过滤
        results = [r for r in results if r.get('_score', 0.0) >= min_score]

        # 7. 混合排序（向量相似度 + 关键词命中 + 访问热度）
        results = self._relevance_sort(results, query)

        # 8. 限制数量
        results = results[:limit]

        print(f"🔍 搜索完成：'{query}' → {len(results)} 条结果")
        return results

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _keyword_search(self, rows: List[Dict], keyword: str) -> List[Dict]:
        """在全量数据中进行关键词搜索，返回命中条目（含基础分数）"""
        keyword_lower = keyword.lower()
        matched = []
        for r in rows:
            content = str(r.get('content', '')).lower()
            metadata = str(r.get('metadata', '')).lower()
            if keyword_lower in content or keyword_lower in metadata:
                r = dict(r)
                # 根据关键词在内容中出现的频率给基础分数
                count = content.count(keyword_lower) + metadata.count(keyword_lower)
                r['_score'] = min(0.5 + count * 0.05, 0.85)  # 关键词命中上限 0.85
                r['_match_type'] = 'keyword'
                matched.append(r)
        return matched

    def _merge_results(
        self, vector_results: List[Dict], keyword_results: List[Dict]
    ) -> List[Dict]:
        """合并向量搜索和关键词搜索结果，去重，向量分数优先"""
        seen_ids = {}
        merged = []

        for r in vector_results:
            rid = r.get('id', id(r))
            seen_ids[rid] = len(merged)
            merged.append(r)

        for r in keyword_results:
            rid = r.get('id', id(r))
            if rid in seen_ids:
                # 已有向量结果：提升分数（混合加权）
                existing = merged[seen_ids[rid]]
                v_score = existing.get('_score', 0.0)
                k_score = r.get('_score', 0.0)
                existing['_score'] = 0.7 * v_score + 0.3 * k_score
                existing['_match_type'] = 'hybrid'
            else:
                seen_ids[rid] = len(merged)
                merged.append(r)

        return merged

    def _tier_filter(self, results: List[Dict], tier: str) -> List[Dict]:
        """层级过滤"""
        return [r for r in results if r.get('tier') == tier]

    def _time_filter(self, results: List[Dict], since: datetime) -> List[Dict]:
        """时间过滤"""
        filtered = []
        for r in results:
            created_at = r.get('created_at')
            if created_at:
                if isinstance(created_at, (int, float)):
                    created_at = datetime.fromtimestamp(created_at)
                if created_at >= since:
                    filtered.append(r)
        return filtered

    def _relevance_sort(self, results: List[Dict], query: str) -> List[Dict]:
        """混合排序：向量相似度（60%）+ 访问热度（25%）+ 关键词权重（15%）"""
        max_access = max((r.get('access_count', 0) for r in results), default=1) or 1

        def score(r: Dict) -> float:
            base = r.get('_score', 0.0)
            access_norm = r.get('access_count', 0) / max_access
            # 关键词加权：hybrid 命中额外加分
            kw_bonus = 0.05 if r.get('_match_type') == 'hybrid' else 0.0
            return 0.60 * base + 0.25 * access_norm + 0.15 * kw_bonus

        return sorted(results, key=score, reverse=True)


# 测试函数
def test_search():
    """测试搜索功能（使用 mock 数据，不依赖 DB）"""
    print("🔍 智能搜索测试")

    mock_results = [
        {"id": "1", "content": "用户喜欢 Python 编程", "tier": "HOT", "access_count": 10, "_score": 0.9},
        {"id": "2", "content": "Java 项目笔记", "tier": "WARM", "access_count": 5, "_score": 0.7},
        {"id": "3", "content": "Python 数据分析教程", "tier": "HOT", "access_count": 8, "_score": 0.85},
    ]

    # 测试关键词过滤
    searcher = SmartSearch.__new__(SmartSearch)
    searcher.config = {"default_limit": 5, "min_relevance_score": 0.6}

    filtered = searcher._keyword_search(mock_results, "python")
    assert len(filtered) == 2, f"期望 2 条，实际 {len(filtered)} 条"

    sorted_results = searcher._relevance_sort(mock_results, "python")
    assert sorted_results[0]['id'] == '1', "分数最高的应排第一"

    print(f"  关键词过滤：{len(filtered)} 条 ✅")
    print(f"  排序结果：{[r['id'] for r in sorted_results]} ✅")
    print("  测试通过 ✅")


if __name__ == "__main__":
    test_search()
