#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 ChromaDB 中的数据"""

import asyncio
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.initialize import chromadb

async def main():
    # 初始化 ChromaDB
    chromadb.init_chromadb()
    
    print("=" * 60)
    print("ChromaDB 数据检查")
    print("=" * 60)
    
    # 获取 collection
    collection = chromadb_core._get_or_create_collection()
    
    # 获取 collection 信息
    print(f"\n📊 Collection 名称: {collection.name}")
    print(f"📊 Collection 元数据: {collection.metadata}")
    
    # 获取所有数据
    print("\n正在查询所有数据...")
    results = collection.get(
        include=["documents", "metadatas", "embeddings"]
    )
    
    total_count = len(results['ids']) if results['ids'] else 0
    print(f"\n✅ 总记录数: {total_count}")
    
    if total_count > 0:
        print("\n" + "=" * 60)
        print("详细数据:")
        print("=" * 60)
        
        for i in range(total_count):
            print(f"\n[{i+1}] ID: {results['ids'][i]}")
            print(f"    内容: {results['documents'][i][:100]}...")
            
            metadata = results['metadatas'][i]
            print(f"    角色: {metadata.get('role')}")
            print(f"    用户ID: {metadata.get('user_id')}")
            print(f"    会话ID: {metadata.get('session_id', '')[:30]}...")
            print(f"    时间戳: {metadata.get('timestamp')}")
    else:
        print("\n⚠️ 数据库为空")
    
    # 按用户统计
    print("\n" + "=" * 60)
    print("按用户统计:")
    print("=" * 60)
    
    user_stats = {}
    if results['metadatas']:
        for metadata in results['metadatas']:
            user_id = metadata.get('user_id', 'unknown')
            user_stats[user_id] = user_stats.get(user_id, 0) + 1
    
    for user_id, count in user_stats.items():
        print(f"  用户 {user_id}: {count} 条消息")

if __name__ == "__main__":
    asyncio.run(main())
