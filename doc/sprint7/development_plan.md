# Sprint 7 开发计划

> 目标：实现 SPARQL CONSTRUCT/ASK/DESCRIBE 查询和多数据库方言框架  
> 计划周期：2-3 周  
> 基于：`ontop_comparison.md` 差距分析

---

## 1. Sprint 目标

### 1.1 总体目标
- 实现 SPARQL 1.1 完整查询协议（CONSTRUCT/ASK/DESCRIBE）
- 建立多数据库方言框架，支持 MySQL/SQLite
- 提升系统完成度从 50% → 65%

### 1.2 具体目标
| 目标 | 完成标准 | 优先级 |
|------|---------|--------|
| CONSTRUCT 查询 | 支持三元组模板生成 | P0 |
| ASK 查询 | 支持布尔结果返回 | P0 |
| DESCRIBE 查询 | 支持资源描述生成 | P1 |
| 方言框架 | 抽象层 + MySQL/SQLite 支持 | P0 |
| CLI 工具 | 基础命令行接口 | P1 |

---

## 2. 任务分解

### 2.1 P0 任务（必须完成）

#### [S7-P0-1] SPARQL CONSTRUCT 查询支持
**状态**: 🔴 未开始  
**工作量**: 3 天  
**负责人**: TBD  
**依赖**: IR Construction 节点完善

**验收标准**:
```rust
// 测试用例
#[test]
fn test_construct_basic() {
    let sparql = "CONSTRUCT { ?s a ex:Person } WHERE { ?s ex:name ?name }";
    let result = translate_sparql(sparql);
    assert!(result.contains("INSERT") || result.contains("CONSTRUCT"));
}
```

**实现步骤**:
1. 扩展 AST 支持 `ConstructQuery` 节点
2. 实现 `pattern_to_construct_node` 转换
3. 更新 SQL 生成器支持 CONSTRUCT 输出格式
4. 添加集成测试

**相关文件**:
- `src/parser/ast.rs`
- `src/parser/sparql_parser_v2.rs`
- `src/ir/node.rs` (Construction 节点已存在)
- `src/codegen/postgresql_generator.rs`

---

#### [S7-P0-2] SPARQL ASK 查询支持
**状态**: 🔴 未开始  
**工作量**: 2 天  
**负责人**: TBD  
**依赖**: 无

**验收标准**:
```rust
#[test]
fn test_ask_basic() {
    let sparql = "ASK WHERE { ?s a ex:Person }";
    let sql = translate_sparql(sparql);
    assert!(sql.contains("EXISTS") || sql.contains("COUNT"));
}
```

**实现步骤**:
1. 扩展 AST 支持 `AskQuery` 节点
2. 实现 ASK → SQL EXISTS/COUNT 转换
3. 添加布尔结果处理
4. 添加集成测试

**相关文件**:
- `src/parser/ast.rs`
- `src/parser/sparql_parser_v2.rs`
- `src/codegen/postgresql_generator.rs`

---

#### [S7-P0-3] 多数据库方言框架
**状态**: 🔴 未开始  
**工作量**: 5 天  
**负责人**: TBD  
**依赖**: 无

**验收标准**:
```rust
#[test]
fn test_dialect_framework() {
    let pg = SqlDialect::PostgreSql;
    let mysql = SqlDialect::MySql;
    let sqlite = SqlDialect::Sqlite;
    
    assert!(pg.quote_identifier("table") == "\"table\"");
    assert!(mysql.quote_identifier("table") == "`table`");
    assert!(sqlite.quote_identifier("table") == "\"table\"");
}
```

**实现步骤**:
1. 创建 `SqlDialect` Trait
2. 实现 PostgreSqlDialect
3. 实现 MySqlDialect
4. 实现 SqliteDialect
5. 重构 SQL 生成器使用方言
6. 添加方言选择配置

**相关文件**:
- `src/sql/dialect.rs` (新建)
- `src/sql/dialect/postgresql.rs` (新建)
- `src/sql/dialect/mysql.rs` (新建)
- `src/sql/dialect/sqlite.rs` (新建)
- `src/codegen/postgresql_generator.rs` (重构)

---

### 2.2 P1 任务（建议完成）

#### [S7-P1-1] SPARQL DESCRIBE 查询支持
**状态**: 🔴 未开始  
**工作量**: 3 天  
**负责人**: TBD  
**依赖**: [S7-P0-1] CONSTRUCT

**验收标准**:
```rust
#[test]
fn test_describe_resource() {
    let sparql = "DESCRIBE <http://example.org/person1>";
    let result = translate_sparql(sparql);
    // 生成描述资源的三元组查询
    assert!(result.len() > 0);
}
```

**实现步骤**:
1. 扩展 AST 支持 `DescribeQuery` 节点
2. 实现 DESCRIBE → CONSTRUCT 内部转换
3. 生成资源属性查询
4. 添加集成测试

---

#### [S7-P1-2] CLI 工具基础
**状态**: 🔴 未开始  
**工作量**: 4 天  
**负责人**: TBD  
**依赖**: [S7-P0-3] 方言框架

**验收标准**:
```bash
$ ontop --version
ontop 0.7.0

$ ontop translate --sparql "SELECT * WHERE { ?s a ex:Person }" --mapping mappings.ttl
SELECT ... FROM ...
```

**实现步骤**:
1. 创建 CLI 项目结构
2. 实现 `ontop` 主命令
3. 实现 `translate` 子命令
4. 实现 `validate` 子命令
5. 实现 `materialize` 子命令 (基础)
6. 添加配置加载

**相关文件**:
- `src/bin/ontop.rs` (新建)
- `src/cli/mod.rs` (新建)
- `src/cli/commands.rs` (新建)

