#!/usr/bin/env python3
"""
JOIN 和 OPTIONAL 查询测试 (SPARQL 1.1)
涵盖: 隐式JOIN、显式JOIN、左外连接(OPTIONAL)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestJoinEmployeeDepartment(TestCaseBase):
    """基础JOIN：查询员工及其部门"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?deptName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName", 
               d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LIMIT 10
        """


class TestJoinEmployeePosition(TestCaseBase):
    """多表JOIN：员工-部门-职位"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?deptName ?positionTitle
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept ;
                 ex:position_id ?pos .
            ?dept ex:department_name ?deptName .
            ?pos ex:position_title ?positionTitle .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               d.department_name AS "deptName", p.position_title AS "positionTitle"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        JOIN positions p ON e.position_id = p.position_id
        LIMIT 10
        """


class TestOptionalEmployeeSalary(TestCaseBase):
    """OPTIONAL：查询员工及其薪资（可能不存在）"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?baseSalary
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            OPTIONAL {
                ?emp ex:salary_record ?sal .
                ?sal ex:base_salary ?baseSalary .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               s.base_salary AS "baseSalary"
        FROM employees e
        LEFT JOIN salaries s ON e.employee_id = s.employee_id
        LIMIT 10
        """


class TestOptionalEmployeeProject(TestCaseBase):
    """OPTIONAL多属性：员工及其项目分配"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?projectName ?role
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            OPTIONAL {
                ?emp ex:assigned_to ?assignment .
                ?assignment ex:project ?proj ;
                          ex:role ?role .
                ?proj ex:project_name ?projectName .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               p.project_name AS "projectName", ep.role
        FROM employees e
        LEFT JOIN employee_projects ep ON e.employee_id = ep.employee_id
        LEFT JOIN projects p ON ep.project_id = p.project_id
        LIMIT 10
        """


class TestJoinWithFilter(TestCaseBase):
    """JOIN + FILTER：特定部门的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?deptName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
            FILTER(?deptName = "Engineering")
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        WHERE d.department_name = 'Engineering'
        LIMIT 10
        """


class TestNestedOptional(TestCaseBase):
    """嵌套OPTIONAL：员工-部门-经理"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?empName ?deptName ?managerName
        WHERE {
            ?emp ex:first_name ?empName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
            OPTIONAL {
                ?dept ex:manager ?mgr .
                ?mgr ex:first_name ?managerName .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "empName", d.department_name AS "deptName",
               m.first_name AS "managerName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN employees m ON d.manager_id = m.employee_id
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestJoinEmployeeDepartment(),
        TestJoinEmployeePosition(),
        TestOptionalEmployeeSalary(),
        TestOptionalEmployeeProject(),
        TestJoinWithFilter(),
        TestNestedOptional(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_join_optional_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
