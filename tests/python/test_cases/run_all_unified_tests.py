#!/usr/bin/env python3
"""
运行所有统一测试案例

这个脚本运行所有从 Rust 统一测试转换而来的 Python 测试案例
"""

import sys
import os
import subprocess
import json

# 测试案例列表
test_cases = [
    "test_unified_join_001.py",
    "test_unified_join_002.py", 
    "test_unified_join_003.py",
    "test_unified_agg_001.py",
    "test_unified_agg_002.py",
    "test_unified_agg_003.py",
    "test_unified_having_001.py",
    "test_unified_having_002.py",
    "test_unified_order_001.py",
    "test_unified_order_002.py",
    "test_unified_order_003.py",
    "test_unified_filter_001.py",
    "test_unified_filter_002.py",
    "test_unified_map_001.py",
    "test_unified_map_002.py",
    "test_unified_edge_001.py",
    "test_unified_edge_002.py",
    "test_unified_perf_001.py",
]

def run_test_case(test_file):
    """运行单个测试案例"""
    test_path = os.path.join(os.path.dirname(__file__), test_file)
    
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时
        )
        
        return {
            'test': test_file,
            'passed': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {
            'test': test_file,
            'passed': False,
            'output': '',
            'error': 'Test timeout after 30 seconds'
        }
    except Exception as e:
        return {
            'test': test_file,
            'passed': False,
            'output': '',
            'error': str(e)
        }

def main():
    """主函数"""
    print(f"\n{'='*80}")
    print(f"统一测试案例套件 - Python版本")
    print(f"{'='*80}")
    print(f"共 {len(test_cases)} 个测试案例\n")
    
    results = []
    passed_count = 0
    failed_count = 0
    
    for test_case in test_cases:
        print(f"运行: {test_case}")
        result = run_test_case(test_case)
        results.append(result)
        
        if result['passed']:
            passed_count += 1
            print(f"  ✓ 通过")
        else:
            failed_count += 1
            print(f"  ✗ 失败")
            if result['error']:
                print(f"    错误: {result['error']}")
    
    # 打印总结
    print(f"\n{'='*80}")
    print(f"测试结果总结")
    print(f"{'='*80}")
    print(f"总计: {len(test_cases)}")
    print(f"通过: {passed_count}")
    print(f"失败: {failed_count}")
    print(f"成功率: {passed_count/len(test_cases)*100:.1f}%")
    print(f"{'='*80}")
    
    # 保存详细结果到JSON文件
    with open('/tmp/unified_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total': len(test_cases),
                'passed': passed_count,
                'failed': failed_count,
                'success_rate': passed_count/len(test_cases)*100
            },
            'results': results
        }, f, indent=2)
    
    print(f"详细结果已保存到: /tmp/unified_test_results.json")
    
    # 如果有失败的测试，返回非零退出码
    if failed_count > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
