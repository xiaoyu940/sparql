#!/usr/bin/env python3
"""
调试脚本: 详细分析TestAskWithJoin生成的SQL
"""

import subprocess
import os

os.environ['PGPASSWORD'] = '123456'
os.environ['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + os.environ.get('PATH', '')

# TestAskWithJoin的SPARQL
sparql = """ASK { 
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> "Engineering" .
}"""

escaped = sparql.replace("'", "''")

# 获取生成的SQL
query = f"SELECT ontop_translate('{escaped}');"

print("=" * 80)
print("SPARQL查询:")
print(sparql)
print("=" * 80)

cmd = [
    'psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu',
    '-d', 'rs_ontop_core', '-t', '-A', '-c', query
]

result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)

print("\n生成的SQL:")
generated_sql = result.stdout.strip()
print(generated_sql)

# 基线SQL
baseline = """
SELECT EXISTS(
    SELECT 1 FROM employees e
    JOIN departments d ON e.department_id = d.department_id
    WHERE d.department_name = 'Engineering'
) AS result
"""

print("\n基线SQL:")
print(baseline)

# 执行对比
print("\n" + "=" * 80)
print("执行结果对比:")
print("=" * 80)

# 执行生成的SQL
exec_cmd = ['psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu',
            '-d', 'rs_ontop_core', '-t', '-A', '-c', generated_sql]
result1 = subprocess.run(exec_cmd, capture_output=True, text=True, env=os.environ)
print(f"\n生成的SQL结果: {result1.stdout.strip()}")

# 执行基线SQL
exec_cmd2 = ['psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu',
             '-d', 'rs_ontop_core', '-t', '-A', '-c', baseline]
result2 = subprocess.run(exec_cmd2, capture_output=True, text=True, env=os.environ)
print(f"基线SQL结果: {result2.stdout.strip()}")
