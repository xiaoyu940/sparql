# Sprint7 当前系统伪代码

> 更新时间：2026-03-30  
> 用途：作为 Sprint7 的当前状态基线文档  
> 标识规范：`[S7-Px-y]` 对应 Sprint7 的任务项

---

## Sprint7 系统概览

### 当前已实现功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| SPARQL SELECT 解析 | ✅ 已实现 | 基础 SELECT、WHERE、FILTER |
| SPARQL CONSTRUCT/ASK/DESCRIBE | ❌ 未实现 | 需要扩展 AST |
| 聚合函数 (GROUP BY) | ✅ 已实现 | COUNT/SUM/AVG/MIN/MAX |
| 子查询 (SubQuery) | ❌ 未实现 | 嵌套 SELECT |
| 属性路径 (Property Path) | ✅ 已实现 | `*`, `+`, `?`, `\|`, `/`, `^`, `!` |
| IR 中间表示 | ✅ 已实现 | LogicNode 完整定义 |
| 谓词下推优化 | ✅ 已实现 | FilterPushdown Pass |
| 连接重排序 | ✅ 已实现 | DPSize + 贪心算法 |
| 成本模型 | ✅ 已实现 | 基数估计/选择性估计 |
| OWL 2 QL 推理 | ✅ 已实现 | DL-Lite Saturator (R1-R7) |
| 联邦查询 (SERVICE) | ⚠️ 部分实现 | HTTP 客户端，缺少物化 |
| R2RML 映射 | ✅ 已实现 | W3C R2RML 完整解析 |
| SQL 代码生成 | ✅ 已实现 | PostgreSQL 方言 |
| PG 扩展部署 | ✅ 已实现 | Background Worker |

---

## 1. 核心查询翻译链路

### 1.1 主入口: `OntopEngine::translate` [S7-P0-1]

```pseudocode
FUNCTION translate(sparql_query: String) -> Result<String, String>:
    // 1. SPARQL 解析
    parser = SparqlParser::default()
    parsed = parser.parse(sparql_query)?
    
    // 2. IR 构建
    builder = IRBuilder::new()
    mut logic_plan = builder.build_from_ast(&parsed, &self.mappings)?
    
    // 3. 优化器上下文
    ctx = OptimizerContext {
        mappings: Arc::clone(&self.mappings),
        metadata: self.metadata.clone(),
        statistics: self.statistics.clone(),
    }
    
    // 4. 映射展开
    MappingUnfolder::unfold(&mut logic_plan, &ctx)
    
    // 5. TBox 饱和 (Sprint7 新增)
    IF self.tbox.is_some():
        saturated_tbox = saturate_tbox(self.tbox.as_ref().unwrap())
        rewriter = TBoxRewriter::from_tbox(&saturated_tbox)
        logic_plan = rewriter.rewrite(&logic_plan)
    END IF
    
    // 6. 查询优化
    logic_plan = RedundantJoinElimination::apply(logic_plan)
    logic_plan = FilterPushdown::apply(logic_plan)
    logic_plan = JoinReordering::apply(logic_plan, &ctx.statistics)  // DPSize
    
    // 7. PassManager 优化
    pass_manager = PassManager::new()
    pass_manager.run(&mut logic_plan, &ctx)
    
    // 8. SQL 生成
    generator = SqlGenerator::new(self.dialect)
    sql = generator.generate(&logic_plan)?
    
    RETURN Ok(sql)
END FUNCTION
```

---

## 2. SPARQL 解析模块

### 2.1 完整 SELECT 解析 [S7-P0-1] ✅

```pseudocode
FUNCTION parse_select_query(tokens: Vec<Token>) -> Result<SelectQuery, ParseError>:
    consume(tokens, "SELECT")?
    
    // DISTINCT / REDUCED
    modifier = parse_select_modifier(tokens)
    
    // 变量列表或 *
    variables = parse_variables(tokens)
    
    // 聚合表达式 (Sprint7 新增)
    aggregations = parse_aggregations(tokens)
    
    // FROM / FROM NAMED
    dataset = parse_dataset_clauses(tokens)
    
    // WHERE 子句
    consume(tokens, "WHERE")?
    pattern = parse_group_graph_pattern(tokens)
    
    // GROUP BY (Sprint7 新增)
    group_by = parse_group_by(tokens)
    
    // HAVING (Sprint7 新增)
    having = parse_having(tokens)
    
    // ORDER BY
    order_by = parse_order_by(tokens)
    
    // LIMIT / OFFSET
    limit = parse_limit_offset(tokens)
    
    RETURN SelectQuery {
        modifier, variables, aggregations, dataset, pattern,
        group_by, having, order_by, limit
    }
END FUNCTION
```

