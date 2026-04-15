# RS Ontop Core 测试方案总览文档

本文档汇总 `/tests/integration` 目录下所有测试方案的详细说明。

## 目录结构

```
tests/integration/
├── README.md                          # SPARQL-SQL对齐验证测试主文档
├── TEST_SUITE_DOCUMENTATION.md        # 本文档 - 测试方案总览
├── mod.rs                             # 模块注册
├── sparql_sql_test_cases.rs           # 测试案例定义（新）
├── sparql_sql_tests.toml              # TOML配置（新）
├── test_executor.rs                   # 执行引擎（新）
├── sparql_sql_alignment_tests.rs      # 主测试入口（新）
├── bulk_verify.rs                     # 批量验证测试
├── complex_sparql_suite.rs            # 50个复杂SPARQL查询测试套件
├── postgresql_integration_test.rs     # PostgreSQL集成测试
├── sql_execution_tests.rs             # SQL执行测试
├── sql_result_accuracy_tests.rs       # SQL结果准确性验证
├── performance_benchmarks.rs          # 性能基准测试
└── stress_tests.rs                    # 压力测试
```

---

## 1. SPARQL-SQL对齐验证测试 (sparql_sql_alignment_tests.rs)

**文档**: [README.md](./README.md)

### 1.1 核心目标
验证SPARQL查询翻译为SQL的正确性，通过双路执行对比机制：

```
SPARQL查询 → [系统翻译] → SQL A → [执行] → 结果 A
                                    ↕ 对比
参考SQL B → [执行] → 结果 B
```

### 1.2 测试案例 (8个)

| ID | 名称 | 类别 | 核心验证点 |
|----|------|------|-----------|
| TC001 | Department Employee Count | aggregation | COUNT, AVG, GROUP BY, HAVING |
| TC002 | Employees with Late Attendance | subquery | EXISTS子查询 |
| TC003 | High Earners and Project Managers | union | UNION + OPTIONAL |
| TC004 | Project Assignment Path | property_path | 属性路径导航 |
| TC005 | Department Project Statistics | aggregation | COUNT DISTINCT, SUM, MAX, AVG |
| TC006 | Recent Active Employees | filter | 复杂FILTER + 日期范围 |
| TC007 | Top Salary by Department | subquery | 嵌套子查询 + 相关性 |
| TC008 | Employee Project Assignment | optional | LEFT JOIN处理 |

### 1.3 运行方式

```bash
# 运行全部测试
cargo test --test sparql_sql_alignment -- --nocapture

# 详细模式
TEST_VERBOSE=1 cargo test --test sparql_sql_alignment -- --nocapture

# 单个测试
cargo test --test sparql_sql_alignment test_individual_tc001 -- --ignored
```

---

## 2. 批量验证测试 (bulk_verify.rs)

### 2.1 核心目标
从外部Markdown文件加载批量测试案例，验证HR环境完整映射配置的翻译正确性。

### 2.2 关键特性
- **完整HR环境**: 包含6个表（employees, departments, job_history, attendance, bonuses, salaries）
- **外键约束**: 完整的表间关系定义
- **批量加载**: 从Markdown文件读取测试案例
- **30+映射规则**: 覆盖完整的HR领域谓词

### 2.3 数据结构

```rust
// 完整表元数据定义
metadata.insert("employees", TableMetadata {
    columns: vec!["employee_id", "first_name", ..., "created_at"],
    primary_keys: vec!["employee_id"],
    foreign_keys: vec![
        ForeignKey { local_columns: ["department_id"], target_table: "departments" },
        ForeignKey { local_columns: ["manager_id"], target_table: "employees" },
    ],
    not_null_columns: vec!["employee_id", "first_name", ...],
});

// 映射规则示例
mappings.insert_mapping(MappingRule {
    predicate: "http://example.org/firstName",
    table_name: "employees",
    position_to_column: [(0, "employee_id"), (1, "first_name")],
});
```

