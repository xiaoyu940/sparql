#!/usr/bin/env python3
"""
强制重新编译并测试
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, QueryResult, run_test_case


class TestBasicJoin(TestCaseBase):
    """测试基础 JOIN: employees 和 departments"""
    
    def sparql_query(self) -> QueryResult:
        """SPARQL 查询: 通过 HTTP 端口 5820 执行"""
        sparql = """
        SELECT ?firstName ?deptName
        WHERE {
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
        }
        LIMIT 5
        """
        return self.execute_sparql_http(sparql)
    
    def sql_query(self) -> QueryResult:
        """对应的 SQL 查询（作为基准）"""
        baseline_sql = """
        SELECT e.first_name AS firstname, d.department_name AS deptname
        FROM employees e
        INNER JOIN departments d ON e.department_id = d.department_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '123456')
    }
    
    print("="*80)
    print("强制重新编译并测试")
    print("="*80)
    
    # 创建测试实例
    test = TestBasicJoin(db_config)
    
    # 检查并安装扩展（增量编译，仅当需要时）
    print("\n>>> 检查并安装扩展...")
    if not test.ensure_extension_installed():
        print("✗ 扩展安装失败")
        sys.exit(1)
    
    # 运行测试
    print("\n>>> 运行测试...")
    result = test.run()
    
    print("\n" + "="*80)
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print("="*80)
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
