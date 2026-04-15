# SPARQL HTTP 测试框架

基于 SPARQL 1.1/1.2 协议的 HTTP 接口测试框架，结合 HR 业务场景验证 SPARQL 到 SQL 的转换正确性。

## 架构说明

- **SPARQL Endpoint**: `http://localhost:5280/sparql` (HTTP协议)
- **SQL Baseline**: `localhost:5432/rs_ontop_core` (PostgreSQL)
- **验证方式**: SPARQL查询结果与手工编写的SQL基线进行比对

## 文件结构

```
tests/sparql/
├── framework.py              # 测试框架核心
├── test_basic_select.py    # 基础SELECT测试
├── test_join_optional.py   # JOIN和OPTIONAL测试
├── test_filter_bind.py     # FILTER和BIND测试
├── test_aggregate_subquery.py  # 聚合和子查询测试
├── test_union_advanced.py  # UNION和高级特性测试
├── run_all_tests.py        # 主运行脚本
└── README.md               # 本文档
```

## 测试类别

### 1. 基础SELECT查询 (test_basic_select.py)
- 基本三元组模式查询
- 特定属性选择
- ORDER BY排序
- DISTINCT去重
- COUNT聚合
- ASK存在性查询

### 2. JOIN和OPTIONAL (test_join_optional.py)
- 隐式JOIN（多三元组）
- 多表JOIN（员工-部门-职位）
- OPTIONAL左外连接
- JOIN + FILTER组合
- 嵌套OPTIONAL

### 3. FILTER和BIND (test_filter_bind.py)
- 数值比较运算
- 字符串匹配
- 日期范围筛选
- 逻辑运算（AND/OR）
- BIND表达式计算
- 字符串拼接
- 条件分类（IF）

### 4. 聚合和子查询 (test_aggregate_subquery.py)
- COUNT/SUM/AVG/MIN/MAX
- GROUP BY分组
- HAVING过滤
- EXISTS子查询
- NOT EXISTS子查询
- 标量子查询

### 5. UNION和高级特性 (test_union_advanced.py)
- UNION并集
- VALUES内联数据
- IN/NOT IN过滤器
- COALESCE空值处理
- IF条件表达式
- MINUS差集
- SERVICE跨源查询

## 使用方法

### 运行单个测试文件
```bash
python test_basic_select.py
python test_join_optional.py
python test_filter_bind.py
python test_aggregate_subquery.py
python test_union_advanced.py
```

### 运行全部测试
```bash
python run_all_tests.py
```

### 运行特定测试类
```python
from test_basic_select import TestFilterNumericComparison
test = TestFilterNumericComparison()
result = test.run()
print(result)
```

## 测试框架API

### TestCaseBase 抽象类

继承此类创建新测试案例：

```python
class MyTestCase(TestCaseBase):
    def sparql_query(self) -> str:
        return "SELECT ... WHERE { ... }"
    
    def baseline_sql(self) -> str:
        return "SELECT ... FROM ..."
```

### QueryResult 数据类

```python
@dataclass
class QueryResult:
    columns: List[str]           # 列名
    rows: List[Dict]             # 数据行
    row_count: int              # 行数
    passed: bool                # 是否通过
    error: Optional[str]        # 错误信息
    execution_time_ms: float    # 执行时间
```

### 结果对比逻辑

框架自动对比：
1. 错误状态（均无错误才继续）
2. 行数是否一致
3. 首行数据值是否匹配（支持类型转换）

## 扩展测试案例

创建新测试文件的模板：

```python
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite

class TestMyFeature(TestCaseBase):
    \"\"\"测试描述\"\"\"
    
    def sparql_query(self) -> str:
        return \"\"\"
        PREFIX ex: <http://example.org/>
        SELECT ?var
        WHERE {
            ?s ex:predicate ?var .
        }
        \"\"\"
    
    def baseline_sql(self) -> str:
        return \"\"\"
        SELECT column AS var FROM table
        \"\"\"

if __name__ == "__main__":
    test_cases = [TestMyFeature()]
    results = run_test_suite(test_cases, "results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
```

## HR业务数据模型

测试案例基于以下数据模型：

### 实体
- **Employee**: 员工 (employees表)
- **Department**: 部门 (departments表)
- **Position**: 职位 (positions表)
- **Salary**: 薪资 (salaries表)
- **Project**: 项目 (projects表)
- **Attendance**: 考勤 (attendance表)

### 常用属性
| SPARQL属性 | SQL列 | 说明 |
|-----------|-------|------|
| ex:first_name | first_name | 名 |
| ex:last_name | last_name | 姓 |
| ex:email | email | 邮箱 |
| ex:salary | salary | 薪资 |
| ex:department_id | department_id | 部门ID |
| ex:department_name | department_name | 部门名 |
| ex:hire_date | hire_date | 入职日期 |

## 故障排除

### SPARQL Endpoint 连接失败
```
Connection error: Is the SPARQL endpoint running at http://localhost:5280/sparql?
```
**解决**: 确保PostgreSQL扩展已加载，HTTP服务已启动

### SQL 基线不匹配
```
Row count mismatch: SPARQL=5, SQL=3
```
**解决**: 检查SQL是否正确表达了SPARQL的语义

### 值类型不匹配
```
Value mismatch for 'salary': SPARQL='50000', SQL='50000.00'
```
**解决**: 这是正常现象，框架会进行类型转换后比较

## 依赖

```bash
pip install requests psycopg2-binary
```

## 贡献指南

添加新测试案例时：
1. 选择合适的测试类别文件
2. 继承 `TestCaseBase`
3. 实现 `sparql_query()` 和 `baseline_sql()`
4. 确保SQL语义正确对应SPARQL
5. 运行验证通过

## 许可证

RS Ontop Core 测试框架
