# RS Ontop Core 当前系统伪代码（Sprint4 基线）

> 更新时间：2026-03-29  
> 用途：作为 Sprint4 的"当前状态基线文档"，描述 Sprint3 完成后已落地实现路径  
> 基于实际代码生成，反映 `/src` 目录当前状态

> 标识规范：`[S4-Px-y]` 对应 Sprint4 的任务项。  
> 优先级：`P0` 必做，`P1` 应做，`P2` 可选。

---

## Sprint4 开发任务规划

### 核心目标
完善查询执行能力，实现 ORDER BY/OFFSET SQL 生成，提升性能与兼容性。

### 任务分解

| 标识 | 任务项 | 优先级 | 关键修改位置 | 状态 |
|------|--------|--------|-------------|------|
| [S4-P0-1] | ORDER BY 支持 | P0 | `flat_generator.rs` 生成 ORDER BY 子句 | 待实现 |
| [S4-P0-2] | OFFSET 支持 | P0 | `flat_generator.rs` 扩展 offset 处理 | 待实现 |
| [S4-P1-1] | 属性路径 | P1 | 新增 `LogicNode::Path` | 待实现 |
| [S4-P1-2] | SPARQL 函数库 | P1 | `Expr::Function` 扩展 | 待实现 |
| [S4-P1-3] | 查询缓存 | P1 | `PassManager` 前添加缓存层 | 待实现 |
| [S4-P2-1] | SERVICE 联邦查询 | P2 | 新增 `LogicNode::Service` | 待实现 |

---

## Sprint4 系统概览

### 已实现的 Sprint3 核心功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 聚合查询 (Aggregation) | ✅ 已实现 | COUNT/AVG/SUM/MIN/MAX + GROUP BY + HAVING |
| 子查询 (Subquery) | ✅ 已实现 | 嵌套 SELECT 通过递归 JOIN 处理 |
| BIND 表达式 | ✅ 已实现 | 变量绑定到 Construction 节点 |
| VALUES 数据块 | ✅ 已实现 | 内联数据表支持 |
| 优化器 Pass 管理 | ✅ 已实现 | 固定点迭代优化框架 |
| 投影归一化 | ✅ 已实现 | NormalizeProjectionPass |
| 无用列剪枝 | ✅ 已实现 | PruneUnusedColumnsPass |
| 左连接转内连接 | ✅ 已实现 | LeftToInnerJoinPass |
| 映射展开 | ✅ 已实现 | UnfoldingPass |

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
    
    // 6. Sprint4 PassManager        // [S4-P1-3] TODO: 查询缓存层 - 在 PassManager 前添加缓存检查
        // [S4-P1-3] 建议实现：
        // IF cache.contains_key(query_hash):
        //     RETURN cache.get(query_hash)
        pass_manager = PassManager::new()
        pass_manager.run(&mut logic_plan, &ctx)
    
    // 7. SQL 生成
    mut generator = FlatSQLGenerator::new()
    generator.generate(&logic_plan)
END FUNCTION
```

---

## 2. IR (Intermediate Representation) 层

### 2.1 LogicNode 枚举

```pseudocode
ENUM LogicNode:
    // 投影、别名和计算列
    Construction {
        projected_vars: Vec<String>,           // 投影变量列表
        bindings: HashMap<String, Expr>,       // 变量名 -> 表达式
        child: Box<LogicNode>,                 // 子节点
    }
    
    // N 元连接操作符
    Join {
        children: Vec<LogicNode>,              // 子节点列表
        condition: Option<Expr>,               // JOIN 条件
        join_type: JoinType,                   // Inner | Left | Union
    }
    
    // 物理表扫描
    ExtensionalData {
        table_name: String,                    // 表名
        column_mapping: HashMap<String, String>, // 变量 -> 物理列
        metadata: Arc<TableMetadata>,          // 表元数据
    }
    
    // 未展开的逻辑谓词（虚拟 RDF 谓词）
    IntensionalData {
        predicate: String,                     // 谓词名
        args: Vec<Term>,                       // 参数列表
    }
    
    // 过滤操作
    Filter {
        expression: Expr,                      // 过滤表达式
        child: Box<LogicNode>,                   // 子节点
    }
    
    // 并集操作
    Union(Vec<LogicNode>)
    
    // 分组聚合 [Sprint3 P0-1 已实现]
    Aggregation {
        group_by: Vec<String>,                  // GROUP BY 变量
        aggregates: HashMap<String, Expr>,      // 别名 -> 聚合表达式
        child: Box<LogicNode>,                  // 子节点
    }
    
    // 分页限制
    Limit {
        limit: usize,                           // 限制数量
        offset: Option<usize>,                  // 偏移量
        child: Box<LogicNode>,                    // 子节点
    }
    
    // VALUES 数据块 [Sprint3 P2-2 已实现]
    Values {
        variables: Vec<String>,                 // 变量名列表
        rows: Vec<Vec<Term>>,                   // 数据行
    }
    
    // [S4-P1-1] TODO: 属性路径 (Property Path) - 如 ?x :knows+ ?y
    // Path {
    //     subject: Term,
    //     property_path: PropertyPath,           // Sequence | Alternative | Star | Plus
    //     object: Term,
    // }
    
    // [S4-P2-1] TODO: SERVICE 联邦查询
    // Service {
    //     endpoint: String,                    // SPARQL Endpoint URL
    //     query: Box<LogicNode>,                 // 子查询
    //     silent: bool,                          // 失败时是否忽略
    // }
