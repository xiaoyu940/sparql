# RS Ontop Core 当前系统伪代码（Sprint5 基线）

> 更新时间：2026-03-29  
> 用途：作为 Sprint5 的"当前状态基线文档"，描述 Sprint4 完成后已落地实现路径  
> 基于实际代码生成，反映 `/src` 目录当前状态

> 标识规范：`[S4-Px-y]` 对应 Sprint4 的任务项。  
> 优先级：`P0` 必做，`P1` 应做，`P2` 可选。

---

## Sprint5 系统概览

### 已实现的 Sprint4 核心功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 查询缓存 (CacheManager) | ✅ 已实现 | QueryPlanCache + CacheManager + PG 函数 |
| 属性路径 (Property Path) | ✅ 已实现 | `LogicNode::Path` + `PropertyPath` 枚举 |
| 属性路径解析器 | ✅ 已实现 | `PropertyPathParser` 支持 *, +, ?, /, \|, ^, ! |
| 属性路径 SQL 生成 | ✅ 已实现 | 递归 CTE 生成器 |
| SERVICE 联邦查询 | ✅ 已实现 | `service.rs` 模块框架 |
| ORDER BY 支持 | ✅ 已实现 | `flat_generator.rs` 生成 ORDER BY 子句 |
| OFFSET 支持 | ✅ 已实现 | `LogicNode::Limit` offset 字段处理 |

---

## 1. 核心查询翻译链路

### 1.1 主入口: `OntopEngine::translate`

```pseudocode
FUNCTION translate(sparql_query: String) -> Result<String, String>:
    // 1. SPARQL 解析
    parser = SparqlParserV2::default()
    parsed = parser.parse(sparql_query)?
    
    // 2. IR 构建
    builder = IRBuilder::new()
    mut logic_plan = builder.build_with_mappings(
        &parsed, 
        &self.metadata, 
        Some(self.mappings.as_ref())
    )?
    
    // 3. 优化器上下文
    ctx = OptimizerContext {
        mappings: Arc::clone(&self.mappings),
        metadata: self.metadata.clone(),
    }
    
    // 4. 映射展开 + TBox 重写
    MappingUnfolder::unfold(&mut logic_plan, &ctx)
    logic_plan = TBoxRewriter::rewrite(&logic_plan, &self.mappings)
    
    // 5. 传统优化
    logic_plan = RedundantJoinElimination::apply(logic_plan)
    logic_plan = FilterPushdown::apply(logic_plan)
    logic_plan = JoinReordering::apply(logic_plan)
    
    // 6. PassManager 优化
    pass_manager = PassManager::new()
    pass_manager.run(&mut logic_plan, &ctx)
    
    // 7. SQL 生成
    mut generator = FlatSQLGenerator::new()
    generator.generate(&logic_plan)
END FUNCTION
```

### 1.2 带缓存的翻译: `OntopEngine::translate_with_cache` [S4-P1-3]

```pseudocode
FUNCTION translate_with_cache(sparql_query: String) -> Result<String, String>:
    // 如果缓存禁用，直接走普通翻译流程
    IF !self.cache_manager.is_enabled():
        RETURN self.translate(sparql_query)
    
    // 1. 构建优化器上下文（用于生成缓存键）
    ctx = OptimizerContext {
        mappings: Arc::clone(&self.mappings),
        metadata: self.metadata.clone(),
    }
    
    // 2. 生成缓存键
    cache_key = self.cache_manager.generate_cache_key(sparql_query, &ctx)
    
    // 3. 尝试从缓存获取
    cached_plan = self.cache_manager.get_or_create(&cache_key, || None)
    
    // 4. 缓存命中，直接返回
    IF cached_plan EXISTS:
        RETURN Ok(cached_plan.generated_sql)
    
    // 5. 缓存未命中，执行翻译
    sql = self.translate(sparql_query)?
    
    // 6. 创建并插入缓存计划
    new_plan = CachedPlan::new(
        LogicNode::Union(vec![]),
        sql.clone(),
        1.0,
    )
    self.cache_manager.get_or_create(&cache_key, || Some(new_plan))
    
    RETURN Ok(sql)
END FUNCTION
```

---

## 2. IR (Intermediate Representation) 层

### 2.1 LogicNode 枚举

```pseudocode
ENUM LogicNode:
    // 投影、别名和计算列
    Construction {
        projected_vars: Vec<String>,
        bindings: HashMap<String, Expr>,
        child: Box<LogicNode>,
    }
    
    // N 元连接操作符
    Join {
        children: Vec<LogicNode>,
        condition: Option<Expr>,
        join_type: JoinType,
    }
    
    // 物理表扫描
    ExtensionalData {
        table_name: String,
        column_mapping: HashMap<String, String>,
        metadata: Arc<TableMetadata>,
    }
    
    // 未展开的逻辑谓词（虚拟 RDF 谓词）
    IntensionalData {
        predicate: String,
        args: Vec<Term>,
    }
    
    // 过滤操作
    Filter {
        expression: Expr,
        child: Box<LogicNode>,
    }
    
    // 并集操作
    Union(Vec<LogicNode>)
    
    // 分组聚合
    Aggregation {
        group_by: Vec<String>,
        aggregates: HashMap<String, Expr>,
        child: Box<LogicNode>,
    }
    
    // 分页限制 [S4-P0-2] OFFSET 支持已实现
    Limit {
        limit: usize,
        offset: Option<usize>,              // 字段已启用
        order_by: Vec<(String, bool)>,      // [S4-P0-1] ORDER BY 支持
        child: Box<LogicNode>,
    }
    
    // VALUES 数据块
    Values {
        variables: Vec<String>,
        rows: Vec<Vec<Term>>,
    }
    
    // [S4-P1-1] 属性路径 (Property Path) - 已实现
    Path {
        subject: Term,
        path: PropertyPath,                  // 属性路径表达式
        object: Term,
    }
END ENUM
```

