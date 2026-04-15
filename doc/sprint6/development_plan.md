# Sprint6 开发计划

> 更新时间：2026-03-30  
> 基线文档：`/doc/sprint6/current_system_pseudocode.md`  
> 目标：缩小与开源 Ontop 的能力差距，实现生产就绪的核心功能

---

## 1. 能力差距总结

### 1.1 与 Ontop 对比矩阵

| 能力维度 | Sprint6 基线 | Ontop 目标 | 差距 | 权重 |
|---------|-------------|-----------|------|------|
| **SPARQL 完整度** | 60% | 100% | 40% | 高 |
| **查询优化** | 40% | 95% | 55% | 高 |
| **OWL 2 QL 推理** | 50% | 95% | 45% | 中 |
| **联邦查询** | 40% | 90% | 50% | 中 |
| **数据源支持** | 10% | 100% | 90% | 低 |
| **部署方式** | 30% | 95% | 65% | 低 |
| **总体成熟度** | **38%** | **96%** | **58%** | - |

### 1.2 关键缺失功能

| 功能 | 状态 | 阻塞影响 |
|-----|------|---------|
| R2RML 映射 | ❌ 未实现 | 无法使用行业标准映射格式 |
| 聚合函数 (GROUP BY) | ❌ 未实现 | 无法执行统计分析类查询 |
| 成本模型 | ❌ 未实现 | 查询优化依赖启发式，性能不稳定 |
| DL-Lite 饱和算法 | ❌ 未实现 | 推理不完备，TBox 重写有遗漏 |
| SERVICE 物化 | ❌ 未实现 | 联邦查询无法实际执行 |
| CONSTRUCT/ASK/DESCRIBE | ❌ 未实现 | SPARQL 1.1 协议不完整 |

---

## 2. Sprint6 任务规划

### 2.1 任务总览

```
Sprint6 周期: 6 周
├── Week 1-2: P0 任务（核心能力补全）
├── Week 3-4: P1 任务（竞争力提升）
└── Week 5-6: P2 任务（生态完善）+ 集成测试
```

---

## 3. P0 - 必须实现（Week 1-2）

### [S6-P0-4] R2RML 映射解析器

**目标**: 实现 W3C R2RML 标准映射解析，与现有 OBDA 格式并存

**交付物**:
- `src/mapping/r2rml_parser.rs` - R2RML TTL/Turtle 格式解析
- `src/mapping/r2rml_loader.rs` - 映射加载与验证
- `src/mapping/mapping_registry.rs` - 多格式映射统一注册表

**关键设计**:
```rust
// R2RML 映射结构
triplesMap: IRIsOrBNodes;
logicalTable: R2RMLLogicalTable;
subjectMap: R2RMLSubjectMap;
predicateObjectMap: List<R2RMLPredicateObjectMap>;

// 与现有 Mapping 的转换
trait MappingConverter {
    fn to_internal_mapping(&self) -> Mapping;
    fn from_internal_mapping(m: &Mapping) -> Self;
}
```

**依赖**: 无  
**工作量**: 3 人天  
**验收标准**:
- [ ] 解析示例 R2RML 文件 `tests/data/example.r2rml.ttl`
- [ ] 通过 R2RML 测试套件（至少 10 个测试用例）
- [ ] 与现有 OBDA 格式功能等价验证

---

### [S6-P1-2] GROUP BY / 聚合函数

**目标**: 扩展 AST 和 IR 支持聚合查询

**交付物**:
- `src/sparql/aggregate_parser.rs` - 聚合函数解析
- `src/ir/aggregate_node.rs` - IR 聚合节点定义
- `src/codegen/aggregate_sql_generator.rs` - 聚合 SQL 生成

**AST 扩展**:
```pseudocode
ENUM SparqlExpr:
    // 现有表达式...
    Aggregate { func: AggFunc, expr: Box<Expr>, distinct: bool }

ENUM AggFunc:
    COUNT, SUM, AVG, MIN, MAX, GROUP_CONCAT, SAMPLE
```

