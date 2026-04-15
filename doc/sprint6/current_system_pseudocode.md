# Sprint6 当前系统伪代码

> 更新时间：2026-03-29  
> 用途：作为 Sprint6 的当前状态基线文档  
> 标识规范：`[S6-Px-y]` 对应 Sprint6 的任务项

---

## Sprint6 系统概览

### 当前已实现功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| SPARQL SELECT 解析 | ✅ 已实现 | 基础 SELECT、WHERE、FILTER |
| SPARQL CONSTRUCT/ASK/DESCRIBE | ❌ 未实现 | 需要扩展 AST |
| 聚合函数 (GROUP BY) | ❌ 未实现 | COUNT/SUM/AVG/MIN/MAX |
| 子查询 (SubQuery) | ❌ 未实现 | 嵌套 SELECT |
| 属性路径 (Property Path) | ✅ 已实现 | `*`, `+`, `?`, `|`, `/`, `^`, `!` |
| IR 中间表示 | ✅ 已实现 | LogicNode 完整定义 |
| 谓词下推优化 | ✅ 已实现 | FilterPushdown Pass |
| 连接重排序 | ⚠️ 部分实现 | 贪心算法，缺少 DPSize |
| 成本模型 | ❌ 未实现 | 需要统计信息和选择性估计 |
| OWL 2 QL 推理 | ⚠️ 部分实现 | 概念/属性层次，缺少饱和算法 |
| 联邦查询 (SERVICE) | ⚠️ 部分实现 | HTTP 客户端，缺少物化 |
| R2RML 映射 | ❌ 未实现 | 仅 OBDA 基础格式 |
| SQL 代码生成 | ⚠️ 部分实现 | PostgreSQL 方言 |
| PG 扩展部署 | ✅ 已实现 | Background Worker |

---

## 1. 核心查询翻译链路

### 1.1 主入口: `OntopEngine::translate` [S6-P0-1]

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
    
    // 5. TBox 重写 (OWL 2 QL)
    IF self.tbox.is_some():
        rewriter = TBoxRewriter::from_tbox(self.tbox.as_ref().unwrap())
        logic_plan = rewriter.rewrite(&logic_plan)
    END IF
    
    // 6. 查询优化
    logic_plan = RedundantJoinElimination::apply(logic_plan)
    logic_plan = FilterPushdown::apply(logic_plan)
    logic_plan = JoinReordering::apply(logic_plan, &ctx.statistics)
    
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

### 2.1 基础 SELECT 解析 [S6-P0-1] ✅

```pseudocode
FUNCTION parse_select_query(tokens: Vec<Token>) -> Result<SelectQuery, ParseError>:
    consume(tokens, "SELECT")?
    
    // DISTINCT / REDUCED
    modifier = parse_select_modifier(tokens)
    
    // 变量列表或 *
    variables = parse_variables(tokens)
    
    // FROM / FROM NAMED
    dataset = parse_dataset_clauses(tokens)
    
    // WHERE 子句
    consume(tokens, "WHERE")?
    pattern = parse_group_graph_pattern(tokens)
    
    // ORDER BY / LIMIT / OFFSET
    solution_modifiers = parse_solution_modifiers(tokens)
    
    RETURN SelectQuery {
        modifier,
        variables,
        dataset,
        pattern,
        solution_modifiers,
    }
END FUNCTION
```

### 2.2 属性路径解析 [S6-P1-1] ✅

```pseudocode
FUNCTION parse_property_path(tokens: Vec<Token>) -> Result<PropertyPath, ParseError>:
    // 替代 (最低优先级): a | b
    RETURN parse_alternative(tokens)
END FUNCTION

FUNCTION parse_alternative(tokens: Vec<Token>) -> Result<PropertyPath, ParseError>:
    alternatives = [parse_sequence(tokens)]
    
    WHILE peek(tokens) == "|":
        consume(tokens)
        alternatives.push(parse_sequence(tokens))
    END WHILE
    
    IF alternatives.len() == 1:
        RETURN alternatives[0]
    ELSE:
        RETURN PropertyPath::Alternative(alternatives)
    END IF
END FUNCTION

FUNCTION parse_sequence(tokens: Vec<Token>) -> Result<PropertyPath, ParseError>:
    sequences = [parse_inverse_or_primary(tokens)]
    
    WHILE peek(tokens) == "/":
        consume(tokens)
        sequences.push(parse_inverse_or_primary(tokens))
    END WHILE
    
    IF sequences.len() == 1:
        RETURN sequences[0]
    ELSE:
        RETURN PropertyPath::Sequence(sequences)
    END IF
END FUNCTION
```

