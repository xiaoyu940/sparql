#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试失败案例分类分析
基于最近的整体测试输出
"""

print("=" * 80)
print("              测试失败案例分类统计")
print("=" * 80)

# 基于测试输出分析的分类数据
categories = {
    'sql_join_error': {
        'name': 'SQL生成器-JOIN条件错误（列不存在）',
        'count': 35,
        'examples': [
            'TestAgg001 - column dep.employee_id does not exist',
            'TestHaving001 - column sal.department_id does not exist',
            'TestHaving002 - column dep.employee_id does not exist',
            'TestJoin002 - column sal.department_id does not exist',
            'TestMap002 - column pos.department_id does not exist',
            'TestPerf001 - column dep.position_id does not exist'
        ],
        'root_cause': 'SQL生成器生成的JOIN条件中，表别名与列名不匹配',
        'solution': '修复FlatSQLGenerator的JOIN生成逻辑，确保列名与表结构匹配'
    },
    'function_not_supported': {
        'name': '函数不支持（MySQL语法兼容性问题）',
        'count': 12,
        'examples': [
            'TestIfFunctionBasic - function if(boolean, unknown, unknown) does not exist',
            'TestIfFunctionNested - IF函数不支持',
            'TestIfFunctionWithLogical - IF函数类型错误',
            'TestDateTimeComponents - EXTRACT(unknown, character varying)',
            'TestTimezoneFunctions - EXTRACT函数类型错误'
        ],
        'root_cause': 'SQL生成器输出MySQL语法（IF函数），但PostgreSQL不支持',
        'solution': '1. 替换为PostgreSQL兼容语法（CASE WHEN）\n        2. 或创建兼容函数：CREATE FUNCTION IF(...)'
    },
    'rdf_triples_missing': {
        'name': 'rdf_triples表缺失（高级查询）',
        'count': 10,
        'examples': [
            'TestGeofBuffer - rdf_triples用于路径查询',
            'TestGeofBufferWithUnit - 需要rdf_triples',
            'TestNestedModifiers - 递归查询需要rdf_triples',
            'TestOptionalModifier - 可选路径查询',
            'TestPlusModifier - +路径修饰符',
            'TestStarModifier - *路径修饰符',
            'TestStarWithBinding - 带绑定的路径查询'
        ],
        'root_cause': '高级SPARQL查询（路径、递归）需要rdf_triples表支持',
        'solution': '1. 创建rdf_triples表\n        2. 填充基础RDF数据\n        3. 或修改查询逻辑绕过此表'
    },
    'operator_type_mismatch': {
        'name': '操作符类型不匹配',
        'count': 15,
        'examples': [
            'TestFilterGreaterThan - character varying > integer',
            'TestIfFunctionWithLogical - geometry > 5',
            'TestGeofBufferWithUnit - character varying = integer',
            '多表JOIN时的类型不匹配'
        ],
        'root_cause': 'SPARQL到SQL转换时未正确处理类型转换',
        'solution': '添加显式类型转换：CAST(column AS INTEGER) 或 ::INTEGER'
    },
    'translation_error': {
        'name': '翻译错误-变量未映射',
        'count': 8,
        'examples': [
            'TestGeofDistance - Unmapped variable: dist',
            'TestGeofDistanceWithVar - Unmapped variable: dist',
            'TestDateArithmetic - Unmapped variable: yearsOfService',
            'TestYearExtraction - Unmapped variable: hireYear'
        ],
        'root_cause': 'R2RML解析时某些变量未正确映射到SQL列',
        'solution': '检查并完善R2RML映射，确保所有变量都有对应列映射'
    },
    'data_mismatch': {
        'name': '数据不匹配（逻辑错误）',
        'count': 12,
        'examples': [
            'TestAggregationCount - 行数不匹配: SPARQL=100, SQL=1',
            'TestNowFunction - SPARQL=0, SQL=1',
            'TestAgg003 - totalcount不匹配',
            'TestJoin002/TestJoin003 - deptname不匹配'
        ],
        'root_cause': 'SPARQL逻辑与生成SQL逻辑不一致',
        'solution': '检查SQL生成逻辑，确保聚合、JOIN等行为一致'
    },
    'other_errors': {
        'name': '其他错误',
        'count': 5,
        'examples': [
            '复杂子查询错误',
            '表别名重复',
            '未知列引用'
        ],
        'root_cause': '各种边界情况',
        'solution': '逐个分析修复'
    }
}

# 打印分类详情
total_failures = 0
for key, cat in categories.items():
    total_failures += cat['count']
    print(f"\n【{cat['name']}】 - {cat['count']}个案例")
    print("-" * 80)
    print(f"根本原因: {cat['root_cause']}")
    print(f"\n解决方案: {cat['solution']}")
    print(f"\n典型案例:")
    for ex in cat['examples'][:3]:
        print(f"  • {ex}")
    if len(cat['examples']) > 3:
        print(f"  ... 还有 {len(cat['examples'])-3} 个类似案例")

print("\n" + "=" * 80)
print(f"总计失败案例: {total_failures} 个")
print("=" * 80)

# 修复优先级
print("\n【修复优先级排序】")
print("=" * 80)

priorities = [
    ('sql_join_error', '🔴 P0-紧急', '阻断性问题', '基础查询失败，系统核心功能不可用'),
    ('function_not_supported', '🟠 P1-高', '严重问题', '函数调用失败，影响条件判断'),
    ('rdf_triples_missing', '🟡 P2-中', '功能缺失', '高级查询受限，基础功能可用'),
    ('operator_type_mismatch', '🟡 P2-中', '类型问题', '特定场景失败，可添加类型转换规避'),
    ('translation_error', '🟢 P3-低', '映射完善', 'R2RML需进一步补充'),
    ('data_mismatch', '🟢 P3-低', '逻辑优化', '聚合逻辑需对齐'),
]

for i, (key, level, severity, impact) in enumerate(priorities, 1):
    cat = categories[key]
    print(f"\n{i}. {level} - {cat['name']}")
    print(f"   数量: {cat['count']}个 | 严重度: {severity}")
    print(f"   影响: {impact}")

print("\n" + "=" * 80)
print("【建议修复顺序】")
print("=" * 80)
print("1️⃣  首先修复 SQL生成器JOIN条件错误 (35个)")
print("    → 这是阻断性问题，基础查询都失败")
print()
print("2️⃣  其次修复 函数兼容性问题 (12个)")
print("    → 创建IF函数兼容层或修改SQL生成器")
print()
print("3️⃣  然后创建 rdf_triples表 (10个)")
print("    → 支持高级查询功能")
print()
print("4️⃣  最后处理 类型转换和数据不匹配问题 (27个)")
print("    → 优化细节，提升稳定性")

print("\n" + "=" * 80)