**IR 扩展**:
```pseudocode
ENUM LogicNode:
    // 现有节点...
    GroupBy {
        groups: Vec<String>,           // 分组变量
        aggregates: Vec<Aggregate>,    // 聚合定义
        having: Option<Expr>,           // HAVING 条件
        child: Box<LogicNode>
    }
```

**依赖**: 无  
**工作量**: 4 人天  
**验收标准**:
- [ ] 支持 `SELECT ?c (COUNT(*) AS ?cnt) WHERE ... GROUP BY ?c`
- [ ] 支持 HAVING 子句过滤
- [ ] 聚合函数嵌套（如 COUNT(DISTINCT ?x)）
- [ ] 10+ 集成测试用例通过

---

### [S6-P1-3] 基础成本模型

**目标**: 实现选择性估计和统计信息基础设施

**交付物**:
- `src/optimizer/statistics.rs` - 统计信息管理
- `src/optimizer/selectivity.rs` - 选择性估计器
- `src/optimizer/cost_model.rs` - 成本模型实现
- `src/optimizer/dp_size.rs` - DPSize 连接重排序算法

**核心设计**:
```rust
// 表级统计
struct TableStatistics {
    table_name: String,
    row_count: u64,
    column_stats: HashMap<String, ColumnStatistics>,
}

// 列级统计
struct ColumnStatistics {
    null_fraction: f64,
    distinct_values: u64,
    histogram: Option<Histogram>,  // 等深直方图
    most_common_values: Vec<(String, f64)>,  // Top-N 频繁值
}

// 选择性估计
trait SelectivityEstimator {
    fn estimate_eq(&self, column: &str, value: &Term) -> f64;
    fn estimate_range(&self, column: &str, low: &Term, high: &Term) -> f64;
    fn estimate_like(&self, column: &str, pattern: &str) -> f64;
}
```

**DPSize 算法**:
```pseudocode
FUNCTION dp_size_optimal_order(relations, predicates, stats):
    n = relations.len()
    dp = Array[n+1]  // dp[s] = 最优子计划，s 是子集位掩码
    dp[0] = (cost=0, plan=[])
    
    FOR size FROM 1 TO n:
        FOR each subset S of size:
            dp[S] = MIN(
                FOR each R in S:
                    S_minus_R = S - {R}
                    IF connected(R, S_minus_R, predicates):
                        cost = dp[S_minus_R].cost + 
                               join_cost(dp[S_minus_R].plan, R, stats)
                        (cost, dp[S_minus_R].plan + R)
            )
    
    RETURN dp[(1<<n)-1].plan
END FUNCTION
```

**依赖**: 无（统计信息可从 PostgreSQL `pg_stats` 读取）  
**工作量**: 5 人天  
**验收标准**:
- [ ] 从 PostgreSQL 自动采集统计信息
- [ ] 实现等深直方图（默认 100 bucket）
- [ ] DPSize 算法正确性验证（与贪心算法对比）
- [ ] 选择性估计误差 < 30%（对比实际查询结果）

---

## 4. P1 - 重要实现（Week 3-4）

### [S6-P1-2] SERVICE 结果物化

**目标**: 实现联邦查询结果的临时表物化

**交付物**:
- `src/federation/materializer.rs` - 结果物化器
- `src/federation/temp_table_manager.rs` - 临时表生命周期管理

**伪代码**:
```pseudocode
FUNCTION materialize_service_results(result: ServiceResult) -> Result<TableName, Error>:
    table_name = generate_temp_table_name("service_")
    
    // 1. 创建临时表
    columns = result.variables.map(|v| Column {
        name: sanitize(v),
        type: infer_sql_type(v, &result.bindings)
    })
    create_temp_table(table_name, columns)?
    
    // 2. 批量插入（使用 COPY 协议优化）
    IF result.bindings.len() > 1000:
        copy_bulk_insert(table_name, result.bindings)?
    ELSE:
        batch_insert(table_name, result.bindings, batch_size=100)?
    
    // 3. 注册到查询上下文
    query_context.register_temp_table(table_name, columns)
    
    RETURN Ok(table_name)
END FUNCTION
```

