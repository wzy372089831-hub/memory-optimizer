#!/usr/bin/env python3
"""
重建 LanceDB 表 (修复维度问题)
将向量维度从 1536 改为 384 (匹配本地模型)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lancedb_connector import LanceDBConnector
import json

def recreate_table():
    """重建表"""
    print("🔄 重建 LanceDB 表...")
    
    # 加载配置
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # 创建连接器
    connector = LanceDBConnector(config)
    connector.connect()
    
    # 删除旧表 (如果存在)
    db_path = os.path.expanduser(config['lancedb']['path'])
    table_path = os.path.join(db_path, 'memories.lance')
    
    if os.path.exists(table_path):
        print(f"🗑️  删除旧表：{table_path}")
        import shutil
        shutil.rmtree(table_path)
    
    # 创建新表 (384 维)
    connector.create_table('memories')
    
    print("✅ 表重建完成！")
    print(f"📊 向量维度：384 (匹配 sentence-transformers)")
    
    return True

if __name__ == "__main__":
    recreate_table()
