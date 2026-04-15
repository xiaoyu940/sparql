#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查TestGeofDistance类结构"""

import sys
sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')

import importlib.util

spec = importlib.util.spec_from_file_location("geosparql_test", 
    "/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py")
module = importlib.util.module_from_spec(spec)
sys.modules["geosparql_test"] = module
spec.loader.exec_module(module)

print("TestGeofDistance 类的方法和属性:")
TestGeofDistance = getattr(module, 'TestGeofDistance')
for attr in dir(TestGeofDistance):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# 创建实例查看
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rs_ontop_core',
    'user': 'yuxiaoyu',
    'password': '123456'
}

test = TestGeofDistance(db_config)
print("\n实例的方法和属性:")
for attr in dir(test):
    if not attr.startswith('_'):
        print(f"  - {attr}")
