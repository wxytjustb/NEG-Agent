# ChromaDB 短期记忆模块

## 功能概述

基于 ChromaDB 向量数据库的短期记忆管理模块，用于存储和检索用户的对话历史。

### 核心功能

1. **添加消息** - 将对话消息向量化并存储
2. **语义搜索** - 基于相似度检索相关记忆
3. **获取历史** - 获取指定会话的所有消息
4. **删除记忆** - 清理指定会话的记忆数据
5. **统计计数** - 统计会话消息数量

### 关键特性

- ✅ **自动向量化** - ChromaDB 自动生成 embedding 向量
- ✅ **元数据过滤** - 支持按 `user_id` 和 `session_id` 过滤
- ✅ **语义检索** - 基于语义相似度而非关键词匹配
- ✅ **会话隔离** - 不同会话的记忆完全隔离

## 使用方法

### 1. 导入模块

```python
from app.modules.chromadb.core.chromadb_core import chromadb_core
```

### 2. 添加对话消息

```python
# 存储用户消息
message_id = chromadb_core.add_message(
    user_id="user_123",
    session_id="session_456",
    role="user",
    content="Python 有哪些数据类型？"
)

# 存储助手回复
chromadb_core.add_message(
    user_id="user_123",
    session_id="session_456",
    role="assistant",
    content="Python 的主要数据类型包括：int、float、str、list、dict 等"
)
```

### 3. 语义搜索记忆

```python
# 搜索相关记忆
results = chromadb_core.search_memory(
    user_id="user_123",
    session_id="session_456",
    query_text="Python 的基本类型",
    n_results=5  # 返回前5条最相似的结果
)

for result in results:
    print(f"相似度: {result['distance']}")
    print(f"内容: {result['content']}")
    print(f"角色: {result['role']}")
```

### 4. 获取所有消息

```python
# 获取会话的所有消息（按时间排序）
messages = chromadb_core.get_all_messages(
    user_id="user_123",
    session_id="session_456",
    limit=10  # 可选：限制返回数量
)

for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

### 5. 统计消息数量

```python
count = chromadb_core.count_messages(
    user_id="user_123",
    session_id="session_456"
)
print(f"当前会话有 {count} 条消息")
```

### 6. 删除会话记忆

```python
deleted_count = chromadb_core.delete_session_memory(
    user_id="user_123",
    session_id="session_456"
)
print(f"已删除 {deleted_count} 条记忆")
```

## API 接口集成示例

### 在 Agent Service 中使用

```python
from app.modules.chromadb.core.chromadb_core import chromadb_core

class AgentService:
    async def chat(self, user_id: str, session_token: str, message: str):
        # 1. 保存用户消息
        chromadb_core.add_message(
            user_id=user_id,
            session_id=session_token,
            role="user",
            content=message
        )
        
        # 2. 搜索相关记忆（可选 - 用于增强上下文）
        relevant_memories = chromadb_core.search_memory(
            user_id=user_id,
            session_id=session_token,
            query_text=message,
            n_results=3
        )
        
        # 3. 调用 LLM 生成回复
        response = await self.llm.chat(message, context=relevant_memories)
        
        # 4. 保存助手回复
        chromadb_core.add_message(
            user_id=user_id,
            session_id=session_token,
            role="assistant",
            content=response
        )
        
        return response
```

## 数据结构

### 消息记录格式

```python
{
    "id": "user_123_session_456_1703001234567",
    "content": "消息内容",
    "role": "user",  # 或 "assistant"
    "timestamp": "2024-12-22T10:30:00.123456",
    "user_id": "user_123",
    "session_id": "session_456"
}
```

### 搜索结果格式

```python
{
    "id": "消息ID",
    "content": "消息内容",
    "role": "user",
    "timestamp": "2024-12-22T10:30:00",
    "distance": 0.123,  # 越小越相似
    "user_id": "user_123",
    "session_id": "session_456"
}
```

## 测试

运行测试文件：

```bash
cd backend
python tests/test_chromadb_memory.py
```

测试内容包括：
- ✅ 添加多条对话消息
- ✅ 语义搜索测试
- ✅ 获取所有消息
- ✅ 会话隔离性测试
- ✅ 删除记忆测试

## 注意事项

1. **向量生成** - ChromaDB 使用默认的 embedding function 自动生成向量
2. **性能优化** - 对于大量数据，建议定期清理过期会话
3. **元数据索引** - `user_id` 和 `session_id` 已自动建立索引
4. **相似度阈值** - `distance` 值越小表示越相似，通常 < 0.3 表示高度相关

## 配置项

在 `.env` 文件中配置：

```bash
# ChromaDB 配置
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_USE_HTTP=true
```

## 集合管理

- **集合名称**: `short_term_memory`
- **自动创建**: 首次使用时自动创建集合
- **持久化**: 数据持久化存储在 ChromaDB 中
