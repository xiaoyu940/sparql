#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os

env = os.environ.copy()
env['PGPASSWORD'] = '123456'

def run_sql(sql):
    cmd = ['bash', '-c', f"export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c \"{sql}\""]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout

print("=== 查找所有备份表 ===")
backup_tables = run_sql("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND (table_name LIKE '%backup%' OR table_name LIKE '%ontop_mappings%')
    ORDER BY table_name;
""")
print(backup_tables)

print("\n=== 查找所有相关表 ===")
all_tables = run_sql("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")
print(all_tables)

print("\n=== 检查ontop_mappings_backup表 ===")
backup_data = run_sql("SELECT COUNT(*) FROM ontop_mappings_backup;")
print(f"记录数: {backup_data}")

if "0" not in backup_data:
    print("\n=== 原ontop_mappings备份数据 ===")
    data = run_sql("SELECT * FROM ontop_mappings_backup LIMIT 20;")
    print(data)