### 2.3 CONSTRUCT / 聚合 / 子查询 [S6-P1-2] ❌

```pseudocode
FUNCTION parse_construct_query(tokens: Vec<Token>) -> Result<ConstructQuery, ParseError>:
    // [S6-P2-1] 未实现
    // 需要: 模板图模式解析、RDF 序列化
    UNIMPLEMENTED("CONSTRUCT 查询需要模板实例化")
END FUNCTION

FUNCTION parse_aggregate_query(tokens: Vec<Token>) -> Result<AggregateQuery, ParseError>:
    // [S6-P1-2] 未实现
    // 需要: GROUP BY、COUNT/SUM/AVG、HAVING
    UNIMPLEMENTED("聚合查询需要 AST 扩展")
END FUNCTION

FUNCTION parse_subquery(tokens: Vec<Token>) -> Result<SubQuery, ParseError>:
    // [S6-P2-1] 未实现
    // 需要: 作用域管理、关联子查询检测
    UNIMPLEMENTED("子查询需要作用域管理")
END FUNCTION
```

---

## 3. IR (中间表示) 模块

### 3.1 LogicNode 定义 [S6-P0-1] ✅

```pseudocode
ENUM LogicNode:
    // 数据节点
    IntensionalData { predicate: String, args: Vec<Term> }
    ExtensionalData { table: String, args: Vec<Term> }
    
    // 操作节点
    Join { join_type: JoinType, left: Box<LogicNode>, right: Box<LogicNode>, conditions: Vec<(Term, Term)> }
    Filter { expression: Expr, child: Box<LogicNode> }
    Project { variables: Vec<String>, child: Box<LogicNode> }
    Distinct { child: Box<LogicNode> }
    OrderBy { variables: Vec<String>, ascending: Vec<bool>, child: Box<LogicNode> }
    Limit { limit: usize, offset: Option<usize>, child: Box<LogicNode> }
    
    // 图模式
    Graph { graph_name: Term, child: Box<LogicNode>, is_named_graph: bool }
    GraphUnion { left: Box<LogicNode>, right: Box<LogicNode> }
    Union { left: Box<LogicNode>, right: Box<LogicNode> }
    
    // 联邦查询
    Service { endpoint: String, query: String, child: Option<Box<LogicNode>> }
    
    // [S6-P1-2] 未实现:
    // GroupBy { groups, aggregates, child }
    // Aggregate { function, expr, distinct }
    // SubQuery { query, alias, correlated_vars }
END ENUM
```

### 3.2 IR 构建器 [S6-P0-1] ✅

```pseudocode
FUNCTION build_from_ast(ast: SparqlAst) -> Result<LogicNode, IRError>:
    MATCH ast:
        CASE Select(query):
            RETURN build_select_query(query)
        CASE _:
            RETURN Err(IRError::UnsupportedQueryType)
    END MATCH
END FUNCTION

FUNCTION build_select_query(query: SelectQuery) -> Result<LogicNode, IRError>:
    // 1. 基本图模式
    current = build_bgp(query.pattern.bgp)?
    
    // 2. OPTIONAL (左连接)
    FOR optional IN query.pattern.optionals:
        optional_node = build_bgp(optional.pattern)?
        current = Join {
            join_type: LeftOuter,
            left: current,
            right: optional_node,
            conditions: infer_join_conditions(&current, &optional_node),
        }
    END FOR
    
    // 3. UNION
    FOR union IN query.pattern.unions:
        union_node = build_union_branches(union)?
        current = Union { left: current, right: union_node }
    END FOR
    
    // 4. FILTER
    FOR filter IN query.pattern.filters:
        current = Filter { expression: filter.expression, child: current }
    END FOR
    
    // 5. GRAPH
    FOR graph IN query.pattern.graphs:
        current = Graph { graph_name: graph.name, child: current, is_named_graph: graph.is_named }
    END FOR
    
    // 6. 投影、去重、排序、限制
    IF query.variables != ["*"]:
        current = Project { variables: query.variables, child: current }
    END IF
    
    IF query.solution_modifiers.distinct:
        current = Distinct { child: current }
    END IF
    
    IF query.solution_modifiers.order_by.is_some():
        ob = query.solution_modifiers.order_by.unwrap()
        current = OrderBy { variables: ob.variables, ascending: ob.ascending, child: current }
    END IF
    
    IF query.solution_modifiers.limit.is_some():
        current = Limit {
            limit: query.solution_modifiers.limit.unwrap(),
            offset: query.solution_modifiers.offset,
            child: current,
        }
    END IF
    
    RETURN Ok(current)
END FUNCTION
```

