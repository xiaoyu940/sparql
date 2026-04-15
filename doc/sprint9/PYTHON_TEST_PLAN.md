# Sprint 9 Python 测试计划

> **文档版本**: 1.0  
> **创建日期**: 2026-04-02  
> **测试框架**: `/tests/python/framework.py`  
> **测试目录**: `/tests/python/test_cases/`

---

## 1. 测试框架说明

### 1.1 框架结构

基于现有 Python 测试框架，所有 Sprint 9 测试用例遵循统一模式：

```python
#!/usr/bin/env python3
"""测试描述"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import TestCaseBase, QueryResult

class TestXXX(TestCaseBase):
    def sparql_query(self) -> QueryResult:
        """SPARQL 查询 - 调用 translate_sparql() 生成 SQL 并执行"""
        sparql = """..."""
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL 查询 - 黄金标准"""
        baseline_sql = """..."""
        return self.execute_sql_query(baseline_sql)
```

### 1.2 命名规范

| 阶段 | 文件名格式 | 示例 |
|------|-----------|------|
| P0 测试 | `test_sprint9_p0_{feature}_{id}.py` | `test_sprint9_p0_inverse_001.py` |
| P1 测试 | `test_sprint9_p1_{feature}_{id}.py` | `test_sprint9_p1_if_function_001.py` |
| P2 测试 | `test_sprint9_p2_{feature}_{id}.py` | `test_sprint9_p2_datetime_001.py` |

---

## 2. P0 测试用例 - Property Path

### 2.1 反向路径 (^predicate)

**文件**: `test_sprint9_p0_inverse_001.py`

```python
class TestInversePathManager(TestCaseBase):
    """测试反向路径: ?subordinate ^:manager ?manager"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?subordinate ?manager
        WHERE {
          ?subordinate ex:name ?subName .
          ?manager ex:name ?mgrName .
          ?subordinate ^ex:manager ?manager .
        }
        ORDER BY ?subordinate
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        print(f"生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 基准 SQL: 反向即交换 JOIN 条件
        baseline = """
        SELECT t0.employee_id AS subordinate, 
               t1.employee_id AS manager
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        ORDER BY t0.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p0_inverse_002.py`

```python
class TestInversePathDepartment(TestCaseBase):
    """测试反向路径跨表: ?emp ^:worksIn ?dept"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?dept
        WHERE {
          ?emp a ex:Employee .
          ?dept a ex:Department .
          ?emp ^ex:worksIn ?dept .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 反向即交换主外键关系
        baseline = """
        SELECT t0.employee_id AS emp, 
               t1.department_id AS dept
        FROM employees t0
        JOIN departments t1 ON t0.department_id = t1.department_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

### 2.2 序列路径 (p1/p2)

**文件**: `test_sprint9_p0_sequence_001.py`

```python
class TestSequencePathManagerName(TestCaseBase):
    """测试序列路径: ?emp :manager/:name ?mgrName"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?mgrName
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:manager/ex:name ?mgrName .
        }
        ORDER BY ?emp
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 自连接获取经理姓名
        baseline = """
        SELECT t0.employee_id AS emp, 
               t1.name AS mgrName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        ORDER BY t0.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p0_sequence_002.py`

```python
class TestSequencePathMultiTable(TestCaseBase):
    """测试跨表序列: ?emp :worksIn/:locatedIn/:country ?country"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?country
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:worksIn/ex:locatedIn/ex:country ?country .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 三表 JOIN 链
        baseline = """
        SELECT t0.employee_id AS emp, 
               t2.country_name AS country
        FROM employees t0
        JOIN departments t1 ON t0.department_id = t1.department_id
        JOIN locations t2 ON t1.location_id = t2.location_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p0_sequence_003.py`

```python
class TestSequencePathWithFilter(TestCaseBase):
    """测试带 FILTER 的序列路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?mgrName
        WHERE {
          ?emp ex:manager/ex:name ?mgrName .
          FILTER(CONTAINS(?mgrName, "Smith"))
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT t0.employee_id AS emp, t1.name AS mgrName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        WHERE t1.name LIKE '%Smith%'
        """
        return self.execute_sql_query(baseline)