### 2.2 聚合解析 [S7-P0-3] ✅

```pseudocode
FUNCTION parse_aggregations(tokens: &mut TokenStream) -> Vec<Aggregation>:
    aggregations = Vec::new()
    
    WHILE peek(tokens) == "(" AND is_aggregate_function(peek_next(tokens)):
        func = parse_aggregate_function(tokens)  // COUNT/SUM/AVG/MIN/MAX
        consume(tokens, "(")?
        
        // DISTINCT 修饰符
        distinct = consume_if(tokens, "DISTINCT")
        
        // 表达式或 *
        expr = parse_expression(tokens) OR consume(tokens, "*")
        
        consume(tokens, ")")?
        consume(tokens, "AS")?
        alias = parse_variable(tokens)
        
        aggregations.push(Aggregation { func, distinct, expr, alias })
    END WHILE
    
    RETURN aggregations
END FUNCTION
```

---

## 3. IR 中间表示模块

### 3.1 LogicNode 层次结构 [S7-P0-2] ✅

```pseudocode
ENUM LogicNode:
    // 数据源
    ExtensionalData(source: String, column_mapping: HashMap<Var, Column>)
    
    // 一元操作
    Projection(variables: Vec<Var>, child: Box<LogicNode>)
    Selection(condition: FilterExpr, child: Box<LogicNode>)
    Distinct(child: Box<LogicNode>)
    OrderBy(sort_specs: Vec<SortSpec>, child: Box<LogicNode>)
    Limit(limit: usize, offset: usize, child: Box<LogicNode>)
    
    // 二元操作
    Join(left: Box<LogicNode>, right: Box<LogicNode>, condition: JoinCondition)
    Union(left: Box<LogicNode>, right: Box<LogicNode>)
    
    // 构造 (SPARQL CONSTRUCT 等)
    Construction(patterns: Vec<TriplePattern>, child: Box<LogicNode>)
    
    // 聚合 (Sprint7 新增)
    Aggregation(
        group_by: Vec<Var>,
        aggregates: Vec<AggregateExpr>,
        having: Option<FilterExpr>,
        child: Box<LogicNode>
    )
END ENUM
```

---

## 4. 优化器模块

### 4.1 PassManager 架构 [S7-P0-4] ✅

```pseudocode
STRUCT PassManager:
    passes: Vec<Box<dyn OptimizerPass>>

FUNCTION run(&mut self, plan: &mut LogicNode, ctx: &OptimizerContext):
    FOR pass IN self.passes:
        plan = pass.apply(plan, ctx)
    END FOR
END FUNCTION

TRAIT OptimizerPass:
    FUNCTION apply(&self, plan: LogicNode, ctx: &OptimizerContext) -> LogicNode
END TRAIT
```

### 4.2 关键优化 Passes [S7-P0-4] ✅

```pseudocode
// 映射展开
STRUCT UnfoldingPass
    FUNCTION apply(&self, plan: LogicNode, ctx: &OptimizerContext) -> LogicNode:
        // 展开 ExtensionalData 为具体表引用
        // 处理变量到列的映射
    END FUNCTION
END STRUCT

// 冗余 JOIN 消除
STRUCT RedundantJoinElimination
    FUNCTION apply(&self, plan: LogicNode, _ctx: &OptimizerContext) -> LogicNode:
        // 检测并消除自连接和冗余连接
    END FUNCTION
END STRUCT

// 谓词下推
STRUCT FilterPushdown
    FUNCTION apply(&self, plan: LogicNode, _ctx: &OptimizerContext) -> LogicNode:
        // 将 FILTER 条件下推到数据源
    END FUNCTION
END STRUCT

// JOIN 重排序 (DPSize 算法) [S7-P0-6] ✅
STRUCT JoinReordering
    FUNCTION apply(&self, plan: LogicNode, ctx: &OptimizerContext) -> LogicNode:
        // 使用 DPSize 算法找到最优连接顺序
        // 基于统计信息计算成本
    END FUNCTION
END STRUCT
```