---

## 4. 查询优化模块

### 4.1 Pass 管理器 [S6-P0-2] ✅

```pseudocode
STRUCT PassManager:
    passes: Vec<Box<dyn OptimizationPass>>,
    execution_order: Vec<usize>,
END STRUCT

FUNCTION new() -> PassManager:
    manager = PassManager::default()
    
    // 已实现的 Pass
    manager.register(FilterPushdown::new(), weight=50)
    manager.register(JoinReordering::new(), weight=200)
    manager.register(RedundantJoinElimination::new(), weight=100)
    manager.register(ConstantFolding::new(), weight=75)
    
    // [S6-P1-3] 未实现:
    // ProjectionPushdown (weight=60)
    // DistinctPushdown (weight=70)
    
    manager.compute_execution_order()
    RETURN manager
END FUNCTION

FUNCTION execute(manager: PassManager, plan: LogicNode, ctx: OptimizerContext) -> Result<LogicNode, OptimizerError>:
    current = plan
    
    FOR pass_idx IN manager.execution_order:
        pass = manager.passes[pass_idx]
        IF !pass.is_enabled():
            CONTINUE
        END IF
        current = pass.optimize(current, &ctx)?
    END FOR
    
    RETURN Ok(current)
END FUNCTION
```

### 4.2 谓词下推 [S6-P0-2] ✅

```pseudocode
FUNCTION pushdown_filter(plan: LogicNode) -> LogicNode:
    MATCH plan:
        CASE Filter { expression, child }:
            RETURN try_push_filter(expression, child)
        
        CASE Join { join_type, left, right, conditions }:
            new_left = pushdown_filter(left)
            new_right = pushdown_filter(right)
            RETURN Join { join_type, left: new_left, right: new_right, conditions }
        
        CASE Graph { graph_name, child, is_named_graph }:
            RETURN Graph { graph_name, child: pushdown_filter(child), is_named_graph }
        
        CASE Union { left, right }:
            // 下推到两边
            RETURN Union {
                left: Filter { expression: expression.clone(), child: left },
                right: Filter { expression, child: right },
            }
        
        CASE _:
            RETURN plan.map_children(|c| pushdown_filter(c))
    END MATCH
END FUNCTION

FUNCTION try_push_filter(expr: Expr, child: LogicNode) -> LogicNode:
    MATCH child:
        CASE Join { join_type, left, right, conditions }:
            // 分析变量分布
            expr_vars = extract_variables(expr)
            left_vars = extract_variables_from_node(left)
            right_vars = extract_variables_from_node(right)
            
            // 分类表达式
            (left_only, right_only, both) = classify_expression(expr, left_vars, right_vars)
            
            new_left = IF left_only.is_empty() THEN left
                ELSE Filter { expression: combine_expressions(left_only), child: left }
            END IF
            
            new_right = IF right_only.is_empty() THEN right
                ELSE Filter { expression: combine_expressions(right_only), child: right }
            END IF
            
            join_node = Join { join_type, left: new_left, right: new_right, conditions }
            
            IF both.is_empty():
                RETURN join_node
            ELSE:
                RETURN Filter { expression: combine_expressions(both), child: join_node }
            END IF
        
        CASE _:
            RETURN Filter { expression: expr, child }
    END MATCH
END FUNCTION
```