**依赖**: [S6-P1-1] 联邦查询 HTTP 客户端  
**工作量**: 3 人天  
**验收标准**:
- [ ] SERVICE 查询结果可参与后续 JOIN
- [ ] 临时表自动清理（事务结束或查询完成）
- [ ] 大数据量（>10k 行）使用 COPY 协议优化
- [ ] 物化结果正确性验证

---

### [S6-P1-3] DL-Lite 饱和算法

**目标**: 实现 DL-Lite R 的完备推理规则

**交付物**:
- `src/reasoning/saturator.rs` - TBox 饱和器
- `src/reasoning/inference_rules.rs` - R1-R7 推理规则实现

**推理规则实现**:
```pseudocode
FUNCTION saturate_tbox(tbox: TBox) -> SaturatedTBox:
    changed = true
    saturated = clone(tbox)
    
    WHILE changed:
        changed = false
        
        // R1: C1 ⊑ C2, C2 ⊑ C3 => C1 ⊑ C3 (传递性)
        FOR (c1, c2) IN saturated.subsumptions:
            FOR (c2_prime, c3) IN saturated.subsumptions:
                IF c2 == c2_prime AND !saturated.has_subsumption(c1, c3):
                    saturated.add_subsumption(c1, c3)
                    changed = true
        
        // R2: ∃R ⊑ C, C ⊑ D => ∃R ⊑ D
        FOR (r, c) IN saturated.existential_subsumptions:
            FOR (c_prime, d) IN saturated.subsumptions:
                IF c == c_prime:
                    saturated.add_existential_subsumption(r, d)
                    changed = true
        
        // R3: C ⊑ ∃R, ∃R ⊑ D => C ⊑ D
        FOR (c, r) IN saturated.existential_parents:
            FOR (r_prime, d) IN saturated.existential_subsumptions:
                IF r == r_prime:
                    saturated.add_subsumption(c, d)
                    changed = true
        
        // R4: R ⊑ S, S ⊑ T => R ⊑ T (属性传递)
        FOR (r, s) IN saturated.property_subsumptions:
            FOR (s_prime, t) IN saturated.property_subsumptions:
                IF s == s_prime:
                    saturated.add_property_subsumption(r, t)
                    changed = true
        
        // R5: R ⊑ S, domain(S)=C => domain(R)=C
        FOR (r, s) IN saturated.property_subsumptions:
            IF saturated.domain.contains_key(s):
                c = saturated.domain[s]
                IF !saturated.domain.get(r) == Some(c):
                    saturated.domain.insert(r, c)
                    changed = true
        
        // R6: R ⊑ S, range(S)=C => range(R)=C
        FOR (r, s) IN saturated.property_subsumptions:
            IF saturated.range.contains_key(s):
                c = saturated.range[s]
                IF !saturated.range.get(r) == Some(c):
                    saturated.range.insert(r, c)
                    changed = true
        
        // R7: R ⊑ S => inv(R) ⊑ inv(S)
        FOR (r, s) IN saturated.property_subsumptions:
            inv_r = inverse_property(r)
            inv_s = inverse_property(s)
            IF !saturated.has_property_subsumption(inv_r, inv_s):
                saturated.add_property_subsumption(inv_r, inv_s)
                changed = true
    
    RETURN saturated
END FUNCTION
```

**依赖**: [S6-P0-3] TBox 结构  
**工作量**: 4 人天  
**验收标准**:
- [ ] 实现全部 7 条推理规则
- [ ] 通过 DL-Lite 推理测试套件
- [ ] 饱和算法收敛性验证（无循环推理）
- [ ] 与 Ontop 推理结果对比一致性 > 95%

