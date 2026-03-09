# 记忆优化器 API 文档

**版本**: 0.1.0  
**更新**: 2026-03-09

---

## 📦 模块结构

```
src/
├── memory_optimizer.py    # 主入口类
├── lancedb_connector.py   # LanceDB 连接器
├── memory_tiering.py      # 记忆分级模块
├── smart_search.py        # 智能搜索模块
└── cleanup_scheduler.py   # 清理调度模块
```

---

## 🔧 MemoryOptimizer 主类

### 初始化

```python
from memory_optimizer import MemoryOptimizer

optimizer = MemoryOptimizer(config_path="config.json")
optimizer.initialize()
```

### 方法

#### `initialize()`

初始化所有子模块（连接器、分级、搜索、清理）。

```python
optimizer.initialize()
# 输出：✅ 所有模块已初始化
```

#### `search(query, limit=5, tier="all")`

智能搜索记忆。

**参数**:
- `query` (str): 搜索关键词
- `limit` (int): 返回数量限制，默认 5
- `tier` (str): 记忆层级过滤，可选 "HOT"|"WARM"|"COLD"|"all"

**返回**: `List[Dict]` - 搜索结果列表

**示例**:
```python
results = optimizer.search("用户偏好", limit=5)
for r in results:
    print(f"ID: {r['id']}, Score: {r['_score']:.2f}")
```

#### `get_stats()`

获取记忆分级统计。

**返回**: `Dict` - 统计信息

**示例**:
```python
stats = optimizer.get_stats()
# 返回：{"hot": 10, "warm": 50, "cold": 100, "total": 160, "db_size_mb": 5.2}
```

#### `cleanup_old_memories(days=30, dry_run=False)`

清理/归档冷记忆。

**参数**:
- `days` (int): 超过 N 天未访问的记忆，默认 30
- `dry_run` (bool): 只预览不执行，默认 False

**返回**: `Dict` - 清理结果

**示例**:
```python
# 预览
result = optimizer.cleanup_old_memories(days=30, dry_run=True)
print(f"将归档 {result['archived']} 条记忆")

# 执行
result = optimizer.cleanup_old_memories(days=30)
print(f"已归档 {result['archived']} 条记忆")
```

---

## 🔌 LanceDBConnector 类

### 初始化

```python
from lancedb_connector import LanceDBConnector

connector = LanceDBConnector(config)
```

### 方法

#### `connect()`

连接到 LanceDB 数据库。

#### `create_table(table_name="memories")`

创建记忆表（带向量索引）。

#### `batch_insert(records)`

批量插入记忆记录。

#### `search(query_vector, limit=5)`

向量搜索。

#### `get_stats()`

获取数据库统计。

---

## 📊 MemoryTiering 类

### 初始化

```python
from memory_tiering import MemoryTiering

tiering = MemoryTiering(config)
```

### 方法

#### `classify(memory) -> str`

分类单条记忆（返回 "HOT"|"WARM"|"COLD"）。

#### `auto_classify_batch(memories) -> Dict`

批量自动分类。

**返回**: `{"HOT": 10, "WARM": 50, "COLD": 100}`

#### `promote(memory, new_tier="HOT")`

升级记忆到指定层级。

---

## 🔍 SmartSearch 类

### 初始化

```python
from smart_search import SmartSearch

searcher = SmartSearch(config, connector)
```

### 方法

#### `search(query, query_vector=None, limit=5, ...)`

混合搜索（向量 + 关键词 + 时间）。

---

## 🧹 CleanupScheduler 类

### 初始化

```python
from cleanup_scheduler import CleanupScheduler

scheduler = CleanupScheduler(config, connector)
```

### 方法

#### `auto_archive(days=30, dry_run=False)`

自动归档冷记忆。

#### `get_stats()`

获取归档统计。

---

## 🪝 Hook 函数

### `on_write(memory_data)`

记忆写入时的优化钩子。

### `on_read(query, results)`

记忆读取时的优化钩子。

---

## 📝 完整示例

```python
from memory_optimizer import MemoryOptimizer

# 1. 初始化
optimizer = MemoryOptimizer('config.json')
optimizer.initialize()

# 2. 搜索
results = optimizer.search("Python 编程", limit=5)

# 3. 查看统计
stats = optimizer.get_stats()
print(f"记忆分布：HOT={stats['hot']}, WARM={stats['warm']}, COLD={stats['cold']}")

# 4. 清理
result = optimizer.cleanup_old_memories(days=30, dry_run=True)
print(f"将归档 {result['archived']} 条记忆")
```

---

## ⚙️ 配置格式

```json
{
  "lancedb": {
    "path": "~/.openclaw/memory/lancedb",
    "index_type": "IVF_PQ",
    "cache_size_mb": 1024
  },
  "tiering": {
    "hot_threshold_hours": 24,
    "warm_threshold_days": 7,
    "hot_max_count": 50,
    "warm_max_count": 500
  },
  "search": {
    "default_limit": 5,
    "max_limit": 20,
    "min_relevance_score": 0.6,
    "hybrid_search": true
  },
  "cleanup": {
    "auto_archive": true,
    "archive_path": "~/.openclaw/memory/archive",
    "delete_after_days": 90
  }
}
```

---

*完整文档，如有遗漏请提 Issue*
