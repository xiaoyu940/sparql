#!/usr/bin/env python3

import subprocess
import os

env = os.environ.copy()
env['PGPASSWORD'] = '123456'

# 检查R2RML映射数量和大小
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT id, name, LENGTH(ttl_content) as size FROM ontop_r2rml_mappings ORDER BY id;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print("=== R2RML映射概况 ===")
print(result.stdout)

# 获取第一个映射的完整内容
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT ttl_content FROM ontop_r2rml_mappings LIMIT 1;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print("\n=== R2RML映射内容详情 ===")
print(result.stdout)

# 检查ontop_mappings表是否还存在
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT COUNT(*) FROM ontop_mappings;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print("\n=== ontop_mappings表记录数 ===")
print(result.stdout)

# 检查是否有备份表
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT table_name FROM information_schema.tables WHERE table_schema = '\''public'\'' AND (table_name LIKE '%ontop%' OR table_name LIKE '%rdf%' OR table_name LIKE '%mapping%') ORDER BY table_name;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print("\n=== 相关表列表 ===")
print(result.stdout)