### 4.3 连接重排序 [S6-P1-2] ⚠️

```pseudocode
FUNCTION reorder_joins(plan: LogicNode, statistics: Statistics) -> LogicNode:
    (relations, predicates) = collect_joins(plan)
    
    IF relations.len() <= 2:
        RETURN rebuild_plan(relations, predicates)
    END IF
    
    // 选择算法
    IF relations.len() <= 10 AND statistics.is_available():
        optimal_order = dp_size_optimal_order(relations, predicates, statistics)  // [S6-P1-3] 未完整实现
    ELSE:
        optimal_order = greedy_order(relations, predicates, statistics)  // ✅ 已实现
    END IF
    
    RETURN rebuild_plan(optimal_order, predicates)
END FUNCTION

FUNCTION greedy_order(relations: Vec<LogicNode>, predicates: JoinPredicates, stats: Statistics) -> Vec<LogicNode>:
    remaining = relations
    result = []
    current_vars = {}
    
    // 选择基数最小的作为起始
    start_idx = argmin(remaining, |rel| estimate_cardinality(rel, stats))
    start_rel = remaining.remove(start_idx)
    result.push(start_rel)
    current_vars = extract_variables(start_rel)
    
    // 贪心选择
    WHILE !remaining.is_empty():
        best_idx = argmin(remaining, |rel| estimate_join_cost(current_vars, rel, predicates, stats))
        best_rel = remaining.remove(best_idx)
        result.push(best_rel)
        current_vars.extend(extract_variables(best_rel))
    END WHILE
    
    RETURN result
END FUNCTION
```

### 4.4 成本模型 [S6-P2-2] ❌

```pseudocode
STRUCT CostModel:
    table_statistics: Map<String, TableStatistics>,
    column_statistics: Map<String, ColumnStatistics>,
END STRUCT

FUNCTION estimate_cost(cost_model: CostModel, plan: LogicNode) -> f64:
    // [S6-P2-2] 未实现
    // 需要: 表/列统计信息、直方图、选择性估计
    UNIMPLEMENTED("成本模型需要完整的统计信息基础设施")
END FUNCTION

FUNCTION estimate_selectivity(cost_model: CostModel, expr: Expr, table: String) -> f64:
    // [S6-P2-2] 未实现
    UNIMPLEMENTED("选择性估计需要直方图数据")
END FUNCTION
```

---

## 5. OWL 2 QL 推理模块

### 5.1 TBox 结构 [S6-P0-3] ✅

```pseudocode
STRUCT TBox:
    concepts: Map<String, ConceptDefinition>
    properties: Map<String, PropertyDefinition>
    subsumptions: Vec<(String, String)>  // C ⊑ D
    equivalences: Vec<(String, String)>  // C ≡ D
    property_subsumptions: Vec<PropertySubsumption>  // P ⊑ Q
    domain_constraints: Map<String, String>  // property -> concept
    range_constraints: Map<String, String>
    property_characteristics: Map<String, PropertyCharacteristics>
END STRUCT

STRUCT PropertyCharacteristics:
    functional: bool           // ⚠️ 部分实现
    inverse_functional: bool  // ❌ 未使用
    reflexive: bool           // ❌ 未使用
    irreflexive: bool         // ❌ 未使用
    symmetric: bool           // ❌ 未使用
    asymmetric: bool          // ❌ 未使用
    transitive: bool            // ❌ 未使用
END STRUCT
```

### 5.2 概念层次管理 [S6-P0-3] ✅