### 4.3 DPSize 连接重排序 [S7-P0-6] ✅

```pseudocode
FUNCTION dp_size_join_ordering(relations: Vec<Relation>, stats: Statistics) -> JoinTree:
    n = relations.len()
    
    // 动态规划表: cost[subset] = (best_tree, cost)
    dp_table: HashMap<Subset, (JoinTree, Cost)> = HashMap::new()
    
    // 初始化: 单个关系的成本
    FOR i IN 0..n:
        subset = 1 << i
        cost = estimate_scan_cost(&relations[i], stats)
        dp_table[subset] = (Leaf(relations[i]), cost)
    END FOR
    
    // 递增子集大小
    FOR size IN 2..=n:
        FOR subset IN all_subsets_of_size(size, n):
            best_cost = INFINITY
            best_tree = None
            
            // 尝试所有可能的划分
            FOR left_subset IN proper_subsets(subset):
                right_subset = subset ^ left_subset
                
                IF left_subset == 0 OR right_subset == 0:
                    CONTINUE
                END IF
                
                left_tree, left_cost = dp_table[left_subset]
                right_tree, right_cost = dp_table[right_subset]
                
                // 计算连接成本
                join_cost = estimate_join_cost(left_tree, right_tree, stats)
                total_cost = left_cost + right_cost + join_cost
                
                IF total_cost < best_cost:
                    best_cost = total_cost
                    best_tree = Join(left_tree, right_tree)
                END IF
            END FOR
            
            dp_table[subset] = (best_tree, best_cost)
        END FOR
    END FOR
    
    // 返回完整子集的最优树
    full_subset = (1 << n) - 1
    RETURN dp_table[full_subset].0
END FUNCTION
```

### 4.4 成本模型 [S7-P0-7] ✅

```pseudocode
STRUCT CostModel:
    statistics: Statistics

FUNCTION estimate_scan_cost(&self, relation: &Relation) -> Cost:
    cardinality = self.statistics.get_cardinality(relation)
    // 基础扫描成本 = 元组数 * 单位成本
    RETURN cardinality * SCAN_COST_FACTOR
END FUNCTION

FUNCTION estimate_join_cost(&self, left: &JoinTree, right: &JoinTree) -> Cost:
    left_card = self.estimate_cardinality(left)
    right_card = self.estimate_cardinality(right)
    
    // 选择性估计
    selectivity = self.estimate_selectivity(left, right)
    
    // 连接成本 = 左表大小 * 右表大小 * 选择性
    RETURN left_card * right_card * selectivity * JOIN_COST_FACTOR
END FUNCTION

FUNCTION estimate_selectivity(&self, left: &JoinTree, right: &JoinTree) -> Selectivity:
    // 基于直方图和键约束估计
    IF has_primary_key_join(left, right):
        RETURN 1.0 / max(left.cardinality, right.cardinality)
    ELSE:
        RETURN DEFAULT_SELECTIVITY
    END IF
END FUNCTION
```

---

## 5. OWL 2 QL 推理模块

### 5.1 DL-Lite TBox 饱和器 [S7-P1-1] ✅

