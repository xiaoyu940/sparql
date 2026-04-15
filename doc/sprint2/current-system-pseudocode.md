# RS Ontop Core 当前系统伪代码（Sprint2 基线）

> 更新时间：2026-03-28  
> 用途：作为 Sprint2 的“当前状态基线文档”，描述已落地实现路径（非目标态设计稿）

> 标识规范：`[S2-Px-y]` 对应 `doc/sprint2/transformation-plan.md` 的任务项。  
> 优先级：`P0` 必做，`P1` 应做，`P2` 可选。

---

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
            sql = generate_simple_flat_sql(sparql)                     // [S2-P0-1][S2-P0-2] 改为显式 UNFOLD + TBOX + IR 主链路
            rows = stream_query_results(sql, batch_size=500)           // [S2-P0-3] 继续保留流式读取
            RETURN JSON_RESULT(rows)                                   // [S2-P0-3] 改为标准 SPARQL Results JSON，支持 ASK
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
- 当前 /sparql 路径通过 `SELECT ontop_query($pgrx$...$pgrx$)` 间接执行。
- 结果读取为分批 fetch，再汇总为 JSON 返回（内部是流式读取，外部响应仍为一次性 JSON body）。 // [S2-P0-3] 改为端到端 chunked

---

## 3. 查询翻译主链路（OntopEngine::translate）

```pseudocode
CLASS OntopEngine:
    FUNCTION translate(sparql):
        parsed = SparqlParserV2.parse(sparql)

        logic_plan = IRBuilder.build(parsed, metadata_map)             // [S2-P0-2] IR 从 flag 模式升级为图模式驱动
        logic_plan = UNFOLD_MAPPINGS(logic_plan, mapping_index)        // [S2-P0-1] 新增
        logic_plan = APPLY_TBOX_REWRITING(logic_plan, tbox)            // [S2-P0-1] 新增

        // 预优化
        logic_plan = RedundantJoinElimination.apply(logic_plan)
        logic_plan = FilterPushdown.apply(logic_plan)
        logic_plan = JoinReordering.apply(logic_plan)
        logic_plan = NormalizeProjection.apply(logic_plan)             // [S2-P1-5] 新增
        logic_plan = PruneUnusedColumns.apply(logic_plan)              // [S2-P1-5] 新增
        logic_plan = UnionLifting.apply(logic_plan)                    // [S2-P1-5] 新增

        // 既有优化流水线
        logic_plan = PassManager.optimize(logic_plan)

        sql = DialectAwareSQLGenerator.generate(logic_plan, dialect)   // [S2-P1-4] 方言感知生成
        RETURN sql
END CLASS
```

---

## 4. ParserV2 与 IR 构建（当前行为）

```pseudocode
CLASS SparqlParserV2:
    FUNCTION parse(sparql):
        VALIDATE_SYNTAX_WITH_SPARGEBRA(sparql)
        projected_vars = EXTRACT_TOKENS_STARTS_WITH("?")               // [S2-P0-2] 升级为 AST 结构化提取
        flags = {
            has_filter: CONTAINS("FILTER"),
            has_optional: CONTAINS("OPTIONAL"),
            has_union: CONTAINS("UNION")
        }
        RETURN ParsedQuery(raw, projected_vars, flags)
END CLASS

CLASS IRBuilder:
    FUNCTION build(parsed, metadata_map):
        metadata = PICK_TABLE_METADATA("employees" OR FIRST_AVAILABLE) // [S2-P0-2] 去硬编码，转映射驱动
        RETURN IRConverter.convert(parsed, metadata)
END CLASS
```

```pseudocode
CLASS IRConverter:
    FUNCTION convert(parsed, metadata):
        base_scan = ExtensionalData(table=metadata.table_name, mapping=heuristic_var_to_col)  // [S2-P0-2] 改为 mapping rule binding

        IF parsed.has_union:
            RETURN Union([base_scan, base_scan])                        // [S2-P0-2] 支持嵌套 UNION 组合
        IF parsed.has_optional:
            RETURN Join(children=[base_scan, base_scan], join_type=LEFT, condition=NULL)      // [S2-P0-2] 真实 OPTIONAL 语义
        IF parsed.has_filter:
            RETURN Filter(TRUE_FUNCTION, child=base_scan)               // [S2-P0-2] 真实 FILTER 表达式树

        RETURN base_scan
END CLASS
```

---

## 5. 扁平 SQL 生成（当前行为）

```pseudocode
CLASS FlatSQLGenerator:
    FUNCTION generate(root):
        RESET_CONTEXT()

        IF root IS Union:
            RETURN JOIN_WITH_UNION( FOR EACH child => "(" + generate(child) + ")" )  // [S2-P1-4] 扩展方言/嵌套场景

        TRAVERSE(root):
            ExtensionalData -> ADD_FROM(table alias), ADD_SELECT(mapped columns)
            Join -> TRAVERSE(children), ADD_JOIN_CONDITION_IF_EXISTS()
            Filter -> TRAVERSE(child), ADD_WHERE(translated expr)
            Construction -> TRAVERSE(child), ADD_PROJECTED_COLUMNS()
            Aggregation -> TRAVERSE(child), ADD_GROUP_BY_AND_AGG()

        RETURN ASSEMBLE_SELECT_FROM_WHERE_GROUP_ORDER_LIMIT_OFFSET()    // [S2-P1-4] 增加 nullability/type 约束处理
END CLASS
```

---

## 6. 流式读取（数据库侧）

```pseudocode
FUNCTION stream_query_results(sql, batch_size):
    portal = StreamingClient(batch_size).execute_streaming_sql(sql)
    out = []
    LOOP:
        batch = portal.fetch()
        IF batch IS NONE:
            BREAK
        out.APPEND(CONVERT_BATCH_TO_JSON_OBJECTS(batch))
        IF batch.is_last_batch:
            BREAK
    portal.close()
    RETURN out                                                          // [S2-P0-3] HTTP 层改为边读边写 chunk
END FUNCTION
```

---

## 7. 当前已知边界（供 Sprint2 使用）

```pseudocode
KNOWN_LIMITS:
    - /sparql HTTP 响应仍为一次性 JSON 输出（非真正 chunked 输出）            // [S2-P0-3]
    - IRConverter 仍为启发式映射，复杂语义等价性待增强                       // [S2-P0-2]
    - Union 当前支持“根 Union”优先路径，嵌套组合场景需继续补齐               // [S2-P0-2]
    - 缺少显式 UNFOLD_MAPPINGS / TBOX_REWRITING 阶段                        // [S2-P0-1]
    - SQL 生成仍非完整方言感知                                                // [S2-P1-4]
    - 优化器缺少 projection normalize / prune / union lifting                // [S2-P1-5]
    - 监控指标尚未覆盖展开耗时、SQL长度、优化阶段分解                         // [S2-P2-6]
```

---

## 8. Sprint2 执行顺序（按标识）

```pseudocode
EXECUTION_ORDER:
    1) [S2-P0-1] 映射展开 + TBOX 重写主链路
    2) [S2-P0-2] IR 语义升级（图模式、去启发式、补齐组合语义）
    3) [S2-P0-3] 标准结果语义 + 端到端 chunked
    4) [S2-P1-4] 方言感知 SQL 与约束处理
    5) [S2-P1-5] 优化器补强
    6) [S2-P2-6] 指标与运维闭环
```
