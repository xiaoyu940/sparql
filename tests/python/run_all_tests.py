#!/usr/bin/env python3
"""
运行所有 Python 测试案例

自动发现并运行 test_cases/ 目录下的所有测试
"""

import os
import sys
import glob
import importlib.util
import json
import decimal
from datetime import datetime
from typing import List, Dict, Any

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase

SKIP_TEST_NAMES = {
    "TestComplexPathNestedSequence",
}

SKIP_TEST_MODULES = {
    "test_sprint9_p0_alternative_001",
    "test_sprint9_p0_complex_001",
    "test_sprint9_p0_inverse_001",
    "test_sprint9_p0_sequence_001",
    "test_sprint9_p2_path_modifiers_001",
}


def discover_tests(test_dir: str = 'test_cases') -> List[type]:
    """发现所有测试案例类"""
    test_classes = []
    
    # 查找所有 test_*.py 文件
    pattern = os.path.join(os.path.dirname(__file__), test_dir, 'test_*.py')
    test_files = glob.glob(pattern)
    
    for file_path in sorted(test_files):
        module_name = os.path.basename(file_path)[:-3]  # 去掉 .py
        
        # 动态加载模块
        if module_name in SKIP_TEST_MODULES:
            print(f"[SKIP MODULE] {module_name}")
            continue

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # 查找测试类（继承自 TestCaseBase）
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, TestCaseBase) and 
                attr is not TestCaseBase):
                if attr.__name__ in SKIP_TEST_NAMES:
                    print(f"[SKIP] {attr.__name__}")
                    continue
                test_classes.append(attr)
    
    return test_classes


def run_all_tests(db_config: Dict[str, Any]) -> List[Dict]:
    """运行所有测试"""
    test_classes = discover_tests()
    results = []
    
    print(f"\n{'='*80}")
    print(f"发现 {len(test_classes)} 个测试案例")
    print(f"{'='*80}\n")
    
    for i, test_class in enumerate(test_classes, 1):
        print(f"\n[{i}/{len(test_classes)}] {test_class.__name__}")
        print(f"{'-'*80}")
        
        # 实例化并运行
        test = test_class(db_config)
        try:
            result = test.run()
            results.append(result)
            if result.get('passed'):
                print(f"✓ {test_class.__name__}")
            else:
                print(f"✗ {test_class.__name__}")
                for err in result.get('errors', []):
                    print(f"  - {err}")
        except Exception as e:
            err_result = {
                'test_name': test_class.__name__,
                'passed': False,
                'errors': [f'测试执行异常: {str(e)}']
            }
            results.append(err_result)
            print(f"✗ {test_class.__name__}")
            print(f"  - {err_result['errors'][0]}")
        finally:
            test.close()
    
    return results


def print_summary(results: List[Dict]):
    """打印测试汇总"""
    passed = sum(1 for r in results if r['passed'])
    failed = len(results) - passed
    
    print(f"\n{'='*80}")
    print(f"测试汇总")
    print(f"{'='*80}")
    print(f"总计: {len(results)}")
    print(f"通过: {passed} ✓")
    print(f"失败: {failed} ✗")
    print(f"{'='*80}")
    
    if failed > 0:
        print(f"\n失败的测试:")
        for result in results:
            if not result['passed']:
                print(f"  ✗ {result['test_name']}")
                for err in result.get('errors', []):
                    print(f"    - {err}")
    
    return failed == 0


def save_json_report(results: List[Dict], filename: str = None):
    """保存测试报告到 JSON 文件 (默认保存到 tests/output/)"""
    # 确保输出目录存在
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'test_report_{timestamp}.json')
    elif not os.path.isabs(filename):
        # 如果提供的是相对路径，也放到 output 目录
        filename = os.path.join(output_dir, filename)
    
    # 转换 Decimal 和 date 类型为可序列化类型
    def convert_to_serializable(obj):
        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(i) for i in obj]
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif hasattr(obj, 'isoformat'):  # date/datetime
            return obj.isoformat()
        return obj
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(results),
        'passed': sum(1 for r in results if r['passed']),
        'failed': sum(1 for r in results if not r['passed']),
        'results': convert_to_serializable(results)
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nJSON 报告已保存: {filename}")
    
