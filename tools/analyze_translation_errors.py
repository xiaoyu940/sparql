#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析翻译错误的具体原因 - BIND已实现的情况下
"""

print("=" * 80)
print("       翻译错误深度分析（BIND已实现）")
print("=" * 80)

errors = [
    {
        "test": "TestGeofDistance",
        "variable": "dist",
        "sparql_pattern": "BIND(geof:distance(?wkt1, ?wkt2) AS ?dist)",
        "sql_error": "Unmapped variable: dist",
        "likely_cause": "地理函数 geof:distance 生成SQL后，结果变量未正确映射"
    },
    {
        "test": "TestGeofDistanceWithVar", 
        "variable": "dist",
        "sparql_pattern": "BIND(geof:distance(...) AS ?dist)",
        "sql_error": "Unmapped variable: dist",
        "likely_cause": "同上，地理距离计算结果未映射"
    },
    {
        "test": "TestDateArithmetic",
        "variable": "yearsOfService",
        "sparql_pattern": "BIND(YEAR(NOW()) - YEAR(?hireDate) AS ?yearsOfService)",
        "sql_error": "Unmapped variable: yearsOfService",
        "likely_cause": "日期算术表达式结果未正确映射到SQL列"
    },
    {
        "test": "TestYearExtraction",
        "variable": "hireYear", 
        "sparql_pattern": "BIND(YEAR(?date) AS ?hireYear)",
        "sql_error": "Unmapped variable: hireYear",
        "likely_cause": "YEAR函数结果未映射"
    }
]

print("\n【具体错误分析】")
print("-" * 80)

for i, err in enumerate(errors, 1):
    print(f"\n{i}. {err['test']}")
    print(f"   变量: ?{err['variable']}")
    print(f"   SPARQL: {err['sparql_pattern']}")
    print(f"   错误: {err['sql_error']}")
    print(f"   可能原因: {err['likely_cause']}")

print("\n" + "=" * 80)
print("【根本原因推测】")
print("=" * 80)

print("""
既然BIND表达式已实现，问题可能是：

1. **特定函数不支持** 
   - geof:distance (地理函数)
   - YEAR() (日期函数)
   - 这些函数生成SQL后，结果未正确映射

2. **复杂表达式处理**
   - YEAR(NOW()) - YEAR(?hireDate) 这种复合表达式
   - 内层变量未展开或映射

3. **SQL生成阶段问题**
   - BIND生成了SQL，但SELECT子句未包含该列
   - 或列别名与变量名不匹配

4. **IR转换问题**
   - BIND表达式在IR阶段被优化掉了
   - 或变量在IR阶段丢失

【建议排查方向】
1. 检查 geof:distance 和 YEAR 函数的SQL生成
2. 验证BIND表达式是否正确生成SQL列
3. 检查IR中是否保留了BIND变量
4. 确认SELECT子句是否包含BIND结果
""")

print("=" * 80)