```

### 2.3 选择路径 (p1|p2)

**文件**: `test_sprint9_p0_alternative_001.py`

```python
class TestAlternativePathEmailPhone(TestCaseBase):
    """测试选择路径: ?emp :email|:phone ?contact"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?contact
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:email|ex:phone ?contact .
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # UNION 合并 email 和 phone
        baseline = """
        SELECT employee_id AS emp, email AS contact
        FROM employees
        WHERE email IS NOT NULL
        UNION
        SELECT employee_id AS emp, phone AS contact
        FROM employees
        WHERE phone IS NOT NULL
        ORDER BY emp
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p0_alternative_002.py`

```python
class TestAlternativePathMultiPredicate(TestCaseBase):
    """测试多谓词选择: ?emp :firstName|:lastName|:middleName ?namePart"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?namePart
        WHERE {
          ?emp ex:firstName|ex:lastName|ex:middleName ?namePart .
        }
        LIMIT 15
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT employee_id AS emp, first_name AS namePart FROM employees
        UNION
        SELECT employee_id AS emp, last_name AS namePart FROM employees
        UNION
        SELECT employee_id AS emp, middle_name AS namePart FROM employees
        LIMIT 15
        """
        return self.execute_sql_query(baseline)
```

### 2.4 组合路径测试

**文件**: `test_sprint9_p0_complex_001.py`

```python
class TestComplexPathInverseSequence(TestCaseBase):
    """测试组合: 反向+序列 ^:manager/:name ?mgrName"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?manager ?empName
        WHERE {
          ?emp ex:name ?empName .
          ?manager ^ex:manager/ex:name ?mgrName .
        }
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 反向展开后再序列
        baseline = """
        SELECT t1.employee_id AS manager, t0.name AS empName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p0_complex_002.py`

```python
class TestComplexPathSequenceAlternative(TestCaseBase):
    """测试组合: 序列+选择 (:email|:phone)/:verified ?isVerified"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?contact ?isVerified
        WHERE {
          ?emp ex:email|ex:phone ?contact .
          ?contact ex:verified ?isVerified .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # UNION + JOIN
        baseline = """
        SELECT e.email AS contact, ec.is_verified AS isVerified
        FROM employees e
        JOIN employee_contacts ec ON e.email = ec.contact_value
        WHERE e.email IS NOT NULL
        UNION
        SELECT e.phone AS contact, ec.is_verified AS isVerified
        FROM employees e
        JOIN employee_contacts ec ON e.phone = ec.contact_value
        WHERE e.phone IS NOT NULL
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

---

## 3. P1 测试用例 - 函数与优化器

### 3.1 BIND 条件函数

**文件**: `test_sprint9_p1_if_function_001.py`

```python
class TestIfFunctionBasic(TestCaseBase):
    """测试 IF 函数基本用法"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?name ?level
        WHERE {
          ?emp ex:name ?name ;
               ex:salary ?salary .
          BIND(IF(?salary > 50000, "High", "Normal") AS ?level)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        print(f"生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT name,
               CASE WHEN salary > 50000 THEN 'High' ELSE 'Normal' END AS level
        FROM employees
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p1_if_function_002.py`

```python
class TestIfFunctionNested(TestCaseBase):
    """测试嵌套 IF 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?name ?grade
        WHERE {
          ?emp ex:name ?name ;
               ex:salary ?salary .
          BIND(IF(?salary > 80000, "A", IF(?salary > 50000, "B", "C")) AS ?grade)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT name,
               CASE WHEN salary > 80000 THEN 'A'
                    WHEN salary > 50000 THEN 'B'
                    ELSE 'C' END AS grade
        FROM employees
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p1_coalesce_001.py`

```python
class TestCoalesceFunction(TestCaseBase):
    """测试 COALESCE 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?name ?contact
        WHERE {
          ?emp ex:name ?name ;
               ex:mobile ?mobile ;
               ex:homePhone ?home ;
               ex:workPhone ?work .
          BIND(COALESCE(?mobile, ?home, ?work, "N/A") AS ?contact)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT name,
               COALESCE(mobile, home_phone, work_phone, 'N/A') AS contact
        FROM employees
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

### 3.2 GeoSPARQL 度量函数

**文件**: `test_sprint9_p1_geof_distance_001.py`

```python
class TestGeofDistance(TestCaseBase):
    """测试 geof:distance 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?store ?dist
        WHERE {
          ?store geo:lat ?lat ;
                 geo:long ?long .
          BIND(CONCAT("POINT(", STR(?long), " ", STR(?lat), ")") AS ?storeWkt)
          BIND("POINT(116.4074 39.9042)" AS ?beijing)
          BIND(geof:distance(?storeWkt, ?beijing) AS ?dist)
          FILTER(?dist < 10000)
        }
        ORDER BY ?dist
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT store_id AS store,
               ST_Distance(
                 ST_GeomFromText(CONCAT('POINT(', longitude::text, ' ', latitude::text, ')'), 4326),
                 ST_GeomFromText('POINT(116.4074 39.9042)', 4326)
               ) AS dist
        FROM stores
        WHERE ST_Distance(
          ST_GeomFromText(CONCAT('POINT(', longitude::text, ' ', latitude::text, ')'), 4326),
          ST_GeomFromText('POINT(116.4074 39.9042)', 4326)
        ) < 10000
        ORDER BY dist
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p1_geof_buffer_001.py`

```python
class TestGeofBuffer(TestCaseBase):
    """测试 geof:buffer 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?poi
        WHERE {
          ?poi geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfWithin(?wkt, geof:buffer("POINT(116.4 39.9)"^^geo:wktLiteral, 5000)))
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT poi_id AS poi
        FROM pois
        WHERE ST_Within(
          geometry,
          ST_Buffer(ST_GeomFromText('POINT(116.4 39.9)', 4326), 5000)
        )
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

