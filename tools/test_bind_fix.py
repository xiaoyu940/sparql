#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os
import re

print("=== 运行BIND相关测试 ===")

bash_cmd = """
cd /home/yuxiaoyu/rs_ontop_core/tests/python
source venv/bin/activate
python3 run_all_tests.py 2>&1
"""

result = subprocess.run(
    ['bash', '-c', bash_cmd],
    capture_output=True,
    text=True
)

output = result.stdout + result.stderr

# 保存完整输出
with open('/tmp/test_bind_fix.txt', 'w') as f:
    f.write(output)

# 统计总体结果
passed = len(re.findall(r'✓ 测试通过', output))
failed = len(re.findall(r'✗ 测试失败', output))
error = len(re.findall(r'✗ 执行异常', output))
total = passed + failed + error

print(f"\n总体统计: 通过{passed} | 失败{failed} | 异常{error} | 总计{total}")

# 检查BIND相关测试
bind_tests = ['TestGeofDistance', 'TestGeofDistanceWithVar', 'TestDateArithmetic', 'TestYearExtraction']
print("\n=== BIND相关测试结果 ===")

for test in bind_tests:
    # 查找测试位置
    idx = output.find(f'] {test}')
    if idx == -1:
        print(f"⚪ {test}: 未找到")
        continue
    
    # 提取状态（前后100字符）
    snippet = output[max(0, idx-100):idx+200]
    
    if '✓ 测试通过' in snippet:
        print(f"✅ {test}: 通过")
    elif '✗ 测试失败' in snippet:
        # 提取失败原因
        reason_match = re.search(r'- (.*?)(?=\n)', snippet[snippet.find('测试失败'):])
        reason = reason_match.group(1) if reason_match else "未知"
        print(f"❌ {test}: 失败 - {reason[:50]}")
    elif '✗ 执行异常' in snippet:
        # 提取异常原因
        if 'Translation error' in snippet:
            print(f"⚠️  {test}: Translation error (修复未生效)")
        elif 'Unmapped variable' in snippet:
            var_match = re.search(r'Unmapped variable: (\w+)', snippet)
            var = var_match.group(1) if var_match else "unknown"
            print(f"⚠️  {test}: Unmapped variable: {var} (修复未生效)")
        else:
            error_match = re.search(r'执行异常: (.*?)(?=\n)', snippet[snippet.find('执行异常'):])
            error = error_match.group(1) if error_match else "未知"
            print(f"⚠️  {test}: {error[:50]}")
    else:
        print(f"⚪ {test}: 状态未知")

print("\n详细日志: /tmp/test_bind_fix.txt")
