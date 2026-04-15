# 测试方案说明文档

本文档详细说明 `/tests/integration` 目录下的 SPARQL-SQL 对齐验证测试方案。

## 目录

1. [测试架构概述](#1-测试架构概述)
2. [测试案例分类](#2-测试案例分类)
3. [运行方式](#3-运行方式)
4. [测试结果分析](#4-测试结果分析)
5. [扩展与维护](#5-扩展与维护)

## 1. 测试架构概述

### 1.1 核心目标

验证 SPARQL 查询翻译为 SQL 的正确性，通过以下流程：

```
SPARQL Query → [系统翻译] → SQL A → [执行] → 结果 A
                              ↕ 对比
Reference SQL B → [执行] → 结果 B
```

当结果 A 和结果 B 对齐（行数、列名、数值一致）时，测试通过。

### 1.2 文件结构

| 文件 | 功能 |
|-----|------|
| `sparql_sql_test_cases.rs` | 测试案例结构定义、默认测试套件 |
| `sparql_sql_tests.toml` | 外部配置化测试案例 |
| `test_executor.rs` | 测试执行引擎（翻译、执行、对比） |
| `sparql_sql_alignment_tests.rs` | 主测试入口 |
| `mod.rs` | 模块注册 |

### 1.3 依赖关系

```
sparql_sql_alignment_tests.rs
        ↓
  sparql_sql_test_cases.rs
        ↓
  sparql_sql_tests.toml (可选)
        ↓
  test_executor.rs → PostgreSQL (psql)
```

## 2. 测试案例分类

### 2.1 案例概览（8 个测试案例）

| ID | 名称 | 类别 | 核心验证点 |
|----|------|------|-----------|
| TC001 | Department Employee Count | aggregation | COUNT, AVG, GROUP BY, HAVING, ORDER BY |
| TC002 | Employees with Late Attendance | subquery | EXISTS 子查询 |
| TC003 | High Earners and Project Managers | union | UNION + OPTIONAL |
| TC004 | Project Assignment Path | property_path | 属性路径导航 |
| TC005 | Department Project Statistics | aggregation | COUNT DISTINCT, SUM, MAX, AVG |
| TC006 | Recent Active Employees | filter | 复杂 FILTER + 日期范围 |
| TC007 | Top Salary by Department | subquery | 嵌套子查询 + 相关性 |
| TC008 | Employee Project Assignment | optional | LEFT JOIN 处理 |

### 2.2 按类别说明

#### 2.2.1 聚合查询 (TC001, TC005)

**SPARQL 特性**:
- `COUNT()`, `SUM()`, `MAX()`, `AVG()`
- `COUNT(DISTINCT ?var)`
- `GROUP BY`
- `HAVING` 筛选

**参考 SQL 模式**:
```sql
SELECT 
    d.department_name,
    COUNT(DISTINCT ep.project_id) AS projectCount,
    SUM(ep.hours_worked) AS totalHours,
    MAX(ep.hours_worked) AS maxHours,
    AVG(ep.hours_worked) AS avgHours
FROM employees e
JOIN departments d ON ...
JOIN employee_projects ep ON ...
GROUP BY d.department_name
HAVING AVG(...) > threshold
ORDER BY totalHours DESC
```

#### 2.2.2 子查询 (TC002, TC007)

**SPARQL 特性**:
- `FILTER EXISTS { }`
- 嵌套 `SELECT` 子查询
- 相关子查询（correlated subquery）

**参考 SQL 模式**:
```sql
-- EXISTS
SELECT e.* FROM employees e
WHERE EXISTS (
    SELECT 1 FROM attendance a 
    WHERE a.employee_id = e.employee_id
    AND a.status = 'Late'
)

-- 嵌套子查询
SELECT e.* FROM employees e
WHERE e.salary >= (
    SELECT MAX(e2.salary) * 0.95
    FROM employees e2
    WHERE e2.department_id = e.department_id
)
```

#### 2.2.3 多表 JOIN (TC004, TC006)

**SPARQL 特性**:
- 多个三元组模式自动 JOIN
- 隐式属性路径展开

**参考 SQL 模式**:
```sql
SELECT CONCAT(e.first_name, ' ', e.last_name) AS empName,
       p.project_name,
       ep.role
FROM employees e
JOIN employee_projects ep ON e.employee_id = ep.employee_id
JOIN projects p ON ep.project_id = p.project_id
WHERE ep.role != 'Consultant'
ORDER BY p.project_name
```

#### 2.2.4 UNION + OPTIONAL (TC003, TC008)

**SPARQL 特性**:
- 多个 `{ } UNION { }` 模式
- `OPTIONAL { }` 左连接
- `BIND` 表达式

**参考 SQL 模式**:
```sql
-- UNION + LEFT JOIN
SELECT CONCAT(e.first_name, ' ', e.last_name) AS empName,
       CASE WHEN ... THEN 'High Earner' ELSE 'Project Manager' END AS role,
       e.salary,
       e.phone
FROM employees e
LEFT JOIN employee_projects ep ON ...
WHERE e.salary > 80000 OR ep.role = 'Manager'

-- OPTIONAL 转为 LEFT JOIN
SELECT e.first_name, e.last_name, 
       p.project_name, ep.hours_worked
FROM employees e
LEFT JOIN employee_projects ep ON e.employee_id = ep.employee_id
LEFT JOIN projects p ON ep.project_id = p.project_id
```

### 2.3 数据规模

测试基于 HR 数据集：
- departments: 100
- positions: 1,000
- employees: 100,000
- salaries: 100,000
- attendance: 3,000,000
- projects: 10,000
- employee_projects: 200,000

## 3. 运行方式

### 3.1 环境准备

**前提条件**:
```bash
# PostgreSQL 客户端已安装
which psql

# 数据库已初始化，包含 HR 数据
# 执行过 tests/script/setup_rdf_mappings.sql
# 执行过 tests/script/generate_100k_data.sql

# 环境变量（可选）
export PGPASSWORD="your_password"
```

### 3.2 运行全部测试

```bash
# 编译并运行
cargo test --test sparql_sql_alignment -- --nocapture

# 详细模式（显示生成的 SQL）
TEST_VERBOSE=1 cargo test --test sparql_sql_alignment -- --nocapture
```

### 3.3 运行单个测试

```bash
# 运行特定测试案例（需使用 #[ignore] 标记的测试）
cargo test --test sparql_sql_alignment test_individual_tc001 -- --ignored --nocapture

# 运行 SQL 数据验证测试
cargo test --test sql_data_verification -- --nocapture

# 运行单个 SQL 验证测试
cargo test --test sql_data_verification test_employees_data -- --nocapture
```

### 3.4 从 TOML 配置加载

默认行为：
1. 首先尝试加载 `tests/integration/sparql_sql_tests.toml`
2. 如果失败，使用内置默认测试套件

修改测试案例：直接编辑 `sparql_sql_tests.toml`，无需重新编译。

## 4. 测试结果分析

### 4.1 成功输出示例

```
================================================================================
SPARQL-SQL Alignment Verification Tests
================================================================================
[Test: TC001] === Department Employee Count and Average Salary ===
Translation: 45 ms
Generated SQL:
SELECT d.department_name, COUNT(e.employee_id), AVG(e.salary)
FROM employees e JOIN departments d ON ...
GROUP BY d.department_name HAVING AVG(e.salary) > 50000
ORDER BY avg_salary DESC
SPARQL->SQL: 100 rows in 120 ms
Direct SQL: 100 rows in 95 ms
--------------------------------------------------------------------------------
Test Results
--------------------------------------------------------------------------------
ID     Name                                Status     Details
--------------------------------------------------------------------------------
TC001  Department Employee Count...        PASS       OK (rows=100/100, ...)
TC002  Employees with Late...              PASS       OK (rows=200/200, ...)
...
--------------------------------------------------------------------------------
Summary: Total=8, Passed=8, Failed=0, Skipped=0, Time=1250ms
================================================================================
```

### 4.2 失败分析

**常见失败原因**:

1. **行数不匹配**
   ```
   Row count mismatch: SPARQL=50, SQL=100
   ```
   → 检查 WHERE 条件是否正确翻译

2. **列名不匹配**
   ```
   Row 0 mismatch: SPARQL: {"col_s": "1"} vs SQL: {"deptName": "..."}
   ```
   → 检查 SELECT 表达式列名映射

3. **数值不匹配**
   ```
   Numeric mismatch for 'avgSalary': 50000.5 vs 50000.6 (epsilon: 0.01)
   ```
   → 调整 `epsilon` 容差值，或检查聚合计算

4. **翻译失败**
   ```
   ERROR: Translation failed: -- Translation Error: ...
   ```
   → 检查 `ontop_translate` 函数是否正常，引擎是否已初始化

### 4.3 验证配置参数

TOML 配置中的 `[test_cases.validation]` 段：

```toml
[test_cases.validation]
ignore_columns = []           # 忽略的列（如内部生成 ID）
sort_before_compare = true    # 比较前是否排序
sort_keys = ["deptName"]      # 排序键（多列支持）
epsilon = 0.01               # 浮点数比较容差
row_limit = 100              # 最大返回行数
```

## 5. 扩展与维护

### 5.1 添加新测试案例

**方法一：编辑 TOML（推荐）**

在 `sparql_sql_tests.toml` 末尾添加：

```toml
[[test_cases]]
id = "TC009"
name = "New Test Case"
description = "描述测试目的"
category = "aggregation"  # 或 join/subquery/filter/etc
enabled = true

sparql = """
PREFIX ex: <http://example.org/>
SELECT ?var1 ?var2
WHERE { ... }
"""

reference_sql = """
SELECT col1, col2 FROM ...
"""

[test_cases.validation]
ignore_columns = []
sort_before_compare = true
sort_keys = ["var1"]
epsilon = 0.01
row_limit = 100
```

**方法二：修改 Rust 代码**

在 `sparql_sql_test_cases.rs` 中：

```rust
fn create_test_case_9() -> TestCase {
    TestCase {
        id: "TC009".to_string(),
        name: "New Test".to_string(),
        // ...
    }
}
```

并添加到 `create_default_test_suite()` 中。

### 5.2 调试技巧

**手动测试翻译**:
```bash
psql -U yuxiaoyu -d rs_ontop_core

SELECT ontop_refresh();

SELECT ontop_translate('
PREFIX ex: <http://example.org/>
SELECT ?s WHERE { ?s a ex:Employee }
');
```

**检查映射加载**:
```sql
SELECT * FROM ontop_mappings LIMIT 5;
SELECT * FROM ontop_ontology_snapshots;
```

### 5.3 性能基准

测试框架自动记录各阶段耗时：
- **Translation**: SPARQL → SQL 翻译时间
- **Execution**: SQL 执行时间

预期性能（参考）:
- 简单 JOIN: < 100ms
- 复杂聚合: < 200ms
- 子查询: < 300ms

---

**文档版本**: v1.0  
**最后更新**: 2026-03-30  
**维护者**: 测试团队
