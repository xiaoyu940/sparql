# Sprint 7 当前系统伪代码 (已更新)

> 更新时间：2026-04-01  
> 本次更新：CONSTRUCT/ASK/DESCRIBE 支持、OFFSET 修复、FILTER URI 解析修复

---

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         SPARQL 查询                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  1. SparqlParserV2 (parser/sparql_parser_v2.rs)                  │
│     - 解析 SELECT/CONSTRUCT/ASK/DESCRIBE                          │
│     - 提取 LIMIT/OFFSET/ORDER BY                                 │
│     - 提取三元组模式和 FILTER 表达式                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │    ParsedQuery       │
                    │  - query_type        │
                    │  - projected_vars    │
                    │  - limit/offset      │
                    │  - filter_expressions│
                    │  - describe_resources│
                    └──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. IRConverter (parser/ir_converter.rs)                         │
│     - 将 ParsedQuery 转换为 LogicNode (IR)                      │
│     - 处理变量映射、JOIN、FILTER                                  │
│     - 构建 Limit/Offset/OrderBy 节点                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │     LogicNode        │
                    │  中间表示树 (IR)      │
                    └──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. FlatSQLGenerator (sql/flat_generator.rs)                   │
│     - traverse_node(): 遍历 IR 树，收集 SQL 组件                │
│     - assemble_sql(): 拼装最终 SQL                              │
│     - build_describe_sql(): RDF 三元组格式 SQL                  │
│     - build_construct_sql(): CONSTRUCT 模板 SQL                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │    PostgreSQL SQL    │
                    └──────────────────────┘
```

---

## 1. SparqlParserV2 模块

### 1.1 查询类型检测与解析

```pseudocode
STRUCT SparqlParserV2

FUNCTION parse(sparql: &str) -> Result<ParsedQuery, OntopError>:
    // 1. 检测查询类型
    query_type = IF upper.starts_with("CONSTRUCT") THEN QueryType::Construct
                ELSE IF upper.starts_with("ASK") THEN QueryType::Ask
                ELSE IF upper.starts_with("DESCRIBE") THEN QueryType::Describe
                ELSE QueryType::Select
    
    // 2. 提取 WHERE 块
    where_block = extract_where_block(trimmed)
    expanded_where = expand_prefixes(&where_block)
    
    // 3. 提取 LIMIT/OFFSET [FIXED]
    limit = extract_limit(trimmed)          // 从 "LIMIT 10" 提取 10
    offset = extract_offset(trimmed)        // 从 "OFFSET 5" 提取 5 [NEW]
    
    // 4. 提取 ORDER BY
    order_by = extract_order_by(trimmed)
    
    // 5. 提取三元组模式
    main_patterns = extract_triple_patterns(&expanded_where)
    
    // 6. 提取 FILTER 表达式
    filter_expressions = extract_filter_expressions(&expanded_where)
    
    // 7. 查询特定提取
    construct_template = IF query_type == Construct THEN extract_construct_template(trimmed) ELSE empty
    describe_resources = IF query_type == Describe THEN extract_describe_resources(trimmed) ELSE empty
    
    RETURN ParsedQuery {
        query_type, projected_vars, main_patterns,
        filter_expressions, limit, offset,          // [FIXED] offset 不再硬编码为 None
        order_by, construct_template, describe_resources
    }
END FUNCTION
```

### 1.2 DESCRIBE 资源提取

```pseudocode
FUNCTION extract_describe_resources(sparql: &str) -> Vec<String>:
    IF let Some(describe_pos) = upper.find("DESCRIBE"):
        after_describe = &sparql[describe_pos + 8..]
        
        // 提取到 WHERE 或查询结束
        end_pos = upper[describe_pos..].find("WHERE")
                  .map(|p| p - 8)
                  .unwrap_or(after_describe.len())
        
        resources_part = &after_describe[..end_pos.min(after_describe.len())]
        
        // 解析 URI (<...>) 或变量 (?var)
        re = Regex::new(r"(<[^>]+>|\?[A-Za-z_][A-Za-z0-9_]*)")
        FOR cap IN re.captures_iter(resources_part):
            resources.push(cap[1].to_string())
        
    RETURN resources
