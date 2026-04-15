#!/usr/bin/env python3
"""
聚合函数和子查询测试 (SPARQL 1.1)
涵盖: COUNT, SUM, AVG, MIN, MAX, GROUP BY, HAVING, 子查询
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestAggregateCountByDepartment(TestCaseBase):
    """聚合：按部门统计员工数"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?deptName (COUNT(?emp) AS ?empCount)
        WHERE {
            ?emp ex:department_id ?dept ;
                 ex:first_name ?fn .
            ?dept ex:department_name ?deptName .
        }
        GROUP BY ?deptName
        ORDER BY DESC(?empCount)
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT d.department_name AS "deptName", COUNT(*) AS "empCount"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        ORDER BY "empCount" DESC
        LIMIT 10
        """


class TestAggregateAvgSalary(TestCaseBase):
    """聚合：计算部门平均薪资"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?deptName (AVG(?salary) AS ?avgSalary) (MAX(?salary) AS ?maxSalary)
        WHERE {
            ?emp ex:department_id ?dept ;
                 ex:salary ?salary .
            ?dept ex:department_name ?deptName .
        }
        GROUP BY ?deptName
        HAVING (AVG(?salary) > 50000)
        ORDER BY DESC(?avgSalary)
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT d.department_name AS "deptName",
               AVG(e.salary) AS "avgSalary",
               MAX(e.salary) AS "maxSalary"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        HAVING AVG(e.salary) > 50000
        ORDER BY "avgSalary" DESC
        LIMIT 10
        """


class TestAggregateSum(TestCaseBase):
    """聚合：计算部门总薪资支出"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?deptName (SUM(?salary) AS ?totalSalary) (COUNT(?emp) AS ?headCount)
        WHERE {
            ?emp ex:department_id ?dept ;
                 ex:salary ?salary .
            ?dept ex:department_name ?deptName .
        }
        GROUP BY ?deptName
        ORDER BY DESC(?totalSalary)
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT d.department_name AS "deptName",
               SUM(e.salary) AS "totalSalary",
               COUNT(*) AS "headCount"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        ORDER BY "totalSalary" DESC
        LIMIT 10
        """


class TestSubqueryExists(TestCaseBase):
    """子查询：EXISTS - 查询有项目的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            FILTER EXISTS {
                ?emp ex:assigned_to ?assignment .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName"
        FROM employees e
        WHERE EXISTS (SELECT 1 FROM employee_projects ep WHERE ep.employee_id = e.employee_id)
        LIMIT 10
        """


class TestSubqueryNotExists(TestCaseBase):
    """子查询：NOT EXISTS - 查询没有项目的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            FILTER NOT EXISTS {
                ?emp ex:assigned_to ?assignment .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName"
        FROM employees e
        WHERE NOT EXISTS (SELECT 1 FROM employee_projects ep WHERE ep.employee_id = e.employee_id)
        LIMIT 10
        """


class TestSubqueryScalar(TestCaseBase):
    """子查询：标量子查询 - 查询薪资高于平均水平的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?salary
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:salary ?salary .
            FILTER(?salary > (SELECT (AVG(?s) AS ?avgSal) WHERE { ?e ex:salary ?s }))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", salary
        FROM employees
        WHERE salary > (SELECT AVG(salary) FROM employees)
        LIMIT 10
        """


class TestGroupByMultiple(TestCaseBase):
    """多列分组：按部门和职位统计"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?deptName ?positionTitle (COUNT(?emp) AS ?count) (AVG(?salary) AS ?avgSalary)
        WHERE {
            ?emp ex:department_id ?dept ;
                 ex:position_id ?pos ;
                 ex:salary ?salary .
            ?dept ex:department_name ?deptName .
            ?pos ex:position_title ?positionTitle .
        }
        GROUP BY ?deptName ?positionTitle
        ORDER BY ?deptName DESC(?count)
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT d.department_name AS "deptName", p.position_title AS "positionTitle",
               COUNT(*) AS "count", AVG(e.salary) AS "avgSalary"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        JOIN positions p ON e.position_id = p.position_id
        GROUP BY d.department_name, p.position_title
        ORDER BY d.department_name, "count" DESC
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestAggregateCountByDepartment(),
        TestAggregateAvgSalary(),
        TestAggregateSum(),
        TestSubqueryExists(),
        TestSubqueryNotExists(),
        TestSubqueryScalar(),
        TestGroupByMultiple(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_aggregate_subquery_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
