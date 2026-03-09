"""
OpenClaw 记忆优化器 - 主模块
功能：LanceDB 配置优化 + 记忆分级 + 智能搜索 + 定期清理
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 支持两种导入方式：作为包运行 or 作为脚本运行
try:
    from src.lancedb_connector import LanceDBConnector
    from src.memory_tiering import MemoryTiering
    from src.smart_search import SmartSearch
    from src.cleanup_scheduler import CleanupScheduler
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from lancedb_connector import LanceDBConnector
    from memory_tiering import MemoryTiering
    from smart_search import SmartSearch
    from cleanup_scheduler import CleanupScheduler


class MemoryOptimizer:
    """记忆优化器主类（集成所有模块）"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.connector = None
        self.tiering = None
        self.searcher = None
        self.cleanup = None
        self._initialized = False
        
    def _load_config(self, path: str) -> Dict:
        """加载配置文件"""
        with open(path, 'r') as f:
            return json.load(f)
    
    def initialize(self):
        """初始化所有模块（幂等：重复调用无副作用）"""
        if self._initialized:
            return
        # 1. 连接 LanceDB
        self.connector = LanceDBConnector(self.config)
        try:
            self.connector.connect()
            self.connector.create_table()
        except Exception as e:
            raise RuntimeError(f"LanceDB 连接失败：{e}") from e
        
        # 2. 初始化记忆分级
        self.tiering = MemoryTiering(self.config)
        
        # 3. 初始化智能搜索
        self.searcher = SmartSearch(self.config, self.connector)
        
        # 4. 初始化清理调度
        self.cleanup = CleanupScheduler(self.config, self.connector)

        # 5. 确保 token_tracking 报告目录存在
        report_path = self.config.get('token_tracking', {}).get('report_path', '')
        if report_path:
            os.makedirs(os.path.dirname(os.path.expanduser(report_path)), exist_ok=True)

        self._initialized = True
        logger.info("所有模块已初始化")
        
    def search(self, query: str, limit: int = 5, tier: str = "all") -> List[Dict]:
        """智能搜索 (向量 + 关键词 + 时间)"""
        if self.searcher is None:
            self.initialize()
        return self.searcher.search(query, limit=limit, tier=tier)
        
    def get_stats(self) -> Dict:
        """获取记忆分级统计"""
        if self.connector is None:
            self.initialize()
        
        # 获取所有记忆
        all_memories = self._get_all_memories()
        
        # 自动分类
        tier_stats = self.tiering.auto_classify_batch(all_memories)
        
        # LanceDB 统计
        db_stats = self.connector.get_stats()

        return {
            "hot": tier_stats.get("HOT", 0),
            "warm": tier_stats.get("WARM", 0),
            "cold": tier_stats.get("COLD", 0),
            "total": db_stats.get('count', 0),
            "db_size_mb": db_stats.get('size_mb', 0)
        }
        
    def cleanup_old_memories(self, days: int = 90, dry_run: bool = False, force: bool = False) -> Dict:
        """清理/归档冷记忆（带安全保障）"""
        if self.cleanup is None:
            self.initialize()
        return self.cleanup.auto_archive(days=days, dry_run=dry_run, force=force)

    def protect_memory(self, memory_id: str) -> bool:
        """将记忆加入白名单保护"""
        if self.cleanup is None:
            self.initialize()
        return self.cleanup.protect(memory_id)

    def unprotect_memory(self, memory_id: str) -> bool:
        """解除记忆的白名单保护"""
        if self.cleanup is None:
            self.initialize()
        return self.cleanup.unprotect(memory_id)

    def list_trash(self) -> List[Dict]:
        """列出回收站中的记忆"""
        if self.cleanup is None:
            self.initialize()
        return self.cleanup.list_trash()

    def restore_from_trash(self, memory_id: str) -> bool:
        """从回收站恢复记忆"""
        if self.cleanup is None:
            self.initialize()
        return self.cleanup.restore_from_trash(memory_id)
    
    def _get_all_memories(self) -> List[Dict]:
        """获取所有记忆"""
        if self.connector.table is None:
            return []
        try:
            df = self.connector.table.to_pandas()
            return df.to_dict('records')
        except Exception as e:
            logger.warning("获取记忆失败：%s", e)
            return []


