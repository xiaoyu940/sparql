#!/usr/bin/env python3
"""
测试案例: 无GROUP BY聚合

验证 SPARQL 无GROUP BY聚合查询是否正确翻译为 SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestAgg003(TestCaseBase):
    """测试无GROUP BY聚合: employees, departments"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 获取员工总数
        
        对应 SQL:
        SELECT COUNT(*) AS totalCount
        FROM employees AS emp
        INNER JOIN departments AS dep ON emp.department_id = dep.department_id
        """
        sparql = """
        SELECT (COUNT(*) AS ?totalCount) WHERE {
            ?emp <http://example.org/department_id> ?dept .
        }
        """
        
        # 翻译 SPARQL
        sql = self.translate_sparql(sparql)
        self._generated_sql = sql
        
        # 验证生成的 SQL 包含预期模式
        expected_patterns = ["COUNT"]
        excluded_patterns = ["GROUP BY"]  # 不应出现GROUP BY
        
        for pattern in expected_patterns:
            if pattern not in sql:
                return QueryResult(
                    passed=False,
                    error=f"Missing expected pattern: {pattern}",
                    sql=sql
                )
        
        for pattern in excluded_patterns:
            if pattern in sql:
                return QueryResult(
                    passed=False,
                    error=f"Found excluded pattern: {pattern}",
                    sql=sql
                )
        
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        基准 SQL - 这是我们认为正确的查询
        """
        baseline_sql = """
        SELECT COUNT(*) AS totalCount
        FROM employees AS emp
        INNER JOIN departments AS dep ON emp.department_id = dep.department_id
        """
        
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    import json
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    print(f"\n{'='*80}")
    print(f"测试: 无GROUP BY聚合")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestAgg003, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