### 2.2 PropertyPath 枚举 [S4-P1-1]

```pseudocode
ENUM PropertyPath:
    // 零次或多次: p*
    Star(Box<PropertyPath>),
    
    // 一次或多次: p+
    Plus(Box<PropertyPath>),
    
    // 零次或一次: p?
    Optional(Box<PropertyPath>),
    
    // 序列: p1/p2
    Sequence(Vec<PropertyPath>),
    
    // 选择: p1|p2
    Alternative(Vec<PropertyPath>),
    
    // 逆序: ^p
    Inverse(Box<PropertyPath>),
    
    // 否定属性集: !p 或 !(p1|p2)
    Negated(Vec<String>),
    
    // 简单谓词 (IRI)
    Predicate(String),
END ENUM
```

### 2.3 Expression 系统

```pseudocode
ENUM Term:
    Variable(String)
    Constant(String)
    Literal { value: String, datatype: Option<String> }

ENUM Expr:
    Term(Term)
    Compare {
        left: Box<Expr>,
        op: ComparisonOp,                   // Eq | Neq | Lt | Lte | Gt | Gte | In | NotIn
        right: Box<Expr>,
    }
    Logical {
        op: LogicalOp,                        // And | Or | Not
        args: Vec<Expr>,
    }
    Function {
        name: String,                         // 函数名: COUNT, AVG, STR, REGEX, etc.
        args: Vec<Expr>,
    }
END ENUM
```

### 2.4 IRConverter 属性路径处理 [S4-P1-1]

```pseudocode
FUNCTION convert_property_path(
    pattern: &TriplePattern,
    metadata: Arc<TableMetadata>,
    mappings: Option<&MappingStore>
) -> LogicNode:
    
    pred = pattern.predicate.trim()
    
    // 去除最外层括号
    IF pred.starts_with('(') AND pred.ends_with(')'):
        pred = pred[1..pred.len() - 1].trim()
    
    // 处理选择路径 (p1|p2)
    IF pos = find_logical_op(pred, "|"):
        p1 = pred[..pos].trim()
        p2 = pred[pos + 1..].trim()
        
        RETURN LogicNode::Union(vec![
            pattern_to_logic_node(p1_pattern),
            pattern_to_logic_node(p2_pattern)
        ])
    
    // 处理序列路径 (p1/p2)
    ELSE IF pos = find_logical_op(pred, "/"):
        p1 = pred[..pos].trim()
        p2 = pred[pos + 1..].trim()
        
        // 生成空白节点
        blank_var = format!("?bl_{}", uuid)
        
        n1 = pattern_to_logic_node(subject-p1-blank)
        n2 = pattern_to_logic_node(blank-p2-object)
        
        RETURN LogicNode::Join {
            children: vec![n1, n2],
            condition: None,
            join_type: JoinType::Inner,
        }
    
    // [S4-P1-1] 解析并构建 PropertyPath
    IF parsed_path = PropertyPathParser::parse(pred):
        RETURN LogicNode::Path {
            subject: token_to_term(pattern.subject),
            path: parsed_path,
            object: token_to_term(pattern.object),
        }
    
    // Fallback: 普通谓词
    RETURN pattern_to_logic_node(pattern)
END FUNCTION
```

---

## 3. 属性路径解析器 [S4-P1-1]

### 3.1 PropertyPathParser

```pseudocode
STRUCT PropertyPathParser

FUNCTION parse(path_str: &str) -> Option<PropertyPath>:
    trimmed = path_str.trim()
    IF trimmed.is_empty(): RETURN None
    
    // 检查修饰符: *, +, ?
    IF stripped = trimmed.strip_suffix("*"):
        RETURN parse(stripped).map(|inner| PropertyPath::Star(Box::new(inner)))
    
    IF stripped = trimmed.strip_suffix("+"):
        RETURN parse(stripped).map(|inner| PropertyPath::Plus(Box::new(inner)))
    
    IF stripped = trimmed.strip_suffix("?"):
        RETURN parse(stripped).map(|inner| PropertyPath::Optional(Box::new(inner)))
    
    // 检查逆序: ^p
    IF stripped = trimmed.strip_prefix("^"):
        RETURN parse(stripped).map(|inner| PropertyPath::Inverse(Box::new(inner)))
    
    // 检查序列: p1/p2 (优先级高于 |)
    IF path = parse_sequence(trimmed):
        RETURN Some(path)
    
    // 检查选择: p1|p2
    IF path = parse_alternative(trimmed):
        RETURN Some(path)
    
    // 检查否定: !p 或 !(p1|p2)
    IF trimmed.starts_with("!"):
        RETURN parse_negated(trimmed)
    
    // 简单谓词 (IRI 或缩写)
    RETURN Some(PropertyPath::Predicate(trimmed.to_string()))
END FUNCTION

FUNCTION parse_sequence(path_str: &str) -> Option<PropertyPath>:
    parts = split_path(path_str, '/')
    IF parts.len() > 1:
        paths = parts.iter().filter_map(|p| parse(p)).collect()
        IF paths.len() > 1:
            RETURN Some(PropertyPath::Sequence(paths))
    RETURN None
END FUNCTION

FUNCTION parse_alternative(path_str: &str) -> Option<PropertyPath>:
    parts = split_path(path_str, '|')
    IF parts.len() > 1:
        paths = parts.iter().filter_map(|p| parse(p)).collect()
        IF paths.len() > 1:
            RETURN Some(PropertyPath::Alternative(paths))
    RETURN None
END FUNCTION
```