END ENUM
```

### 2.2 Expression 系统

```pseudocode
ENUM Term:
    Variable(String)                           // ?var 变量
    Constant(String)                           // 常量 IRI/值
    Literal { value: String, datatype: Option<String> }  // 字面量

ENUM Expr:
    Term(Term)                                 // 基本项
    Compare {                                  // 比较表达式
        left: Box<Expr>,
        op: ComparisonOp,                       // Eq | Neq | Lt | Lte | Gt | Gte
        right: Box<Expr>,
    }
    Logical {                                  // 逻辑表达式
        op: LogicalOp,                          // And | Or | Not
        args: Vec<Expr>,
    }
    Function {                                 // 函数调用
        name: String,                           // 函数名
        args: Vec<Expr>,                        // 参数列表
    }
END ENUM
```

### 2.3 IRBuilder

```pseudocode
STRUCT IRBuilder

FUNCTION build_with_mappings(
    parsed: &ParsedQuery,
    metadata_map: &HashMap<String, Arc<TableMetadata>>,
    mappings: Option<&MappingStore>
) -> Result<LogicNode, OntopError>:
    
    // 1. 解析主表元数据
    primary_table = Self::resolve_primary_table(parsed, mappings, metadata_map)?
    
    // 2. 调用 IRConverter 转换
    RETURN IRConverter::convert_with_mappings(parsed, primary_table, mappings)
END FUNCTION

FUNCTION resolve_primary_table(...) -> Result<Arc<TableMetadata>, OntopError>:
    predicates = Self::extract_predicates(parsed)
    
    // 策略1: 从映射配置找匹配表
    IF mappings EXISTS:
        FOR pred IN predicates:
            IF rule = store.mappings.get(pred):
                IF metadata = metadata_map.get(rule.table_name):
                    RETURN metadata
    
    // 策略2: 回退到第一个可用表
    IF metadata_map NOT EMPTY:
        RETURN metadata_map.iter().next()
    
    // 策略3: 报错
    THROW OntopError::MissingMetadata
END FUNCTION
```

### 2.4 IRConverter (详细转换逻辑)

```pseudocode
STRUCT IRConverter

