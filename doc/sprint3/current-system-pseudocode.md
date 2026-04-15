# RS Ontop Core 当前系统伪代码（Sprint3 基线）

> 更新时间：2026-03-29  
> 用途：作为 Sprint3 的"当前状态基线文档"，描述已落地实现路径

> 标识规范：`[S3-Px-y]` 对应 Sprint3 的任务项。  
> 优先级：`P0` 必做，`P1` 应做，`P2` 可选。

---

## Sprint3 查询重写开发规划

### 核心目标
完善查询重写能力，实现 SPARQL 到 SQL 的高效、正确转换。

### 开发任务分解

| 标识 | 任务项 | 优先级 | 说明 |
|------|--------|--------|------|
| [S3-P0-1] | 聚合查询支持 | P0 | 实现 COUNT/AVG/SUM/MIN/MAX 聚合函数 |
| [S3-P0-2] | FILTER 表达式修复 | P0 | 修复括号内逻辑操作符匹配问题 |
| [S3-P0-3] | 变量解析修复 | P0 | 修复 translate_term 变量查找错误处理 |
| [S3-P1-1] | 子查询 (Subquery) 支持 | P1 | 实现嵌套 SELECT 查询 |
| [S3-P1-2] | BIND 表达式支持 | P1 | 实现变量绑定功能 |
| [S3-P1-3] | HAVING 子句支持 | P1 | 实现聚合过滤条件 |
| [S3-P1-4] | SPARQL 函数库完善 | P1 | 支持 STR/REGEX/NOW 等内置函数 |
| [S3-P1-5] | 投影归一化优化 | P1 | NormalizeProjection 优化规则 |
| [S3-P1-6] | 无用列剪枝优化 | P1 | PruneUnusedColumns 优化规则 |
| [S3-P2-1] | 属性路径 (Property Path) | P2 | 实现 `*`/`+`/`?` 路径表达式 |
| [S3-P2-2] | VALUES 数据块 | P2 | 实现 VALUES 内联数据 |
| [S3-P2-3] | 服务调用 (SERVICE) | P2 | 联邦查询支持 |

### 查询重写关键路径

```pseudocode
FUNCTION rewrite_sparql_to_sql(sparql_query):
    // [S3-P0] 解析阶段
    parsed = SparqlParserV2.parse(sparql_query)        // [S3-P0-1] 聚合解析
    
    // [S3-P0] IR 构建阶段  
    ir_plan = IRBuilder.build(parsed, metadata)      // [S3-P0-1] Aggregation 节点
    
    // [S3-P0] 映射展开
    ir_plan = UnfoldingPass.apply(ir_plan)           // [S3-P0-1] 处理聚合内部展开
    
    // [S3-P1] 查询重写阶段（待实现）
    // ir_plan = SubqueryRewriter.apply(ir_plan)     // [S3-P1-1] 子查询重写
    // ir_plan = BindRewriter.apply(ir_plan)        // [S3-P1-2] BIND 重写
    // ir_plan = HavingRewriter.apply(ir_plan)      // [S3-P1-3] HAVING 重写
    
    // [S3-P1] 优化阶段
    ir_plan = NormalizeProjection.apply(ir_plan)     // [S3-P1-5] 投影归一化
    ir_plan = PruneUnusedColumns.apply(ir_plan)      // [S3-P1-6] 无用列剪枝
    ir_plan = FilterPushdown.apply(ir_plan)          // 谓词下推
    ir_plan = LeftToInnerJoinPass.apply(ir_plan)     // 左连接转内连接
    
    // [S3-P0] SQL 生成
    sql = FlatSQLGenerator.generate(ir_plan)         // [S3-P0-1] 聚合SQL生成
    RETURN sql
END FUNCTION

## 1. HTTP 后台服务主循环

```pseudocode
FUNCTION ontop_sparql_bgworker_main():
    ATTACH_SIGNAL_HANDLERS(SIGHUP, SIGTERM)
    CONNECT_TO_DATABASE("rs_ontop_core")
    server = BIND_HTTP_SERVER("0.0.0.0:5820")

    WHILE wait_latch():
        CHECK_FOR_INTERRUPTS()
        request = server.recv_timeout(100ms)
        IF request == NONE:
            CONTINUE

        IF request.path STARTS_WITH "/ontology":
            HANDLE_ONTOLOGY(request)
            CONTINUE

        IF request.path STARTS_WITH "/sparql":
            HANDLE_SPARQL(request)
            CONTINUE

        RESPOND_404(request)
END FUNCTION
```

---

## 2. SPARQL 请求处理（当前实现）

```pseudocode
FUNCTION HANDLE_SPARQL(request):
    sparql = EXTRACT_QUERY_FROM_GET_OR_POST(request)
    IF sparql IS EMPTY:
        RESPOND_400_JSON("Missing query parameter")
        RETURN

    result = CATCH_UNWIND(
        TRANSACTION(
            sql = generate_simple_flat_sql(sparql)
            rows = stream_query_results(sql, batch_size=500)
            RETURN JSON_RESULT(rows)
        )
    )

    IF result IS OK:
        RESPOND_200_JSON(result)
    ELSE:
        status = map_error_to_http_status(result.error)
        RESPOND_ERROR_JSON(status, result.error)