---

## 4. SQL 生成层

### 4.1 FlatSQLGenerator

```pseudocode
STRUCT FlatSQLGenerator:
    ctx: GeneratorContext
    alias_manager: AliasManager

FUNCTION generate(root_node: &LogicNode) -> Result<String, GenerationError>:
    self.reset_context()
    
    // UNION 根节点特殊处理
    IF LogicNode::Union(children) = root_node:
        self.ctx.union_sql = self.generate_union_sql(children)?
        RETURN self.assemble_sql()
    
    // 遍历 IR 树
    self.traverse_node(root_node)?
    
    // 拼装 SQL
    self.assemble_sql()
END FUNCTION

FUNCTION traverse_node(node: &LogicNode) -> Result<(), GenerationError>:
    MATCH node:
        ExtensionalData { ... }:
            self.handle_extensional_data(...)
        
        Join { ... }:
            self.handle_join(...)
        
        Filter { ... }:
            self.handle_filter(...)
        
        Construction { ... }:
            self.handle_construction(...)
        
        Union(children):
            self.handle_union(children)
        
        Aggregation { ... }:
            self.handle_aggregation(...)
        
        // [S4-P0-1] ORDER BY + [S4-P0-2] OFFSET 支持
        Limit { limit, offset, order_by, child }:
            self.handle_limit(*limit, *offset, order_by, child)?
        
        // [S4-P1-1] 属性路径 SQL 生成
        Path { subject, path, object }:
            self.handle_property_path(subject, path, object)?
        
        Values { ... }:
            self.handle_values(...)
END FUNCTION
```

### 4.2 属性路径 SQL 生成 [S4-P1-1]

```pseudocode
FUNCTION handle_property_path(
    subject: &Term,
    path: &PropertyPath,
    object: &Term
) -> Result<(), GenerationError>:
    
    // 使用 PropertyPathSQLGenerator 生成递归 CTE
    path_sql = PropertyPathSQLGenerator::generate(
        subject, path, object, 
        &self.alias_manager.allocate_table_alias("path")
    )?
    
    // 将路径查询作为子查询加入 FROM
    path_alias = self.alias_manager.allocate_table_alias("path_result")
    self.ctx.from_tables.push(FromTable {
        table_name: format!("({})", path_sql),
        alias: path_alias.clone(),
        join_type: None,
        join_condition: None,
    })
END FUNCTION

// PropertyPathSQLGenerator 伪代码
FUNCTION generate_recursive_cte(
    subject: &Term,
    path: &PropertyPath,
    object: &Term
) -> Result<String, GenerationError>:
    
    cte_name = format!("{}_path_{}", alias, counter)
    
    // 基础查询（锚点成员）
    base_query = generate_base_query(subject, path)?
    
    // 递归查询（递归成员）
    recursive_query = generate_recursive_member(cte_name, path, object)?
    
    RETURN format!(
        "{} AS (\n  {}\n  UNION ALL\n  {}\n)",
        cte_name, base_query, recursive_query
    )
END FUNCTION
```

### 4.3 LIMIT + ORDER BY 处理 [S4-P0-1] [S4-P0-2]

```pseudocode
FUNCTION handle_limit(
    limit: usize,
    offset: Option<usize>,
    order_by: &[(String, bool)],
    child: &LogicNode
) -> Result<(), GenerationError>:
    
    // 先处理子节点
    self.traverse_node(child)?
    
    // 设置 LIMIT 和 OFFSET
    self.ctx.limit = Some(limit)
    self.ctx.offset = offset
    
    // [S4-P0-1] 转换 order_by 到 GeneratorContext
    FOR (var_name, is_desc) IN order_by:
        IF expr = self.find_column_expression(var_name):
            self.ctx.order_by.push(OrderByItem {
                expression: expr,
                direction: IF *is_desc { SortDirection::Desc } ELSE { SortDirection::Asc }
            })
    
    RETURN Ok(())
END FUNCTION

FUNCTION assemble_sql() -> Result<String, GenerationError>:
    // ... SELECT, FROM, WHERE, GROUP BY, HAVING ...
    
    // [S4-P0-1] ORDER BY 子句
    IF !self.ctx.order_by.is_empty():
        order_parts = self.ctx.order_by.map(|item| {
            match item.direction:
                SortDirection::Asc => format!("{} ASC", item.expression)
                SortDirection::Desc => format!("{} DESC", item.expression)
        }).collect()
        sql.push_str(" ORDER BY ")
        sql.push_str(&order_parts.join(", "))
    
    // LIMIT 子句
    IF limit = self.ctx.limit:
        sql.push_str(&format!(" LIMIT {}", limit))
    
    // [S4-P0-2] OFFSET 子句
    IF offset = self.ctx.offset:
        sql.push_str(&format!(" OFFSET {}", offset))
    
    RETURN Ok(sql)
END FUNCTION
```

---

## 5. 查询缓存系统 [S4-P1-3]

### 5.1 CacheManager