FUNCTION convert_with_mappings(
    parsed: &ParsedQuery,
    metadata: Arc<TableMetadata>,
    mappings: Option<&MappingStore>
) -> LogicNode:
    
    // 提取投影变量（去掉 ? 前缀）
    projected_vars = parsed.projected_vars
        .map(|v| v.trim_start_matches('?').to_string())
    
    // 1. 构建核心计划 (Join/Scan)
    mut core = Self::build_core_plan_with_vars(
        parsed, metadata.clone(), mappings, &projected_vars
    )
    
    // [S3-P1-1] 处理子查询：递归转换并 JOIN
    FOR sub_parsed IN &parsed.sub_queries:
        sub_plan = Self::convert_with_mappings(sub_parsed, metadata.clone(), mappings)
        Self::join_node_to_core(&mut core, sub_plan)
    
    // [S3-P2-2] 处理 VALUES：构建 Values 节点并 JOIN
    IF values = parsed.values_block:
        values_node = LogicNode::Values {
            variables: values.variables,
            rows: values.rows.map(|r| Term::Constant(r)),
        }
        Self::join_node_to_core(&mut core, values_node)
    
    // 2. 添加 FILTER (聚合前)
    FOR filter IN &parsed.filter_expressions:
        IF expr = Self::parse_filter_expr(filter):
            core = LogicNode::Filter { expression: expr, child: Box::new(core) }
    
    // 3. 处理 BIND 表达式 [S3-P1-2]
    FOR bind IN &parsed.bind_expressions:
        IF expr = Self::parse_filter_expr(&bind.expression):
            // 收集当前所有变量
            mut bindings = HashMap::new()
            FOR var IN core.used_variables():
                bindings.insert(var, Expr::Term(Term::Variable(var)))
            
            // 添加 BIND 新变量
            bindings.insert(bind.alias, expr)
            
            // 构建中间 Construction 节点
            core = LogicNode::Construction {
                projected_vars: bindings.keys().collect().sort(),
                bindings,
                child: Box::new(core),
            }
    
    // 4. 处理聚合查询 [S3-P0-1]
    IF !parsed.aggregates.is_empty() OR !parsed.group_by.is_empty():
        core = Self::build_aggregation_node(parsed, core, &projected_vars)
        
        // 5. 处理 HAVING (聚合后) [S3-P1-3]
        FOR having IN &parsed.having_expressions:
            IF expr = Self::parse_filter_expr(having):
                core = LogicNode::Filter { expression: expr, child: Box::new(core) }
    
    // 6. 添加 LIMIT
    IF limit = parsed.limit:
        core = LogicNode::Limit { limit, offset: None, child: Box::new(core) }
    
    // 7. 构建最终 Construction 节点
    mut final_bindings = HashMap::new()
    FOR var IN &projected_vars:
        final_bindings.insert(var, Expr::Term(Term::Variable(var)))
    
    RETURN LogicNode::Construction {
        projected_vars: projected_vars.clone(),
        bindings: final_bindings,
        child: Box::new(core),
    }
END FUNCTION

FUNCTION build_aggregation_node(
    parsed: &ParsedQuery,
    child: LogicNode,
    projected_vars: &[String]
) -> LogicNode:
    
    // 推断 GROUP BY 变量
    group_by_vars = IF !parsed.group_by.is_empty():
        parsed.group_by.clone()
    ELSE:
        // 推断：非聚合结果的投影变量
        aggregate_aliases = parsed.aggregates.map(|a| a.alias).collect()
        projected_vars.filter(|v| !aggregate_aliases.contains(v)).collect()
    
    // 构建聚合表达式映射
    mut aggregates = HashMap::new()
    FOR agg IN &parsed.aggregates:
        expr = IF agg.arg == "*":
            Expr::Function { name: agg.func, args: [Term::Constant("*")] }
        ELSE IF agg.arg starts_with '?':
            Expr::Function { name: agg.func, args: [Term::Variable(agg.arg)] }
        ELSE:
            Expr::Function { name: agg.func, args: [Term::Constant(agg.arg)] }
        
        aggregates.insert(agg.alias, expr)
    
    // 创建 Aggregation 节点
    agg_node = LogicNode::Aggregation {
        group_by: group_by_vars,
        aggregates,
        child: Box::new(child),
    }
    
    // 包装 Construction 节点
    mut bindings = HashMap::new()
    FOR var IN projected_vars:
        bindings.insert(var, Expr::Term(Term::Variable(var)))
    
    RETURN LogicNode::Construction {
        projected_vars: projected_vars.to_vec(),
        bindings,
        child: Box::new(agg_node),
    }
END FUNCTION
```

---

## 3. SPARQL 解析层

### 3.1 SparqlParserV2

```pseudocode
STRUCT ParsedQuery:
    raw: String                              // 原始查询
    projected_vars: Vec<String>              // 投影变量
    has_filter: bool                         // 是否有 FILTER
    has_optional: bool                       // 是否有 OPTIONAL
    has_union: bool                          // 是否有 UNION
    has_aggregate: bool                     // 是否有聚合
    main_patterns: Vec<TriplePattern>        // 主三元组模式
    optional_patterns: Vec<Vec<TriplePattern>>  // OPTIONAL 模式
    union_patterns: Vec<Vec<TriplePattern>>   // UNION 模式
    filter_expressions: Vec<String>          // FILTER 表达式字符串
    limit: Option<usize>                    // LIMIT
    order_by: Vec<OrderByItem>               // ORDER BY
    group_by: Vec<String>                    // GROUP BY [S3-P0-1]
    having_expressions: Vec<String>         // HAVING [S3-P1-3]
    bind_expressions: Vec<BindExpr>          // BIND [S3-P1-2]
    sub_queries: Vec<ParsedQuery>             // 子查询 [S3-P1-1]
    values_block: Option<ValuesBlock>        // VALUES [S3-P2-2]
    aggregates: Vec<AggregateExpr>           // 聚合表达式 [S3-P0-1]

