#!/usr/bin/env python3
"""
CONSTRUCT 查询和 GRAPH 命名图测试 (SPARQL 1.1)
涵盖: CONSTRUCT WHERE, CONSTRUCT 模板, GRAPH ?g, FROM NAMED
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestConstructBasic(TestCaseBase):
    """基础 CONSTRUCT: 构造员工RDF图"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        CONSTRUCT {
            ?emp a ex:Employee ;
                 ex:name ?fullName ;
                 ex:worksIn ?deptName .
        }
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
            BIND(CONCAT(?firstName, " ", ?lastName) AS ?fullName)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        # CONSTRUCT 返回三元组，简化为SELECT验证
        return """
        SELECT e.employee_id AS "emp", 
               CONCAT(e.first_name, ' ', e.last_name) AS "fullName",
               d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LIMIT 10
        """


class TestConstructWhere(TestCaseBase):
    """CONSTRUCT WHERE 简写形式"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        CONSTRUCT WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:email ?email .
        }
        LIMIT 5
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT employee_id AS "emp", first_name AS "firstName",
               last_name AS "lastName", email
        FROM employees
        LIMIT 5
        """


class TestGraphVariable(TestCaseBase):
    """GRAPH 变量: 从命名图查询"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?g ?firstName ?deptName
        WHERE {
            GRAPH ?g {
                ?emp ex:first_name ?firstName ;
                     ex:department_id ?dept .
                ?dept ex:department_name ?deptName .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        # GRAPH 在SQL中可能通过分区或标记实现
        return """
        SELECT 'http://example.org/graph/hr' AS "g",
               e.first_name AS "firstName",
               d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LIMIT 10
        """


class TestGraphNamed(TestCaseBase):
    """GRAPH 常量: 指定命名图"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?salary
        FROM NAMED <http://example.org/graph/employees>
        WHERE {
            GRAPH <http://example.org/graph/employees> {
                ?emp ex:first_name ?firstName ;
                     ex:salary ?salary .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", salary
        FROM employees
        LIMIT 10
        """


class TestGraphUnion(TestCaseBase):
    """多图联合查询"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?source
        WHERE {
            {
                GRAPH <http://example.org/graph/hr> {
                    ?emp ex:first_name ?firstName .
                    BIND("HR" AS ?source)
                }
            }
            UNION
            {
                GRAPH <http://example.org/graph/crm> {
                    ?cust ex:contact_name ?firstName .
                    BIND("CRM" AS ?source)
                }
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", 'HR' AS "source"
        FROM employees
        LIMIT 10
        """


class TestConstructTemplate(TestCaseBase):
    """CONSTRUCT 复杂模板: 创建组织架构图"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        CONSTRUCT {
            ?dept a ex:Department ;
                  ex:hasEmployee ?emp ;
                  ex:managedBy ?mgr .
            ?emp ex:reportsTo ?mgr .
        }
        WHERE {
            ?emp ex:first_name ?empName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName ;
                  ex:manager ?mgr .
            ?mgr ex:first_name ?mgrName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT d.department_id AS "dept", e.employee_id AS "emp",
               m.employee_id AS "mgr"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN employees m ON d.manager_id = m.employee_id
        LIMIT 10
        """


class TestFromGraph(TestCaseBase):
    """FROM 指定默认图"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName
        FROM <http://example.org/graph/current>
        WHERE {
            ?emp ex:first_name ?firstName .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName"
        FROM employees
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestConstructBasic(),
        TestConstructWhere(),
        TestGraphVariable(),
        TestGraphNamed(),
        TestGraphUnion(),
        TestConstructTemplate(),
        TestFromGraph(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_construct_graph_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