```pseudocode
STRUCT CacheManager:
    cache: QueryPlanCache
    config: CacheConfig

FUNCTION new(config: CacheConfig) -> Self:
    RETURN CacheManager {
        cache: QueryPlanCache::new(config.max_size, config.max_age_seconds),
        config,
    }
END FUNCTION

FUNCTION is_enabled(&self) -> bool:
    RETURN self.config.enabled
END FUNCTION

FUNCTION get_or_create<F>(
    &mut self,
    key: &str,
    f: F
) -> Option<CachedPlan>
WHERE F: FnOnce() -> Option<CachedPlan>:
    IF !self.config.enabled:
        RETURN f()
    
    // 尝试获取缓存
    IF let Some(plan) = self.cache.get(key):
        RETURN Some(plan)
    
    // 缓存未命中，创建
    IF let Some(new_plan) = f():
        self.cache.insert(key.to_string(), new_plan.clone())
        RETURN Some(new_plan)
    
    RETURN None
END FUNCTION

FUNCTION generate_cache_key(sparql: &str, ctx: &OptimizerContext) -> String:
    // 组合查询文本和上下文哈希
    context_hash = hash(&ctx.mappings)
    format!("{}:{}", hash(sparql), context_hash)
END FUNCTION

FUNCTION get_stats(&self) -> CacheStats:
    self.cache.get_stats()
END FUNCTION

FUNCTION clear(&mut self):
    self.cache.clear()
END FUNCTION
```

### 5.2 QueryPlanCache

```pseudocode
STRUCT CachedPlan:
    optimized_plan: LogicNode           // 优化后的逻辑计划
    generated_sql: String                 // 生成的 SQL
    cost: f64                             // 计划成本估算
    created_at: Instant                   // 创建时间

STRUCT QueryPlanCache:
    cache: HashMap<String, CachedPlan>
    max_size: usize
    max_age_seconds: u64
    total_hits: u64
    total_misses: u64
    evictions: u64

FUNCTION get(&mut self, key: &str) -> Option<CachedPlan>:
    IF let Some(plan) = self.cache.get(key):
        IF !self.is_expired(plan):
            self.total_hits += 1
            RETURN Some(plan.clone())
        ELSE:
            self.cache.remove(key)
    
    self.total_misses += 1
    RETURN None
END FUNCTION

FUNCTION insert(&mut self, key: String, plan: CachedPlan):
    // 智能淘汰
    IF self.cache.len() >= self.max_size AND self.config.smart_eviction:
        self.evict_lru_or_costly()
    
    self.cache.insert(key, plan)
END FUNCTION

FUNCTION get_stats(&self) -> CacheStats:
    total = self.total_hits + self.total_misses
    hit_rate = IF total > 0 { self.total_hits as f64 / total as f64 } ELSE { 0.0 }
    
    RETURN CacheStats {
        size: self.cache.len(),
        max_size: self.max_size,
        total_hits: self.total_hits,
        total_misses: self.total_misses,
        hit_rate,
        evictions: self.evictions,
    }
END FUNCTION
```

---

## 6. SERVICE 联邦查询 [S4-P2-1]

### 6.1 FederatedQueryExecutor

```pseudocode
STRUCT ServiceEndpoint:
    name: String                           // 端点标识符
    url: String                           // SPARQL Endpoint URL
    default_graph: Option<String>          // 默认图
    timeout_seconds: u64                   // 请求超时
    requires_auth: bool                    // 是否需要认证
    auth_token: Option<String>             // 认证令牌

STRUCT ServiceQuery:
    endpoint: String                       // 端点标识符
    bindings: HashMap<String, Term>        // 变量绑定
    inner_plan: Box<LogicNode>            // 子查询逻辑计划
    silent: bool                           // SILENT 模式

STRUCT FederatedQueryExecutor:
    endpoints: HashMap<String, ServiceEndpoint>
    default_timeout: u64

FUNCTION execute_service_query(
    &self,
    service_query: &ServiceQuery
) -> Future<Result<ServiceResult, ServiceError>>:
    
    // 1. 解析端点
    endpoint = self.resolve_endpoint(&service_query.endpoint)?
    
    // 2. 构建子查询 SPARQL
    sparql = self.build_service_sparql(service_query)?
    
    // 3. 发送 HTTP 请求
    TRY:
        result = self.send_sparql_request(&endpoint, &sparql).await
        RETURN Ok(result)
    CATCH e:
        IF service_query.silent:
            RETURN Ok(ServiceResult::empty())  // SILENT 模式返回空结果
        ELSE:
            RETURN Err(e)
END FUNCTION

FUNCTION resolve_endpoint(&self, identifier: &str) -> Result<ServiceEndpoint, ServiceError>:
    // 尝试直接匹配命名端点
    IF let Some(ep) = self.endpoints.get(identifier):
        RETURN Ok(ep.clone())
    
    // 处理 IRI 格式: <http://example.org/sparql>
    url = identifier.trim_start_matches('<').trim_end_matches('>')
    IF url.starts_with("http://") OR url.starts_with("https://"):
        RETURN Ok(ServiceEndpoint {
            name: url.clone(),
            url,
            default_graph: None,
            timeout_seconds: self.default_timeout,
            requires_auth: false,
            auth_token: None,
        })
    
    RETURN Err(ServiceError::UnknownEndpoint(identifier.to_string()))
END FUNCTION
```

---

## 7. PostgreSQL 外部函数

