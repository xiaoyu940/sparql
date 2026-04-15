#!/usr/bin/env python3

import re

# 读取测试输出
with open('/home/yuxiaoyu/rs_ontop_core/test_output.txt', 'r') as f:
    content = f.read()

# 统计测试结果
passed = len(re.findall(r'✓ 测试通过', content))
failed = len(re.findall(r'✗ 测试失败', content))
error = len(re.findall(r'✗ 执行异常', content))
total = passed + failed + error

print(f"=== 整体测试结果（删除ontop_mappings后）===")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"异常: {error}")
print(f"总计: {total}")
print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "通过率: N/A")

# 分析错误类型
rdf_errors = content.count('rdf_triples" does not exist')
translation_errors = content.count('Translation error')
function_errors = content.count('function does not exist')
operator_errors = content.count('operator does not exist')
column_errors = content.count('column') + content.count('does not exist')

print(f"\n=== 错误类型分析 ===")
if rdf_errors > 0:
    print(f"rdf_triples表缺失: {rdf_errors}次")
if translation_errors > 0:
    print(f"翻译错误: {translation_errors}次")
if function_errors > 0:
    print(f"函数不存在: {function_errors}次")
if operator_errors > 0:
    print(f"操作符错误: {operator_errors}次")
if column_errors > 0:
    print(f"列不存在: {column_errors}次")

print(f"\n=== 结论 ===")
if total > 0:
    if passed/total > 0.7:
        print("✅ 基础功能稳定，高级功能受限")
    elif passed/total > 0.5:
        print("🟡 部分功能正常，需要优化R2RML映射")
    else:
        print("❌ 大量测试失败，R2RML映射可能不完整")
else:
    print("⚠️ 无法解析测试结果")
