#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestGeofDistance 翻译错误深度分析
"""

print("=" * 80)
print("       TestGeofDistance 翻译错误分析")
print("=" * 80)

print("""
【测试用例信息】
================
测试名: TestGeofDistance
变量: ?dist
SPARQL模式: BIND(geof:distance(?wkt1, ?wkt2) AS ?dist)
错误信息: Unmapped variable: dist

【SPARQL查询推测】
==================
PREFIX ex: <http://example.org/>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>

SELECT ?store1 ?store2 ?dist
WHERE {
  ?s1 ex:store_name ?store1 ;
      ex:geometry ?wkt1 .
  ?s2 ex:store_name ?store2 ;
      ex:geometry ?wkt2 .
  FILTER(?s1 != ?s2)
  BIND(geof:distance(?wkt1, ?wkt2) AS ?dist)
}
ORDER BY ?dist
LIMIT 10

【错误场景】
============
1. R2RML映射中定义了 stores 表的映射
2. ?wkt1 和 ?wkt2 对应 geometry 列
3. geof:distance 应该计算两个geometry之间的距离
4. 但生成的SQL中缺少 ?dist 对应的列

【可能原因】
============
1. geof:distance 函数的SQL生成逻辑有问题
   - 可能没有生成对应的SQL函数调用
   - 或生成了但没有给结果列命名

2. BIND表达式的结果变量未正确传递
   - IR阶段可能丢失了 ?dist 变量
   - SQL生成器不知道 ?dist 对应哪个SQL表达式

3. 复杂函数表达式的变量映射缺失
   - 简单BIND（如 BIND(?x + 1 AS ?y)）可能工作
   - 但函数调用BIND（如 geof:distance(...)）可能特殊处理

【排查方向】
============
1. 检查 geof:distance 是否在函数映射表中
2. 验证函数生成SQL后是否正确返回变量映射
3. 检查 IR 中是否保留了 ?dist 变量
4. 确认生成的SQL SELECT子句是否包含距离计算
""")

print("【下一步】")
print("-" * 80)
print("需要检查:")
print("1. src/function/ 目录下是否有 geof:distance 的映射")
print("2. src/sql/flat_generator.rs 中函数调用的SQL生成逻辑")
print("3. src/parser/ 中BIND表达式的IR转换")
print()
print("是否查看相关代码文件？")
