#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单BIND测试 - 验证修复是否生效
"""

import psycopg2
import os

# 设置环境
os.environ['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + os.environ.get('PATH', '')

# 简单的BIND测试，不涉及属性路径
simple_sparql = '''
PREFIX ex: <http://example.org/>

SELECT ?emp ?double_salary
WHERE {
  ?emp a ex:Employee .
  ?emp ex:salary ?salary .
  BIND(?salary * 2 AS ?double_salary)
}
LIMIT 5
'''

print("=" * 60)
print("简单BIND测试（无属性路径）")
print("=" * 60)

try:
    print("\n连接数据库...")
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='rs_ontop_core',
        user='yuxiaoyu',
        password='123456'
    )
    print("✅ 连接成功")
    
    print("\nSPARQL查询:")
    print(simple_sparql)
    
    print("\n翻译SPARQL...")
    cur = conn.cursor()
    escaped = simple_sparql.replace("'", "''")
    cur.execute(f"SELECT ontop_translate('{escaped}');")
    sql = cur.fetchone()[0]
    print(f"✅ 生成的SQL:\n{sql}")
    
    print("\n执行查询...")
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"✅ 查询成功！返回 {len(rows)} 行")
    for row in rows[:3]:
        print(f"   {row}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    error_msg = str(e)
    print(f"\n❌ 失败: {error_msg}")
    if 'Unmapped variable' in error_msg:
        print("   → BIND修复未生效")
        # 提取变量名
        import re
        var_match = re.search(r'Unmapped variable: (\w+)', error_msg)
        if var_match:
            print(f"   → 未映射的变量: {var_match.group(1)}")
    elif 'Translation error' in error_msg:
        print("   → 翻译错误")
        
print("\n" + "=" * 60)
