#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清空 ChromaDB 数据"""

from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.initialize import chromadb

# 初始化 ChromaDB
chromadb.init_chromadb()

# 获取 collection
collection = chromadb_core._get_or_create_collection()

# 获取所有数据的 ID
results = collection.get(include=[])

if results['ids']:
    count = len(results['ids'])
    print(f"正在删除 {count} 条记录...")
    
    # 删除所有数据
    collection.delete(ids=results['ids'])
    
    print(f"✅ 已删除 {count} 条记录")
else:
    print("⚠️ 数据库已经是空的")

# 验证
verify_results = collection.get(include=[])
final_count = len(verify_results['ids']) if verify_results['ids'] else 0
print(f"\n✅ 当前记录数: {final_count}")