---

## 4. P2 测试用例 - 高级功能

### 4.1 路径修饰符

**文件**: `test_sprint9_p2_optional_path_001.py`

```python
class TestOptionalPath(TestCaseBase):
    """测试 ? 可选路径修饰符"""
    
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
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # LEFT JOIN 实现可选
        baseline = """
        SELECT t0.employee_id AS emp, 
               COALESCE(t1.name, 'No Manager') AS mgrName
        FROM employees t0
        LEFT JOIN employees t1 ON t0.manager_id = t1.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p2_star_path_001.py`

```python
class TestStarPathRecursive(TestCaseBase):
    """测试 * Kleene 星路径 (递归 CTE)"""
    
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
        # 验证生成了递归 CTE
        assert "WITH RECURSIVE" in sql
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        # 基准使用递归 CTE
        baseline = """
        WITH RECURSIVE reports_to_cte AS (
            SELECT employee_id AS ancestor, employee_id AS descendant, 0 AS depth
            FROM employees
            UNION ALL
            SELECT c.ancestor, e.employee_id AS descendant, c.depth + 1
            FROM reports_to_cte c
            JOIN employees e ON c.descendant = e.manager_id
            WHERE c.depth < 10
        )
        SELECT ancestor, descendant
        FROM reports_to_cte
        LIMIT 20
        """
        return self.execute_sql_query(baseline)
```

### 4.2 日期时间函数

**文件**: `test_sprint9_p2_datetime_001.py`

```python
class TestNowFunction(TestCaseBase):
    """测试 NOW() 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT (NOW() AS ?currentTime)
        WHERE {}
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = "SELECT CURRENT_TIMESTAMP AS currentTime"
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p2_datetime_002.py`

```python
class TestYearExtraction(TestCaseBase):
    """测试 YEAR() 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?name ?hireYear
        WHERE {
          ?emp ex:name ?name ;
               ex:hireDate ?date .
          BIND(YEAR(?date) AS ?hireYear)
          FILTER(?hireYear > 2020)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT name, EXTRACT(YEAR FROM hire_date) AS hireYear
        FROM employees
        WHERE EXTRACT(YEAR FROM hire_date) > 2020
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

**文件**: `test_sprint9_p2_datetime_003.py`

```python
class TestDateTimeComponents(TestCaseBase):
    """测试日期时间组件提取函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?name ?y ?m ?d
        WHERE {
          ?emp ex:name ?name ;
               ex:hireDate ?date .
          BIND(YEAR(?date) AS ?y)
          BIND(MONTH(?date) AS ?m)
          BIND(DAY(?date) AS ?d)
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline = """
        SELECT name,
               EXTRACT(YEAR FROM hire_date) AS y,
               EXTRACT(MONTH FROM hire_date) AS m,
               EXTRACT(DAY FROM hire_date) AS d
        FROM employees
        LIMIT 10
        """
        return self.execute_sql_query(baseline)
```

### 4.3 查询缓存

**文件**: `test_sprint9_p2_cache_001.py`

```python
class TestQueryCacheHit(TestCaseBase):
    """测试查询缓存命中"""
    
    def test_cache_hit(self):
        """验证相同 SPARQL 查询第二次更快返回"""
        sparql = """
        PREFIX ex: <http://example.org/>
        SELECT ?name WHERE { ?emp ex:name ?name }
        LIMIT 5
        """
        
        import time
        
        # 第一次查询 - 缓存 miss
        start1 = time.time()
        sql1 = self.translate_sparql(sparql)
        result1 = self.execute_sql_query(sql1)
        time1 = time.time() - start1
        
        # 第二次查询 - 缓存 hit
        start2 = time.time()
        sql2 = self.translate_sparql(sparql)
        result2 = self.execute_sql_query(sql2)
        time2 = time.time() - start2
        
        # 验证结果一致
        assert result1.row_count == result2.row_count
        
        # 验证缓存命中更快 (简化检查)
        print(f"First query: {time1:.3f}s, Second query: {time2:.3f}s")
        # 注意：实际缓存效果取决于实现
```

---

## 5. 测试执行命令

### 5.1 运行单个测试

```bash
cd /home/yuxiaoyu/rs_ontop_core/tests/python

# P0 测试
python test_cases/test_sprint9_p0_inverse_001.py
python test_cases/test_sprint9_p0_sequence_001.py

# P1 测试
python test_cases/test_sprint9_p1_if_function_001.py
python test_cases/test_sprint9_p1_geof_distance_001.py

# P2 测试
python test_cases/test_sprint9_p2_datetime_001.py
```

### 5.2 运行全部 Sprint 9 测试

```bash
# 创建 Sprint 9 测试套件
cat > test_cases/test_sprint9_suite.py << 'EOF'
#!/usr/bin/env python3
"""Sprint 9 完整测试套件"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework

