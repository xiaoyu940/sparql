#!/usr/bin/env python3
"""
调试脚本: TestAskWithJoin 问题分析
"""

import subprocess
import os

# 设置环境变量
os.environ['PGPASSWORD'] = '123456'
os.environ['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + os.environ.get('PATH', '')

sparql = """ASK { 
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> "Engineering" .
}"""

escaped = sparql.replace("'", "''")

query = f"""
SELECT ontop_translate('{escaped}');
"""

print("=" * 80)
print("SPARQL查询:")
print(sparql)
print("=" * 80)
print("\n调用ontop_translate...")

cmd = [
    'psql',
    '-h', 'localhost',
    '-p', '5432',
    '-U', 'yuxiaoyu',
    '-d', 'rs_ontop_core',
    '-t', '-A',
    '-c', query
]

result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)

print(f"\n返回码: {result.returncode}")
print(f"\n生成的SQL:")
print(result.stdout)

if result.stderr:
    print(f"\n错误输出:")
    print(result.stderr)