STRUCT AggregateExpr:
    func: String                             // COUNT, AVG, MIN, MAX, SUM
    arg: String                              // * 或 ?var
    alias: String                             // AS ?alias
    distinct: bool                           // DISTINCT 修饰符

STRUCT BindExpr:
    expression: String                        // 表达式字符串
    alias: String                             // 变量别名

STRUCT SparqlParserV2

FUNCTION parse(sparql: &str) -> Result<ParsedQuery, OntopError>:
    trimmed = sparql.trim()
    IF trimmed.is_empty():
        THROW OntopError::IRError("Empty SPARQL query")
    
    // spargebra 语法验证（排除 ORDER BY）
    IF !trimmed.to_uppercase().contains("ORDER BY"):
        Query::parse(trimmed, None)?  // 失败则抛出
    
    // 提取各组件
    projected_vars = extract_projected_vars(trimmed)
    aggregates = extract_aggregate_exprs(trimmed)
    where_block = extract_where_block(trimmed)
    
    RETURN ParsedQuery {
        raw: trimmed,
        projected_vars,
        has_aggregate: !aggregates.is_empty(),
        main_patterns: extract_triple_patterns(&where_block),
        optional_patterns: extract_optional_patterns(&where_block),
        union_patterns: extract_union_patterns(&where_block),
        filter_expressions: extract_filter_expressions(&where_block),
        limit: extract_limit(trimmed),
        order_by: extract_order_by(trimmed),
        group_by: extract_group_by(trimmed),           // [S3-P0-1]
        having_expressions: extract_having(trimmed),   // [S3-P1-3]
        bind_expressions: extract_binds(trimmed),      // [S3-P1-2]
        sub_queries: extract_subqueries(trimmed),      // [S3-P1-1]
        values_block: extract_values(trimmed),         // [S3-P2-2]
        aggregates,
    }
END FUNCTION
```

---

## 4. SQL 生成层

### 4.1 FlatSQLGenerator

```pseudocode
STRUCT FlatSQLGenerator:
    ctx: GeneratorContext                      // 生成上下文
    alias_manager: AliasManager               // 别名管理器

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
        ExtensionalData { table_name, column_mapping, .. }:
            self.handle_extensional_data(table_name, column_mapping)?
        
        Join { children, condition, join_type }:
            self.handle_join(children, condition, join_type)?
        
        Filter { expression, child }:
            self.handle_filter(expression, child)?
        
        Construction { projected_vars, bindings, child }:
            self.handle_construction(projected_vars, bindings, child)?
        
        Union(children):
            self.handle_union(children)?
        
        Aggregation { group_by, aggregates, child }:   // [S3-P0-1]
            self.handle_aggregation(group_by, aggregates, child)?
        
        // [S4-P0-1] TODO: 在 SQL 生成中添加 ORDER BY 子句处理
        // [S4-P0-2] TODO: 在 SQL 生成中添加 OFFSET 处理
        Limit { limit, offset, child }:
            self.handle_limit(limit, offset, child)?
        
        IntensionalData { .. }:
            THROW GenerationError::UnexpandedPredicate("必须先展开")
        
        Values { variables, rows }:                   // [S3-P2-2]
            self.handle_values(variables, rows)?
END FUNCTION

FUNCTION handle_aggregation(
    group_by: &[String],
    aggregates: &HashMap<String, Expr>,
    child: &LogicNode
) -> Result<(), GenerationError>:
    
    // 先处理子节点
    self.traverse_node(child)?
    
    // 生成 SELECT 中的聚合表达式
    FOR (alias, expr) IN aggregates:
        sql_expr = self.translate_expression(expr)?
        self.ctx.select_items.push(SelectItem {
            expression: sql_expr,
            alias: Some(alias),
            is_aggregate: true,
        })
    
    // 设置 GROUP BY
    self.ctx.group_by = group_by.to_vec()
    
    Ok()
