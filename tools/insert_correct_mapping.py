#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入正确的R2RML映射到数据库
"""

import psycopg2
from datetime import datetime

# 读取正确的TTL文件
with open('/home/yuxiaoyu/rs_ontop_core/correct_mapping.ttl', 'r') as f:
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

# 确保表存在
cur.execute("""
CREATE TABLE IF NOT EXISTS ontop_r2rml_mappings (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    ttl_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# 清空现有映射
cur.execute("DELETE FROM ontop_r2rml_mappings;")
print("✅ 已清空现有映射")

# 插入正确映射
cur.execute(
    "INSERT INTO ontop_r2rml_mappings (name, ttl_content, created_at) VALUES (%s, %s, %s)",
    ('correct_mapping', ttl_content, datetime.now())
)

conn.commit()

# 验证
cur.execute("SELECT COUNT(*) FROM ontop_r2rml_mappings;")
count = cur.fetchone()[0]
cur.execute("SELECT LENGTH(ttl_content) FROM ontop_r2rml_mappings WHERE name = 'correct_mapping';")
size = cur.fetchone()[0]
print(f"✅ 插入完成: {count} 条映射, {size} 字符")

cur.close()
conn.close()

print("\n🎉 正确的R2RML映射已插入数据库！")
print("请运行 SELECT ontop_refresh(); 刷新引擎后测试。")