```pseudocode
STRUCT ConceptHierarchy:
    parents: Map<String, Set<String>>
    children: Map<String, Set<String>>
    transitive_cache: Map<String, Set<String>>
END STRUCT

FUNCTION add_edge(hierarchy: ConceptHierarchy, sub: String, sup: String):
    hierarchy.parents[sub].insert(sup)
    hierarchy.children[sup].insert(sub)
    clear_cache(hierarchy, sub)
    clear_cache(hierarchy, sup)
END FUNCTION

FUNCTION is_subsumed(hierarchy: ConceptHierarchy, sub: String, sup: String) -> bool:
    IF sub == sup:
        RETURN true
    END IF
    
    all_parents = get_all_parents(hierarchy, sub)
    RETURN all_parents.contains(sup)
END FUNCTION

FUNCTION get_all_parents(hierarchy: ConceptHierarchy, concept: String) -> Set<String>:
    // 检查缓存
    IF hierarchy.transitive_cache.has_key(concept):
        RETURN hierarchy.transitive_cache[concept].clone()
    END IF
    
    // BFS 计算传递闭包
    result = Set::new()
    queue = [concept]
    
    WHILE !queue.is_empty():
        current = queue.pop()
        IF result.insert(current):
            FOR parent IN hierarchy.parents.get(current, []):
                queue.push(parent)
            END FOR
        END IF
    END WHILE
    
    hierarchy.transitive_cache[concept] = result.clone()
    RETURN result
END FUNCTION
```

### 5.3 TBox 重写器 [S6-P0-3] ✅

```pseudocode
FUNCTION rewrite_plan(rewriter: TBoxRewriter, plan: LogicNode) -> LogicNode:
    MATCH plan:
        CASE IntensionalData { predicate, args }:
            RETURN rewrite_intensional(rewriter, predicate, args)
        
        CASE Join { join_type, left, right, conditions }:
            new_left = rewrite_plan(rewriter, left)
            new_right = rewrite_plan(rewriter, right)
            RETURN Join { join_type, left: new_left, right: new_right, conditions }
        
        CASE Filter { expression, child }:
            RETURN Filter { expression, child: rewrite_plan(rewriter, child) }
        
        CASE Graph { graph_name, child, is_named_graph }:
            RETURN Graph { graph_name, child: rewrite_plan(rewriter, child), is_named_graph }
        
        CASE _:
            RETURN plan
    END MATCH
END FUNCTION

FUNCTION rewrite_intensional(rewriter: TBoxRewriter, predicate: String, args: Vec<Term>) -> LogicNode:
    sub_properties = get_sub_properties(rewriter.property_hierarchy, predicate)
    
    IF sub_properties.is_empty():
        RETURN IntensionalData { predicate, args }
    END IF
    
    // 构建 Union 节点
    branches = [IntensionalData { predicate: predicate.clone(), args: args.clone() }]
    
    FOR (sub_prop, inverse) IN sub_properties:
        IF inverse.is_some():
            rewritten_args = [args[1], args[0]]  // 交换参数
        ELSE:
            rewritten_args = args.clone()
        END IF
        
        branches.push(IntensionalData { predicate: sub_prop, args: rewritten_args })
    END FOR
    
    RETURN build_left_deep_union(branches)
END FUNCTION
```

### 5.4 DL-Lite 饱和算法 [S6-P1-3] ❌

```pseudocode
FUNCTION saturate_tbox(tbox: TBox) -> TBox:
    // [S6-P1-3] 未实现
    // DL-Lite R 推理规则：
    // R1: C1 ⊑ C2, C2 ⊑ C3 => C1 ⊑ C3 (传递性)
    // R2: ∃R ⊑ C, C ⊑ D => ∃R ⊑ D
    // R3: C ⊑ ∃R, ∃R ⊑ D => C ⊑ D
    // R4: R ⊑ S, S ⊑ T => R ⊑ T (传递性)
    // R5: R ⊑ S, domain(S)=C => domain(R)=C
    // R6: R ⊑ S, range(S)=C => range(R)=C
    // R7: R ⊑ S => inv(R) ⊑ inv(S)
    
    UNIMPLEMENTED("DL-Lite 饱和算法需要完整的推理规则实现")
END FUNCTION
```

---

## 6. 联邦查询模块

### 6.1 联邦查询执行器 [S6-P1-1] ⚠️

