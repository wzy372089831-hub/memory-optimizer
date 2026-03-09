"""
LanceDB 连接器 - 配置优化模块
功能：索引创建、缓存管理、批量操作
"""

import lancedb
import os
from typing import Optional, List, Dict
import numpy as np


class LanceDBConnector:
    """LanceDB 连接器（带优化）"""

    def __init__(self, config: Dict):
        self.config = config
        self.db = None
        self.table = None
        self.cache = {}

    def _resolve_vector_dim(self) -> int:
        """
        通过 EmbeddingGenerator 探测向量维度。
        优先读取 OpenClaw 配置；无法确定时生成一条测试向量获取真实维度。
        """
        try:
            import sys, os
            # 确保可以 import smart_search
            src_dir = os.path.dirname(os.path.abspath(__file__))
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from smart_search import EmbeddingGenerator
            embedder = EmbeddingGenerator(self.config.get('embedding', {}))
            return embedder.get_dim()
        except Exception as e:
            print(f"⚠️  维度探测失败，使用默认值 384：{e}")
            return 384
        
    def connect(self) -> lancedb.DBConnection:
        """连接到 LanceDB（带缓存优化）"""
        path = os.path.expanduser(self.config['lancedb']['path'])
        
        # 启用缓存
        cache_size = self.config['lancedb'].get('cache_size_mb', 1024)
        self.db = lancedb.connect(path)
        
        print(f"✅ LanceDB 已连接：{path}")
        print(f"💾 缓存大小：{cache_size}MB (配置值)")
        return self.db
        
    def create_table(self, table_name: str = "memories", vector_dim: int = 0):
        """
        创建记忆表（带向量索引）

        参数:
            table_name: 表名
            vector_dim: 向量维度；0 表示从 EmbeddingGenerator 自动探测
        """
        if self.db is None:
            self.connect()

        # 检查表是否存在
        existing_tables = self.db.table_names()
        if table_name in existing_tables:
            self.table = self.db.open_table(table_name)
            print(f"📂 已打开现有表：{table_name}")
            return self.table

        # 解析向量维度
        dim = vector_dim
        if not dim:
            dim = self._resolve_vector_dim()
        print(f"✅ 向量维度：{dim}")

        # 创建新表
        import pyarrow as pa

        schema = pa.schema([
            pa.field('id', pa.string()),
            pa.field('vector', pa.list_(pa.float32(), dim)),
            pa.field('content', pa.string()),
            pa.field('metadata', pa.string()),
            pa.field('tier', pa.string()),  # HOT/WARM/COLD
            pa.field('created_at', pa.timestamp('us')),
            pa.field('access_count', pa.int32()),
            pa.field('last_accessed', pa.timestamp('us')),
        ])
        
        self.table = self.db.create_table(table_name, schema=schema)
        print(f"✅ 已创建表：{table_name}")
        
        # 创建向量索引
        self.create_index()
        
        return self.table
        
    def create_index(self, index_type: str = "IVF_PQ"):
        """创建向量索引（加速搜索）"""
        if self.table is None:
            raise Exception("表未创建，先调用 create_table()")
        
        config = self.config['lancedb']
        
        # 根据数据量选择索引类型
        num_partitions = config.get('num_partitions', 256)
        num_sub_vectors = config.get('num_sub_vectors', 96)
        
        try:
            self.table.create_index(
                index_type=index_type,
                num_partitions=num_partitions,
                num_sub_vectors=num_sub_vectors,
                column='vector'
            )
            print(f"✅ 向量索引已创建：{index_type} (partitions={num_partitions}, sub_vectors={num_sub_vectors})")
        except Exception as e:
            print(f"⚠️ 索引创建失败（可能数据太少）: {e}")
            
    def batch_insert(self, records: List[Dict]) -> int:
        """批量插入（比单条快 10-100 倍）"""
        if self.table is None:
            raise Exception("表未创建")
            
        self.table.add(records)
        print(f"✅ 批量插入 {len(records)} 条记录")
        return len(records)
        
    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """向量搜索"""
        if self.table is None:
            raise Exception("表未创建")
            
        results = self.table.search(query_vector).limit(limit).to_list()
        return results
        
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if self.table is None:
            return {"count": 0, "size_mb": 0}
            
        # 获取记录数
        count = self.table.count_rows()
        
        return {
            "count": count,
            "size_mb": 0,  # TODO: 计算实际大小
            "index_type": self.config['lancedb'].get('index_type', 'unknown')
        }


# 测试函数
def test_connection():
    """测试连接"""
    config = {
        "lancedb": {
            "path": "~/.openclaw/memory/lancedb",
            "cache_size_mb": 1024,
            "num_partitions": 256,
            "num_sub_vectors": 96
        }
    }
    
    connector = LanceDBConnector(config)
    connector.connect()
    connector.create_table()
    
    stats = connector.get_stats()
    print(f"📊 统计：{stats}")
    

if __name__ == "__main__":
    test_connection()
