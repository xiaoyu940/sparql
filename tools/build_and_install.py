#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

# 设置环境
env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

# 编译
print("=== 编译项目 ===")
result = subprocess.run(
    ['cargo', 'build', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

if result.returncode != 0:
    print("编译失败:")
    print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
    exit(1)

print("✅ 编译成功！")

# 安装扩展
print("\n=== 安装PostgreSQL扩展 ===")
result = subprocess.run(
    ['cargo', 'pgrx', 'install', '--release'],
    cwd='/home/yuxiaoyu/rs_ontop_core',
    capture_output=True,
    text=True,
    env=env
)

if result.returncode != 0:
    print("安装失败:")
    print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
    exit(1)

print("✅ 扩展安装成功！")

# 刷新引擎
print("\n=== 刷新PostgreSQL引擎 ===")
env2 = os.environ.copy()
env2['PGPASSWORD'] = '123456'
result = subprocess.run(
    ['psql', '-h', 'localhost', '-p', '5432', '-U', 'yuxiaoyu', '-d', 'rs_ontop_core', '-c', 'SELECT ontop_refresh();'],
    capture_output=True,
    text=True,
    env=env2
)

if result.returncode != 0:
    print("刷新失败:", result.stderr)
else:
    print("✅ 引擎刷新成功！")

print("\n请运行测试验证BIND修复是否生效")
