#!/usr/bin/env python3

import subprocess
import os

# 直接查询R2RML映射内容
env = os.environ.copy()
env['PGPASSWORD'] = '123456'

cmd = [
    'bash', '-c',
    'export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -c "SELECT ttl_content FROM ontop_r2rml_mappings WHERE name = '\''simple'\'';"'
]

result = subprocess.run(cmd, capture_output=True, text=True, env=env)

print("=== R2RML映射内容 ===")
print("输出:")
print(result.stdout)
print("错误:")
print(result.stderr)
print("返回码:", result.returncode)

# 分析为什么测试通过率不高
print("\n=== 分析R2RML映射问题 ===")

if result.returncode == 0 and "simple" in result.stdout:
    print("✅ R2RML映射存在")
    
    # 检查映射内容长度
    content_lines = result.stdout.split('\n')
    ttl_content = None
    
    for line in content_lines:
        if line.strip() and not line.startswith('--') and not line.startswith('RE name'):
            ttl_content = line.strip()
            break
    
    if ttl_content:
        print(f"映射内容长度: {len(ttl_content)} 字符")
        print(f"映射内容预览: {ttl_content[:200]}...")
        
        # 检查关键谓词
        key_predicates = [
            'http://example.org/first_name',
            'http://example.org/last_name',
            'http://example.org/email',
            'http://example.org/department_id'
        ]
        
        found_predicates = []
        for predicate in key_predicates:
            if predicate in ttl_content:
                found_predicates.append(predicate)
        
        print(f"找到的谓词: {len(found_predicates)}/{len(key_predicates)}")
        for pred in found_predicates:
            print(f"  ✅ {pred}")
        
        missing_predicates = [p for p in key_predicates if p not in found_predicates]
        for pred in missing_predicates:
            print(f"  ❌ {pred}")
            
        if len(found_predicates) < len(key_predicates):
            print("\n⚠️ R2RML映射不完整，缺少关键谓词")
            print("这可能导致测试失败率较高")
        else:
            print("\n✅ R2RML映射包含所有关键谓词")
    else:
        print("❌ 无法提取R2RML映射内容")
else:
    print("❌ R2RML映射查询失败")
    print("可能原因:")
    print("1. 数据库连接问题")
    print("2. 表不存在")
    print("3. 权限问题")

print(f"\n=== 结论 ===")
print("Bug未减少的可能原因:")
print("1. R2RML映射内容不完整")
print("2. R2RML加载器未正确集成到引擎")
print("3. 代码层面仍使用ontop_mappings逻辑")
print("4. 高级查询需要更多R2RML支持")
