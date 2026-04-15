#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

# 编译
env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

print("=== 编译BIND修复 ===")
result = subprocess.run(
    ['cargo', 'build', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

if result.returncode != 0:
    print("❌ 编译失败")
    print(result.stderr[-1000:])
    exit(1)

print("✅ 编译成功")

# 安装扩展
print("\n=== 安装扩展 ===")
result = subprocess.run(
    ['cargo', 'pgrx', 'install', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

if result.returncode != 0:
    print("❌ 安装失败")
    print(result.stderr[-500:])
    exit(1)

print("✅ 扩展安装成功")

# 刷新引擎
print("\n=== 刷新PostgreSQL引擎 ===")
env2 = os.environ.copy()
env2['PGPASSWORD'] = '123456'
result = subprocess.run(
    ['psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu', 
     '-d', 'rs_ontop_core', '-c', 'SELECT ontop_refresh();'],
    capture_output=True,
    text=True,
    env=env2
)

if result.returncode != 0:
    print("⚠️  刷新警告:", result.stderr)
else:
    print("✅ 引擎已刷新")

print("\n🎉 BIND修复已部署，请运行测试验证！")
