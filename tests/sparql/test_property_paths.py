#!/usr/bin/env python3
"""
属性路径测试 (SPARQL 1.1 Property Paths)
涵盖: 序列、反向、替代、重复路径
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestPathSequence(TestCaseBase):
    """序列路径 / : 查询员工的部门名称"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?deptName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:department_id/ex:department_name ?deptName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LIMIT 10
        """


class TestPathInverse(TestCaseBase):
    """反向路径 ^ : 查询管理某部门的经理"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?managerName ?deptName
        WHERE {
            ?mgr ex:first_name ?managerName .
            ?dept ex:manager ^ex:reports_to ?mgr ;
                  ex:department_name ?deptName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT m.first_name AS "managerName", d.department_name AS "deptName"
        FROM departments d
        JOIN employees m ON d.manager_id = m.employee_id
        LIMIT 10
        """


class TestPathAlternative(TestCaseBase):
    """替代路径 | : 查询员工的邮箱或电话"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?contact
        WHERE {
            ?emp ex:first_name ?firstName ;
                 (ex:email|ex:phone) ?contact .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        # 使用 UNION 模拟替代路径
        return """
        SELECT first_name AS "firstName", email AS "contact"
        FROM employees WHERE email IS NOT NULL
        UNION ALL
        SELECT first_name, phone FROM employees WHERE phone IS NOT NULL
        LIMIT 10
        """


class TestPathZeroOrMore(TestCaseBase):
    """零或多 * : 查询所有下属（包括间接）"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?manager ?subordinate
        WHERE {
            ?mgr ex:first_name ?manager .
            ?sub ex:reports_to* ?mgr ;
               ex:first_name ?subordinate .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        # 递归CTE模拟*路径
        return """
        WITH RECURSIVE subordinates AS (
            SELECT employee_id, first_name AS "subordinate", manager_id
            FROM employees WHERE manager_id IS NOT NULL
            UNION ALL
            SELECT e.employee_id, e.first_name, e.manager_id
            FROM employees e
            JOIN subordinates s ON e.manager_id = s.employee_id
        )
        SELECT m.first_name AS "manager", s."subordinate"
        FROM subordinates s
        JOIN employees m ON s.manager_id = m.employee_id
        LIMIT 10
        """


class TestPathOneOrMore(TestCaseBase):
    """一或多 + : 查询间接下属（不包括直接上级）"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?manager ?indirectSub
        WHERE {
            ?mgr ex:first_name ?manager .
            ?sub ex:reports_to+/ex:first_name ?indirectSub .
            ?sub ex:reports_to/ex:manager ?mid .
            FILTER(?mid != ?mgr)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        WITH RECURSIVE subordinates AS (
            SELECT employee_id, first_name, manager_id, 1 AS level
            FROM employees WHERE manager_id IS NOT NULL
            UNION ALL
            SELECT e.employee_id, e.first_name, e.manager_id, s.level + 1
            FROM employees e
            JOIN subordinates s ON e.manager_id = s.employee_id
            WHERE s.level >= 1
        )
        SELECT m.first_name AS "manager", s.first_name AS "indirectSub"
        FROM subordinates s
        JOIN employees m ON s.manager_id = m.employee_id
        WHERE s.level > 1
        LIMIT 10
        """


class TestPathOptional(TestCaseBase):
    """可选 ? : 查询可能有上级的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?managerName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:reports_to?/ex:first_name ?managerName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", m.first_name AS "managerName"
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.employee_id
        LIMIT 10
        """


class TestPathNegation(TestCaseBase):
    """否定 ! : 查询非邮箱的联系方式"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?notEmail
        WHERE {
            ?emp ex:first_name ?firstName ;
                 !(ex:email) ?notEmail .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", phone AS "notEmail"
        FROM employees
        WHERE phone IS NOT NULL
        LIMIT 10
        """


class TestPathComplex(TestCaseBase):
    """复杂组合 : 部门-职位-薪资路径"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?empName ?deptName ?positionLevel
        WHERE {
            ?emp ex:first_name ?empName ;
                 (ex:department_id|ex:position_id)/ex:department_name ?deptName ;
                 ex:position_id/ex:position_level ?positionLevel .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "empName", d.department_name AS "deptName",
               p.position_level AS "positionLevel"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        JOIN positions p ON e.position_id = p.position_id
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestPathSequence(),
        TestPathInverse(),
        TestPathAlternative(),
        TestPathZeroOrMore(),
        TestPathOneOrMore(),
        TestPathOptional(),
        TestPathNegation(),
        TestPathComplex(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_property_paths_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
