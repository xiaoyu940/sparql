#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证BIND修复是否生效"""

import subprocess
import sys
import os

sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')

from framework import SparqlTestFramework

# 加载测试模块
import importlib.util

spec = importlib.util.spec_from_file_location("geosparql_test", 
    "/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py")
module = importlib.util.module_from_spec(spec)
sys.modules["geosparql_test"] = module
spec.loader.exec_module(module)

print("=" * 60)
print("BIND修复验证 - TestGeofDistance")
print("=" * 60)

TestGeofDistance = getattr(module, 'TestGeofDistance')

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rs_ontop_core',
    'user': 'yuxiaoyu',
    'password': '123456'
}

test = TestGeofDistance(db_config)

try:
    print("\n运行测试...")
    result = test.run()
    
    if result is True:
        print("✅ TestGeofDistance: 通过！BIND修复生效！")
    elif result is False:
        print("❌ TestGeofDistance: 失败")
    else:
        print(f"⚠️  测试返回: {result}")
        
except Exception as e:
    error_msg = str(e)
    if 'Unmapped variable' in error_msg:
        print(f"❌ BIND修复未生效: {error_msg[:100]}")
    elif 'Translation error' in error_msg:
        print(f"❌ 翻译错误: {error_msg[:100]}")
    else:
        print(f"❌ 测试异常: {error_msg[:150]}")
    import traceback
    traceback.print_exc()
finally:
    test.close()

print("\n" + "=" * 60)