### 7.1 缓存相关函数 [S4-P1-3]

```pseudocode
// 获取缓存统计信息
FUNCTION ontop_cache_stats() -> JsonB:
    guard = ENGINE.lock().unwrap()
    IF let Some(engine) = guard.as_ref():
        stats = engine.cache_manager.get_stats()
        RETURN serde_json::json!({
            "size": stats.size,
            "max_size": stats.max_size,
            "total_hits": stats.total_hits,
            "total_misses": stats.total_misses,
            "hit_rate": stats.hit_rate,
            "evictions": stats.evictions,
            "enabled": engine.cache_manager.is_enabled()
        })
    RETURN JsonB(Null)
END FUNCTION

// 清空缓存
FUNCTION ontop_clear_cache() -> String:
    mut guard = ENGINE.lock().unwrap()
    IF let Some(engine) = guard.as_mut():
        engine.cache_manager.clear()
        RETURN "Cache cleared successfully."
    RETURN "Engine not initialized."
END FUNCTION

// 带缓存的 SPARQL 翻译
FUNCTION ontop_translate(sparql: &str) -> String:
    mut guard = ENGINE.lock()
    let Some(engine) = guard.as_mut():
        RETURN "-- Translation Error: Ontop engine not initialized."
    
    MATCH engine.translate_with_cache(sparql):
        Ok(sql) => RETURN sql
        Err(e) => RETURN format!("-- Translation Error: {}", e)
END FUNCTION
```

---

## 8. 测试覆盖

### 8.1 Sprint4 测试套件

| 测试文件 | 测试数量 | 覆盖功能 |
|---------|---------|---------|
| `sprint4_cache_tests.rs` | 6 | 缓存创建、插入/获取、命中率、清空、禁用、键生成 |
| `sprint4_property_path_tests.rs` | 20 | 路径解析 (*, +, ?, /, \|, ^, !)、SQL 生成、节点操作 |
| `sprint4_service_tests.rs` | 10 | 端点配置、注册、节点转换、SILENT 模式、错误处理 |
| `sprint4_integration_tests.rs` | 10 | 缓存与属性路径结合、复杂路径解析、可视化、缓存淘汰 |
| **总计** | **46** | - |

---

## 9. 与开源 Ontop 能力对比

### 9.1 已对齐能力

| 能力项 | RS Ontop Core | 开源 Ontop | 状态 |
|--------|--------------|-----------|------|
| 基础三元组模式 | ✅ | ✅ | 对齐 |
| FILTER | ✅ | ✅ | 对齐 |
| OPTIONAL (Left Join) | ✅ | ✅ | 对齐 |
| UNION | ✅ | ✅ | 对齐 |
| 聚合 (COUNT/AVG/SUM) | ✅ | ✅ | 对齐 |
| GROUP BY | ✅ | ✅ | 对齐 |
| HAVING | ✅ | ✅ | 对齐 |
| 子查询 | ✅ | ✅ | 对齐 |
| BIND | ✅ | ✅ | 对齐 |
| VALUES | ✅ | ✅ | 对齐 |
| ORDER BY | ✅ | ✅ | [S4-P0-1] 已完成 |
| OFFSET | ✅ | ✅ | [S4-P0-2] 已完成 |
| 查询缓存 | ✅ | ✅ | [S4-P1-3] 已完成 |
| 属性路径 | ✅ | ✅ | [S4-P1-1] 已完成 |
| 映射展开 | ✅ | ✅ | 对齐 |
| 谓词下推 | ✅ | ✅ | 对齐 |
| Join 优化 | ✅ | ✅ | 对齐 |

### 9.2 差距项 (Gap Analysis)

| 能力项 | RS Ontop Core | 开源 Ontop | 差距等级 |
|--------|--------------|-----------|---------|
| SERVICE 联邦查询 | ⚠️ 框架实现 | ✅ 完整 | 中 |
| SPARQL 函数库 (STR, REGEX, NOW) | ⚠️ 基础框架 | ✅ 完整 | 中 |
| OWL 2 QL 推理 | ❌ 未实现 | ✅ 核心优势 | 高 |
| 命名图 (GRAPH) | ❌ 未实现 | ✅ 支持 | 高 |

---

## 10. 已知边界与限制

### 10.1 当前已知限制

```pseudocode
// 1. 属性路径复杂嵌套
// PropertyPathParser 支持基础嵌套，但复杂括号组合可能需进一步优化

// 2. SERVICE 联邦查询
// 框架已实现，但 HTTP 客户端实际请求部分需外部库支持

// 3. 复杂 FILTER 表达式
// 支持基本比较、逻辑运算、聚合函数
// 不支持 EXISTS, NOT EXISTS, IN (列表)
```

### 10.2 生产环境建议

```pseudocode
// Sprint5+ 建议实现：
1. OWL 2 QL 推理 (高优先级)
2. 命名图 (GRAPH) 支持 (高优先级)
3. SPARQL 函数库扩展 (中优先级)
4. SERVICE 联邦查询完整 HTTP 实现 (中优先级)
```

---

**维护者**: RS Ontop Core Team  
**关联文档**: 
- `/doc/sprint4/current-system-pseudocode.md` (前置版本)
- `/doc/sprint4/capability-comparison.md` (能力对比)

---

## 11. Sprint5 开发规划

### 11.1 Sprint5 目标

**核心目标**: 实现 OWL 2 QL 推理和命名图支持，提升系统语义能力，达到 SPARQL 1.1 完整合规。

