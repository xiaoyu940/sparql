这是为您整理的 **RS Ontop Core V2.0 完整改造伪代码文档**。

本方案已将**逻辑中间层 (IR)**、**扁平化 SQL 生成**以及 **pgrx 流式处理** 完整嵌入。文档中通过注释清晰标注了 `[改造]`、`[新增]` 以及 `[删除/废弃]` 的部分，确保在下一次迭代开发时有明确的对照。

---

# RS Ontop Core 系统伪代码文档 (V2.0 全量重构版)

## 1. 系统架构与 HTTP 监听器

### 1.1 主入口函数 (保持稳定)
```pseudocode
FUNCTION ontop_sparql_bgworker_main():
    ATTACH_SIGNAL_HANDLERS(SIGHUP, SIGTERM)
    CONNECT_TO_DATABASE("rs_ontop_core")
    server = CREATE_HTTP_SERVER("0.0.0.0:5820")
    
    WHILE wait_latch(100ms):
        CHECK_FOR_INTERRUPTS()
        request = server.recv_timeout(100ms)
        IF request == NULL: CONTINUE
        
        IF request.url.path STARTS_WITH "/sparql":
            handle_sparql_request(request)
        // ... 其他路由
END FUNCTION
```

### 1.2 SPARQL 请求处理 (改造：引入流式事务)
```pseudocode
FUNCTION handle_sparql_request(request):
    sparql_query = extract_query_from_request(request)
    IF sparql_query == EMPTY: 
        send_error_response(request, 400, "Missing query")
        RETURN

    // [改造: 使用流式处理替代原有的全量 Result 缓存]
    result = CATCH_UNWIND(() -> {
        EXECUTE_IN_TRANSACTION(() -> {
            EXECUTE_WITH_SPI_CLIENT((client) -> {
                // [新增: 资源保护]
                client.execute("SET statement_timeout = '30s'")
                
                // [改造: 调用 V2 引擎生成扁平化 SQL]
                sql = ontop_engine_v2.translate(sparql_query)
                
                // [改造: 使用 SPI Portal 游标实现流式读取]
                portal = client.open_cursor(sql)
                
                // 写入响应头，准备分块传输 (Chunked Transfer)
                request.send_response_header(200, "application/sparql-results+json")
                request.start_body_stream()
                
                WHILE rows = portal.fetch(batch_size=500):
                    IF rows.EMPTY: BREAK
                    // 增量转换并实时写入 HTTP 缓冲区
                    json_chunk = ResultProcessor.to_json_fragment(rows)
                    request.write_body_chunk(json_chunk)
                
                request.end_body_stream()
                portal.close()
            })
        })
    })
    
    IF result.IS_ERR():
        handle_panic_and_error(result, request)
END FUNCTION
```

---

## 2. SPARQL 查询引擎 (核心改造层)

### 2.1 引擎主流水线 (新增 IR 阶段)
```pseudocode
CLASS OntopEngineV2:
    FUNCTION translate(sparql_str):
        // 1. 语法解析
        parsed_query = SparqlParser.parse(sparql_str)
        
        // 2. [新增: 构建逻辑中间表示 IR]
        // 这一步将三元组模式转为逻辑算子，解除与 SQL 语法的直接耦合
        logic_plan = IRBuilder.build(parsed_query)
        
        // 3. [新增: 逻辑优化]
        optimized_plan = QueryOptimizer.optimize(logic_plan)
        
        // 4. [改造: 调用扁平化生成器生成 SQL]
        sql = FlatSQLGenerator.generate(optimized_plan)
        
        RETURN sql
END CLASS
```

### 2.2 逻辑算子定义 (新增 IR 结构)
```pseudocode
ENUM IRNode:
    Scan(table, alias, bindings)      // 物理表扫描
    Join(left, right, join_vars)      // 逻辑连接
    Filter(expression, child)         // 过滤条件
    Project(vars, child)              // 结果投影
```

