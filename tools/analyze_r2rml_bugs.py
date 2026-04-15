#!/usr/bin/env python3

# 深度分析R2RML迁移后的bug问题

print("=== R2RML迁移后bug分析 ===")

# 1. 检查当前映射状态
import subprocess
import os

env = os.environ.copy()
env['PGPASSWORD'] = '123456'

print("\n1. 检查当前映射状态:")

# 检查ontop_mappings
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT COUNT(*) FROM ontop_mappings;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
ontop_count = result.stdout.strip()

# 检查R2RML
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT COUNT(*) FROM ontop_r2rml_mappings;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
r2rml_count = result.stdout.strip()

print(f"ontop_mappings: {ontop_count} 条")
print(f"ontop_r2rml_mappings: {r2rml_count} 条")

# 2. 检查R2RML映射内容
print("\n2. 检查R2RML映射内容:")
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT name, LENGTH(ttl_content) as size FROM ontop_r2rml_mappings;"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print(f"R2RML映射详情:\n{result.stdout}")

# 3. 测试基础R2RML功能
print("\n3. 测试基础R2RML功能:")
test_sparql = "SELECT ?name WHERE { ?emp <http://example.org/first_name> ?name } LIMIT 3"
escaped = test_sparql.replace("'", "''")

cmd = [
    'bash', '-c',
    f'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT ontop_query(\'{escaped}\');"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print(f"基础R2RML查询结果:\n{result.stdout}")

# 4. 测试R2RML翻译功能
print("\n4. 测试R2RML翻译功能:")
cmd = [
    'bash', '-c',
    f'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT ontop_translate(\'{escaped}\');"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print(f"R2RML翻译结果:\n{result.stdout}")

# 5. 分析测试结果中的错误模式
print("\n5. 分析测试错误模式:")

with open('/home/yuxiaoyu/rs_ontop_core/test_results.txt', 'r') as f:
    content = f.read()

# 分析rdf_triples相关错误
rdf_triples_errors = content.count('rdf_triples" does not exist')
print(f"rdf_triples相关错误: {rdf_triples_errors} 次")

# 分析翻译错误
translation_errors = content.count('Translation error')
print(f"翻译错误: {translation_errors} 次")

# 分析函数不存在错误
function_errors = content.count('function does not exist')
print(f"函数不存在错误: {function_errors} 次")

# 分析列不存在错误
column_errors = content.count('column does not exist')
print(f"列不存在错误: {column_errors} 次")

# 6. 检查引擎初始化日志
print("\n6. 检查引擎初始化状态:")
cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT ontop_refresh();"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)
print(f"引擎刷新结果:\n{result.stdout}")

# 7. 分析R2RML映射的完整性
print("\n7. 分析R2RML映射完整性:")

if int(r2rml_count) > 0:
    cmd = [
        'bash', '-c',
        'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c "SELECT ttl_content FROM ontop_r2rml_mappings LIMIT 1;"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    r2rml_content = result.stdout.strip()
    
    print(f"R2RML内容长度: {len(r2rml_content)} 字符")
    
    # 检查关键谓词
    key_predicates = [
        'http://example.org/first_name',
        'http://example.org/last_name', 
        'http://example.org/email',
        'http://example.org/department_id'
    ]
    
    for predicate in key_predicates:
        if predicate in r2rml_content:
            print(f"✅ 找到谓词: {predicate}")
        else:
            print(f"❌ 缺失谓词: {predicate}")

print(f"\n=== 问题分析 ===")

if int(ontop_count) == 0 and int(r2rml_count) > 0:
    print("✅ 数据库层面: 已迁移到R2RML")
else:
    print("❌ 数据库层面: 迁移不完整")

if "0 rows" in result.stdout or result.stdout.strip() == "":
    print("❌ 代码层面: R2RML映射未生效")
    print("   - ontop_query返回空结果")
    print("   - 引擎未加载R2RML映射")
else:
    print("✅ 代码层面: R2RML映射可能已生效")

print(f"\n=== Bug未减少的原因 ===")

if int(ontop_count) == 0 and int(r2rml_count) > 0:
    print("1. 🔧 代码层面问题:")
    print("   - R2RML加载器已实现但未接入主流程")
    print("   - refresh_engine_from_spi仍只加载ontop_mappings")
    print("   - 需要修改Rust代码集成R2RML")

if rdf_triples_errors > 0:
    print("2. 📊 功能缺失问题:")
    print("   - 高级查询需要rdf_triples表支持")
    print("   - R2RML当前不支持递归查询")
    print("   - 路径查询、地理查询受限")

if translation_errors > 0:
    print("3. 🔄 翻译器问题:")
    print("   - R2RML解析可能不完整")
    print("   - 复杂查询翻译失败")
    print("   - 需要增强R2RML支持")

if function_errors > 0:
    print("4. ⚙️ 函数支持问题:")
    print("   - SQL函数映射不完整")
    print("   - 类型转换函数缺失")
    print("   - 需要扩展函数库")

print(f"\n=== 解决方案 ===")
print("1. 🎯 立即修复:")
print("   - 修改refresh_engine_from_spi集成R2RML加载器")
print("   - 确保R2RML映射正确解析")
print("   - 测试基础查询功能")

print("2. 🚀 中期改进:")
print("   - 扩展R2RML支持复杂查询")
print("   - 实现递归查询支持")
print("   - 完善函数映射")

print("3. 🔧 长期优化:")
print("   - 性能优化和缓存")
print("   - 错误处理改进")
print("   - 完整的测试覆盖")
