#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计测试通过率
"""

import re

# 读取测试输出文件
with open('/home/yuxiaoyu/rs_ontop_core/tests/python/test_output.txt', 'r') as f:
    content = f.read()

# 统计各种结果
passed = len(re.findall(r'✓ 测试通过', content))
failed = len(re.findall(r'✗ 测试失败', content))
error = len(re.findall(r'✗ 执行异常', content))
total = passed + failed + error

print("=" * 60)
print("       整体测试结果统计（R2RML映射修正后）")
print("=" * 60)
print(f"\n  ✅ 测试通过: {passed}")
print(f"  ❌ 测试失败: {failed}")
print(f"  ⚠️  执行异常: {error}")
print(f"  📊 总计: {total}")
print(f"  📈 通过率: {passed/total*100:.1f}%" if total > 0 else "  📈 通过率: N/A")

print("\n" + "=" * 60)
print("       错误类型分析")
print("=" * 60)

# 分析错误类型
error_types = {
    'rdf_triples表缺失': content.count('rdf_triples" does not exist'),
    '列不存在': len(re.findall(r'column.*does not exist', content)),
    '函数不存在': len(re.findall(r'function.*does not exist', content)),
    '操作符错误': len(re.findall(r'operator does not exist', content)),
    '翻译错误': content.count('Translation error'),
    '数据不匹配': content.count('数据不匹配'),
    '行数不匹配': content.count('行数不匹配'),
}

for error_type, count in error_types.items():
    if count > 0:
        print(f"  • {error_type}: {count}次")

print("\n" + "=" * 60)
print("       结论")
print("=" * 60)

if total > 0:
    pass_rate = passed / total
    if pass_rate >= 0.8:
        print("  🎉 优秀: 大部分测试通过，系统基本可用")
    elif pass_rate >= 0.5:
        print("  🟡 部分可用: 基础功能正常，高级功能受限")
    elif pass_rate >= 0.3:
        print("  🔶 需要改进: 约一半测试失败，需要修复关键问题")
    else:
        print("  🔴 严重问题: 大部分测试失败，系统不稳定")

print(f"\n  当前状态: 仅R2RML映射，无ontop_mappings回退")
print(f"  主要问题: SQL生成器列映射错误、函数兼容性问题")

print("\n" + "=" * 60)
