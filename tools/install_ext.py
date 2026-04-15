#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

print("=== 安装PostgreSQL扩展 ===")
result = subprocess.run(
    ['cargo', 'pgrx', 'install', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

print("STDOUT:", result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
print(f"返回码: {result.returncode}")