END FUNCTION
```

---

## 5. 优化器层

### 5.1 OptimizerPass Trait

```pseudocode
TRAIT OptimizerPass:
    FUNCTION name(&self) -> &str
    FUNCTION apply(&self, node: &mut LogicNode, ctx: &OptimizerContext)
END TRAIT

STRUCT OptimizerContext:
    mappings: Arc<MappingStore>                // 映射配置
    metadata: HashMap<String, Arc<TableMetadata>>  // 表元数据
```

### 5.2 PassManager (固定点迭代框架)

```pseudocode
STRUCT PassManager:
    passes: Vec<Box<dyn OptimizerPass>>

FUNCTION new() -> Self:
    RETURN PassManager {
        passes: vec![
            Box::new(UnfoldingPass::new()),
            Box::new(SelfJoinEliminationPass::new()),
            Box::new(JoinEliminationPass::new()),
            Box::new(LeftToInnerJoinPass::new()),
            Box::new(NormalizeProjectionPass::new()),     // [S3-P1-5]
            Box::new(PruneUnusedColumnsPass::new()),       // [S3-P1-6]
        ],
    }
END FUNCTION

FUNCTION run(&self, node: &mut LogicNode, ctx: &OptimizerContext):
    mut changed = true
    mut iterations = 0
    const MAX_ITERATIONS = 10
    
    WHILE changed AND iterations < MAX_ITERATIONS:
        initial_node = node.clone()
        
        FOR pass IN &self.passes:
            pass.apply(node, ctx)
        
        changed = (node != initial_node)
        iterations += 1
    END WHILE
END FUNCTION
```

### 5.3 UnfoldingPass (映射展开)

```pseudocode
STRUCT UnfoldingPass

FUNCTION apply(node: &mut LogicNode, ctx: &OptimizerContext):
    MATCH node:
        IntensionalData { predicate, args }:
            // 查找映射规则
            IF rule = ctx.mappings.mappings.get(predicate):
                
                // 构建列映射
                mut column_mapping = HashMap::new()
                
                // 从 subject_template 提取 subject 列
                IF template = rule.subject_template:
                    col = template.extract_between('{', '}')
                    IF Term::Variable(var) = args[0]:
                        column_mapping.insert(var, col)
                
                // 从 position_to_column 提取其他列
                FOR (pos, term) IN args.iter().enumerate().skip(1):
                    IF Term::Variable(var) = term:
                        IF col = rule.position_to_column.get(&pos):
                            column_mapping.insert(var, col)
                
                // 替换为 ExtensionalData
                IF metadata = ctx.metadata.get(&rule.table_name):
                    *node = LogicNode::ExtensionalData {
                        table_name: rule.table_name,
                        column_mapping,
                        metadata: Arc::clone(metadata),
                    }
        
        // 递归处理子节点
        Construction { child, .. } => self.apply(child, ctx)
        Join { children, .. } => FOR c IN children { self.apply(c, ctx) }
        Filter { child, .. } => self.apply(child, ctx)
        Aggregation { child, .. } => self.apply(child, ctx)
        Union(children) => FOR c IN children { self.apply(c, ctx) }
