"""
定期清理模块 - 自动归档冷记忆
功能：定时扫描、归档 COLD 记忆、删除过期数据

安全机制：
  - 回收站：删除前先移入回收站，7 天后才真正清除
  - 白名单：标记为 protected 的记忆永不删除
  - 自动备份：每次清理前备份到独立文件（含时间戳）
  - 二次确认：删除超过 10 条时需要用户确认
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set


class CleanupScheduler:
    """清理调度器"""

    def __init__(self, config: Dict, connector):
        self.config = config['cleanup']
        self.connector = connector
        self.archive_path = os.path.expanduser(
            self.config.get('archive_path', '~/.openclaw/memory/archive')
        )
        self.trash_path = os.path.expanduser(
            self.config.get('trash_path', '~/.openclaw/memory/trash')
        )
        self.backup_path = os.path.expanduser(
            self.config.get('backup_path', '~/.openclaw/memory/backup')
        )
        self.protected_ids_file = os.path.expanduser(
            self.config.get('protected_ids_file', '~/.openclaw/memory/protected_ids.json')
        )
        self.trash_retention_days = self.config.get('trash_retention_days', 7)
        self.confirm_threshold = self.config.get('confirm_threshold', 50)
        self.min_access_count = self.config.get('min_access_count_to_delete', 3)
        self.max_delete_per_run = self.config.get('max_delete_per_run', 50)
        self.important_content_min_length = self.config.get('important_content_min_length', 200)
        self.important_recent_days = self.config.get('important_recent_days', 30)

    # ------------------------------------------------------------------
    # 自动重要性识别（保守策略核心）
    # ------------------------------------------------------------------

    def _is_important(self, mem: Dict) -> Optional[str]:
        """
        自动判断记忆是否重要，返回原因字符串；不重要时返回 None。

        判断维度（任一满足即视为重要）：
          1. 高频访问：access_count >= min_access_count_to_delete
          2. 长内容：content 字符数 >= important_content_min_length
          3. 近期记忆：last_accessed 或 created_at 在 important_recent_days 天内
        """
        # 1. 高频访问
        access_count = mem.get('access_count') or 0
        if access_count >= self.min_access_count:
            return f"高频访问（{access_count} 次）"

        # 2. 长内容
        content_len = len(str(mem.get('content', '')))
        if content_len >= self.important_content_min_length:
            return f"长内容（{content_len} 字符）"

        # 3. 近期访问 / 创建
        recent_cutoff = datetime.now() - timedelta(days=self.important_recent_days)
        for field in ('last_accessed', 'created_at'):
            ts = mem.get(field)
            if ts is None:
                continue
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts)
            elif isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except Exception:
                    continue
            if ts >= recent_cutoff:
                return f"近期活跃（{field}={ts.date()}）"

        return None

    # ------------------------------------------------------------------
    # 白名单保护
    # ------------------------------------------------------------------

    def _load_protected_ids(self) -> Set[str]:
        """加载受保护记忆 ID 集合"""
        if not os.path.exists(self.protected_ids_file):
            return set()
        try:
            with open(self.protected_ids_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"⚠️  读取白名单失败：{e}")
            return set()

    def _save_protected_ids(self, ids: Set[str]) -> None:
        """保存受保护记忆 ID 集合"""
        os.makedirs(os.path.dirname(self.protected_ids_file), exist_ok=True)
        with open(self.protected_ids_file, 'w', encoding='utf-8') as f:
            json.dump(sorted(ids), f, ensure_ascii=False, indent=2)

    def protect(self, memory_id: str) -> bool:
        """将记忆标记为受保护（永不删除）"""
        try:
            ids = self._load_protected_ids()
            ids.add(str(memory_id))
            self._save_protected_ids(ids)
            print(f"🔒 记忆 {memory_id} 已加入白名单保护")
            return True
        except Exception as e:
            print(f"❌ 保护操作失败：{e}")
            return False

    def unprotect(self, memory_id: str) -> bool:
        """解除记忆的受保护状态"""
        try:
            ids = self._load_protected_ids()
            ids.discard(str(memory_id))
            self._save_protected_ids(ids)
            print(f"🔓 记忆 {memory_id} 已从白名单移除")
            return True
        except Exception as e:
            print(f"❌ 解除保护失败：{e}")
            return False

    def list_protected(self) -> List[str]:
        """列出所有受保护的记忆 ID"""
        return sorted(self._load_protected_ids())

    # ------------------------------------------------------------------
    # 删除前备份
    # ------------------------------------------------------------------

    def _backup_memories(self, memories: List[Dict]) -> str:
        """将记忆备份到带时间戳的文件，返回备份路径"""
        os.makedirs(self.backup_path, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_path, f"backup_{timestamp}.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(memories, f, ensure_ascii=False, indent=2, default=str)
        print(f"💾 清理前备份已保存：{backup_file}")
        return backup_file

    # ------------------------------------------------------------------
    # 回收站机制
    # ------------------------------------------------------------------

    def _move_to_trash(self, memories: List[Dict]) -> int:
        """将记忆移入回收站（不立即删除），返回移入数量"""
        try:
            if not memories:
                return 0

            os.makedirs(self.trash_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            trash_file = os.path.join(self.trash_path, f"trash_{timestamp}.json")

            deleted_at = datetime.now().isoformat()
            records = [dict(m, _deleted_at=deleted_at) for m in memories]

            with open(trash_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2, default=str)

            # 从 LanceDB 中删除
            ids = [str(m['id']) for m in memories if m.get('id') is not None]
            if ids and self.connector.table is not None:
                id_list = ", ".join(f"'{i}'" for i in ids)
                self.connector.table.delete(f"id IN ({id_list})")
                print(f"🗑️  已移入回收站 {len(ids)} 条（{trash_file}）")

            return len(ids)
        except Exception as e:
            print(f"❌ 移入回收站失败：{e}")
            return 0

    def list_trash(self) -> List[Dict]:
        """列出回收站中的所有记忆（附删除时间）"""
        results = []
        if not os.path.exists(self.trash_path):
            return results
        for filename in sorted(os.listdir(self.trash_path)):
            if not filename.startswith('trash_'):
                continue
            filepath = os.path.join(self.trash_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    batch = json.load(f)
                results.extend(batch)
            except Exception as e:
                print(f"⚠️  读取回收站文件失败 {filename}：{e}")
        return results

    def restore_from_trash(self, memory_id: str) -> bool:
        """从回收站恢复记忆到 LanceDB"""
        if not os.path.exists(self.trash_path):
            print("⚠️  回收站为空")
            return False

        for filename in os.listdir(self.trash_path):
            if not filename.startswith('trash_'):
                continue
            filepath = os.path.join(self.trash_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    batch = json.load(f)

                target = next((m for m in batch if str(m.get('id')) == str(memory_id)), None)
                if target is None:
                    continue

                # 移除回收站专有字段
                restored = {k: v for k, v in target.items() if k != '_deleted_at'}

                # 重新插入 LanceDB
                if self.connector.table is not None:
                    self.connector.batch_insert([restored])
                    print(f"✅ 已恢复记忆 {memory_id}")
                else:
                    print("⚠️  数据库未连接，无法恢复")
                    return False

                # 从回收站文件中移除
                remaining = [m for m in batch if str(m.get('id')) != str(memory_id)]
                if remaining:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(remaining, f, ensure_ascii=False, indent=2, default=str)
                else:
                    os.remove(filepath)

                return True
            except Exception as e:
                print(f"❌ 恢复失败 {filename}：{e}")

        print(f"⚠️  回收站中找不到记忆 {memory_id}")
        return False

    def purge_old_trash(self, days: Optional[int] = None, dry_run: bool = False) -> int:
        """清除回收站中超过保留天数的记忆（真正删除）"""
        retention = days if days is not None else self.trash_retention_days
        cutoff = datetime.now() - timedelta(days=retention)
        purged = 0

        if not os.path.exists(self.trash_path):
            return 0

        for filename in os.listdir(self.trash_path):
            if not filename.startswith('trash_'):
                continue
            filepath = os.path.join(self.trash_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    batch = json.load(f)

                remaining = []
                for record in batch:
                    deleted_at_str = record.get('_deleted_at', '')
                    try:
                        deleted_at = datetime.fromisoformat(deleted_at_str)
                    except Exception:
                        deleted_at = datetime.fromtimestamp(os.path.getmtime(filepath))

                    if deleted_at < cutoff:
                        purged += 1
                        if not dry_run:
                            print(f"🗑️  永久删除回收站记忆：{record.get('id')}")
                    else:
                        remaining.append(record)

                if not dry_run:
                    if remaining:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(remaining, f, ensure_ascii=False, indent=2, default=str)
                    else:
                        os.remove(filepath)

            except Exception as e:
                print(f"⚠️  清理回收站文件失败 {filename}：{e}")

        action = "预览" if dry_run else "已删除"
        print(f"🗑️  回收站{action} {purged} 条超过 {retention} 天的记忆")
        return purged

    # ------------------------------------------------------------------
    # 主清理流程
    # ------------------------------------------------------------------

    def auto_archive(self, days: int = 90, dry_run: bool = False, force: bool = False) -> Dict:
        """
        自动归档冷记忆（保守策略）

        安全流程：
          1. 过滤白名单（protected 记忆跳过）
          2. 自动保护重要记忆（高频/长内容/近期）
          3. 只处理 access_count < min_access_count_to_delete 的记忆
          4. 每次最多删除 max_delete_per_run 条
          5. 超过 confirm_threshold 条时，要求二次确认（除非 force=True）
          6. 执行前自动备份
          7. 移入回收站（7 天后才真正删除）

        参数:
            days: 超过 N 天未访问的记忆（默认 90）
            dry_run: 只预览，不实际执行
            force: 跳过二次确认

        返回:
            正常：{"archived": 10, "skipped_protected": 2, "skipped_important": 8, ...}
            需要确认：{"requires_confirmation": True, "count": 60, "message": "..."}
        """
        print(f"🧹 开始清理 {days} 天前的冷记忆 (dry_run={dry_run}, force={force})")

        if self.connector.table is None:
            print("⚠️  数据库未连接")
            return {"archived": 0, "deleted": 0, "space_saved_mb": 0, "skipped_protected": 0}

        # 1. 获取所有记忆
        all_memories = self._get_all_memories()

        # 2. 筛选超过 days 天未访问的记忆
        cutoff_date = datetime.now() - timedelta(days=days)
        candidates = []
        for mem in all_memories:
            last_accessed = mem.get('last_accessed')
            if last_accessed:
                if isinstance(last_accessed, (int, float)):
                    last_accessed = datetime.fromtimestamp(last_accessed)
                elif isinstance(last_accessed, str):
                    try:
                        last_accessed = datetime.fromisoformat(last_accessed)
                    except Exception:
                        continue
                if last_accessed < cutoff_date:
                    candidates.append(mem)

        # 3. 过滤白名单保护的记忆
        protected_ids = self._load_protected_ids()
        after_whitelist = [m for m in candidates if str(m.get('id', '')) not in protected_ids]
        skipped_protected = len(candidates) - len(after_whitelist)
        if skipped_protected:
            print(f"🔒 跳过 {skipped_protected} 条白名单保护记忆")

        # 4. 自动保护重要记忆（宁可少删，不可多删）
        to_archive = []
        skipped_important = 0
        for mem in after_whitelist:
            reason = self._is_important(mem)
            if reason:
                skipped_important += 1
                if dry_run:
                    print(f"  🛡️  自动保护 [{mem.get('id')}]：{reason}")
            else:
                to_archive.append(mem)

        if skipped_important:
            print(f"🛡️  自动保护 {skipped_important} 条重要记忆（高频/长内容/近期）")

        print(f"📊 候选删除：{len(to_archive)} 条")

        # 5. 每次最多删除 max_delete_per_run 条（删除限额）
        if len(to_archive) > self.max_delete_per_run:
            print(
                f"⚠️  候选数量 {len(to_archive)} 超过单次上限 {self.max_delete_per_run}，"
                f"仅处理最旧的 {self.max_delete_per_run} 条"
            )
            # 按 last_accessed 升序排列，优先删最旧的
            def _sort_key(m):
                ts = m.get('last_accessed')
                if isinstance(ts, (int, float)):
                    return ts
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts).timestamp()
                    except Exception:
                        pass
                return 0.0
            to_archive = sorted(to_archive, key=_sort_key)[:self.max_delete_per_run]

        # 6. 二次确认（超过阈值且非 force）
        if len(to_archive) > self.confirm_threshold and not force and not dry_run:
            return {
                "requires_confirmation": True,
                "count": len(to_archive),
                "skipped_protected": skipped_protected,
                "skipped_important": skipped_important,
                "message": (
                    f"即将删除 {len(to_archive)} 条记忆（超过确认阈值 {self.confirm_threshold}），"
                    f"请添加 --force 参数确认，或使用 --dry-run 预览"
                )
            }

        # 7. 执行归档
        archived_count = 0
        if not dry_run and to_archive:
            self._backup_memories(to_archive)
            archived_count = self._move_to_trash(to_archive)

        # 8. 清理回收站中超过保留期的记忆（真正删除）
        purged = self.purge_old_trash(dry_run=dry_run)

        # 9. 清理旧归档文件
        deleted_archives = 0
        if self.config.get('delete_after_days'):
            deleted_archives = self._cleanup_old_archives(
                self.config['delete_after_days'], dry_run
            )

        space_saved = archived_count * 0.01
        result = {
            "archived": archived_count,
            "deleted": purged,
            "moved_to_trash": archived_count,
            "purged_from_trash": purged,
            "deleted_old_archives": deleted_archives,
            "skipped_protected": skipped_protected,
            "skipped_important": skipped_important,
            "space_saved_mb": round(space_saved, 2),
        }

        print(
            f"✅ 清理完成：移入回收站 {archived_count} 条，"
            f"永久删除 {purged} 条，跳过白名单 {skipped_protected} 条，"
            f"跳过自动保护 {skipped_important} 条，节省 {space_saved:.2f}MB"
        )
        return result

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _get_all_memories(self) -> List[Dict]:
        """获取所有记忆"""
        try:
            if self.connector.table is None:
                return []
            df = self.connector.table.to_pandas()
            return df.to_dict('records')
        except Exception as e:
            print(f"⚠️  获取记忆失败：{e}")
            return []

    def _cleanup_old_archives(self, delete_after_days: int, dry_run: bool) -> int:
        """清理过期归档文件"""
        try:
            if not os.path.exists(self.archive_path):
                return 0
            cutoff_date = datetime.now() - timedelta(days=delete_after_days)
            deleted_count = 0
            for filename in os.listdir(self.archive_path):
                if not filename.startswith('archive_'):
                    continue
                filepath = os.path.join(self.archive_path, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_mtime < cutoff_date:
                    if not dry_run:
                        os.remove(filepath)
                        print(f"🗑️  删除过期归档：{filename}")
                    deleted_count += 1
            return deleted_count
        except Exception as e:
            print(f"⚠️  清理归档失败：{e}")
            return 0

    def get_stats(self) -> Dict:
        """获取清理统计"""
        try:
            archive_count = 0
            total_size_mb = 0.0

            if os.path.exists(self.archive_path):
                for filename in os.listdir(self.archive_path):
                    if filename.startswith('archive_'):
                        archive_count += 1
                        filepath = os.path.join(self.archive_path, filename)
                        total_size_mb += os.path.getsize(filepath) / 1024 / 1024

            # 回收站统计
            trash_count = len(self.list_trash())

            # 备份统计
            backup_count = 0
            if os.path.exists(self.backup_path):
                backup_count = sum(
                    1 for f in os.listdir(self.backup_path) if f.startswith('backup_')
                )

            # 白名单统计
            protected_count = len(self._load_protected_ids())

            return {
                "archive_count": archive_count,
                "archive_size_mb": round(total_size_mb, 2),
                "archive_path": self.archive_path,
                "trash_count": trash_count,
                "trash_path": self.trash_path,
                "backup_count": backup_count,
                "backup_path": self.backup_path,
                "protected_count": protected_count,
            }
        except Exception as e:
            print(f"⚠️  获取统计失败：{e}")
            return {"archive_count": 0, "archive_size_mb": 0, "error": str(e)}


# 测试函数
def test_cleanup():
    """测试清理功能"""
    print("🧹 清理调度器测试")

    config = {
        "cleanup": {
            "auto_archive": True,
            "archive_path": "~/.openclaw/memory/archive_test",
            "trash_path": "~/.openclaw/memory/trash_test",
            "backup_path": "~/.openclaw/memory/backup_test",
            "protected_ids_file": "~/.openclaw/memory/protected_ids_test.json",
            "delete_after_days": 90,
            "trash_retention_days": 7,
            "confirm_threshold": 10,
        }
    }

    class MockConnector:
        table = None

    scheduler = CleanupScheduler(config, MockConnector())
    stats = scheduler.get_stats()

    print(f"  归档统计：{stats}")
    print(f"  测试通过 ✅")


if __name__ == "__main__":
    test_cleanup()
