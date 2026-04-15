#!/usr/bin/env python3
"""
SPARQL HTTP 测试套件 - 主运行脚本
运行所有测试类别并生成汇总报告
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入所有测试模块
from test_basic_select import (
    TestBasicSelectAllEmployees, TestSelectSpecificColumns, TestSelectWithOrderBy,
    TestSelectDistinctDepartments, TestSelectCountEmployees, TestAskEmployeeExists
)
from test_join_optional import (
    TestJoinEmployeeDepartment, TestJoinEmployeePosition, TestOptionalEmployeeSalary,
    TestOptionalEmployeeProject, TestJoinWithFilter, TestNestedOptional
)
from test_filter_bind import (
    TestFilterNumericComparison, TestFilterStringEquality, TestFilterDateRange,
    TestFilterLogicalAnd, TestBindCalculation, TestBindStringConcat, TestBindWithFilter
)
from test_aggregate_subquery import (
    TestAggregateCountByDepartment, TestAggregateAvgSalary, TestAggregateSum,
    TestSubqueryExists, TestSubqueryNotExists, TestSubqueryScalar, TestGroupByMultiple
)
from test_union_advanced import (
    TestUnionTwoPatterns, TestValuesBlock, TestInFilter,
    TestCoalesce, TestIfExpression, TestMinusPattern, TestServicePattern
)

from framework import run_test_suite


def main():
    """运行所有测试套件"""
    print("\n" + "="*80)
    print("SPARQL HTTP 综合测试套件")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"SPARQL Endpoint: http://localhost:5820/sparql")
    print(f"SQL Database: localhost:5432/rs_ontop_core")
    print("="*80)
    
    all_results = []
    start_time = time.time()
    
    # 定义所有测试套件
    test_suites = [
        ("基础 SELECT 查询", [
            TestBasicSelectAllEmployees(),
            TestSelectSpecificColumns(),
            TestSelectWithOrderBy(),
            TestSelectDistinctDepartments(),
            TestSelectCountEmployees(),
            TestAskEmployeeExists(),
        ]),
        ("JOIN 和 OPTIONAL", [
            TestJoinEmployeeDepartment(),
            TestJoinEmployeePosition(),
            TestOptionalEmployeeSalary(),
            TestOptionalEmployeeProject(),
            TestJoinWithFilter(),
            TestNestedOptional(),
        ]),
        ("FILTER 和 BIND", [
            TestFilterNumericComparison(),
            TestFilterStringEquality(),
            TestFilterDateRange(),
            TestFilterLogicalAnd(),
            TestBindCalculation(),
            TestBindStringConcat(),
            TestBindWithFilter(),
        ]),
        ("聚合和子查询", [
            TestAggregateCountByDepartment(),
            TestAggregateAvgSalary(),
            TestAggregateSum(),
            TestSubqueryExists(),
            TestSubqueryNotExists(),
            TestSubqueryScalar(),
            TestGroupByMultiple(),
        ]),
        ("UNION 和高级特性", [
            TestUnionTwoPatterns(),
            TestValuesBlock(),
            TestInFilter(),
            TestCoalesce(),
            TestIfExpression(),
            TestMinusPattern(),
            TestServicePattern(),
        ]),
    ]
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    
    # 运行每个测试套件
    for suite_name, test_cases in test_suites:
        print(f"\n\n{'='*80}")
        print(f"测试套件: {suite_name}")
        print(f"{'='*80}")
        
        results = run_test_suite(test_cases)
        all_results.extend(results)
        
        suite_passed = sum(1 for r in results if r["passed"])
        suite_failed = sum(1 for r in results if not r["passed"])
        
        total_tests += len(test_cases)
        total_passed += suite_passed
        total_failed += suite_failed
        
        print(f"\n{suite_name}: {suite_passed}/{len(test_cases)} 通过")
    
    # 汇总报告
    elapsed_time = time.time() - start_time
    
    print("\n\n" + "="*80)
    print("测试汇总报告")
    print("="*80)
    print(f"总测试数:   {total_tests}")
    print(f"通过:       {total_passed} ✓")
    print(f"失败:       {total_failed} ✗")
    print(f"通过率:     {total_passed/total_tests*100:.1f}%")
    print(f"总耗时:     {elapsed_time:.2f} 秒")
    print("="*80)
    
    # 失败的测试详情
    if total_failed > 0:
        print("\n失败的测试:")
        for result in all_results:
            if not result["passed"]:
                print(f"  ✗ {result['name']}")
                for error in result.get("errors", []):
                    print(f"    - {error}")
    
    # 保存完整报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": f"{total_passed/total_tests*100:.1f}%",
            "elapsed_seconds": elapsed_time
        },
        "results": all_results
    }
    
    report_file = f"sparql_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n完整报告已保存: {report_file}")
    
    # 返回退出码
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