**与开源 Ontop 差距缩小**: 从 90% → 95% SPARQL 完整度

### 11.2 Sprint5 任务分解

| 标识 | 任务项 | 优先级 | 关键修改位置 | 预期工作量 |
|------|--------|--------|-------------|-----------|
| [S5-P0-1] | OWL 2 QL 推理引擎 | P0 | `src/reasoner/` 新增模块 | 2-3 周 |
| [S5-P0-2] | 命名图 (GRAPH) 支持 | P0 | `LogicNode::Graph` + 解析器 | 1-2 周 |
| [S5-P1-1] | SERVICE HTTP 完整实现 | P1 | `service.rs` HTTP 客户端 | 1 周 |
| [S5-P1-2] | SPARQL 函数库扩展 | P1 | `Expr::Function` 扩展 | 1 周 |
| [S5-P2-1] | TBox 推理缓存 | P2 | 与 QueryPlanCache 集成 | 1 周 |
| [S5-P2-2] | 多数据源适配框架 | P2 | `datasource/` 模块 | 2 周 |

### 11.3 OWL 2 QL 推理引擎 [S5-P0-1]

#### 11.3.1 核心组件设计

```pseudocode
// OWL 2 QL 推理引擎主入口
STRUCT Owl2QlReasoner:
    // TBox 本体存储
    tbox: TBox,
    // 概念层次索引
    concept_hierarchy: ConceptHierarchy,
    // 属性层次索引  
    property_hierarchy: PropertyHierarchy,
    // 推理规则集
    rules: Vec<InferenceRule>,

// TBox 表示
STRUCT TBox:
    // 概念定义 (类)
    concepts: HashMap<IRI, ConceptDefinition>,
    // 属性定义
    properties: HashMap<IRI, PropertyDefinition>,
    // 包含公理
    sub_class_of: Vec<(IRI, IRI)>,
    // 属性包含
    sub_property_of: Vec<(IRI, IRI)>,
    // 域/范围约束
    domain_constraints: HashMap<IRI, IRI>,
    range_constraints: HashMap<IRI, IRI>,

// 概念定义
STRUCT ConceptDefinition:
    iri: IRI,
    concept_type: ConceptType,
    // 父概念
    parents: Vec<IRI>,
    // 等价概念
    equivalents: Vec<IRI>,
    // 互斥概念
    disjoints: Vec<IRI>,

ENUM ConceptType:
    Atomic(IRI),                           // 原子概念
    Intersection(Vec<ConceptType>),        // 交集
    Union(Vec<ConceptType>),                 // 并集
    ExistentialRestriction(IRI, IRI),       // ∃R.C
    UniversalRestriction(IRI, IRI),       // ∀R.C
    Nominal(Vec<IRI>),                     // {a1, a2, ...}
```

#### 11.3.2 推理规则集

```pseudocode
// OWL 2 QL 核心推理规则
STRUCT InferenceRule:
    name: String,
    premise: Vec<Axiom>,
    conclusion: Axiom,

// 推理规则实现
FUNCTION apply_rules(tbox: &TBox) -> Vec<InferredAxiom>:
    mut inferred = Vec::new()
    
    // R1: 子类传递性
    // SubClassOf(C1, C2) ∧ SubClassOf(C2, C3) → SubClassOf(C1, C3)
    FOR (c1, c2) IN &tbox.sub_class_of:
        FOR (c2_prime, c3) IN &tbox.sub_class_of:
            IF c2 == c2_prime:
                inferred.push(InferredAxiom::SubClassOf(c1, c3))
    
    // R2: 属性域推理
    // Domain(R, C) ∧ PropertyAssertion(R, a, b) → ClassAssertion(C, a)
    // (此规则在 ABox 查询时应用)
    
    // R3: 属性范围推理  
    // Range(R, C) ∧ PropertyAssertion(R, a, b) → ClassAssertion(C, b)
    // (此规则在 ABox 查询时应用)
    
    // R4: 存在量词展开
    // SubClassOf(C1, ∃R.C2) ∧ SubPropertyOf(R1, R) → SubClassOf(C1, ∃R1.C2)
    
    // R5: 全称量词推理
    // SubClassOf(C1, ∀R.C2) ∧ Domain(R, C3) → SubClassOf(∃R.C3, C2)
    
    RETURN inferred
END FUNCTION
```

#### 11.3.3 TBox 重写器

```pseudocode
// TBox 重写器 - 将本体推理集成到查询重写
STRUCT TBoxRewriter:
    reasoner: Owl2QlReasoner,

FUNCTION rewrite(logic_plan: &LogicNode, tbox: &TBox) -> LogicNode:
    // 1. 预计算所有蕴含的包含关系
    implied_hierarchy = self.compute_transitive_closure(tbox)
    
    // 2. 重写逻辑计划中的概念和属性引用
    self.rewrite_node(logic_plan, &implied_hierarchy)
END FUNCTION

FUNCTION rewrite_node(
    node: &mut LogicNode, 
    hierarchy: &ImpliedHierarchy
):
    MATCH node:
        IntensionalData { predicate, args }:
            // 检查谓词是否在本体中定义
            IF hierarchy.properties.contains(predicate):
                // 展开为包含该属性的所有子属性
                sub_properties = hierarchy.get_sub_properties(predicate)
                IF sub_properties.len() > 1:
                    // 转换为 UNION 的 ExtensionalData
                    *node = self.expand_to_union(sub_properties, args)
        
        // 递归处理子节点
        Construction { child, .. } => self.rewrite_node(child, hierarchy)
        Join { children, .. } => FOR c IN children { self.rewrite_node(c, hierarchy) }
        Filter { child, .. } => self.rewrite_node(child, hierarchy)
        Aggregation { child, .. } => self.rewrite_node(child, hierarchy)
        Union(children) => FOR c IN children { self.rewrite_node(c, hierarchy) }
        _ => // 叶子节点无需处理
END FUNCTION
```

