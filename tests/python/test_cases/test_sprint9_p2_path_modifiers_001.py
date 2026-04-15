#!/usr/bin/env python3
"""
Sprint 9 P2 路径修饰符测试 - ? (Optional), * (Star), + (Plus)

测试目标：验证路径修饰符在OBDA架构下的SQL生成
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestOptionalModifier(TestCaseBase):
    """测试 ? 可选路径修饰符 (零次或一次)"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?mgrName
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:manager? ?mgr .
          ?mgr ex:name ?mgrName .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P2-1] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - LEFT JOIN 实现可选"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp, 
            COALESCE(t1.name, 'No Manager') AS mgrName
        FROM employees t0
        LEFT JOIN employees t1 ON t0.manager_id = t1.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestStarModifier(TestCaseBase):
    """测试 * Kleene Star 路径修饰符 (零次或多次)"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?ancestor ?descendant
        WHERE {
          ?ancestor ex:reportsTo* ?descendant .
        }
        LIMIT 20
        """
        sql = self.translate_sparql(sparql)
        # 验证生成了递归CTE
        assert "WITH RECURSIVE" in sql
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 递归CTE (查询时传递闭包)"""
        baseline_sql = """
        WITH RECURSIVE reports_to_cte AS (
            -- 锚点：零步（每个人是自己的祖先）
            SELECT employee_id AS ancestor, employee_id AS descendant, 0 AS depth
            FROM employees
            UNION
            -- 锚点：直接一步
            SELECT employee_id AS ancestor, manager_id AS descendant, 1 AS depth
            FROM employees
            WHERE manager_id IS NOT NULL
            
            UNION ALL
            
            -- 递归：继续向上
            SELECT c.ancestor, e.manager_id AS descendant, c.depth + 1
            FROM reports_to_cte c
            JOIN employees e ON c.descendant = e.employee_id
            WHERE e.manager_id IS NOT NULL
              AND c.depth < 10
        )
        SELECT ancestor, descendant
        FROM reports_to_cte
        LIMIT 20
        """
        return self.execute_sql_query(baseline_sql)


class TestPlusModifier(TestCaseBase):
    """测试 + Kleene Plus 路径修饰符 (一次或多次)"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?manager ?subordinate
        WHERE {
          ?manager ex:manages+ ?subordinate .
        }
        LIMIT 20
        """
        sql = self.translate_sparql(sparql)
        assert "WITH RECURSIVE" in sql
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 递归CTE (至少一步)"""
        baseline_sql = """
        WITH RECURSIVE manages_cte AS (
            -- 锚点：直接管理关系（深度=1）
            SELECT manager_id AS manager, employee_id AS subordinate, 1 AS depth
            FROM employees
            WHERE manager_id IS NOT NULL
            
            UNION ALL
            
            -- 递归：间接管理
            SELECT c.manager, e.employee_id AS subordinate, c.depth + 1
            FROM manages_cte c
            JOIN employees e ON c.subordinate = e.manager_id
            WHERE c.depth < 10
        )
        SELECT manager, subordinate
        FROM manages_cte
        LIMIT 20
        """
        return self.execute_sql_query(baseline_sql)


class TestStarWithBinding(TestCaseBase):
    """测试 * 修饰符带变量绑定"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?person ?colleague
        WHERE {
          ?person a ex:Employee .
          ?person ex:knows* ?colleague .
          FILTER(?person != ?colleague)
        }
        LIMIT 30
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 递归CTE带过滤（使用 employees 自连接）"""
        baseline_sql = """
        WITH RECURSIVE knows_cte AS (
            SELECT employee_id AS start, employee_id AS end, 0 AS depth
            FROM employees
            UNION
            SELECT employee_id AS start, manager_id AS end, 1 AS depth
            FROM employees
            WHERE manager_id IS NOT NULL
            
            UNION ALL
            
            SELECT c.start, e.manager_id AS end, c.depth + 1
            FROM knows_cte c
            JOIN employees e ON c.end = e.employee_id
            WHERE c.depth < 10
        )
        SELECT start AS person, end AS colleague
        FROM knows_cte
        WHERE start != end
        LIMIT 30
        """
        return self.execute_sql_query(baseline_sql)


class TestNestedModifiers(TestCaseBase):
    """测试嵌套修饰符序列: (:knows*)?"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?person ?network
        WHERE {
          ?person ex:socialNetwork? ?network .
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 可选的闭包路径（使用 employees 自连接）"""
        baseline_sql = """
        WITH RECURSIVE network_cte AS (
            SELECT employee_id AS start, employee_id AS end, 0 AS depth
            FROM employees
            UNION
            SELECT employee_id AS start, manager_id AS end, 1 AS depth
            FROM employees
            WHERE manager_id IS NOT NULL
            
            UNION ALL
            
            SELECT c.start, e.manager_id AS end, c.depth + 1
            FROM network_cte c
            JOIN employees e ON c.end = e.employee_id
            WHERE c.depth < 5
        )
        SELECT 
            e.employee_id AS person,
            COALESCE(n.end, e.employee_id) AS network
        FROM employees e
        LEFT JOIN network_cte n ON e.employee_id = n.start AND n.depth > 0
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
        ("S9-P2 Optional Modifier (?)", TestOptionalModifier),
        ("S9-P2 Star Modifier (*)", TestStarModifier),
        ("S9-P2 Plus Modifier (+)", TestPlusModifier),
        ("S9-P2 Star with Binding", TestStarWithBinding),
        ("S9-P2 Nested Modifiers", TestNestedModifiers),
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
