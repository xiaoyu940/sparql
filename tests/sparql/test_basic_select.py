#!/usr/bin/env python3
"""
基础 SELECT 查询测试 (SPARQL 1.1)
涵盖: 基本三元组模式、变量绑定、简单投影
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestBasicSelectAllEmployees(TestCaseBase):
    """基础查询：获取所有员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?emp ?firstName ?lastName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT employee_id AS emp, first_name AS "firstName", last_name AS "lastName"
        FROM employees
        LIMIT 10
        """


class TestSelectSpecificColumns(TestCaseBase):
    """查询特定属性：员工姓名和邮箱"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?email
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:email ?email .
        }
        LIMIT 5
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", email
        FROM employees
        LIMIT 5
        """


class TestSelectWithOrderBy(TestCaseBase):
    """排序查询：按入职日期排序"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?hireDate
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:hire_date ?hireDate .
        }
        ORDER BY DESC(?hireDate)
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", hire_date AS "hireDate"
        FROM employees
        ORDER BY hire_date DESC
        LIMIT 10
        """


class TestSelectDistinctDepartments(TestCaseBase):
    """去重查询：获取所有不重复的部门"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT DISTINCT ?deptName
        WHERE {
            ?dept ex:department_name ?deptName .
        }
        ORDER BY ?deptName
        LIMIT 20
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT DISTINCT department_name AS "deptName"
        FROM departments
        ORDER BY department_name
        LIMIT 20
        """


class TestSelectCountEmployees(TestCaseBase):
    """计数查询：统计员工总数"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT (COUNT(?emp) AS ?totalEmployees)
        WHERE {
            ?emp ex:first_name ?fn .
        }
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT COUNT(*) AS "totalEmployees"
        FROM employees
        """


class TestAskEmployeeExists(TestCaseBase):
    """ASK查询：检查是否存在员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        ASK {
            ?emp ex:first_name ?fn .
        }
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT EXISTS(SELECT 1 FROM employees) AS result
        """


if __name__ == "__main__":
    test_cases = [
        TestBasicSelectAllEmployees(),
        TestSelectSpecificColumns(),
        TestSelectWithOrderBy(),
        TestSelectDistinctDepartments(),
        TestSelectCountEmployees(),
        TestAskEmployeeExists(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_basic_select_results.json")
    
    # 如果有失败，退出码非0
    sys.exit(0 if all(r["passed"] for r in results) else 1)
