#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

# 设置环境
env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

# 安装扩展
print("正在安装PostgreSQL扩展...")
result = subprocess.run(
    ['cargo', 'pgrx', 'install', '--release'],
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

if result.returncode == 0:
    print("\n✅ 扩展安装成功！")
else:
    print("\n❌ 扩展安装失败！")
