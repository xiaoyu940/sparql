#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用psycopg2直接插入完整R2RML映射
"""

import psycopg2
from datetime import datetime

# 读取TTL文件
with open('/home/yuxiaoyu/rs_ontop_core/complete_mapping.ttl', 'r') as f:
    ttl_content = f.read()

print(f"TTL文件大小: {len(ttl_content)} 字符")

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port='5432',
    database='rs_ontop_core',
    user='yuxiaoyu',
    password='123456'
)

cur = conn.cursor()

# 清空现有映射
cur.execute("DELETE FROM ontop_r2rml_mappings;")
print("✅ 已清空现有映射")

# 插入完整映射
cur.execute(
    "INSERT INTO ontop_r2rml_mappings (name, ttl_content, created_at) VALUES (%s, %s, %s)",
    ('complete_mapping', ttl_content, datetime.now())
)

conn.commit()

# 验证
cur.execute("SELECT COUNT(*) FROM ontop_r2rml_mappings;")
count = cur.fetchone()[0]
cur.execute("SELECT LENGTH(ttl_content) FROM ontop_r2rml_mappings WHERE name = 'complete_mapping';")
size = cur.fetchone()[0]
print(f"✅ 插入完成: {count} 条映射, {size} 字符")

cur.close()
conn.close()

print("\n🎉 完整R2RML映射已插入数据库！")
print("请运行 SELECT ontop_refresh(); 刷新引擎后测试。")