END FUNCTION
```

说明：
- `/sparql` 路径通过 `SELECT ontop_query($pgrx$...$pgrx$)` 间接执行
- 结果读取为分批 fetch，汇总为 JSON 返回

---

## 3. 查询翻译主链路（OntopEngine::translate）

```pseudocode
CLASS OntopEngine:
    FUNCTION translate(sparql):
        parsed = SparqlParserV2.parse(sparql)

        logic_plan = IRBuilder.build(parsed, metadata_map)
        logic_plan = UNFOLD_MAPPINGS(logic_plan, mapping_index)
        logic_plan = APPLY_TBOX_REWRITING(logic_plan, tbox)

        // 预优化
        logic_plan = RedundantJoinElimination.apply(logic_plan)
        logic_plan = FilterPushdown.apply(logic_plan)
        logic_plan = JoinReordering.apply(logic_plan)
        logic_plan = NormalizeProjection.apply(logic_plan)
        logic_plan = PruneUnusedColumns.apply(logic_plan)
        logic_plan = UnionLifting.apply(logic_plan)

        // 既有优化流水线
        logic_plan = PassManager.optimize(logic_plan)

        sql = FlatSQLGenerator.generate(logic_plan)
        RETURN sql
END CLASS
```

---

## 4. ParserV2 与 IR 构建（当前行为）

```pseudocode
CLASS SparqlParserV2:
    FUNCTION parse(sparql):
        VALIDATE_SYNTAX_WITH_SPARGEBRA(sparql)
        projected_vars = EXTRACT_TOKENS_STARTS_WITH("?")
        aggregate_exprs = EXTRACT_AGGREGATE_EXPRESSIONS(sparql)   // [S3-P0-1] 新增聚合解析
        flags = {
            has_filter: CONTAINS("FILTER"),
            has_optional: CONTAINS("OPTIONAL"),
            has_union: CONTAINS("UNION"),
            has_aggregate: aggregate_exprs.NOT_EMPTY()            // [S3-P0-1] 聚合标记
        }
        RETURN ParsedQuery(raw, projected_vars, aggregate_exprs, flags)
END CLASS

CLASS IRBuilder:
    FUNCTION build(parsed, metadata_map):
        IF parsed.has_aggregate:
            RETURN build_aggregation_plan(parsed, metadata_map)     // [S3-P0-1] 聚合查询专用构建
        ELSE:
            RETURN build_standard_plan(parsed, metadata_map)
END CLASS
```

```pseudocode
CLASS IRConverter:
    FUNCTION convert(parsed, metadata):
        base_scan = ExtensionalData(table=metadata.table_name, mapping=heuristic_var_to_col)

        IF parsed.has_union:
            RETURN Union([base_scan, base_scan])
        IF parsed.has_optional:
            RETURN Join(children=[base_scan, base_scan], join_type=LEFT, condition=NULL)
        IF parsed.has_filter:
            // [S3-P0-2] 修复 FILTER 解析：正确处理括号内的逻辑操作符
            filter_expr = PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(parsed.filter_string)
            RETURN Filter(filter_expr, child=base_scan)

        RETURN base_scan

    FUNCTION build_aggregation_plan(parsed, metadata):
        // [S3-P0-1] 聚合查询构建
        base_scan = ExtensionalData(table=metadata.table_name, mapping=heuristic_var_to_col)
        
        // 创建 Aggregation 节点
        RETURN Aggregation(
            child=base_scan,
            group_by=parsed.projected_vars,
            aggregates=parsed.aggregate_exprs
        )
END CLASS
```

---

## 5. 扁平 SQL 生成（当前行为）

```pseudocode
CLASS FlatSQLGenerator:
    FUNCTION generate(root):
        RESET_CONTEXT()

        IF root IS Union:
            RETURN JOIN_WITH_UNION( FOR EACH child => "(" + generate(child) + ")" )

        TRAVERSE(root):
            ExtensionalData -> ADD_FROM(table alias), ADD_SELECT(mapped columns)
            Join -> TRAVERSE(children), ADD_JOIN_CONDITION_IF_EXISTS()
            Filter -> TRAVERSE(child), ADD_WHERE(translated expr)
            Construction -> TRAVERSE(child), ADD_PROJECTED_COLUMNS()
            Aggregation -> HANDLE_AGGREGATION(node)                    // [S3-P0-1] 聚合处理

        RETURN ASSEMBLE_SELECT_FROM_WHERE_GROUP_ORDER_LIMIT_OFFSET()

    FUNCTION HANDLE_AGGREGATION(node):
        // [S3-P0-1] 处理聚合节点
        TRAVERSE(node.child)
        
        // 先为变量分配别名，再翻译表达式
        FOR (alias, expr) IN node.aggregates:
            var_alias = self.alias_manager.allocate_var_alias(alias)  // [S3-P0-1] 先分配别名
            sql_expr = self.translate_expression(expr)                // [S3-P0-1] 再翻译表达式
            
            self.ctx.select_items.push(SelectItem {
                expression: sql_expr,
                alias: var_alias,
                is_aggregate: true,
            })
        
        // 添加 GROUP BY
        IF node.group_by.NOT_EMPTY():
            self.ctx.group_by = node.group_by