---

### [S6-P2-1] 多数据库方言框架

**目标**: 抽象 SQL 方言系统，支持 PostgreSQL/MySQL/SQLite

**交付物**:
- `src/sql/dialect/mod.rs` - 方言 Trait 定义
- `src/sql/dialect/postgresql.rs` - PostgreSQL 方言实现
- `src/sql/dialect/mysql.rs` - MySQL 方言实现
- `src/sql/dialect/sqlite.rs` - SQLite 方言实现

**核心 Trait**:
```rust
trait SqlDialect: Send + Sync {
    fn name(&self) -> &str;
    
    // 标识符引用
    fn quote_identifier(&self, name: &str) -> String;
    
    // LIMIT/OFFSET 语法
    fn format_limit_offset(&self, limit: usize, offset: Option<usize>) -> String;
    
    // 函数映射
    fn map_function(&self, sparql_func: &str) -> Result<String, SqlError>;
    
    // 类型映射
    fn map_type(&self, rdf_type: &str) -> String;
    
    // 布尔字面量
    fn format_bool(&self, value: bool) -> String;
    
    // 字符串连接
    fn format_concat(&self, exprs: &[String]) -> String;
    
    // 递归 CTE 支持
    fn supports_recursive_cte(&self) -> bool;
}

// 方言工厂
struct DialectRegistry {
    dialects: HashMap<String, Box<dyn SqlDialect>>,
}

impl DialectRegistry {
    fn get(&self, name: &str) -> Option<&dyn SqlDialect>;
    fn detect_from_url(&self, url: &str) -> Option<&dyn SqlDialect>;
}
```

**函数映射示例**:
| SPARQL 函数 | PostgreSQL | MySQL | SQLite |
|------------|------------|-------|--------|
| STR | `CAST(x AS TEXT)` | `CAST(x AS CHAR)` | `CAST(x AS TEXT)` |
| CONCAT | `CONCAT(a, b)` | `CONCAT(a, b)` | `a \|\| b` |
| REGEX | `~` (POSIX) | `REGEXP` | `REGEXP` |
| NOW | `NOW()` | `NOW()` | `DATETIME('now')` |
| YEAR | `EXTRACT(YEAR FROM x)` | `YEAR(x)` | `STRFTIME('%Y', x)` |

**依赖**: 无  
**工作量**: 4 人天  
**验收标准**:
- [ ] Trait 接口稳定，新增方言扩展容易
- [ ] MySQL/SQLite 方言基础函数映射完成
- [ ] 现有 PostgreSQL 代码迁移到方言系统
- [ ] 跨方言测试用例通过

---

## 5. P2 - 增强功能（Week 5-6）

### [S6-P2-1] CONSTRUCT/ASK/DESCRIBE 查询

**目标**: 扩展 SPARQL 查询类型支持

**交付物**:
- `src/sparql/construct_parser.rs` - CONSTRUCT 解析
- `src/sparql/ask_describe_parser.rs` - ASK/DESCRIBE 解析
- `src/rdf/serializer.rs` - RDF 序列化（Turtle/JSON-LD/NTriples）

**AST 扩展**:
```pseudocode
ENUM SparqlQuery:
    Select(SelectQuery)
    Construct {
        template: Vec<TriplePattern>,  // 构造模板
        pattern: GroupGraphPattern
    }
    Ask { pattern: GroupGraphPattern }
    Describe {
        resources: Vec<Term>,  // 要描述的资源
        pattern: Option<GroupGraphPattern>
    }
```

**依赖**: [S6-P1-2] 聚合（部分可选）  
**工作量**: 3 人天  
**验收标准**:
- [ ] CONSTRUCT 生成 RDF 图
- [ ] ASK 返回布尔值
- [ ] DESCRIBE 返回资源描述
- [ ] 支持 Turtle/JSON-LD 输出格式