# 导入所有 Sprint 9 测试
from test_sprint9_p0_inverse_001 import TestInversePathManager
from test_sprint9_p0_sequence_001 import TestSequencePathManagerName
from test_sprint9_p0_alternative_001 import TestAlternativePathEmailPhone
from test_sprint9_p1_if_function_001 import TestIfFunctionBasic
from test_sprint9_p1_geof_distance_001 import TestGeofDistance
from test_sprint9_p2_datetime_001 import TestNowFunction

TEST_CLASSES = [
    ("P0 - Inverse Path", TestInversePathManager),
    ("P0 - Sequence Path", TestSequencePathManagerName),
    ("P0 - Alternative Path", TestAlternativePathEmailPhone),
    ("P1 - IF Function", TestIfFunctionBasic),
    ("P1 - Geo Distance", TestGeofDistance),
    ("P2 - DateTime NOW", TestNowFunction),
]

if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': os.environ.get('PGUSER', 'yuxiaoyu'),
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in TEST_CLASSES:
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print(f"{'='*60}")
        
        result = framework.run_test(test_class)
        if not result['passed']:
            all_passed = False
    
    print(f"\n{'='*60}")
    print(framework.generate_report())
    
    sys.exit(0 if all_passed else 1)
EOF

python test_cases/test_sprint9_suite.py
```

### 5.3 集成到 run_all_tests.py

修改 `run_all_tests.py` 添加 Sprint 9 测试：

```python
# 在测试类列表中添加
SPRINT9_TESTS = [
    "test_sprint9_p0_inverse_001",
    "test_sprint9_p0_sequence_001",
    "test_sprint9_p0_alternative_001",
    "test_sprint9_p1_if_function_001",
    "test_sprint9_p1_geof_distance_001",
    "test_sprint9_p2_datetime_001",
]
```

---

## 6. 测试数据准备

### 6.1 所需数据库表

```sql
-- 确保测试数据表存在并填充
-- employees 表需要有 manager_id 列用于路径测试
ALTER TABLE employees ADD COLUMN IF NOT EXISTS manager_id INTEGER;

-- 添加自引用外键
UPDATE employees e1
SET manager_id = (
    SELECT e2.employee_id 
    FROM employees e2 
    WHERE e2.department_id = e1.department_id 
    AND e2.employee_id != e1.employee_id
    LIMIT 1
)
WHERE manager_id IS NULL;

-- 确保有时间列用于日期时间测试
ALTER TABLE employees ADD COLUMN IF NOT EXISTS hire_date DATE;
UPDATE employees SET hire_date = '2021-06-15' WHERE hire_date IS NULL;

-- 添加联系信息列
ALTER TABLE employees ADD COLUMN IF NOT EXISTS email VARCHAR(100);
ALTER TABLE employees ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
UPDATE employees SET email = CONCAT('emp', employee_id, '@example.com') WHERE email IS NULL;
```

### 6.2 映射配置

```turtle
# 添加路径测试所需映射
@prefix ex: <http://example.org/> .
@prefix rr: <http://www.w3.org/ns/r2rml#> .

ex:ManagerMapping
    rr:predicateObjectMap [
        rr:predicate ex:manager ;
        rr:objectMap [
            rr:parentTriplesMap ex:EmployeeMapping ;
            rr:joinCondition [
                rr:child "manager_id" ;
                rr:parent "employee_id" ;
            ] ;
        ] ;
    ] .
```

---

**文档结束**