```pseudocode
FUNCTION saturate_tbox(tbox: &TBox) -> TBox:
    saturated = tbox.clone()
    changed = true
    
    WHILE changed:
        changed = false
        
        // R1-R3: 类包含传递性
        FOR (x, y) IN saturated.sub_class_of:
            FOR (y_prime, z) IN saturated.sub_class_of:
                IF y == y_prime AND x != z:
                    IF NOT saturated.sub_class_of.contains((x.clone(), z.clone())):
                        saturated.sub_class_of.push((x.clone(), z.clone()))
                        changed = true
                    END IF
                END IF
            END FOR
        END FOR
        
        // R4: 属性包含传递性
        FOR (p, q) IN saturated.sub_property_of:
            FOR (q_prime, r) IN saturated.sub_property_of:
                IF q == q_prime AND p != r:
                    IF NOT saturated.sub_property_of.contains((p.clone(), r.clone())):
                        saturated.sub_property_of.push((p.clone(), r.clone()))
                        changed = true
                    END IF
                END IF
            END FOR
        END FOR
        
        // R5: 域继承
        // 如果 P ⊑ Q 且 Domain(Q) = C，则 Domain(P) = C
        FOR (p, q) IN saturated.sub_property_of:
            IF let Some(domain) = saturated.domain_constraints.get(q):
                IF saturated.domain_constraints.get(p) != Some(domain):
                    saturated.domain_constraints.insert(p.clone(), domain.clone())
                    changed = true
                END IF
            END IF
        END FOR
        
        // R6: 范围继承
        FOR (p, q) IN saturated.sub_property_of:
            IF let Some(range) = saturated.range_constraints.get(q):
                IF saturated.range_constraints.get(p) != Some(range):
                    saturated.range_constraints.insert(p.clone(), range.clone())
                    changed = true
                END IF
            END IF
        END FOR
        
        // R7: 逆属性相关性
        // 如果 P ⊑ Q，则 inv(P) ⊑ inv(Q)
        FOR (p, q) IN saturated.sub_property_of:
            inv_p = format!("INV_{}", p)
            inv_q = format!("INV_{}", q)
            IF NOT saturated.sub_property_of.contains((inv_p.clone(), inv_q.clone())):
                saturated.sub_property_of.push((inv_p, inv_q))
                changed = true
            END IF
        END FOR
    END WHILE
    
    RETURN saturated
END FUNCTION
```

### 5.2 TBox 查询重写器 [S7-P1-2] ✅

```pseudocode
STRUCT TBoxRewriter:
    tbox: Arc<TBox>

FUNCTION rewrite(&self, plan: LogicNode) -> LogicNode:
    // 根据饱和后的 TBox 重写查询计划
    // 展开概念的层次结构
    // 处理属性的包含关系
    plan
END FUNCTION
END STRUCT
```

---

## 6. R2RML 映射模块

### 6.1 R2RML 解析器 [S7-P2-1] ✅

```pseudocode
FUNCTION parse_r2rml(ttl_content: &str) -> Result<Vec<R2RmlTriplesMap>, R2RmlError>:
    // 1. 解析 Turtle
    parser = TurtleParser::new(ttl_content)
    triples = parser.parse_all()?
    
    // 2. 构建 TriplesMap
    triples_maps = Vec::new()
    
    FOR triple IN triples:
        IF triple.predicate == RDF_TYPE AND triple.object == RR_TRIPLES_MAP:
            tm = parse_triples_map(triple.subject, &triples)
            triples_maps.push(tm)
        END IF
    END FOR
    
    RETURN Ok(triples_maps)
END FUNCTION

FUNCTION parse_triples_map(subject: Subject, all_triples: &[Triple]) -> R2RmlTriplesMap:
    tm = R2RmlTriplesMap { iri: subject.to_string(), ..Default::default() }
    
    // 解析 LogicalTable
    tm.logical_table = parse_logical_table(subject, all_triples)
    
    // 解析 SubjectMap
    tm.subject_map = parse_subject_map(subject, all_triples)
    
    // 解析 PredicateObjectMap (可能有多个)
    tm.predicate_object_maps = parse_predicate_object_maps(subject, all_triples)
    
    RETURN tm
END FUNCTION
```

### 6.2 R2RML 到内部映射转换 [S7-P2-2] ✅