END FUNCTION
```

### 1.3 OFFSET 提取 [NEW]

```pseudocode
FUNCTION extract_offset(sparql: &str) -> Option<usize>:
    upper = sparql.to_ascii_uppercase()
    
    IF let Some(offset_pos) = upper.find("OFFSET"):
        after_offset = &sparql[offset_pos + 6..]
        
        // 提取数字
        num_str = after_offset
            .trim_start()
            .chars()
            .take_while(|c| c.is_ascii_digit())
            .collect()
        
        RETURN num_str.parse().ok()
    
    RETURN None
END FUNCTION
```

---

## 2. IRConverter 模块

### 2.1 主转换流程

```pseudocode
FUNCTION convert_with_mappings(parsed: &ParsedQuery, metadata_map, mappings) -> LogicNode:
    // 1. 构建核心计划 (ExtensionalData + Join)
    core = build_core_plan_with_vars(...)
    
    // 2. 添加 FILTER (聚合前)
    FOR filter IN &parsed.filter_expressions:
        IF let Some(expr) = Self::parse_filter_expr(filter):
            core = LogicNode::Filter { expression: expr, child: Box::new(core) }
    
    // 3. 添加 BIND
    FOR bind IN &parsed.bind_expressions:
        core = LogicNode::Bind { expression: ..., child: Box::new(core) }
    
    // 4. 添加 GROUP BY / 聚合
    IF !parsed.group_by.is_empty() OR !parsed.aggregates.is_empty():
        core = LogicNode::Aggregate { ... }
    
    // 5. 添加 HAVING
    FOR having IN &parsed.having_expressions:
        core = LogicNode::Filter { expression: ..., child: Box::new(core) } // HAVING 也是 Filter
    
    // 6. 添加 ORDER BY
    // 7. 添加 LIMIT/OFFSET [FIXED]
    IF parsed.limit.is_some() OR parsed.offset.is_some() OR !parsed.order_by.is_empty():
        limit = parsed.limit.unwrap_or(0)
        
        // [FIXED] 使用 parsed.offset 而非硬编码 None
        core = LogicNode::Limit {
            limit,
            offset: parsed.offset,      // ← 修复：原来是 offset: None
            order_by: parsed.order_by.iter().map(...).collect(),
            child: Box::new(core),
        }
    
    // 8. 构建 Construction 节点 (SPARQL 类型包装)
    RETURN LogicNode::Construction {
        projected_vars: projected_vars.clone(),
        bindings: HashMap::new(),
        child: Box::new(core),
    }
END FUNCTION
```

### 2.2 FILTER 表达式解析 [FIXED]

```pseudocode
FUNCTION parse_filter_expr(filter: &str) -> Option<Expr>:
    // [FIXED] 首先检查完整 IRI，避免将 IRI 内的 <> 误解为操作符
    trimmed = filter.trim()
    IF trimmed.starts_with('<') && trimmed.ends_with('>'):
        // 完整 IRI 如 <http://example.org/emp1>
        RETURN Some(Expr::Term(Self::token_to_term(trimmed)))
    
    // 查找逻辑操作符 (&&, ||)
    IF let Some((op, left, right)) = find_logical_op(trimmed):
        left_expr = Self::parse_filter_expr(left)?
        right_expr = Self::parse_filter_expr(right)?
        RETURN Some(Expr::Binary { op, left: Box::new(left_expr), right: Box::new(right_expr) })
    
    // 查找比较操作符
    IF let Some((op, left, right)) = find_comparison_op(trimmed):
        left_term = Self::token_to_term(left)?
        right_term = Self::token_to_term(right)?
        RETURN Some(Expr::Comparison { op, left: left_term, right: right_term })
    
    // 终端节点 (变量或常量)
    RETURN Some(Expr::Term(Self::token_to_term(trimmed)))
END FUNCTION