### 2.3 扁平化 SQL 生成器 (全量重写)
```pseudocode
CLASS FlatSQLGenerator:
    // 上下文容器：收集整个查询树的所有组件，最后一次性拼装
    ctx = { 
        "select_items": [], 
        "from_tables": [], 
        "where_conditions": [], 
        "alias_counter": 0 
    }

    FUNCTION generate(root_node):
        RESET_CONTEXT(ctx)
        traverse(root_node)
        
        // [关键改造: 拼装为扁平 SQL，消除嵌套子查询]
        sql = "SELECT " + JOIN(ctx.select_items, ", ")
        sql += " FROM " + JOIN(ctx.from_tables, ", ")
        IF ctx.where_conditions NOT EMPTY:
            sql += " WHERE " + JOIN(ctx.where_conditions, " AND ")
        
        RETURN sql

    FUNCTION traverse(node):
        MATCH node.TYPE:
            CASE "Scan":
                alias = "t" + (ctx.alias_counter++)
                ctx.from_tables.ADD(node.table + " AS " + alias)
                // 建立 SPARQL 变量到 SQL 列的映射
                FOR var, col IN node.bindings:
                    ctx.select_items.ADD(alias + "." + col + " AS " + var)
                // 处理 Subject 的常量约束
                IF node.subject_const:
                    ctx.where_conditions.ADD(alias + "." + node.pk_col + " = '" + node.subject_val + "'")

            CASE "Join":
                traverse(node.left)
                traverse(node.right)
                // [改造: 自动推导 Join 键]
                // 查找左右子树共同拥有的变量并生成 SQL 等值条件
                FOR var IN node.join_vars:
                    left_col = get_mapped_col(node.left, var)
                    right_col = get_mapped_col(node.right, var)
                    ctx.where_conditions.ADD(left_col + " = " + right_col)

            CASE "Filter":
                traverse(node.child)
                sql_expr = translate_expression(node.expression)
                ctx.where_conditions.ADD(sql_expr)
END CLASS
```

---

## 3. 优化器与映射管理

### 3.1 优化器规则 (改造：语义优化)
```pseudocode
CLASS QueryOptimizer:
    FUNCTION optimize(logic_plan):
        plan = logic_plan
        // [新增: 冗余连接消除]
        // 如果两个 Scan 指向同一张表且 Subject 相同，合并为一个 Scan
        plan = RedundantJoinElimination.apply(plan)
        
        // [新增: 谓词下推]
        plan = FilterPushDown.apply(plan)
        
        // [新增: 基于统计信息的 Join 重排]
        // 将记录数少的表放在左侧作为驱动表
        plan = JoinReordering.apply(plan)
        
        RETURN plan
END CLASS
```

### 3.2 映射管理器 (改造：支持元数据)
```pseudocode
CLASS MappingManager:
    FUNCTION find_mapping(predicate):
        mapping = mappings[predicate]
        // [新增: 记录表的主键和索引信息，供生成器使用]
        mapping.metadata = fetch_pg_metadata(mapping.table_name)
        RETURN mapping
END CLASS
```

---

## 4. 结果处理器 (改造：URI 模板化)

```pseudocode
CLASS ResultProcessor:
    FUNCTION to_json_fragment(rows):
        // [改造: 实时将数据库原始值根据本体模板转换为 RDF Term]
        json_array = []
        FOR row IN rows:
            binding = {}
            FOR col IN row:
                template = get_template_for_col(col.name)
                IF template:
                    // 例子: ID 1 -> <http://example.org/item/1>
                    rdf_val = apply_uri_template(template, col.val)
                ELSE:
                    rdf_val = format_as_literal(col.val)
                binding[col.name] = rdf_val
            json_array.ADD(binding)
        RETURN SERIALIZE_TO_JSON_BATCH(json_array)
END CLASS
```

---

## 5. 废弃代码清理清单 (迭代时需删除)

1.  **[删除]** `PostgreSQLGenerator.generate_join_node`: 旧逻辑使用 `SELECT * FROM (Subquery) JOIN (Subquery)`，在高并发下会导致 PG Planner 内存溢出，必须彻底废弃。
2.  **[删除]** `handle_sparql_request` 中的 `client.select()`: 该同步方法会阻塞整个后台进程直到查询结束，且无法处理海量结果集。
3.  **[删除]** `ontop_query` 中直接生成字符串的逻辑：避免 SQL 注入风险，所有查询必须通过逻辑算子中转。

---

### 总结
这份全量伪代码通过 **IR 算子树** 解耦了查询意图与 SQL 生成，并利用 **FlatSQLGenerator** 确保生成的 SQL 是 PG 优化器最喜欢的扁平结构。同时，**流式 Portal 处理** 保证了系统的工业级稳定性。

**由于此方案涉及多表 Join 别名自动分配，您是否需要我为您编写一个关于“别名碰撞避免算法”的辅助逻辑细节？**