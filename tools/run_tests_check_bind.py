#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os
import re

# 设置环境
env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

print("正在运行测试...")
result = subprocess.run(
    ['python3', 'run_all_tests.py'],
    cwd='/home/yuxiaoyu/rs_ontop_core/tests/python',
    capture_output=True,
    text=True,
    env=env
)

# 保存输出
with open('/tmp/test_output.txt', 'w') as f:
    f.write(result.stdout)
    f.write(result.stderr)

# 统计结果
passed = len(re.findall(r'✓ 测试通过', result.stdout))
failed = len(re.findall(r'✗ 测试失败', result.stdout))
error = len(re.findall(r'✗ 执行异常', result.stdout))
total = passed + failed + error

print("\n" + "="*60)
print("测试结果统计（BIND修复后）")
print("="*60)
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"⚠️  异常: {error}")
print(f"📊 总计: {total}")
if total > 0:
    print(f"📈 通过率: {passed/total*100:.1f}%")

# 检查特定的BIND相关测试
bind_tests = ['TestGeofDistance', 'TestDateArithmetic', 'TestYearExtraction', 'TestGeofDistanceWithVar']
print("\n" + "="*60)
print("BIND相关测试结果")
print("="*60)
for test in bind_tests:
    if test in result.stdout:
        if '✓' in result.stdout[result.stdout.find(test)-50:result.stdout.find(test)]:
            print(f"✅ {test}: 通过")
        elif '✗' in result.stdout[result.stdout.find(test)-50:result.stdout.find(test)]:
            # 提取错误信息
            start = result.stdout.find(test)
            end = result.stdout.find('\n', start + 200)
            snippet = result.stdout[start:min(end, start+200)]
            print(f"❌ {test}: 失败")
            if 'Translation error' in snippet:
                print(f"   错误: Translation error")
        else:
            print(f"⚪ {test}: 未知状态")
    else:
        print(f"⚪ {test}: 未找到")

print("\n详细输出保存在: /tmp/test_output.txt")