```pseudocode
STRUCT FederatedQueryExecutor:
    http_client: HttpClient
    endpoints: Map<String, ServiceEndpoint>
    timeout: Duration
    cache: Map<String, ServiceResult>
END STRUCT

FUNCTION register_endpoint(executor: FederatedQueryExecutor, endpoint: ServiceEndpoint) -> Result:
    validate_endpoint(endpoint)?
    executor.endpoints[endpoint.name] = endpoint
    RETURN Ok(())
END FUNCTION

FUNCTION execute_service_query(executor: FederatedQueryExecutor, endpoint_name: String, query: String) -> Result<ServiceResult, ServiceError>:
    // 1. 查找端点
    endpoint = executor.endpoints.get(endpoint_name)
        .ok_or(Error::EndpointNotFound)?
    
    // 2. 检查缓存
    cache_key = format("{}:{}", endpoint_name, hash(query))
    IF executor.cache.has_key(cache_key):
        RETURN Ok(executor.cache[cache_key].clone())
    END IF
    
    // 3. 发送 HTTP 请求
    request = HttpRequest::new()
        .url(endpoint.url)
        .method("GET")
        .query_param("query", query)
        .header("Accept", "application/sparql-results+json")
    
    IF endpoint.requires_auth:
        request = request.header("Authorization", "Bearer " + endpoint.token)
    END IF
    
    // 4. 执行请求
    response = timeout(executor.timeout, executor.http_client.send(request)).await?
    
    IF !response.is_success():
        RETURN Err(ServiceError::HttpError(response.status))
    END IF
    
    // 5. 解析结果
    result = parse_sparql_json(response.body)?
    
    // 6. 缓存
    executor.cache[cache_key] = result.clone()
    
    RETURN Ok(result)
END FUNCTION
```

### 6.2 SERVICE 结果物化 [S6-P1-2] ❌

```pseudocode
FUNCTION materialize_service_results(result: ServiceResult) -> Result<String, ServiceError>:
    // [S6-P1-2] 未实现
    // 需要:
    // - 创建临时表
    // - 批量插入数据
    // - 返回表名供后续查询使用
    
    table_name = generate_temp_table_name()
    
    // 创建表
    create_sql = format("CREATE TEMP TABLE {} (", table_name)
    FOR var IN result.variables:
        create_sql += format("{} TEXT,", var)
    END FOR
    create_sql += ")"
    
    execute_sql(create_sql)?
    
    // 批量插入
    FOR binding IN result.bindings:
        values = []
        FOR var IN result.variables:
            values.push(format("'{}'", escape_sql(binding[var].value)))
        END FOR
        
        insert_sql = format("INSERT INTO {} VALUES ({})", table_name, join(values, ", "))
        execute_sql(insert_sql)?
    END FOR
    
    RETURN Ok(table_name)
END FUNCTION
```

---

## 7. SQL 生成模块

### 7.1 SQL 生成器 [S6-P0-2] ⚠️

```pseudocode
STRUCT SqlGenerator:
    dialect: SqlDialect  // 当前: PostgreSQL
END STRUCT

FUNCTION generate_sql(generator: SqlGenerator, plan: LogicNode) -> Result<String, SqlError>:
    MATCH plan:
        CASE IntensionalData { predicate, args }:
            RETURN generate_intensional_sql(generator, predicate, args)
        
        CASE Join { join_type, left, right, conditions }:
            RETURN generate_join_sql(generator, join_type, left, right, conditions)
        
        CASE Filter { expression, child }:
            RETURN generate_filter_sql(generator, expression, child)
        
        CASE Union { left, right }:
            left_sql = generate_sql(generator, left)?
            right_sql = generate_sql(generator, right)?
            RETURN format("({} UNION ALL {})", left_sql, right_sql)
        
        CASE Project { variables, child }:
            child_sql = generate_sql(generator, child)?
            RETURN format("SELECT {} FROM ({}) AS proj", join(variables, ", "), child_sql)
        
        CASE Distinct { child }:
            child_sql = generate_sql(generator, child)?
            RETURN format("SELECT DISTINCT * FROM ({}) AS distinct_tbl", child_sql)
        
        CASE OrderBy { variables, ascending, child }:
            child_sql = generate_sql(generator, child)?
            order_clauses = []
            FOR (i, var) IN variables.enumerate():
                dir = IF ascending[i] THEN "ASC" ELSE "DESC" END IF
                order_clauses.push(format("{} {}", var, dir))
            END FOR
            RETURN format("{} ORDER BY {}", child_sql, join(order_clauses, ", "))
        
        CASE Limit { limit, offset, child }:
            child_sql = generate_sql(generator, child)?
            sql = format("{} LIMIT {}", child_sql, limit)
            IF offset.is_some():
                sql += format(" OFFSET {}", offset.unwrap())
            END IF
            RETURN sql
        
        // [S6-P1-2] 未实现: GroupBy, Aggregate, SubQuery
        
        CASE _:
            RETURN Err(SqlError::UnsupportedNode)
    END MATCH
END FUNCTION
```