### 11.4 命名图 (GRAPH) 支持 [S5-P0-2]

#### 11.4.1 IR 层扩展

```pseudocode
// [S5-P0-2] 新增 Graph 节点类型
ENUM LogicNode:
    // ... 现有节点 ...
    
    // 命名图查询
    Graph {
        graph_name: Term,                    // 图名称 (IRI 或变量)
        child: Box<LogicNode>,                // 图内的查询模式
        is_named_graph: bool,                 // 是否为命名图 (vs 默认图)
    }
    
    // 多个图的并集 (GRAPH ?g { ... })
    GraphUnion {
        graph_var: String,                    // 图变量
        children: Vec<LogicNode>,             // 各图的查询结果
    }
```

#### 11.4.2 SPARQL 解析器扩展

```pseudocode
FUNCTION extract_graph_patterns(sparql: &str) -> Vec<GraphPattern>:
    patterns = Vec::new()
    
    // 匹配 GRAPH 子句
    // 语法: GRAPH <iri> { ... } 或 GRAPH ?var { ... }
    regex = Regex::new(r"GRAPH\s+(<[^>]+>|\?\w+)\s*\{([^}]*)\}")
    
    FOR cap IN regex.captures_iter(sparql):
        graph_ref = cap[1].trim()
        inner_patterns = cap[2].trim()
        
        graph_term = IF graph_ref.starts_with('<'):
            Term::Constant(graph_ref.trim_matches('<').trim_matches('>'))
        ELSE:
            Term::Variable(graph_ref.trim_start_matches('?'))
        
        patterns.push(GraphPattern {
            graph: graph_term,
            triples: extract_triple_patterns(inner_patterns),
        })
    
    RETURN patterns
END FUNCTION
```

#### 11.4.3 SQL 生成策略

```pseudocode
// 命名图通常映射为带图标识符的表
FUNCTION handle_graph_node(
    graph_name: &Term,
    child: &LogicNode
) -> Result<(), GenerationError>:
    
    graph_sql = match graph_name:
        Term::Constant(iri) => format!("'{}'", iri),
        Term::Variable(var) => format!("{}", var),  // 需要 JOIN 图元数据表
    
    // 假设物理表结构: rdf_quads(subject, predicate, object, graph)
    // 或者通过映射系统获取图特定的表
    
    // 1. 确定图的物理位置
    table_ref = self.resolve_graph_table(graph_name)?
    
    // 2. 生成带图筛选的查询
    self.ctx.where_conditions.push(Condition {
        expression: format!("graph = {}", graph_sql),
        condition_type: ConditionType::Filter,
    })
    
    // 3. 继续处理子节点
    self.traverse_node(child)
END FUNCTION
```

### 11.5 SPARQL 函数库扩展 [S5-P1-2]

#### 11.5.1 函数注册系统

```pseudocode
// SPARQL 函数注册表
STRUCT SparqlFunctionRegistry:
    functions: HashMap<String, Box<dyn SparqlFunction>>,

TRAIT SparqlFunction:
    FUNCTION name(&self) -> &str
    FUNCTION arity(&self) -> Arity  // 固定参数数或变长
    FUNCTION evaluate(&self, args: &[Expr], ctx: &EvalContext) -> Result<Term, EvalError>
    FUNCTION translate_to_sql(&self, args: &[String]) -> String

// 注册标准函数
FUNCTION register_standard_functions(registry: &mut SparqlFunctionRegistry):
    // 字符串函数
    registry.register(Box::new(StrFunction::new()))
    registry.register(Box::new(ConcatFunction::new()))
    registry.register(Box::new(ContainsFunction::new()))
    registry.register(Box::new(StartsWithFunction::new()))
    registry.register(Box::new(EndsWithFunction::new()))
    registry.register(Box::new(SubstrFunction::new()))
    registry.register(Box::new(StrlenFunction::new()))
    registry.register(Box::new(UcaseFunction::new()))
    registry.register(Box::new(LcaseFunction::new()))
    
    // 正则表达式
    registry.register(Box::new(RegexFunction::new()))
    
    // 日期时间
    registry.register(Box::new(NowFunction::new()))
    registry.register(Box::new(YearFunction::new()))
    registry.register(Box::new(MonthFunction::new()))
    registry.register(Box::new(DayFunction::new()))
    
    // 算术
    registry.register(Box::new(AbsFunction::new()))
    registry.register(Box::new(RoundFunction::new()))
    registry.register(Box::new(CeilFunction::new()))
    registry.register(Box::new(FloorFunction::new()))
    
    // IRI / URI 处理
    registry.register(Box::new(IriFunction::new()))
    registry.register(Box::new(UriFunction::new()))
    registry.register(Box::new(EncodeForUriFunction::new()))
END FUNCTION
```

#### 11.5.2 函数 SQL 翻译

