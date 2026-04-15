#!/usr/bin/env python3
"""
字符串函数测试 (SPARQL 1.1 String Functions)
涵盖: strlen, substr, ucase, lcase, strstarts, strends, replace
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestStrlenFunction(TestCaseBase):
    """字符串长度 STRLEN()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?nameLength
        WHERE {
            ?emp ex:first_name ?firstName .
            BIND(STRLEN(?firstName) AS ?nameLength)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", LENGTH(first_name) AS "nameLength"
        FROM employees
        LIMIT 10
        """


class TestUcaseFunction(TestCaseBase):
    """转大写 UCASE()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?upperName
        WHERE {
            ?emp ex:first_name ?firstName .
            BIND(UCASE(?firstName) AS ?upperName)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", UPPER(first_name) AS "upperName"
        FROM employees
        LIMIT 10
        """


class TestLcaseFunction(TestCaseBase):
    """转小写 LCASE()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lowerName
        WHERE {
            ?emp ex:first_name ?firstName .
            BIND(LCASE(?firstName) AS ?lowerName)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", LOWER(first_name) AS "lowerName"
        FROM employees
        LIMIT 10
        """


class TestSubstrFunction(TestCaseBase):
    """子字符串 SUBSTR()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?email ?domain
        WHERE {
            ?emp ex:email ?email .
            BIND(SUBSTR(?email, STRLEN(?email) - 12) AS ?domain)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT email, SUBSTRING(email FROM LENGTH(email) - 12) AS "domain"
        FROM employees
        LIMIT 10
        """


class TestStrstartsFunction(TestCaseBase):
    """字符串开头检查 STRSTARTS()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName
        WHERE {
            ?emp ex:first_name ?firstName .
            FILTER(STRSTARTS(?firstName, "John"))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName"
        FROM employees
        WHERE first_name LIKE 'John%'
        LIMIT 10
        """


class TestStrendsFunction(TestCaseBase):
    """字符串结尾检查 STRENDS()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?email
        WHERE {
            ?emp ex:email ?email .
            FILTER(STRENDS(?email, ".com"))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT email
        FROM employees
        WHERE email LIKE '%.com'
        LIMIT 10
        """


class TestReplaceFunction(TestCaseBase):
    """字符串替换 REPLACE()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?email ?maskedEmail
        WHERE {
            ?emp ex:email ?email .
            BIND(REPLACE(?email, "@company.com", "@***.com") AS ?maskedEmail)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT email, REPLACE(email, '@company.com', '@***.com') AS "maskedEmail"
        FROM employees
        LIMIT 10
        """


class TestRegexFunction(TestCaseBase):
    """正则匹配 REGEX()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?phone
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:phone ?phone .
            FILTER(REGEX(?phone, "^[0-9]{3}-[0-9]{4}$"))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", phone
        FROM employees
        WHERE phone ~ '^[0-9]{3}-[0-9]{4}$'
        LIMIT 10
        """


class TestStrbeforeFunction(TestCaseBase):
    """字符串前部 STRBEFORE()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?email ?localPart
        WHERE {
            ?emp ex:email ?email .
            BIND(STRBEFORE(?email, "@") AS ?localPart)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT email, SPLIT_PART(email, '@', 1) AS "localPart"
        FROM employees
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestStrlenFunction(),
        TestUcaseFunction(),
        TestLcaseFunction(),
        TestSubstrFunction(),
        TestStrstartsFunction(),
        TestStrendsFunction(),
        TestReplaceFunction(),
        TestRegexFunction(),
        TestStrbeforeFunction(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_string_functions_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
