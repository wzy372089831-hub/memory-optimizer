# 记忆优化器 (Memory Optimizer)

OpenClaw 记忆优化技能 - 减少 90%+ Token 消耗

## 功能

- 🔧 **配置优化**: LanceDB 索引、缓存、批量操作
- 📊 **记忆分级**: HOT/WARM/COLD 三级管理
- 🔍 **智能搜索**: 向量 + 关键词 + 时间过滤
- ⚡ **按需加载**: 只加载最相关的 3-5 条
- 🧹 **定期清理**: 自动归档冷记忆
- 🛡️ **安全保障**: 回收站、白名单保护、自动备份

## 安全警告

> **数据安全提示**：清理操作会移动记忆到回收站并最终永久删除。
> 请在执行 `cleanup` 前确认以下事项：
>
> - 重要记忆已使用 `protect` 命令加入白名单
> - 如需预览清理范围，先使用 `--dry-run` 参数
> - 回收站中的记忆保留 **7 天**，7 天后将**永久删除**
> - 每次清理前系统会自动备份到 `~/.openclaw/memory/backup/`

## 安装

```bash
cd ~/AI/Claude/memory-optimizer
openclaw skill install .
```

## 使用

```bash
# 智能搜索
python3 -m src.memory_optimizer search "用户偏好" --limit 5

# 查看统计
python3 -m src.memory_optimizer stats

# 清理冷记忆（先预览）
python3 -m src.memory_optimizer cleanup --days 30 --dry-run

# 清理冷记忆（执行，超过 10 条会要求确认）
python3 -m src.memory_optimizer cleanup --days 30

# 清理冷记忆（跳过确认，直接执行）
python3 -m src.memory_optimizer cleanup --days 30 --force

# 保护记忆（加入白名单）
python3 -m src.memory_optimizer protect <memory-id>

# 解除保护
python3 -m src.memory_optimizer unprotect <memory-id>

# 查看回收站
python3 -m src.memory_optimizer trash list

# 从回收站恢复
python3 -m src.memory_optimizer trash restore <memory-id>
```

## 数据保护指南

### 如何保护重要记忆

使用 `protect` 命令将关键记忆加入白名单，白名单中的记忆**永远不会被自动清理**：

```bash
# 保护某条记忆
python3 -m src.memory_optimizer protect <memory-id>

# 解除保护
python3 -m src.memory_optimizer unprotect <memory-id>
```

### 回收站操作

删除的记忆会先进入回收站，在 7 天内可以随时恢复：

```bash
# 查看回收站内容
python3 -m src.memory_optimizer trash list

# 恢复某条记忆
python3 -m src.memory_optimizer trash restore <memory-id>
```

### 备份与恢复

每次 `cleanup` 执行前，系统自动将待删除记忆备份到：

```
~/.openclaw/memory/backup/backup_YYYYMMDD_HHMMSS.json
```

手动恢复备份（示例）：

```bash
# 查看备份文件列表
ls ~/.openclaw/memory/backup/

# 查看备份内容
cat ~/.openclaw/memory/backup/backup_20260309_030000.json

# 手动将备份数据重新导入（需要自定义脚本或直接使用 LanceDB API）
```

### 推荐工作流

```
1. 定期运行 cleanup --dry-run  →  确认清理范围
2. 对重要记忆运行 protect       →  加入白名单
3. 运行 cleanup                 →  安全清理
4. 如误删，运行 trash restore   →  7 天内可恢复
```

## 存储路径说明

| 路径 | 用途 | 保留策略 |
|------|------|----------|
| `~/.openclaw/memory/lancedb/` | 主数据库 | 永久 |
| `~/.openclaw/memory/trash/` | 回收站 | 7 天后永久删除 |
| `~/.openclaw/memory/backup/` | 清理前备份 | 手动管理 |
| `~/.openclaw/memory/archive/` | 旧版归档 | 90 天后删除 |
| `~/.openclaw/memory/protected_ids.json` | 白名单 | 永久 |

## 预期效果

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| Token 消耗 | 5000-50000/次 | 500-5000/次 | -80-95% |
| 搜索延迟 | 100-500ms | 10-50ms | 10x |
| 存储空间 | 1-10GB | 0.1-1GB | -90% |

## 开发进度

- [x] 项目初始化 (3/9)
- [x] LanceDB 连接
- [x] 记忆分级实现
- [x] 智能搜索实现
- [x] 清理功能实现
- [x] 数据安全保障（回收站、白名单、备份、二次确认）
- [x] 测试 (3/3 通过)
- [x] 发布

## 作者

超人

## 许可

MIT