### 2.4 运行方式

```bash
cargo test --test integration bulk_verify_md_cases -- --nocapture
```

---

## 3. 50个复杂SPARQL查询测试套件 (complex_sparql_suite.rs)

### 3.1 核心目标
系统化覆盖SPARQL各类查询场景，共50个测试案例。

### 3.2 测试分类

| 类别 | 数量 | 覆盖场景 |
|------|------|---------|
| 基础查询 | 5 | 单表单列、多列、带条件 |
| 单表多属性 | 5 | 同一实体的多个属性查询 |
| JOIN查询 | 10 | 两表JOIN、三表JOIN、多条件JOIN |
| FILTER条件 | 10 | 数值比较、字符串匹配、逻辑组合 |
| 聚合函数 | 5 | COUNT, SUM, AVG, MAX, MIN |
| ORDER BY/LIMIT | 5 | 排序、分页、Top-N |
| 复杂组合 | 10 | 多子句组合查询 |

### 3.3 测试示例

```rust
// 测试方法命名规范: test_类别_序号_描述
fn test_join_01_employee_department() {
    let sparql = r#"
        SELECT ?firstName ?lastName ?deptName
        WHERE {
            ?emp <http://example.org/employee#firstName> ?firstName .
            ?emp <http://example.org/employee#lastName> ?lastName .
            ?emp <http://example.org/employee#department> ?dept .
            ?dept <http://example.org/department#name> ?deptName .
        }
    "#;
    // 验证翻译生成的SQL包含JOIN
}
```

### 3.4 运行方式

```bash
# 运行全部50个测试
cargo test --test integration -- --nocapture 2>&1 | grep "test_"

# 运行特定类别
# 类别: basic, multi_prop, join, filter, aggregate, order_limit, complex
cargo test --test integration test_join -- --nocapture
```

---

## 4. PostgreSQL集成测试 (postgresql_integration_test.rs)

### 4.1 核心目标
连接真实PostgreSQL数据库，执行生成的SQL并验证结果准确性。

### 4.2 连接配置

```rust
// 从环境变量或默认值加载
fn pg_host() -> &'static str { option_env!("PG_HOST").unwrap_or("localhost") }
fn pg_port() -> &'static str { option_env!("PG_PORT").unwrap_or("5432") }
fn pg_user() -> &'static str { option_env!("PG_USER").unwrap_or("yuxiaoyu") }
fn pg_database() -> &'static str { option_env!("PG_DATABASE").unwrap_or("rs_ontop_core") }
```

### 4.3 测试流程

1. **解析SPARQL** → IR表示
2. **优化** → UnfoldingPass应用映射展开
3. **生成SQL** → FlatSQLGenerator生成最终SQL
4. **执行验证** → psql执行并验证结果

### 4.4 常量定义（避免硬编码）

```rust
const NAMESPACE_EMPLOYEE: &str = "http://example.org/employee#";
const NAMESPACE_DEPARTMENT: &str = "http://example.org/department#";
const PREDICATE_FIRST_NAME: &str = "http://example.org/employee#firstName";
const PREDICATE_LAST_NAME: &str = "http://example.org/employee#lastName";
// ... 更多谓词常量
const TABLE_EMPLOYEES: &str = "employees";
const TABLE_DEPARTMENTS: &str = "departments";
const COL_EMPLOYEE_ID: &str = "employee_id";
// ... 更多列名常量
```

### 4.5 运行方式

```bash
# 设置环境变量（可选）
export PG_HOST=localhost
export PG_PORT=5432
export PG_USER=yuxiaoyu
export PG_DATABASE=rs_ontop_core

# 运行测试
cargo test --test integration postgresql_integration -- --nocapture
```

---

## 5. SQL执行测试 (sql_execution_tests.rs)

### 5.1 核心目标
验证生成的SQL在PostgreSQL上的执行能力和基本正确性。

### 5.2 测试覆盖