---

#### [S7-P1-3] R2RML rr:Join 支持
**状态**: 🔴 未开始  
**工作量**: 3 天  
**负责人**: TBD  
**依赖**: 无

**验收标准**:
```rust
#[test]
fn test_r2rml_join() {
    let r2rml = r#"
    <#Map> rr:parentTriplesMap <#ParentMap>;
           rr:joinCondition [ rr:child "dept_id"; rr:parent "id" ].
    "#;
    let result = parse_r2rml(r2rml);
    assert!(result[0].join_conditions.len() > 0);
}
```

**实现步骤**:
1. 扩展 R2RML 解析器支持 rr:Join
2. 实现 rr:parentTriplesMap 解析
3. 实现 rr:joinCondition 解析
4. 更新映射转换器处理 JOIN
5. 添加测试

**相关文件**:
- `src/mapping/r2rml_parser.rs`
- `src/mapping/r2rml_loader.rs`

---

### 2.3 P2 任务（可选完成）

#### [S7-P2-1] VALUES 数据块支持
**状态**: 🔴 未开始  
**工作量**: 2 天  

**实现要点**:
- 扩展 AST 支持 VALUES 子句
- 转换为 SQL IN 子句或临时表

#### [S7-P2-2] SPARQL 子查询支持
**状态**: 🔴 未开始  
**工作量**: 5 天  

**实现要点**:
- 扩展 AST 支持嵌套 SELECT
- 实现子查询展平或嵌套 SQL 生成

#### [S7-P2-3] 查询缓存系统
**状态**: 🔴 未开始  
**工作量**: 3 天  

**实现要点**:
- LRU 缓存 SPARQL → SQL 翻译结果
- 可配置缓存大小和 TTL

---

## 3. 技术设计

### 3.1 CONSTRUCT 查询翻译流程

```pseudocode
FUNCTION translate_construct(construct_template, where_pattern):
    // 1. 解析 WHERE 模式为 LogicNode
    data_node = parse_where_pattern(where_pattern)
    
    // 2. 将模板三元组转换为 Construction 节点
    construct_node = Construction {
        patterns: construct_template,
        child: data_node
    }
    
    // 3. 应用优化
    optimized = optimize(construct_node)
    
    // 4. 生成 SQL (返回结果用于构造三元组)
    sql = generate_sql(optimized)
    
    // 5. 返回 CONSTRUCT 结果格式
    RETURN ConstructResult { sql, template: construct_template }
END FUNCTION
```

### 3.2 方言框架设计

```rust
// src/sql/dialect.rs
pub trait SqlDialect {
    fn quote_identifier(&self, name: &str) -> String;
    fn quote_string(&self, value: &str) -> String;
    fn cast_type(&self, value: &str, target_type: &str) -> String;
    fn limit_syntax(&self) -> LimitSyntax;
    fn supports_ilike(&self) -> bool;
    fn supports_window_functions(&self) -> bool;
}

pub enum LimitSyntax {
    LimitOffset { limit: String, offset: Option<String> },
    FetchFirst { count: String },
}

pub struct PostgreSqlDialect;
pub struct MySqlDialect;
pub struct SqliteDialect;
```

### 3.3 CLI 架构设计

```rust
// src/cli/mod.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "ontop")]
#[command(about = "Virtual Knowledge Graph System")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Translate SPARQL to SQL
    Translate {
        #[arg(short, long)]
        sparql: String,
        #[arg(short, long)]
        mapping: String,
    },
    /// Validate mappings
    Validate {
        #[arg(short, long)]
        mapping: String,
    },
    /// Materialize RDF
    Materialize {
        #[arg(short, long)]
        output: String,
        #[arg(short, long)]
        mapping: String,
    },
}
```

---

## 4. 测试策略

### 4.1 单元测试
- 每个方言实现独立测试
- CONSTRUCT/ASK/DESCRIBE 解析器测试
- CLI 命令测试

### 4.2 集成测试
- 完整 CONSTRUCT 查询流测试
- 多数据库方言端到端测试
- CLI 工具集成测试

### 4.3 回归测试
- 确保现有 SELECT 查询不受影响
- 确保 PostgreSQL 支持保持完整

---

## 5. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| CONSTRUCT 模板复杂度高 | 中 | 高 | 分阶段实现，先做简单模板 |
| 方言抽象层设计不当 | 中 | 高 | 参考 SQLAlchemy、JOOQ 设计 |
| CLI 依赖过多 | 低 | 中 | 使用轻量级框架 (clap) |
| 时间不足 | 中 | 高 | P1 任务可移至 Sprint 8 |

---

## 6. 里程碑

| 日期 | 里程碑 | 交付物 |
|------|--------|--------|
| Week 1 | 方言框架完成 | MySQL/SQLite 支持 |
| Week 2 | CONSTRUCT/ASK 完成 | 完整 SPARQL 1.1 基础 |
| Week 3 | CLI 工具 + 测试 | 可执行 ontop 命令 |

---

## 7. 成功标准

- [ ] CONSTRUCT 查询测试通过率 > 90%
- [ ] ASK 查询测试通过率 > 95%
- [ ] MySQL 方言基本查询通过
- [ ] SQLite 方言基本查询通过
- [ ] CLI 工具基础命令可用
- [ ] 现有 SELECT 查询无回归

---

## 8. 参考文档

- `doc/sprint7/ontop_comparison.md` - 功能对比分析
- `doc/sprint7/current_system_pseudocode.md` - 当前系统伪代码
- W3C SPARQL 1.1 规范: https://www.w3.org/TR/sparql11-query/
- W3C R2RML 规范: https://www.w3.org/TR/r2rml/