### 7.2 多数据库方言 [S6-P2-1] ❌

```pseudocode
ENUM SqlDialect:
    PostgreSQL   // ✅ 已实现
    MySQL        // ❌ 未实现
    SQLite       // ❌ 未实现
    Oracle       // ❌ 未实现
    SQLServer    // ❌ 未实现
END ENUM

FUNCTION map_sparql_function(dialect: SqlDialect, name: String) -> Result<String, SqlError>:
    MATCH dialect:
        CASE PostgreSQL:
            RETURN map_postgresql_function(name)
        
        CASE MySQL:
            // [S6-P2-1] 未实现
            UNIMPLEMENTED("MySQL 方言支持")
        
        CASE _:
            RETURN Err(SqlError::UnsupportedDialect(dialect))
    END MATCH
END FUNCTION
```

---

## 8. 部署与集成

### 8.1 PostgreSQL 扩展 [S6-P0-3] ✅

```pseudocode
FUNCTION pg_init():
    // 注册后台 Worker
    BackgroundWorkerBuilder::new("rs_ontop_core SPARQL Web Gateway")
        .set_function("sparql_worker_main")
        .set_library("rs_ontop_core")
        .enable_spi_access()
        .load()
    
    // 注册事务回调
    register_xact_callback(transaction_callback)
    
    // 初始化全局状态
    global_state = Arc::new(GlobalState::new())
    store_global_state(global_state)
END FUNCTION

FUNCTION sparql_worker_main(arg: Datum):
    ctx = BackgroundWorkerContext::new()
    runtime = TokioRuntime::new()
    
    runtime.block_on(async {
        server = SparqlServer::new(get_global_state())
        server.run().await
    })
END FUNCTION
```

### 8.2 CLI 工具 [S6-P2-1] ❌

```pseudocode
// [S6-P2-1] 未实现
// 需要: 命令行参数解析、独立运行模式、查询文件批处理、结果输出格式

FUNCTION main_cli():
    UNIMPLEMENTED("CLI 工具需要独立运行模式支持")
END FUNCTION
```

### 8.3 HTTP 服务 [S6-P2-1] ❌

```pseudocode
// [S6-P2-1] 未实现
// 需要: HTTP 路由、SPARQL 协议端点、内容协商、认证/授权

FUNCTION run_http_server(state: Arc<AppState>) -> Result:
    UNIMPLEMENTED("HTTP 服务需要独立服务器支持")
END FUNCTION
```

---

## 9. 能力差距总结

### 9.1 与开源 Ontop 对比

| 能力维度 | Sprint6 状态 | 开源 Ontop | 差距 |
|---------|-------------|-----------|------|
| SPARQL 完整度 | 60% | 100% | 40% |
| 查询优化 | 40% | 95% | 55% |
| OWL 2 QL 推理 | 50% | 95% | 45% |
| 联邦查询 | 40% | 90% | 50% |
| 数据源支持 | 10% | 100% | 90% |
| 部署方式 | 30% | 95% | 65% |
| **总体成熟度** | **38%** | **96%** | **58%** |

### 9.2 优先级建议

**P0 - 必须实现**:
1. R2RML 映射解析器 [S6-P0-4]
2. GROUP BY / 聚合函数 [S6-P1-2]
3. 基础成本模型 [S6-P1-3]

**P1 - 重要实现**:
4. SERVICE 结果物化 [S6-P1-2]
5. DL-Lite 饱和算法 [S6-P1-3]
6. 多数据库方言 [S6-P2-1]

**P2 - 增强功能**:
7. CLI 工具 [S6-P2-1]
8. 独立 HTTP 服务 [S6-P2-1]
9. 监控/日志系统 [S6-P2-2]

---

**文档版本**: Sprint6  
**关联文档**: `/doc/sprint5/current-system-pseudocode.md`
