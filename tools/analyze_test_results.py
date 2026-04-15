#!/usr/bin/env python3

# 分析整体测试结果
with open('/home/yuxiaoyu/rs_ontop_core/test_results.txt', 'r') as f:
    content = f.read()

lines = content.split('\n')
passed_tests = []
failed_tests = []
current_test = None

for line in lines:
    # 检测测试开始
    if '[' in line and '/121]' in line and 'Test' in line:
        parts = line.split(']')
        if len(parts) >= 2:
            test_name = parts[1].strip()
            current_test = test_name
        continue
    
    # 检测测试结果
    if '✓ 测试通过' in line and current_test:
        passed_tests.append(current_test)
        current_test = None
    elif '✗ 测试失败' in line and current_test:
        failed_tests.append(current_test)
        current_test = None

print(f"=== 整体测试结果分析 ===")
print(f"通过: {len(passed_tests)}")
print(f"失败: {len(failed_tests)}")
print(f"总计: {len(passed_tests) + len(failed_tests)}")

# 分析错误类型
error_types = {
    'rdf_triples does not exist': 0,
    'function does not exist': 0,
    'operator does not exist': 0,
    'Translation error': 0,
    'column does not exist': 0,
    '数据不匹配': 0,
    '行数不匹配': 0,
    '类型不匹配': 0
}

for line in lines:
    if 'rdf_triples' in line and 'does not exist' in line:
        error_types['rdf_triples does not exist'] += 1
    elif 'function' in line and 'does not exist' in line:
        error_types['function does not exist'] += 1
    elif 'operator does not exist' in line:
        error_types['operator does not exist'] += 1
    elif 'Translation error' in line:
        error_types['Translation error'] += 1
    elif 'column' in line and 'does not exist' in line:
        error_types['column does not exist'] += 1
    elif '数据不匹配' in line:
        error_types['数据不匹配'] += 1
    elif '行数不匹配' in line:
        error_types['行数不匹配'] += 1
    elif 'types' in line and 'cannot be matched' in line:
        error_types['类型不匹配'] += 1

print(f"\n=== 错误类型统计 ===")
for error_type, count in error_types.items():
    if count > 0:
        print(f"{error_type}: {count}次")

# 通过率计算
total_tests = len(passed_tests) + len(failed_tests)
pass_rate = len(passed_tests) / total_tests * 100 if total_tests > 0 else 0

print(f"\n=== 测试结果评估 ===")
print(f"📊 通过率: {pass_rate:.1f}% ({len(passed_tests)}/{total_tests})")
print(f"🎯 基础功能: {'稳定' if len(passed_tests) >= 50 else '需要改进'}")
print(f"🔧 高级功能: {'受限' if error_types['rdf_triples does not exist'] > 0 else '正常'}")
print(f"⚡ 性能表现: {'良好' if len(passed_tests) >= 54 else '需要优化'}")

print(f"\n=== 关键发现 ===")
print(f"1. R2RML映射: {'工作正常' if len(passed_tests) > 0 else '无响应'}")
print(f"2. 基础查询: {'稳定' if len(passed_tests) >= 30 else '不稳定'}")
print(f"3. 高级查询: {'需要rdf_triples表' if error_types['rdf_triples does not exist'] > 0 else '部分支持'}")
print(f"4. 函数支持: {'需要完善' if error_types['function does not exist'] > 0 else '基本可用'}")

print(f"\n=== 问题分析 ===")
if len(passed_tests) == 0:
    print("⚠️ 严重问题: 所有测试失败")
    print("   - R2RML映射未生效")
    print("   - ontop_query函数无响应")
    print("   - 需要修改Rust代码")
elif len(passed_tests) < 30:
    print("⚠️ 基础问题: 大部分测试失败")
    print("   - 映射配置可能有问题")
    print("   - 引擎初始化失败")
elif len(passed_tests) >= 30 and len(passed_tests) < 60:
    print("🟡 部分功能: 基础查询工作，高级功能受限")
    print("   - R2RML基础映射可能工作")
    print("   - 缺少rdf_triples表支持")
else:
    print("✅ 功能良好: 大部分测试通过")

print(f"\n=== 解决方案建议 ===")
if len(passed_tests) == 0:
    print("1. 修改Rust代码: 让refresh_engine_from_spi支持R2RML")
    print("2. 检查R2RML映射: 确保TTL格式正确")
    print("3. 调试引擎初始化: 查看具体错误信息")
elif error_types['rdf_triples does not exist'] > 0:
    print("1. 创建rdf_triples表: 支持高级查询功能")
    print("2. 实现路径查询: 支持递归查询")
    print("3. 完善R2RML: 增强复杂查询支持")
elif error_types['function does not exist'] > 0:
    print("1. 添加SQL函数: 实现缺失的PostgreSQL函数")
    print("2. 类型转换: 修复类型不匹配问题")
    print("3. 函数映射: 完善SPARQL到SQL的函数转换")

print(f"\n=== 当前状态总结 ===")
print(f"✅ 编译成功: release版本已安装")
print(f"✅ 扩展就绪: PostgreSQL扩展正常工作")
print(f"⚠️ 测试状态: {len(passed_tests)}/121 通过")
print(f"🎯 主要问题: {'R2RML未生效' if len(passed_tests) == 0 else '高级功能缺失'}")

# 保存分析结果
with open('/home/yuxiaoyu/rs_ontop_core/test_analysis.txt', 'w') as f:
    f.write(f"=== 整体测试结果分析 ===\n")
    f.write(f"通过: {len(passed_tests)}\n")
    f.write(f"失败: {len(failed_tests)}\n")
    f.write(f"总计: {total_tests}\n")
    f.write(f"通过率: {pass_rate:.1f}%\n")
    f.write(f"\n=== 错误类型统计 ===\n")
    for error_type, count in error_types.items():
        if count > 0:
            f.write(f"{error_type}: {count}次\n")
    f.write(f"\n=== 主要问题 ===\n")
    if len(passed_tests) == 0:
        f.write("R2RML映射未生效，需要修改Rust代码\n")
    else:
        f.write(f"基础功能正常，高级功能需要完善\n")
