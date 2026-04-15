#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from test_cases.test_sprint8_exists_001 import TestExistsBasic

db_config = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'database': 'ontop_test',
    'password': ''
}

test = TestExistsBasic(db_config)

sparql = """SELECT ?dept ?name WHERE {
  ?dept <http://example.org/dept_name> ?name .
  FILTER EXISTS {
    ?emp <http://example.org/department_id> ?dept .
  }
}"""

print("Testing EXISTS translation...")
sql = test.translate_sparql(sparql)
print("Generated SQL:")
print(sql)
print()

if 'EXISTS' in sql.upper():
    print("✅ EXISTS clause found!")
else:
    print("❌ EXISTS clause NOT found!")