END FUNCTION
```

---

## 6. Sprint4 新增/优化项

### 6.1 当前已实现的 Sprint3 功能

| 标识 | 功能 | 实现状态 | 关键代码位置 |
|-----|------|---------|-------------|
| [S3-P0-1] | 聚合查询 (COUNT/AVG/SUM/MIN/MAX) | ✅ | `ir_converter.rs:181-253`, `flat_generator.rs` |
| [S3-P0-1] | GROUP BY | ✅ | `ir_converter.rs:194-207` |
| [S3-P1-3] | HAVING | ✅ | `ir_converter.rs:127-135` |
| [S3-P1-1] | 子查询 (Subquery) | ✅ | `ir_converter.rs:67-71` |
| [S3-P1-2] | BIND 表达式 | ✅ | `ir_converter.rs:101-121` |
| [S3-P2-2] | VALUES 数据块 | ✅ | `ir_converter.rs:73-89` |
| [S3-P1-5] | 投影归一化 | ✅ | `optimizer/rules/normalize_projection.rs` |
| [S3-P1-6] | 无用列剪枝 | ✅ | `optimizer/rules/prune_unused_columns.rs` |
| [S3-P0-2] | FILTER 表达式修复 | ✅ | `sparql_parser_v2.rs` |

### 6.2 Sprint4 建议实现项

| 标识 | 功能 | 优先级 | 建议实现路径 |
|-----|------|--------|-------------|
| [S4-P0-1] | ORDER BY 支持 | P0 | 在 `flat_generator.rs` 生成 ORDER BY 子句 |
| [S4-P0-2] | OFFSET 支持 | P0 | 扩展 `LogicNode::Limit` 的 offset 字段 |
| [S4-P1-1] | 属性路径 (Property Path) | P1 | 新增 `LogicNode::Path` 节点 |
| [S4-P1-2] | SPARQL 函数库完善 | P1 | 扩展 `Expr::Function` 支持列表 |
| [S4-P1-3] | 查询缓存 | P1 | 在 `PassManager` 前添加缓存层 |
| [S4-P2-1] | SERVICE 联邦查询 | P2 | 新增 `LogicNode::Service` 节点 |

---

## 7. 与开源 Ontop 能力对比

### 7.1 已对齐能力

| 能力项 | RS Ontop Core | 开源 Ontop | 状态 |
|--------|--------------|-----------|------|
| 基础三元组模式 | ✅ | ✅ | 对齐 |
| FILTER | ✅ | ✅ | 对齐 |
| OPTIONAL (Left Join) | ✅ | ✅ | 对齐 |
| UNION | ✅ | ✅ | 对齐 |
| 聚合 (COUNT/AVG/SUM) | ✅ | ✅ | Sprint3 完成 |
| GROUP BY | ✅ | ✅ | Sprint3 完成 |
| HAVING | ✅ | ✅ | Sprint3 完成 |
| 子查询 | ✅ | ✅ | Sprint3 完成 |
| BIND | ✅ | ✅ | Sprint3 完成 |
| VALUES | ✅ | ✅ | Sprint3 完成 |
| 映射展开 | ✅ | ✅ | 对齐 |
| 谓词下推 | ✅ | ✅ | 对齐 |
| Join 优化 | ✅ | ✅ | 对齐 |

### 7.2 差距项 (Gap Analysis)

| 能力项 | RS Ontop Core | 开源 Ontop | 差距等级 |
|--------|--------------|-----------|---------|
| ORDER BY | ⚠️ 解析但未生成 | ✅ 完整 | 低 |
| OFFSET | ⚠️ 字段存在但未使用 | ✅ 完整 | 低 |
| 属性路径 (`*`, `+`, `?`) | ❌ 未实现 | ✅ 完整 | 中 |
| SPARQL 函数 (STR, REGEX, NOW) | ⚠️ 基础框架 | ✅ 完整 | 中 |
| 查询缓存 | ❌ 未实现 | ✅ 支持 | 中 |
| OWL 2 QL 推理 | ❌ 未实现 | ✅ 核心优势 | 高 |
| SERVICE 联邦查询 | ❌ 未实现 | ✅ 支持 | 高 |
| 命名图 (GRAPH) | ❌ 未实现 | ✅ 支持 | 高 |

---

## 8. 已知边界与限制

### 8.1 当前已知限制

```pseudocode
// 1. ORDER BY 解析但不生成 SQL
ParsedQuery.order_by: Vec<OrderByItem>  // 已解析
// 但 flat_generator.rs 未处理，生成的 SQL 无 ORDER BY 子句

// 2. OFFSET 字段存在但未使用
LogicNode::Limit { offset: Option<usize> }  // 字段存在
// 但生成 SQL 时仅使用 LIMIT，未处理 OFFSET

// 3. 属性路径未实现
// 无 LogicNode::Path 节点类型
// sparql_parser_v2.rs 未提取属性路径模式

// 4. 复杂 FILTER 表达式
// 仅支持基本比较和逻辑运算
// 不支持 EXISTS, NOT EXISTS, IN (列表)
```

### 8.2 生产环境建议

```pseudocode
// 建议 Sprint4 优先实现：
1. ORDER BY SQL 生成 (P0)
2. OFFSET 支持 (P0)
3. 查询缓存层 (P1) - 减少重复解析开销
4. SPARQL 函数库扩展 (P1)
5. 属性路径 (P2) - 可选高级特性
```

---

**维护者**: RS Ontop Core Team  
**关联文档**: 
- `/doc/sprint3/current-system-pseudocode.md` (前置版本)
- `/doc/sprint3/capability-comparison.md` (能力对比)
