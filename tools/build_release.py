#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

# 设置环境
env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

# 运行cargo build
print("正在编译项目...")
result = subprocess.run(
    ['cargo', 'build', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

print("STDOUT:")
print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

print(f"\n返回码: {result.returncode}")
