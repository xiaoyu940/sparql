#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接运行BIND相关测试"""

import sys
import os

# 添加路径
sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')

# 加载测试模块
import importlib.util

# 加载 geosparql 测试
spec = importlib.util.spec_from_file_location("geosparql_test", 
    "/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py")
module = importlib.util.module_from_spec(spec)
sys.modules["geosparql_test"] = module

print("加载 test_sprint9_p1_geosparql_metric_001.py...")
try:
    spec.loader.exec_module(module)
    print(f"✅ 模块加载成功")
    
    # 查找测试类
    test_classes = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and attr.__name__.startswith('Test'):
            test_classes.append(attr.__name__)
    
    print(f"发现测试类: {test_classes}")
    
except Exception as e:
    print(f"❌ 模块加载失败: {e}")
    import traceback
    traceback.print_exc()

print("\n准备运行 TestGeofDistance...")