---

### [S6-P2-1] 子查询 (SubQuery)

**目标**: 实现嵌套 SELECT 支持

**交付物**:
- `src/sparql/subquery_parser.rs` - 子查询解析
- `src/ir/subquery_node.rs` - 子查询 IR 节点

**IR 扩展**:
```pseudocode
ENUM LogicNode:
    // 现有节点...
    SubQuery {
        query: Box<LogicNode>,  // 子查询逻辑计划
        alias: String,          // 子查询别名
        correlated_vars: Vec<String>,  // 关联变量
        is_correlated: bool
    }
```

**依赖**: [S6-P1-2] 聚合（子查询常包含聚合）  
**工作量**: 3 人天  
**验收标准**:
- [ ] 非关联子查询（子查询独立执行）
- [ ] 关联子查询（引用外层变量）
- [ ] 子查询作为派生表参与 JOIN
- [ ] 10+ 测试用例通过

---

### [S6-P2-1] CLI 工具

**目标**: 独立命令行工具，支持查询文件批处理

**交付物**:
- `src/bin/ontop_cli.rs` - CLI 入口
- `src/cli/commands.rs` - 命令定义

**命令设计**:
```bash
# 查询执行
ontop query -c config.toml "SELECT * WHERE { ?s a :Person }"

# 文件批处理
ontop query -c config.toml -f queries.sparql

# 结果输出格式
ontop query -c config.toml -f query.sparql -o result.json --format json

# 映射验证
ontop validate -m mapping.obda
ontop validate -m mapping.r2rml.ttl

# 统计信息
ontop stats -c config.toml --update
```

**依赖**: 无  
**工作量**: 2 人天  
**验收标准**:
- [ ] 支持 SPARQL 查询执行
- [ ] 支持查询文件读取
- [ ] 支持 JSON/CSV/Turtle 输出格式
- [ ] 配置文件驱动（TOML 格式）

---

### [S6-P2-1] 独立 HTTP 服务

**目标**: 完整 SPARQL 1.1 Protocol 端点

**交付物**:
- `src/server/http_server.rs` - HTTP 服务
- `src/server/sparql_endpoint.rs` - SPARQL 协议端点
- `src/server/content_negotiation.rs` - 内容协商

**端点设计**:
```
GET  /sparql?query={...}&default-graph-uri={...}     # 查询端点
POST /sparql (Content-Type: application/sparql-query) # 查询端点
GET  /update?update={...}                            # 更新端点（如支持）
GET  /                               # 服务描述（Service Description）
```

**依赖**: [S6-P2-1] CONSTRUCT/ASK/DESCRIBE  
**工作量**: 3 人天  
**验收标准**:
- [ ] 实现 SPARQL 1.1 Protocol 规范
- [ ] 内容协商（Accept 头处理）
- [ ] 错误响应符合规范（HTTP 状态码 + 错误体）
- [ ] 基础认证/授权支持（可选）

---

## 6. 任务依赖图

