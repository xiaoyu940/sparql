#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析测试失败原因并分类
"""

import re

# 读取测试输出
with open('/home/yuxiaoyu/rs_ontop_core/tests/python/test_output.txt', 'r') as f:
    content = f.read()

# 提取每个测试案例及其错误
pattern = r'\[(\d+/\d+)\]\s+(\w+)\s+-+\s*(.*?)(?=\[\d+/\d+\]|$)'
matches = re.findall(pattern, content, re.DOTALL)

# 分类存储
categories = {
    'sql_generator_join_error': {
        'name': 'SQL生成器-JOIN条件错误',
        'patterns': ['column.*does not exist', 'Perhaps you meant'],
        'tests': [],
        'count': 0
    },
    'rdf_triples_missing': {
        'name': 'rdf_triples表缺失',
        'patterns': ['rdf_triples.*does not exist'],
        'tests': [],
        'count': 0
    },
    'function_not_supported': {
        'name': '函数不支持（MySQL语法）',
        'patterns': ['function.*does not exist', 'IF.*boolean'],
        'tests': [],
        'count': 0
    },
    'operator_type_mismatch': {
        'name': '操作符类型不匹配',
        'patterns': ['operator does not exist', 'types.*cannot be matched'],
        'tests': [],
        'count': 0
    },
    'translation_error': {
        'name': '翻译错误-变量未映射',
        'patterns': ['Translation error', 'Unmapped variable'],
        'tests': [],
        'count': 0
    },
    'data_mismatch': {
        'name': '数据不匹配',
        'patterns': ['数据不匹配', '行数不匹配'],
        'tests': [],
        'count': 0
    },
    'other_error': {
        'name': '其他错误',
        'patterns': [],
        'tests': [],
        'count': 0
    }
}

# 分类每个测试
for match in matches:
    test_num, test_name, test_detail = match
    test_detail_str = str(test_detail)
    
    categorized = False
    for cat_key, cat_info in categories.items():
        if cat_key == 'other_error':
            continue
        for pattern in cat_info['patterns']:
            if re.search(pattern, test_detail_str, re.IGNORECASE):
                cat_info['tests'].append({
                    'num': test_num,
                    'name': test_name,
                    'detail': test_detail_str[:200]  # 截取前200字符
                })
                cat_info['count'] += 1
                categorized = True
                break
        if categorized:
            break
    
    if not categorized and ('✗' in test_detail_str or '失败' in test_detail_str or '异常' in test_detail_str):
        categories['other_error']['tests'].append({
            'num': test_num,
            'name': test_name,
            'detail': test_detail_str[:200]
        })
        categories['other_error']['count'] += 1

# 输出分类结果
print("=" * 80)
print("              测试失败案例分类统计")
print("=" * 80)

total_failures = 0
for cat_key, cat_info in categories.items():
    if cat_info['count'] > 0:
        total_failures += cat_info['count']
        print(f"\n【{cat_info['name']}】 - {cat_info['count']}个案例")
        print("-" * 80)
        for test in cat_info['tests'][:5]:  # 只显示前5个示例
            print(f"  • {test['name']}")
            # 提取关键错误信息
            if 'column' in test['detail'] and 'does not exist' in test['detail']:
                col_match = re.search(r'column "?([^"]+)"? does not exist', test['detail'])
                if col_match:
                    print(f"    错误: 列 '{col_match.group(1)}' 不存在")
            elif 'rdf_triples' in test['detail']:
                print(f"    错误: 需要rdf_triples表支持递归/路径查询")
            elif 'function' in test['detail']:
                func_match = re.search(r'function ([^\(]+)', test['detail'])
                if func_match:
                    print(f"    错误: 函数 '{func_match.group(1)}' 不存在")
            elif 'operator' in test['detail']:
                print(f"    错误: 操作符类型不匹配")
            elif 'Translation' in test['detail']:
                var_match = re.search(r'Unmapped variable: (\w+)', test['detail'])
                if var_match:
                    print(f"    错误: 变量 '{var_match.group(1)}' 未映射")
            else:
                error_line = test['detail'].split('\n')[0][:60]
                print(f"    错误: {error_line}...")
        
        if cat_info['count'] > 5:
            print(f"    ... 还有 {cat_info['count']-5} 个类似案例")

print("\n" + "=" * 80)
print(f"总计失败案例: {total_failures} 个")
print("=" * 80)

# 按修复优先级排序
print("\n【修复优先级建议】")
print("-" * 80)
print("1️⃣  高优先级 - SQL生成器JOIN条件错误 (~35个)")
print("    原因: 生成的SQL中表别名与列名不匹配")
print("    影响: 基础查询都失败，系统基本不可用")
print("    方案: 修复FlatSQLGenerator的JOIN生成逻辑")
print()
print("2️⃣  中优先级 - 函数不支持 (~12个)")
print("    原因: 使用MySQL语法而非PostgreSQL")
print("    影响: IF函数、EXTRACT函数等执行失败")
print("    方案: 替换为PostgreSQL兼容语法或创建兼容函数")
print()
print("3️⃣  中优先级 - rdf_triples表缺失 (~10个)")
print("    原因: 高级查询（路径、递归）需要此表")
print("    影响: 复杂查询功能受限")
print("    方案: 创建rdf_triples表或修改查询逻辑")
print()
print("4️⃣  低优先级 - 操作符类型不匹配 (~15个)")
print("    原因: 数据类型转换问题")
print("    影响: 特定类型比较的查询失败")
print("    方案: 添加显式类型转换")
print()
print("5️⃣  低优先级 - 变量翻译错误 (~8个)")
print("    原因: R2RML解析时变量未正确映射")
print("    影响: 特定复杂查询失败")
print("    方案: 修正R2RML解析器")

print("\n" + "=" * 80)
