#!/usr/bin/env python3
"""
Sprint 9 P2 日期时间函数测试 - NOW, YEAR, MONTH, DAY等

测试目标：验证SPARQL 1.1日期时间函数的SQL生成
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestNowFunction(TestCaseBase):
    """测试 NOW() 函数"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?currenttime
        WHERE {
          BIND(NOW() AS ?currenttime)
        }
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P2-3] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = "SELECT CURRENT_TIMESTAMP AS currenttime"
        return self.execute_sql_query(baseline_sql)


class TestYearExtraction(TestCaseBase):
    """测试 YEAR() 函数"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>

        SELECT ?name
        WHERE {
          ?emp ex:first_name ?name ;
               ex:hireDate ?date .
          FILTER(YEAR(?date) > 2020)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS name
        FROM employees
        WHERE EXTRACT(YEAR FROM hire_date) > 2020
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestDateTimeComponents(TestCaseBase):
    """测试日期时间组件提取函数"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>

        SELECT ?name
        WHERE {
          ?emp ex:first_name ?name ;
               ex:hireDate ?dt .
          FILTER(YEAR(?dt) >= 2000 && MONTH(?dt) >= 1 && DAY(?dt) >= 1)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS name
        FROM employees
        WHERE EXTRACT(YEAR FROM hire_date::timestamp) >= 2000
          AND EXTRACT(MONTH FROM hire_date::timestamp) >= 1
          AND EXTRACT(DAY FROM hire_date::timestamp) >= 1
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestTimezoneFunctions(TestCaseBase):
    """测试时区相关函数"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?tz ?tzabbr
        WHERE {
          BIND(TIMEZONE(NOW()) AS ?tz)
          BIND(TZ(NOW()) AS ?tzabbr)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT EXTRACT(TIMEZONE FROM CURRENT_TIMESTAMP) AS tz,
               EXTRACT(TIMEZONE FROM CURRENT_TIMESTAMP) AS tzabbr
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestDateArithmetic(TestCaseBase):
    """测试日期比较和运算"""

    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>

        SELECT ?name
        WHERE {
          ?emp ex:first_name ?name ;
               ex:hireDate ?hireDate .
          FILTER(YEAR(NOW()) - YEAR(?hireDate) > 5)
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)

    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS name
        FROM employees
        WHERE EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM hire_date) > 5
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': os.environ.get('PGUSER', 'yuxiaoyu'),
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("S9-P2 DateTime - NOW()", TestNowFunction),
        ("S9-P2 DateTime - YEAR()", TestYearExtraction),
        ("S9-P2 DateTime - All Components", TestDateTimeComponents),
        ("S9-P2 DateTime - Timezone", TestTimezoneFunctions),
        ("S9-P2 DateTime - Arithmetic", TestDateArithmetic),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class(db_config))
        if not result['passed']:
            all_passed = False
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
