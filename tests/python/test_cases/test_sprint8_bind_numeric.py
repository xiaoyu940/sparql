#!/usr/bin/env python3
"""
Sprint 8 BIND 数值函数测试

测试目标：验证 BIND 表达式中数值函数的正确翻译
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestBindAbs(TestCaseBase):
    """BIND ABS 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?abs_diff
        WHERE {
          ?emp <http://example.org/salary> ?salary .
          BIND(ABS(?salary - 70000) AS ?abs_diff)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ABS 绝对值"""
        baseline_sql = """
        SELECT employee_id AS "emp", ABS(salary - 70000) AS "abs_diff"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindRound(TestCaseBase):
    """BIND ROUND 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?rounded
        WHERE {
          ?emp <http://example.org/bonus> ?bonus .
          BIND(ROUND(?bonus) AS ?rounded)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ROUND"""
        baseline_sql = """
        SELECT employee_id AS "emp", ROUND(bonus) AS "rounded"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindCeilFloor(TestCaseBase):
    """BIND CEIL/FLOOR 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?ceil_val ?floor_val
        WHERE {
          ?emp <http://example.org/bonus> ?bonus .
          BIND(CEIL(?bonus) AS ?ceil_val)
          BIND(FLOOR(?bonus) AS ?floor_val)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - CEILING/FLOOR"""
        baseline_sql = """
        SELECT employee_id AS "emp", 
               CEILING(bonus) AS "ceil_val",
               FLOOR(bonus) AS "floor_val"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindArithmetic(TestCaseBase):
    """BIND 算术运算测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?new_salary
        WHERE {
          ?emp <http://example.org/salary> ?salary .
          BIND(?salary * 1.1 + 1000 AS ?new_salary)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 算术运算"""
        baseline_sql = """
        SELECT employee_id AS "emp", (salary * 1.1 + 1000) AS "new_salary"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindMod(TestCaseBase):
    """BIND MOD 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?remainder
        WHERE {
          ?emp <http://example.org/employee_id> ?id .
          BIND(MOD(?id, 10) AS ?remainder)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - MOD 取模"""
        baseline_sql = """
        SELECT employee_id AS "emp", MOD(employee_id, 10) AS "remainder"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindRand(TestCaseBase):
    """BIND RAND 测试 - 随机数"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?random
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          BIND(RAND() AS ?random)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", RANDOM() AS "random"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

    def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult):
        errors = []
        if sparql_result.row_count != sql_result.row_count:
            errors.append(f"行数不匹配: SPARQL={sparql_result.row_count}, SQL={sql_result.row_count}")

        def find_random_col(columns):
            for c in columns:
                if 'random' in c.lower():
                    return c
            return None

        s_col = find_random_col(sparql_result.columns)
        q_col = find_random_col(sql_result.columns)
        if s_col is None or q_col is None:
            errors.append(f"RAND 列未找到: SPARQL={sparql_result.columns}, SQL={sql_result.columns}")
            return len(errors) == 0, errors

        def in_range(rows, col):
            for r in rows:
                if col not in r:
                    return False
                try:
                    v = float(r[col])
                except (TypeError, ValueError):
                    return False
                if not (0.0 <= v < 1.0):
                    return False
            return True

        if not in_range(sparql_result.rows, s_col):
            errors.append("SPARQL RAND 结果不在 [0,1) 范围")
        if not in_range(sql_result.rows, q_col):
            errors.append("SQL RANDOM 结果不在 [0,1) 范围")

        return len(errors) == 0, errors

if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("BIND - ABS 绝对值", TestBindAbs),
        ("BIND - ROUND 四舍五入", TestBindRound),
        ("BIND - CEIL/FLOOR 取整", TestBindCeilFloor),
        ("BIND - 算术运算", TestBindArithmetic),
        ("BIND - MOD 取模", TestBindMod),
        ("BIND - RAND 随机数", TestBindRand),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class())
        if not result['passed']:
            all_passed = False
            print(f"✗ 失败: {result.get('errors', [])}")
        else:
            print(f"✓ 测试通过")
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
