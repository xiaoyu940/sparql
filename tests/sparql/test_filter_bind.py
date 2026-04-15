#!/usr/bin/env python3
"""
FILTER 和 BIND 查询测试 (SPARQL 1.1)
涵盖: 比较运算、逻辑运算、字符串函数、BIND表达式
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestFilterNumericComparison(TestCaseBase):
    """FILTER数值比较：查询高薪员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?salary
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:salary ?salary .
            FILTER(?salary > 80000)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", salary
        FROM employees
        WHERE salary > 80000
        LIMIT 10
        """


class TestFilterStringEquality(TestCaseBase):
    """FILTER字符串比较：查询特定邮箱域名的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?email
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:email ?email .
            FILTER(CONTAINS(?email, "@company.com"))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", email
        FROM employees
        WHERE email LIKE '%@company.com%'
        LIMIT 10
        """


class TestFilterDateRange(TestCaseBase):
    """FILTER日期范围：查询最近入职的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?firstName ?lastName ?hireDate
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:hire_date ?hireDate .
            FILTER(?hireDate >= "2024-01-01"^^xsd:date)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", hire_date AS "hireDate"
        FROM employees
        WHERE hire_date >= '2024-01-01'
        LIMIT 10
        """


class TestFilterLogicalAnd(TestCaseBase):
    """FILTER逻辑AND：多条件筛选"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?salary ?deptName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:salary ?salary ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
            FILTER(?salary > 60000 && ?deptName = "Engineering")
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               e.salary, d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        WHERE e.salary > 60000 AND d.department_name = 'Engineering'
        LIMIT 10
        """


class TestBindCalculation(TestCaseBase):
    """BIND计算：计算年薪"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?annualSalary
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:salary ?monthlySalary .
            BIND((?monthlySalary * 12) AS ?annualSalary)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName",
               (salary * 12) AS "annualSalary"
        FROM employees
        LIMIT 10
        """


class TestBindStringConcat(TestCaseBase):
    """BIND字符串：拼接全名"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?fullName ?email
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:email ?email .
            BIND(CONCAT(?firstName, " ", ?lastName) AS ?fullName)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT CONCAT(first_name, ' ', last_name) AS "fullName", email
        FROM employees
        LIMIT 10
        """


class TestBindWithFilter(TestCaseBase):
    """BIND + FILTER：计算工作年限并筛选"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?firstName ?lastName ?yearsOfService
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:hire_date ?hireDate .
            BIND(YEAR(NOW()) - YEAR(?hireDate) AS ?yearsOfService)
            FILTER(?yearsOfService > 5)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName",
               (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM hire_date)) AS "yearsOfService"
        FROM employees
        WHERE (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM hire_date)) > 5
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestFilterNumericComparison(),
        TestFilterStringEquality(),
        TestFilterDateRange(),
        TestFilterLogicalAnd(),
        TestBindCalculation(),
        TestBindStringConcat(),
        TestBindWithFilter(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_filter_bind_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