FUNCTION find_logical_op(expr: &str) -> Option<(LogicOp, &str, &str)>:
    // [FIXED] 正确处理括号、IRI、引号
    depth = 0
    in_iri = false
    in_quote = false
    
    FOR (i, c) IN expr.chars().enumerate():
        IF c == '<' && !in_iri && !in_quote:
            in_iri = true
        ELSE IF c == '>' && in_iri:
            in_iri = false
        ELSE IF c == '(' && !in_quote:
            depth += 1
        ELSE IF c == ')' && !in_quote:
            depth -= 1
        ELSE IF c == '"':
            in_quote = !in_quote
        ELSE IF depth == 0 && !in_iri && !in_quote:
            // 查找 && 或 ||
            IF expr[i..].starts_with("&&"):
                RETURN Some((LogicOp::And, &expr[..i], &expr[i+2..]))
            ELSE IF expr[i..].starts_with("||"):
                RETURN Some((LogicOp::Or, &expr[..i], &expr[i+2..]))
    
    RETURN None
END FUNCTION
```

---

## 3. FlatSQLGenerator 模块

### 3.1 主生成流程

```pseudocode
STRUCT FlatSQLGenerator:
    ctx: GeneratorContext              // 收集 SQL 组件
    construct_template: Option<Vec<TriplePattern>>
    describe_resources: Option<Vec<String>>

FUNCTION generate(&mut self, root_node: &LogicNode) -> Result<String, GenerationError>:
    // 保存 CONSTRUCT/DESCRIBE 设置
    saved_describe = self.describe_resources.clone()
    
    // 重置上下文
    self.reset_context()
    
    // 恢复设置
    self.describe_resources = saved_describe
    
    // 处理特殊节点类型
    MATCH root_node:
        LogicNode::Union(children) =>
            self.ctx.union_sql = Some(self.generate_union_sql(children)?)
            RETURN self.assemble_sql()
    
    // 遍历 IR 树，收集组件
    self.traverse_node(root_node)?
    
    // 检查是否是 DESCRIBE 查询
    IF let Some(describe_resources) = self.describe_resources.clone():
        IF !describe_resources.is_empty():
            base_sql = self.assemble_sql()?
            RETURN self.build_describe_sql(&base_sql, &describe_resources)
    
    // 普通查询
    self.assemble_sql()
END FUNCTION
```

### 3.2 DESCRIBE SQL 构建 [FIXED]

```pseudocode
FUNCTION build_describe_sql(&self, base_sql: &str, resources: &[String]) -> Result<String, GenerationError>:
    select_items = &self.ctx.select_items
    
    // 如果没有 select_items，从 all_available_items 获取
    items_to_use = IF select_items.is_empty() THEN &self.ctx.all_available_items ELSE select_items
    
    IF items_to_use.is_empty():
        RETURN Ok(base_sql.to_string())
    
    // [FIXED] 去重：保持原始顺序，根据 alias 去重
    unique_items = Vec::new()
    seen_aliases = HashSet::new()
    FOR item IN items_to_use.iter():
        IF seen_aliases.insert(item.alias.clone()):      // 第一次遇到此 alias
            unique_items.push(item)                      // 保持顺序添加
    
    // 辅助函数：提取列名（去除表别名前缀如 "emp."）
    extract_column_name = |expr: &str| -> String:
        IF let Some(dot_pos) = expr.find('.'):
            RETURN expr[dot_pos + 1..].to_string()
        ELSE:
            RETURN expr.to_string()
    
    describe_parts = Vec::new()
    
    FOR resource IN resources:
        IF resource.starts_with('?'):
            // 变量资源：使用第一列作为 subject
            first_col = extract_column_name(&unique_items[0].expression)
            
            FOR item IN unique_items.iter():
                col_name = extract_column_name(&item.expression)
                
                // [FIXED] 所有值转换为 TEXT 以兼容 UNION ALL
                describe_parts.push(format!(
                    "SELECT {}::TEXT AS subject, '{}' AS predicate, {}::TEXT AS object FROM ({})",
                    first_col,
                    item.alias,
                    col_name,
                    base_sql
                ))
        ELSE:
            // 具体资源（URI）：使用资源 URI 作为 subject
            subject = resource.clone()
            
            FOR item IN unique_items.iter():
                col_name = extract_column_name(&item.expression)
                
                describe_parts.push(format!(
                    "SELECT '{}' AS subject, '{}' AS predicate, {}::TEXT AS object FROM ({})",
                    subject,
                    item.alias,
                    col_name,
                    base_sql
                ))
    
    RETURN Ok(describe_parts.join(" UNION ALL "))