# Hook 函数
def on_write(memory_data: Dict) -> Dict:
    """记忆写入时的优化"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from memory_tiering import MemoryTiering
    tiering = MemoryTiering({"tiering": {}})
    memory_data['tier'] = tiering.classify(memory_data)
    return memory_data
    
def on_read(query: str, results: List[Dict]) -> List[Dict]:
    """记忆读取时的优化"""
    # 按 _score 降序排列，取最相关的 5 条
    processed = sorted(results, key=lambda r: r.get('_score', 0.0), reverse=True)[:5]
    return processed


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw 记忆优化器")
    subparsers = parser.add_subparsers(dest="command")

    # search 子命令
    p_search = subparsers.add_parser("search", help="搜索记忆")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--limit", type=int, default=5, help="返回数量（默认 5）")
    p_search.add_argument("--tier", default="all", choices=["all", "HOT", "WARM", "COLD"])

    # stats 子命令
    subparsers.add_parser("stats", help="查看记忆分级统计")

    # cleanup 子命令
    p_cleanup = subparsers.add_parser("cleanup", help="清理/归档冷记忆")
    p_cleanup.add_argument("--days", type=int, default=90, help="超过 N 天未访问的记忆（默认 90）")
    p_cleanup.add_argument("--dry-run", action="store_true", help="只预览，不执行")
    p_cleanup.add_argument("--force", action="store_true", help="跳过二次确认（删除超过阈值时）")

    # protect 子命令
    p_protect = subparsers.add_parser("protect", help="将记忆加入白名单保护（永不删除）")
    p_protect.add_argument("id", help="记忆 ID")

    # unprotect 子命令
    p_unprotect = subparsers.add_parser("unprotect", help="解除记忆的白名单保护")
    p_unprotect.add_argument("id", help="记忆 ID")

    # trash 子命令
    p_trash = subparsers.add_parser("trash", help="管理回收站")
    trash_sub = p_trash.add_subparsers(dest="trash_action")
    trash_sub.add_parser("list", help="列出回收站中的记忆")
    p_restore = trash_sub.add_parser("restore", help="从回收站恢复记忆")
    p_restore.add_argument("id", help="要恢复的记忆 ID")

    args = parser.parse_args()

    optimizer = MemoryOptimizer()
    optimizer.initialize()

    if args.command == "search":
        results = optimizer.search(args.query, limit=args.limit, tier=args.tier)
        print(f"🔍 搜索结果：{len(results)} 条")
        for r in results:
            print(f"  [{r.get('tier','?')}] {r.get('content','')[:80]}")

    elif args.command == "stats":
        stats = optimizer.get_stats()
        print(f"📊 统计：{stats}")

    elif args.command == "cleanup":
        result = optimizer.cleanup_old_memories(
            days=args.days, dry_run=args.dry_run, force=args.force
        )
        if result.get("requires_confirmation"):
            print(f"\n⚠️  {result['message']}")
            try:
                answer = input("输入 'yes' 确认删除，其他任意键取消：").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer == "yes":
                result = optimizer.cleanup_old_memories(days=args.days, dry_run=False, force=True)
                print(f"🧹 清理结果：{result}")
            else:
                print("❌ 已取消删除")
        else:
            print(f"🧹 清理结果：{result}")

    elif args.command == "protect":
        optimizer.protect_memory(args.id)

    elif args.command == "unprotect":
        optimizer.unprotect_memory(args.id)

    elif args.command == "trash":
        if args.trash_action == "list":
            items = optimizer.list_trash()
            if not items:
                print("🗑️  回收站为空")
            else:
                print(f"🗑️  回收站共 {len(items)} 条记忆：")
                for item in items:
                    print(
                        f"  ID={item.get('id')}  "
                        f"删除时间={item.get('_deleted_at','未知')}  "
                        f"内容={str(item.get('content',''))[:60]}"
                    )
        elif args.trash_action == "restore":
            optimizer.restore_from_trash(args.id)
        else:
            p_trash.print_help()

    else:
        parser.print_help()
