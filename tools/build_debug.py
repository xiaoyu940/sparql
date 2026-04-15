#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import os

env = os.environ.copy()
env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')

print("=== 编译项目（带调试输出）===")
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
else:
    print("✅ 编译成功！")
    if result.stderr:
        print("警告:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