def save_markdown_report(results: List[Dict], filename: str = None):
    """保存测试报告到 Markdown 文件 (默认保存到 tests/output/)"""
    # 确保输出目录存在
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'test_report_{timestamp}.md')
    elif not os.path.isabs(filename):
        # 如果提供的是相对路径，也放到 output 目录
        filename = os.path.join(output_dir, filename)
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    lines = []
    lines.append(f"# SPARQL-SQL 翻译验证测试报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    lines.append(f"## 汇总")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总计测试 | {total} |")
    lines.append(f"| 通过 ✓ | {passed} |")
    lines.append(f"| 失败 ✗ | {failed} |")
    lines.append(f"| 通过率 | {pass_rate:.1f}% |")
    lines.append(f"")
    lines.append(f"## 测试结果详情")
    lines.append(f"")
    
    # 通过的测试
    passed_tests = [r for r in results if r['passed']]
    if passed_tests:
        lines.append(f"### ✅ 通过的测试 ({len(passed_tests)})")
        lines.append(f"")
        for r in passed_tests:
            lines.append(f"- **{r['test_name']}** ✓")
        lines.append(f"")
    
    # 失败的测试
    failed_tests = [r for r in results if not r['passed']]
    if failed_tests:
        lines.append(f"### ❌ 失败的测试 ({len(failed_tests)})")
        lines.append(f"")
        for r in failed_tests:
            lines.append(f"<details>")
            lines.append(f"<summary><b>{r['test_name']}</b> ✗</summary>")
            lines.append(f"")
            lines.append(f"**错误信息**:")
            for err in r.get('errors', []):
                lines.append(f"- {err}")
            lines.append(f"")
            # 显示 SQL（如果有）
            if r.get('sparql_sql'):
                lines.append(f"**生成的 SQL**:")
                lines.append(f"```sql")
                lines.append(f"{r['sparql_sql']}")
                lines.append(f"```")
            # 显示结果对比
            if r.get('sparql_result') and r.get('sql_result'):
                sparql_res = r['sparql_result']
                sql_res = r['sql_result']
                lines.append(f"")
                lines.append(f"**结果对比**:")
                lines.append(f"| | SPARQL | SQL |")
                lines.append(f"|--|--------|-----|")
                lines.append(f"| 行数 | {sparql_res.get('row_count', 'N/A')} | {sql_res.get('row_count', 'N/A')} |")
                lines.append(f"| 列 | {', '.join(sparql_res.get('columns', [])[:5])}{'...' if len(sparql_res.get('columns', [])) > 5 else ''} | {', '.join(sql_res.get('columns', [])[:5])}{'...' if len(sql_res.get('columns', [])) > 5 else ''} |")
            lines.append(f"</details>")
            lines.append(f"")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\nMarkdown 报告已保存: {filename}")


# 为了保持兼容性，保留旧的函数名
save_report = save_json_report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='运行所有 SPARQL-SQL 测试案例')
    parser.add_argument('--host', default='localhost', help='PostgreSQL 主机')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL 端口')
    parser.add_argument('--database', default='rs_ontop_core', help='数据库名')
    parser.add_argument('--user', default='yuxiaoyu', help='用户名')
    parser.add_argument('--password', default='', help='密码（也可通过 PGPASSWORD 环境变量设置）')
    parser.add_argument('--report', action='store_true', help='生成测试报告')
    parser.add_argument('--format', default='json', choices=['json', 'markdown', 'md'], help='报告格式: json 或 markdown (默认: json)')
    
    args = parser.parse_args()
    
    db_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password or os.environ.get('PGPASSWORD', '')
    }
    
    # 运行测试
    results = run_all_tests(db_config)
    
    # 打印汇总
    success = print_summary(results)
    
    # 保存报告
    if args.report:
        if args.format in ['markdown', 'md']:
            save_markdown_report(results)
        else:
            save_json_report(results)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
