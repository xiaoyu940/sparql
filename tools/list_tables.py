#!/usr/bin/env python3
"""
列出数据库中的所有表
"""

import subprocess
import os

os.environ['PGPASSWORD'] = '123456'

query = """
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
"""

cmd = [
    'psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu',
    '-d', 'rs_ontop_core', '-c', query
]

result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)

print("数据库中的表:")
print("=" * 60)
print(result.stdout)

if result.stderr:
    print("错误:", result.stderr)