- **简单SELECT**: 单列、多列、全部列
- **WHERE条件**: 等值、范围、模式匹配
- **JOIN操作**: INNER JOIN、LEFT JOIN
- **聚合查询**: GROUP BY + 聚合函数
- **排序分页**: ORDER BY、LIMIT、OFFSET

### 5.3 元数据结构

```rust
fn create_hr_metadata() -> HashMap<String, Arc<TableMetadata>> {
    let mut map = HashMap::new();
    
    map.insert("employees", Arc::new(TableMetadata {
        table_name: "employees".to_string(),
        columns: vec!["employee_id", "first_name", "last_name", 
                     "email", "department_id", "salary"],
        primary_keys: vec!["employee_id"],
        foreign_keys: vec![],
        unique_constraints: vec![],
        check_constraints: vec![],
        not_null_columns: vec!["employee_id"],
    }));
    
    map.insert("departments", Arc::new(TableMetadata {
        table_name: "departments".to_string(),
        columns: vec!["department_id", "department_name", "location"],
        // ...
    }));
    
    map
}
```

### 5.4 运行方式

```bash
cargo test --test integration sql_execution -- --nocapture
```

---

## 6. SQL结果准确性验证 (sql_result_accuracy_tests.rs)

### 6.1 核心目标
深度验证SQL执行结果的准确性，包括数据类型、数值精度、行数匹配。

### 6.2 验证维度

| 维度 | 验证内容 |
|------|---------|
| 行数匹配 | 返回行数是否符合预期 |
| 列完整性 | 所有期望列是否存在 |
| 数据类型 | 数值、字符串、日期类型正确性 |
| 数值精度 | 浮点数聚合结果精度验证 |
| 排序正确性 | ORDER BY结果顺序验证 |
| 空值处理 | NULL值正确传递 |

### 6.3 精度验证示例

```rust
fn test_aggregate_avg_precision() {
    let sparql = "SELECT (AVG(?salary) AS ?avgSalary) ...";
    let sql = translate(sparql);
    let results = execute_sql(&sql);
    
    // 验证数值精度（误差<0.01）
    assert!(results[0]["avgSalary"].parse::<f64>().unwrap() - expected < 0.01);
}
```

### 6.4 运行方式

```bash
cargo test --test integration sql_result_accuracy -- --nocapture
```

---

## 7. 性能基准测试 (performance_benchmarks.rs)

### 7.1 核心目标
验证系统在负载下的翻译吞吐量和响应时间。

### 7.2 测试内容

```rust
#[test]
#[ignore = "Benchmark-style test; run manually in CI/perf job"]
fn translate_throughput_smoke() {
    let engine = OntopEngine::new(...);
    
    let mut ok = 0usize;
    for _ in 0..500 {  // 500次翻译
        if engine.translate("SELECT ?s ?p ?o WHERE { ?s ?p ?o }").is_ok() {
            ok += 1;
        }
    }
    assert_eq!(ok, 500);  // 100%成功率
}
```

### 7.3 运行方式

```bash
# 手动运行基准测试（需要较长时间）
cargo test --test integration translate_throughput_smoke -- --ignored --nocapture
```

---

## 8. 压力测试 (stress_tests.rs)

### 8.1 核心目标
验证系统在极端负载下的稳定性。

### 8.2 测试内容

```rust
#[test]
#[ignore = "Stress-style test; run manually in load test stage"]
fn parser_stress_smoke() {
    let parser = SparqlParserV2::default();
    
    for _ in 0..10_000 {  // 10,000次解析
        let parsed = parser
            .parse("SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?s = ?s) }")
            .expect("parser should handle basic FILTER");
        assert!(parsed.has_filter);
    }
}
```

### 8.3 运行方式

```bash
# 手动运行压力测试
cargo test --test integration parser_stress_smoke -- --ignored --nocapture
```

---

## 9. SQL数据验证测试 (sql_data_verification.rs)