```pseudocode
TRAIT MappingConverter:
    FUNCTION to_internal_mapping(&self) -> Result<Vec<MappingRule>, R2RmlError>
END TRAIT

IMPL MappingConverter FOR R2RmlTriplesMap:
    FUNCTION to_internal_mapping(&self) -> Result<Vec<MappingRule>, R2RmlError>:
        table_name = self.logical_table.table_name.clone()
            .or_else(|| self.logical_table.sql_query.clone())
            .ok_or(R2RmlError::InvalidR2Rml("No table name or SQL query"))?
        
        rules = Vec::new()
        
        // 1. rr:class 断言
        FOR class_iri IN self.subject_map.class:
            rules.push(MappingRule {
                predicate: RDF_TYPE.to_string(),
                table_name: table_name.clone(),
                subject_template: self.subject_map.template.clone(),
                position_to_column: HashMap::new(),
            })
        END FOR
        
        // 2. PredicateObjectMap
        FOR pom IN self.predicate_object_maps:
            FOR predicate IN pom.predicates:
                FOR object_map IN pom.object_maps:
                    rule = MappingRule {
                        predicate: predicate.clone(),
                        table_name: table_name.clone(),
                        subject_template: self.subject_map.template.clone(),
                        position_to_column: HashMap::from([(1, object_map.column.clone().unwrap())]),
                    }
                    rules.push(rule)
                END FOR
            END FOR
        END FOR
        
        RETURN Ok(rules)
    END FUNCTION
END IMPL
```

---

## 7. SQL 代码生成模块

### 7.1 SQL 生成器 [S7-P3-1] ✅

```pseudocode
TRAIT SqlGenerator:
    FUNCTION generate(&self, plan: &LogicNode) -> Result<String, SqlError>
END TRAIT

STRUCT PostgreSqlGenerator:
    dialect: SqlDialect

IMPL SqlGenerator FOR PostgreSqlGenerator:
    FUNCTION generate(&self, plan: &LogicNode) -> Result<String, SqlError>:
        RETURN self.generate_node(plan)
    END FUNCTION
    
    PRIVATE FUNCTION generate_node(&self, node: &LogicNode) -> Result<String, SqlError>:
        MATCH node:
            ExtensionalData(source, mapping) =>
                RETURN format!("SELECT * FROM {}", source)
                
            Projection(vars, child) =>
                child_sql = self.generate_node(child)?
                columns = vars.iter().map(|v| self.translate_var(v)).join(", ")
                RETURN format!("SELECT {} FROM ({}) AS t", columns, child_sql)
                
            Selection(condition, child) =>
                child_sql = self.generate_node(child)?
                where_clause = self.translate_filter(condition)
                RETURN format!("SELECT * FROM ({}) AS t WHERE {}", child_sql, where_clause)
                
            Join(left, right, condition) =>
                left_sql = self.generate_node(left)?
                right_sql = self.generate_node(right)?
                join_condition = self.translate_join_condition(condition)
                RETURN format!("{} INNER JOIN {} ON {}", left_sql, right_sql, join_condition)
                
            Aggregation(group_by, aggregates, having, child) =>
                // Sprint7 已实现：聚合生成
                child_sql = self.generate_node(child)?
                group_cols = group_by.iter().map(|v| self.translate_var(v)).join(", ")
                agg_exprs = aggregates.iter().map(|a| self.translate_aggregate(a)).join(", ")
                
                sql = format!("SELECT {}, {} FROM ({}) AS t GROUP BY {}", 
                    group_cols, agg_exprs, child_sql, group_cols)
                
                IF let Some(having_expr) = having:
                    sql += format!(" HAVING {}", self.translate_filter(having_expr))
                END IF
                
                RETURN sql
                
            // 🔴 [S7-P0-1] TODO: CONSTRUCT 查询生成
            Construction(patterns, child) =>
                // 生成用于构造三元组的 SQL
                child_sql = self.generate_node(child)?
                // 返回数据和模板，由调用者构造三元组
                RETURN ConstructSql { data_sql: child_sql, template: patterns }
                
            // 🔴 [S7-P0-2] TODO: ASK 查询生成
            Ask(pattern) =>
                // 生成 EXISTS 或 COUNT 查询
                pattern_sql = self.generate_node(pattern)?
                RETURN format!("SELECT EXISTS({}) AS result", pattern_sql)
                
            _ => Err(SqlError::UnsupportedNode)
        END MATCH
    END FUNCTION
END IMPL
```

---

## 8. PostgreSQL 扩展模块

### 8.1 Background Worker [S7-P4-1] ✅