END FUNCTION
```

### 3.3 节点遍历器

```pseudocode
FUNCTION traverse_node(&mut self, node: &LogicNode) -> Result<(), GenerationError>:
    MATCH node:
        LogicNode::ExtensionalData { source, alias, columns, column_aliases } =>
            self.handle_extensional_data(source, alias, columns, column_aliases)
        
        LogicNode::Filter { expression, child } =>
            self.handle_filter(expression, child)
        
        LogicNode::Join { left, right, condition } =>
            self.handle_join(left, right, condition)
        
        LogicNode::Union(children) =>
            self.handle_union(children)
        
        LogicNode::Limit { limit, offset, order_by, child } =>
            self.handle_limit(limit, offset, order_by, child)
        
        LogicNode::Aggregate { group_by, aggregates, child } =>
            self.handle_aggregate(group_by, aggregates, child)
        
        // ... 其他节点类型
END FUNCTION
```

### 3.4 FILTER 处理

```pseudocode
FUNCTION handle_filter(&mut self, expression: &Expr, child: &LogicNode) -> Result<(), GenerationError>:
    // 先处理子节点
    self.traverse_node(child)?
    
    // 翻译过滤条件为 SQL
    sql_condition = self.translate_expression(expression)?
    
    // 分流：如果是聚合后的过滤，放入 HAVING，否则放入 WHERE
    condition = Condition { expression: sql_condition, condition_type: ConditionType::Filter }
    
    IF self.contains_aggregate(expression):
        self.ctx.having_conditions.push(condition)
    ELSE:
        self.ctx.where_conditions.push(condition)
    
    Ok(())
END FUNCTION
```

### 3.5 SQL 拼装

```pseudocode
FUNCTION assemble_sql(&self) -> Result<String, GenerationError>:
    IF let Some(union_sql) = &self.ctx.union_sql:
        RETURN Ok(union_sql.clone())
    
    sql = String::new()
    
    // SELECT 子句
    IF !self.ctx.select_items.is_empty():
        sql.push_str("SELECT ")
        select_parts = self.ctx.select_items.iter().map(|item| format!(
            "{} AS {}", item.expression, item.alias
        )).collect()
        sql.push_str(&select_parts.join(", "))
    ELSE:
        sql.push_str("SELECT *")
    
    // FROM 子句
    IF !self.ctx.from_clause.is_empty():
        sql.push_str(" FROM ")
        sql.push_str(&self.ctx.from_clause.join(", "))
    
    // WHERE 子句
    IF !self.ctx.where_conditions.is_empty():
        where_parts = self.ctx.where_conditions.iter().map(|c| c.expression.clone()).collect()
        sql.push_str(" WHERE ")
        sql.push_str(&where_parts.join(" AND "))
    
    // GROUP BY 子句
    IF !self.ctx.group_by.is_empty():
        sql.push_str(" GROUP BY ")
        sql.push_str(&self.ctx.group_by.join(", "))
    
    // HAVING 子句
    IF !self.ctx.having_conditions.is_empty():
        having_parts = self.ctx.having_conditions.iter().map(|c| c.expression.clone()).collect()
        sql.push_str(" HAVING ")
        sql.push_str(&having_parts.join(" AND "))
    
    // ORDER BY 子句
    IF !self.ctx.order_by.is_empty():
        sql.push_str(" ORDER BY ")
        order_parts = self.ctx.order_by.iter().map(|(col, desc)|
            IF *desc THEN format!("{} DESC", col) ELSE col.clone()
        ).collect()
        sql.push_str(&order_parts.join(", "))
    
    // LIMIT 子句
    IF let Some(limit) = self.ctx.limit:
        sql.push_str(&format!(" LIMIT {}", limit))
    
    // OFFSET 子句 [FIXED]
    IF let Some(offset) = self.ctx.offset:
        sql.push_str(&format!(" OFFSET {}", offset))
    
    RETURN Ok(sql)