**位置**: `tests/sql_data_verification.rs` (根目录)

### 9.1 核心目标
独立验证HR测试数据是否正确加载，不依赖SPARQL翻译功能。

### 9.2 测试覆盖

| 测试 | 验证内容 |
|------|---------|
| test_hr_tables_exist | 9个表是否存在 |
| test_departments_data | 100条部门记录 |
| test_employees_data | 100,000条员工记录 |
| test_salaries_data | 100,000条薪资记录 |
| test_attendance_data | 3,000,000条考勤记录 |
| test_projects_data | 10,000条项目记录 |
| test_employee_projects_data | 200,000条关联记录 |
| test_positions_data | 1,000条职位记录 |
| test_ontop_mappings_data | 48条映射规则 |
| test_complex_join_employee_dept | 复杂JOIN查询 |
| test_complex_join_employee_projects | 多表聚合查询 |
| test_subquery_high_earners | 子查询功能 |
| test_data_integrity | 外键完整性检查 |

### 9.3 运行方式

```bash
# 运行全部15个测试
cargo test --test sql_data_verification -- --nocapture

# 运行单个测试
cargo test --test sql_data_verification test_employees_data -- --nocapture
```

---

## 10. 测试运行总览

### 10.1 快速运行所有测试

```bash
# 1. SQL数据验证（不依赖翻译功能）
cargo test --test sql_data_verification -- --nocapture

# 2. 单元测试
cargo test --lib -- --nocapture

# 3. 集成测试（需要数据库连接）
cargo test --test integration -- --nocapture

# 4. SPARQL-SQL对齐验证
cargo test --test sparql_sql_alignment -- --nocapture
```

### 10.2 CI/CD集成建议

```yaml
# GitHub Actions示例
test:
  steps:
    - name: SQL Data Verification
      run: cargo test --test sql_data_verification
    
    - name: Unit Tests
      run: cargo test --lib
    
    - name: Integration Tests
      run: cargo test --test integration
      env:
        PG_HOST: localhost
        PG_USER: yuxiaoyu
        PG_DATABASE: rs_ontop_core
    
    - name: Performance Benchmarks
      run: cargo test --test integration -- --ignored
      if: github.event_name == 'schedule'
```

### 10.3 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PG_HOST | localhost | PostgreSQL主机 |
| PG_PORT | 5432 | PostgreSQL端口 |
| PG_USER | yuxiaoyu | 数据库用户 |
| PG_DATABASE | rs_ontop_core | 数据库名 |
| PGPASSWORD | (空) | 数据库密码 |
| TEST_VERBOSE | (未设置) | 设置为1启用详细输出 |

---

## 11. 测试维护指南

### 11.1 添加新测试

1. **确定测试类型**: 单元测试(`--lib`) vs 集成测试(`--test integration`)
2. **选择测试文件**: 根据功能选择对应的测试文件
3. **遵循命名规范**: `test_类别_序号_描述` 或 `test_功能_场景`
4. **添加文档注释**: 每个测试函数前添加功能说明
5. **更新本文档**: 在对应章节添加测试说明

### 11.2 调试测试失败

```bash
# 显示详细输出
cargo test --test integration test_name -- --nocapture

# 显示回溯信息
RUST_BACKTRACE=1 cargo test --test integration test_name

# 单线程运行（避免并发干扰）
cargo test --test integration test_name -- --test-threads=1
```

### 11.3 测试数据准备

```bash
# 重新生成测试数据
psql -U yuxiaoyu -d rs_ontop_core < tests/script/setup_rdf_mappings.sql
psql -U yuxiaoyu -d rs_ontop_core < tests/script/generate_100k_data.sql

# 验证数据
psql -U yuxiaoyu -d rs_ontop_core -c "SELECT COUNT(*) FROM employees"
```

---

**文档版本**: v1.0  
**最后更新**: 2026-03-30  
**维护者**: 测试团队
