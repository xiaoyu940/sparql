#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class HttpRegressionBase(TestCaseBase):
    QUERY = ""
    EXPECTED_VARS = []
    NAME = ""

    def sparql_query(self) -> QueryResult:
        return self.execute_sparql_http(self.QUERY)

    def sql_query(self) -> QueryResult:
        # Plan 3 for bug 5820 must validate the real 5820 path, not SQL translation.
        return QueryResult(columns=[], rows=[], row_count=0)

    def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult):
        errors = []
        if sparql_result.error:
            errors.append(f"HTTP regression query failed: {sparql_result.error}")

        columns = sparql_result.columns or []
        for var in self.EXPECTED_VARS:
            if var not in columns:
                errors.append(f"Missing expected variable '{var}' in SPARQL head: {columns}")

        if sparql_result.rows is None:
            errors.append("SPARQL result rows is None")

        return len(errors) == 0, errors


class TestHttpClassIsIri(HttpRegressionBase):
    NAME = "class isIRI"
    QUERY = "SELECT DISTINCT ?class WHERE { ?s a ?class . FILTER(isIRI(?class)) } LIMIT 10"
    EXPECTED_VARS = ["class"]


class TestHttpPredicateObjectIri(HttpRegressionBase):
    NAME = "predicate object isIRI"
    QUERY = "SELECT DISTINCT ?p WHERE { ?s ?p ?o . FILTER(isIRI(?o)) FILTER(isIRI(?p)) } LIMIT 10"
    EXPECTED_VARS = ["p"]


class TestHttpPredicateObjectNotIri(HttpRegressionBase):
    NAME = "predicate object not isIRI"
    QUERY = "SELECT DISTINCT ?p WHERE { ?s ?p ?o . FILTER(!isIRI(?o)) FILTER(isIRI(?p)) } LIMIT 10"
    EXPECTED_VARS = ["p"]


class TestHttpSubjectIri(HttpRegressionBase):
    NAME = "subject isIRI"
    QUERY = "SELECT DISTINCT ?s WHERE { ?s ?p ?o . FILTER(isIRI(?s)) } LIMIT 10"
    EXPECTED_VARS = ["s"]


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '12345678'),
    }

    tests = [
        ("HTTP regression: ?s a ?class + isIRI(?class)", TestHttpClassIsIri),
        ("HTTP regression: ?s ?p ?o + isIRI(?o) + isIRI(?p)", TestHttpPredicateObjectIri),
        ("HTTP regression: ?s ?p ?o + !isIRI(?o) + isIRI(?p)", TestHttpPredicateObjectNotIri),
        ("HTTP regression: ?s ?p ?o + isIRI(?s)", TestHttpSubjectIri),
    ]

    all_passed = True
    for name, test_class in tests:
        print()
        print("=" * 80)
        print(f"Test: {name}")
        print("=" * 80)
        result = run_test_case(test_class, db_config)
        if not result['passed']:
            all_passed = False
            print(f"FAILED: {result['errors']}")

    sys.exit(0 if all_passed else 1)