END FUNCTION
```

---

## 4. 修复总结

### 4.1 OFFSET 支持修复

| 文件 | 修复内容 |
|------|---------|
| `sparql_parser_v2.rs` | 添加 `ParsedQuery.offset` 字段 |
| `sparql_parser_v2.rs` | 实现 `extract_offset()` 函数 |
| `ir_converter.rs` | `LogicNode::Limit` 使用 `parsed.offset` |

### 4.2 FILTER URI 解析修复

| 文件 | 修复内容 |
|------|---------|
| `ir_converter.rs` | `parse_filter_expr()` 优先检测完整 IRI |
| `ir_converter.rs` | `find_logical_op()` 正确处理 IRI 内的 `<>` |

### 4.3 DESCRIBE 重复 UNION 修复

| 文件 | 修复内容 |
|------|---------|
| `flat_generator.rs` | `build_describe_sql()` 使用 HashSet 去重 |
| `flat_generator.rs` | 保持原始顺序的迭代器去重 |
| `flat_generator.rs` | 所有值转换为 `::TEXT` 兼容 UNION ALL |

---

## 5. 测试覆盖

### 5.1 Sprint 7 测试套件

```
test_sprint7_ask.py         - 4 个测试 (基础/FILTER/不存在/JOIN)
test_sprint7_construct.py   - 4 个测试 (基础/多谓词/FILTER/LIMIT)
test_sprint7_describe.py    - 3 个测试 (单一资源/变量/LIMIT)
test_sprint7_dialect.py     - 4 个测试 (方言/引号/类型/LIMIT+OFFSET)
```

### 5.2 Unified 测试套件

```
聚合: test_unified_agg_*.py    (3 个)
边界: test_unified_edge_*.py   (2 个)
过滤: test_unified_filter_*.py (2 个)
HAVING: test_unified_having_*.py (2 个)
JOIN: test_unified_join_*.py   (3 个)
映射: test_unified_map_*.py    (2 个)
排序: test_unified_order_*.py  (3 个)
性能: test_unified_perf_*.py   (1 个)
```

**总计：33 个测试全部通过 ✓**

---

## 6. 关键数据结构

### 6.1 ParsedQuery

```rust
pub struct ParsedQuery {
    pub raw: String,
    pub query_type: QueryType,           // Select/Construct/Ask/Describe
    pub projected_vars: Vec<String>,
    pub filter_expressions: Vec<String>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,           // [NEW]
    pub order_by: Vec<OrderByItem>,
    pub construct_template: Vec<TriplePattern>,
    pub describe_resources: Vec<String>, // [NEW]
    // ... 其他字段
}
```

### 6.2 LogicNode (IR)

```rust
pub enum LogicNode {
    // 数据源
    ExtensionalData { source, alias, columns, column_aliases },
    
    // 一元操作
    Filter { expression, child },
    Limit { limit, offset, order_by, child },  // offset 支持
    
    // 二元操作
    Join { left, right, condition },
    Union(Vec<LogicNode>),
    
    // 构造
    Construction { projected_vars, bindings, child },
    
    // 聚合
    Aggregate { group_by, aggregates, child },
}
```

### 6.3 GeneratorContext

```rust
pub struct GeneratorContext {
    pub select_items: Vec<SelectItem>,
    pub from_clause: Vec<String>,
    pub where_conditions: Vec<Condition>,
    pub having_conditions: Vec<Condition>,
    pub group_by: Vec<String>,
    pub order_by: Vec<(String, bool)>,  // (列名, 是否降序)
    pub limit: Option<usize>,
    pub offset: Option<usize>,          // [NEW]
    pub all_available_items: Vec<SelectItem>,
    pub union_sql: Option<String>,
}
```

---

## 附录：代码文件索引

| 文件 | 功能 | 关键函数/结构 |
|------|------|--------------|
| `src/parser/sparql_parser_v2.rs` | SPARQL V2 解析器 | `SparqlParserV2`, `ParsedQuery` |
| `src/parser/ir_converter.rs` | IR 转换 | `IRConverter::convert_with_mappings` |
| `src/sql/flat_generator.rs` | SQL 生成 | `FlatSQLGenerator`, `build_describe_sql` |
| `src/lib.rs` | PostgreSQL 扩展 | `ontop_translate`, `ontop_query` |