END FUNCTION
```

---

## 6. 映射展开（UnfoldingPass）

```pseudocode
CLASS UnfoldingPass:
    FUNCTION apply(plan, ctx):
        TRAVERSE(plan):
            IF node IS IntensionalData:
                mapping_rules = ctx.mappings.find_by_predicate(node.predicate)
                RETURN EXPAND_TO_EXTENSIONAL(mapping_rules, node.variables)
            
            IF node IS Aggregation:                                 // [S3-P0-1] 处理聚合内部展开
                node.child = self.apply(node.child, ctx)
                RETURN node
        
        RETURN plan
END CLASS
```

---

## 7. FILTER 表达式解析（修复版）

```pseudocode
FUNCTION PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(filter_string):
    // [S3-P0-2] 修复括号内逻辑操作符匹配
    IF filter_string CONTAINS "||":
        left = EXTRACT_LEFT_OF("||")
        right = EXTRACT_RIGHT_OF("||")
        RETURN Expr::Or(
            PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(left),
            PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(right)
        )
    
    IF filter_string CONTAINS "&&":
        // [S3-P0-2] 关键修复：在任意括号深度匹配 &&
        op_pos = FIND_LOGICAL_OP_AT_ANY_DEPTH(filter_string, "&&")
        IF op_pos FOUND:
            left = filter_string[0..op_pos]
            right = filter_string[op_pos+2..]
            RETURN Expr::And(
                PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(left),
                PARSE_FILTER_WITH_PARENTHESIS_SUPPORT(right)
            )
    
    // 解析基本比较表达式
    RETURN PARSE_COMPARISON_EXPRESSION(filter_string)

FUNCTION FIND_LOGICAL_OP_AT_ANY_DEPTH(filter, op):
    // [S3-P0-2] 支持在任意括号深度查找操作符
    paren_depth = 0
    i = 0
    WHILE i < filter.length - op.length:
        c = filter[i]
        IF c == '(':
            paren_depth += 1
        ELSE IF c == ')':
            paren_depth -= 1
        ELSE IF paren_depth >= 0 AND filter[i..].starts_with(op):
            RETURN i
        i += 1
    RETURN NOT_FOUND
END FUNCTION
```

---

## 8. 变量解析（translate_term）

```pseudocode
FUNCTION translate_term(term):
    IF term IS Variable(var_name):
        // [S3-P0-2] 修复变量查找逻辑
        // 1. 先在 select_items 中查找
        FOR item IN self.ctx.select_items:
            IF item.alias == var_name OR item.expression.contains(var_name):
                RETURN item.expression
        
        // 2. 再在 alias_manager 中查找
        IF self.alias_manager.has_alias(var_name):
            alias = self.alias_manager.get_alias(var_name)
            RETURN format("{}.{}", alias.table_ref, alias.column)
        
        // [S3-P0-2] 修复：返回错误而非无效引用
        RETURN ERROR(UnmappedVariable, "Variable {} not found in select_items or alias_manager", var_name)
    
    ELSE IF term IS Constant(value):
        RETURN format_literal(value)
END FUNCTION
```

---

## 9. 流式读取（数据库侧）

```pseudocode
FUNCTION stream_query_results(sql, batch_size):
    portal = StreamingClient(batch_size).execute_streaming_sql(sql)
    out = []
    LOOP:
        batch = portal.fetch()
        IF batch IS NONE:
            BREAK
        out.APPEND(CONVERT_BATCH_TO_JSON_OBJECTS(batch))

```pseudocode
KNOWN_LIMITS:
    - /sparql HTTP 响应仍为一次性 JSON 输出（非真正 chunked 输出）
    - IRConverter 仍为启发式映射，复杂语义等价性待增强
    - Union 嵌套组合场景需继续补齐
    - 缺少显式 TBOX_REWRITING 阶段
    - SQL 生成仍非完整方言感知
    - 优化器缺少 projection normalize / prune / union lifting
    - 监控指标尚未覆盖展开耗时、SQL长度、优化阶段分解
    - [S3-P0-4] FILTER 复杂嵌套表达式仍需增强测试覆盖
    - [S3-P0-4] 多个 FILTER 组合场景需验证
```

---

## 10. Sprint3+ 建议执行顺序

```pseudocode
EXECUTION_ORDER:
    1) [S3-P1-1] 端到端 chunked HTTP 响应
    2) [S3-P1-2] IR 语义升级（图模式、去启发式）
    3) [S3-P1-3] UNION 嵌套与组合语义补齐
    4) [S3-P1-4] TBOX 重写主链路
    5) [S3-P1-5] 方言感知 SQL 生成
    6) [S3-P2-6] 优化器补强（projection normalize 等）
```

---

**维护者**: RS Ontop Core Team  
**基线版本**: Sprint3 完成状态  
**关联文档**: `/doc/sprint3/transformation-plan.md` (待创建)
