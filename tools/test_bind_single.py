#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接运行TestGeofDistance测试BIND修复"""

import sys
import os

# 添加路径
sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')

from framework import SparqlTestFramework, TestCaseBase, QueryResult

# 加载测试模块
import importlib.util

spec = importlib.util.spec_from_file_location("geosparql_test", 
    "/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py")
module = importlib.util.module_from_spec(spec)
sys.modules["geosparql_test"] = module
spec.loader.exec_module(module)

print("=" * 60)
print("运行 TestGeofDistance - BIND修复验证")
print("=" * 60)

# 创建测试实例
test_class = getattr(module, 'TestGeofDistance')
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rs_ontop_core',
    'user': 'yuxiaoyu',
    'password': '123456'
}

test = test_class(db_config)

try:
    print("\n执行SPARQL查询...")
    result = test.sparql_query()
    print(f"✅ SPARQL查询成功: {len(result.rows)} 行")
    
    print("\n执行基准SQL查询...")
    baseline = test.sql_query()
    print(f"✅ 基准SQL查询成功: {len(baseline.rows)} 行")
    
    print("\n比较结果...")
    if result.rows == baseline.rows:
        print("✅ 结果匹配！BIND修复生效")
    else:
        print(f"❌ 结果不匹配")
        print(f"SPARQL: {result.rows[:3] if result.rows else 'empty'}")
        print(f"SQL: {baseline.rows[:3] if baseline.rows else 'empty'}")
        
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
finally:
    test.close()

print("\n" + "=" * 60)