```pseudocode
// 函数到 SQL 的翻译映射
FUNCTION translate_function_to_sql(
    name: &str,
    args: &[String]
) -> Result<String, String>:
    
    MATCH name.to_uppercase().as_str():
        // 字符串函数
        "STR" => Ok(format!("CAST({} AS TEXT)", args[0])),
        "CONCAT" => Ok(format!("CONCAT({})", args.join(", "))),
        "CONTAINS" => Ok(format!("{} LIKE '%' || {} || '%'", args[1], args[0])),
        "STRLEN" => Ok(format!("LENGTH({})", args[0])),
        "UCASE" | "UPPER" => Ok(format!("UPPER({})", args[0])),
        "LCASE" | "LOWER" => Ok(format!("LOWER({})", args[0])),
        
        // 正则表达式 (PostgreSQL 语法)
        "REGEX" => IF args.len() >= 3:
            Ok(format!("{} ~* {}", args[0], args[1]))  // 带标志
        ELSE:
            Ok(format!("{} ~ {}", args[0], args[1])),
        
        // 日期时间
        "NOW" => Ok("CURRENT_TIMESTAMP".to_string()),
        "YEAR" => Ok(format!("EXTRACT(YEAR FROM {})", args[0])),
        "MONTH" => Ok(format!("EXTRACT(MONTH FROM {})", args[0])),
        "DAY" => Ok(format!("EXTRACT(DAY FROM {})", args[0])),
        
        // 算术
        "ABS" => Ok(format!("ABS({})", args[0])),
        "ROUND" => Ok(format!("ROUND({})", args[0])),
        "CEIL" => Ok(format!("CEIL({})", args[0])),
        "FLOOR" => Ok(format!("FLOOR({})", args[0])),
        
        _ => Err(format!("Unknown SPARQL function: {}", name))
END FUNCTION
```

### 11.6 SERVICE HTTP 完整实现 [S5-P1-1]

#### 11.6.1 HTTP 客户端集成

```pseudocode
// HTTP 客户端配置
STRUCT SparqlHttpClient:
    client: reqwest::Client,
    default_timeout: Duration,

FUNCTION send_sparql_request(
    &self,
    endpoint: &ServiceEndpoint,
    sparql: &str
) -> Future<Result<ServiceResult, ServiceError>>:
    
    // 1. 构建请求
    mut request = self.client
        .post(&endpoint.url)
        .timeout(Duration::from_secs(endpoint.timeout_seconds))
        .header("Accept", "application/sparql-results+json")
        .header("Content-Type", "application/x-www-form-urlencoded")
    
    // 2. 添加认证（如果需要）
    IF endpoint.requires_auth:
        IF let Some(token) = &endpoint.auth_token:
            request = request.bearer_auth(token)
    
    // 3. 添加默认图参数
    mut params = HashMap::new()
    params.insert("query", sparql)
    IF let Some(graph) = &endpoint.default_graph:
        params.insert("default-graph-uri", graph)
    
    // 4. 发送请求
    response = request.form(&params).send().await?
    
    // 5. 解析响应
    IF response.status().is_success():
        results = response.json::<SparqlJsonResults>().await?
        RETURN self.convert_to_service_result(results)
    ELSE:
        RETURN Err(ServiceError::HttpError(response.status().to_string()))
END FUNCTION
```

#### 11.6.2 结果转换

```pseudocode
FUNCTION convert_to_service_result(
    &self,
    json_results: SparqlJsonResults
) -> ServiceResult:
    
    mut bindings = Vec::new()
    mut columns = Vec::new()
    
    // 提取变量名
    IF let Some(vars) = json_results.head.vars:
        columns = vars.clone()
    
    // 转换结果绑定
    FOR result IN json_results.results.bindings:
        mut row = HashMap::new()
        FOR (var, value_obj) IN result:
            term = self.json_value_to_term(value_obj)
            row.insert(var, term)
        bindings.push(row)
    
    RETURN ServiceResult { bindings, columns }
END FUNCTION

FUNCTION json_value_to_term(&self, value_obj: JsonValue) -> Term:
    MATCH value_obj.type.as_str():
        "uri" => Term::Constant(value_obj.value),
        "literal" => IF let Some(lang) = value_obj.lang:
            Term::Literal { value: value_obj.value, datatype: None, language: Some(lang) }
        ELSE IF let Some(dt) = value_obj.datatype:
            Term::Literal { value: value_obj.value, datatype: Some(dt), language: None }
        ELSE:
            Term::Literal { value: value_obj.value, datatype: None, language: None },
        "bnode" => Term::BlankNode(value_obj.value),
        _ => Term::Constant(value_obj.value)
END FUNCTION
```

### 11.7 Sprint5 测试规划

| 测试文件 | 测试数量 | 覆盖功能 |
|---------|---------|---------|
| `sprint5_owl_reasoner_tests.rs` | 15 | OWL 2 QL 推理规则、TBox 重写、概念层次 |
| `sprint5_graph_tests.rs` | 10 | GRAPH 解析、命名图 SQL 生成、图变量绑定 |
| `sprint5_sparql_functions_tests.rs` | 20 | STR, REGEX, NOW, CONCAT 等函数测试 |
| `sprint5_service_http_tests.rs` | 8 | HTTP 请求、结果解析、错误处理 |
| `sprint5_integration_tests.rs` | 12 | 推理与查询集成、多图查询、函数组合 |
| **总计** | **65** | - |

---

**维护者**: RS Ontop Core Team  
**关联文档**: 
- `/doc/sprint4/current-system-pseudocode.md` (前置版本)
- `/doc/sprint4/capability-comparison.md` (历史版本)