```
P0 任务（Week 1-2）:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ [S6-P0-4] R2RML │  │ [S6-P1-2] GROUP │  │ [S6-P1-3] 成本  │
│    映射解析器    │  │     BY 聚合      │  │    模型        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
P1 任务（Week 3-4）:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ [S6-P1-2]       │  │ [S6-P1-3]       │  │ [S6-P2-1]       │
│ SERVICE 物化    │  │ DL-Lite 饱和    │  │ 多数据库方言    │
│ （依赖 HTTP）   │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
P2 任务（Week 5-6）:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ [S6-P2-1]       │  │ [S6-P2-1]       │  │ [S6-P2-1]       │  │ [S6-P2-1]       │
│ CONSTRUCT/ASK   │  │ 子查询          │  │ CLI 工具        │  │ HTTP 服务       │
│                 │  │（依赖聚合）     │  │                 │  │（依赖构造查询） │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 7. 验收标准汇总

### 7.1 功能验收

| 任务 | 关键验收点 | 测试数量 |
|-----|-----------|---------|
| R2RML 映射 | 解析 + 加载 + 功能等价 | 10 |
| 聚合函数 | 5 种函数 + HAVING + DISTINCT | 15 |
| 成本模型 | 统计采集 + 选择性估计 + DPSize | 10 |
| SERVICE 物化 | 临时表 + 批量插入 + 清理 | 5 |
| DL-Lite 饱和 | 7 条规则 + 收敛性 | 15 |
| 多数据库方言 | 3 方言 + 函数映射 | 10 |
| CONSTRUCT/ASK | 3 种查询 + 3 种输出 | 10 |
| 子查询 | 关联 + 非关联 | 10 |
| CLI 工具 | 查询 + 文件 + 格式 | 5 |
| HTTP 服务 | 协议合规 + 内容协商 | 10 |

**总计**: 约 100 个新测试用例

### 7.2 性能基准

| 指标 | 基线 | 目标 | 验证方式 |
|-----|------|------|---------|
| 简单查询 P50 延迟 | 50ms | < 50ms | 基准测试 |
| 复杂 Join 查询优化 | 启发式 | DPSize 最优 | EXPLAIN 对比 |
| 聚合查询执行 | 不支持 | < 100ms (1M 行) | 性能测试 |
| 联邦查询物化 | 不支持 | < 500ms (10k 行) | 性能测试 |
| R2RML 加载 | N/A | < 100ms (100 映射) | 性能测试 |

### 7.3 与 Ontop 对齐度

| 维度 | Sprint6 目标 | 验证方式 |
|-----|-------------|---------|
| SPARQL 完整度 | 85% | 功能测试覆盖 |
| 查询优化 | 70% | 执行计划对比 |
| OWL 2 QL 推理 | 75% | 推理结果对比 |
| 联邦查询 | 70% | 端到端测试 |
| 数据源支持 | 30% | 方言测试 |

---

## 8. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|-----|-------|------|---------|
| DPSize 算法复杂度 | 中 | 高 | 限制关系数量 (>10 回退到贪心) |
| R2RML 标准复杂性 | 中 | 中 | 分阶段实现，先支持核心特性 |
| 方言差异过大 | 低 | 中 | 优先支持 ANSI SQL 兼容子集 |
| DL-Lite 推理不完备 | 低 | 高 | 严格测试，与 Ontop 结果对比 |

---

## 9. 附录

### 9.1 参考文档

- `/doc/sprint6/current_system_pseudocode.md` - Sprint6 基线伪代码
- `/doc/sprint5/capability-comparison.md` - Ontop 能力对比（Sprint5）
- `/doc/sprint2/ontop-pseudocode.md` - Ontop 标准架构参考
- [W3C R2RML 规范](https://www.w3.org/TR/r2rml/)
- [SPARQL 1.1 协议](https://www.w3.org/TR/sparql11-protocol/)
- [DL-Lite 论文](https://www.cs.ox.ac.uk/publications/publication2263-abstract.html)

### 9.2 文件命名规范

```
doc/sprint6/
├── current_system_pseudocode.md  # 基线文档（已存在）
├── development_plan.md            # 本文档
└── tasks/
    ├── s6_p0_r2rml.md            # P0-4 详细设计
    ├── s6_p1_aggregate.md        # P1-2 详细设计
    ├── s6_p1_cost_model.md      # P1-3 详细设计
    ├── s6_p1_service.md          # P1-2 SERVICE 详细设计
    ├── s6_p1_saturation.md       # P1-3 DL-Lite 详细设计
    └── s6_p2_*.md                # P2 任务详细设计
```

---

**文档版本**: Sprint6  
**创建日期**: 2026-03-30  
**维护者**: RS Ontop Core Team