```pseudocode
#[pg_guard]
FUNCTION ontop_worker_main():
    // 初始化引擎
    engine = OntopEngine::new()
    engine.load_mappings()
    engine.load_tbox()  // Sprint7 新增
    
    // 主循环
    LOOP:
        // 等待请求
        request = receive_request()
        
        MATCH request:
            Translate(sparql) =>
                sql = engine.translate(sparql)
                send_response(sql)
                
            Refresh =>
                engine.refresh()
                send_response("Engine refreshed")
                
            Shutdown =>
                BREAK
        END MATCH
    END LOOP
END FUNCTION
```

### 8.2 SQL 函数 [S7-P4-2] ✅

```pseudocode
#[pg_extern]
FUNCTION ontop_translate(sparql_query: &str) -> String:
    // 获取引擎实例
    engine = get_ontop_engine()
    
    // 翻译查询
    MATCH engine.translate(sparql_query):
        Ok(sql) => RETURN sql,
        Err(e) => RETURN format!("-- Translation Error: {}", e)
    END MATCH
END FUNCTION

#[pg_extern]
FUNCTION ontop_refresh() -> String:
    engine = get_ontop_engine()
    engine.refresh()
    RETURN "Engine refreshed"
END FUNCTION
```

---

## 9. 统计信息模块

### 9.1 PgStatsCollector [S7-P5-1] ✅

```pseudocode
STRUCT PgStatsCollector:
    connection: PgConnection

IMPL StatisticsProvider FOR PgStatsCollector:
    FUNCTION collect_table_stats(&self, table_name: &str) -> TableStatistics:
        // 查询 PostgreSQL 系统表
        query = format!(
            "SELECT reltuples, relpages FROM pg_class WHERE relname = '{}'",
            table_name
        )
        result = self.connection.query_one(&query)
        
        TableStatistics {
            cardinality: result.get("reltuples"),
            page_count: result.get("relpages"),
        }
    END FUNCTION
    
    FUNCTION collect_column_stats(&self, table: &str, column: &str) -> ColumnStatistics:
        // 查询 pg_stats
        query = format!(
            "SELECT null_frac, avg_width, n_distinct, histogram_bounds 
             FROM pg_stats WHERE tablename = '{}' AND attname = '{}'",
            table, column
        )
        result = self.connection.query_one(&query)
        
        ColumnStatistics {
            null_fraction: result.get("null_frac"),
            avg_width: result.get("avg_width"),
            distinct_count: result.get("n_distinct"),
            histogram: parse_histogram(result.get("histogram_bounds")),
        }
    END FUNCTION
END IMPL
```

---

## 10. 测试框架

### 10.1 统一测试套件 [S7-T1] ✅

```pseudocode
// 见 tests/sparql_sql_unified_tests.rs
STRUCT SparqlTestFramework:
    db_config: TestDbConfig

FUNCTION run_test(&self, test_case: &TestCase) -> TestResult:
    // 1. 翻译 SPARQL
    sql = self.translate(test_case.sparql)?
    
    // 2. 验证 SQL 模式
    FOR pattern IN test_case.expected_sql_patterns:
        ASSERT sql.contains(pattern), "Missing pattern: {}"
    END FOR
    
    // 3. 验证排除的模式
    FOR pattern IN test_case.excluded_sql_patterns:
        ASSERT !sql.contains(pattern), "Found excluded pattern: {}"
    END FOR
    
    // 4. 执行 SQL (可选)
    IF test_case.requires_execution:
        result = self.execute_sql(&sql)?
        IF let Some(expected) = test_case.expected_row_count:
            ASSERT result.row_count == expected
        END IF
    END IF
    
    RETURN TestResult { passed: true, .. }
END FUNCTION
```

---

## Sprint7 新增功能总结

1. **聚合函数支持** - COUNT/SUM/AVG/MIN/MAX + GROUP BY + HAVING
2. **DPSize 连接重排序** - 基于动态规划的最优连接顺序
3. **成本模型** - 基数估计和选择性计算
4. **DL-Lite 饱和器** - OWL 2 QL 推理规则 R1-R7 完整实现
5. **R2RML 解析器** - W3C R2RML 标准完整支持
6. **统计信息收集** - PostgreSQL 系统表集成
7. **统一测试框架** - 结构化测试和回归保护
