#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行BIND测试并捕获调试输出"""

import subprocess
import os
import sys

# 设置环境
env = os.environ.copy()
env['PGPASSWORD'] = '123456'

print("=== 运行TestGeofDistance测试 ===")
print("调试输出将显示BIND处理过程中的变量映射状态\n")

# 使用psql直接执行查询来触发调试输出
sparql = '''
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX ex: <http://example.org/>

SELECT ?store ?dist
WHERE {
  ?store a ex:Store .
  ?store ex:geometry ?geom .
  BIND(geof:distance(?geom, "POINT(116.4074 39.9042)"^^geo:wktLiteral) AS ?dist)
}
LIMIT 1
'''

# 调用ontop_query查看生成的SQL和调试输出
result = subprocess.run(
    ['psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu', 
     '-d', 'rs_ontop_core', '-c', 
     f"SELECT ontop_query('{sparql.replace(chr(39), chr(39)+chr(39))}', 'application/sparql-results+json');"],
    capture_output=True,
    text=True,
    env=env
)

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR (包含调试输出):")
    # 过滤出DEBUG行
    debug_lines = [line for line in result.stderr.split('\n') if '[DEBUG]' in line]
    for line in debug_lines[:50]:  # 只显示前50行
        print(line)
    
    if len(debug_lines) == 0:
        print("(未找到DEBUG输出)")
        print("完整stderr:", result.stderr[-500:])

print(f"\n返回码: {result.returncode}")
