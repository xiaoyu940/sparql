# Sprint 9 最新伪代码（2026-04-09）

> 目标：反映当前仓库最新实现状态（含最近修复）
> 范围：解析层、IR转换、SQL生成、HTTP服务、测试框架

---

## 1. 端到端主流程

`pseudocode
FUNCTION HANDLE_SPARQL_QUERY(sparql_text):
    parsed = PARSE_SPARQL(sparql_text)

    // 1) 解析层预处理
    parsed.main_patterns = STRIP_TOP_LEVEL_SUBQUERIES(parsed.where_block)
    parsed.main_patterns = STRIP_FILTER_EXISTS_BLOCKS(parsed.main_patterns)
    parsed.filter_expressions = EXTRACT_FILTERS_KEEP_EXISTS(parsed.where_block)

    // 2) IR 转换
    logic_ir = CONVERT_TO_LOGIC_NODE(parsed)

    // 3) SQL 生成
    sql = GENERATE_SQL(logic_ir)

    // 4) 执行 + 返回
    rows = EXECUTE_SQL(sql)
    RETURN FORMAT_SPARQL_JSON(rows)
END FUNCTION
`

---

## 2. 解析层（parser）

### 2.1 FILTER 提取（支持 EXISTS / NOT EXISTS）

`pseudocode
FUNCTION EXTRACT_FILTER_EXPRESSIONS(where_block):
    FOR each "FILTER ..." occurrence:
        IF form is FILTER(expr):
            PUSH expr
        ELSE IF form is FILTER EXISTS { body }:
            PUSH "EXISTS { body }"
        ELSE IF form is FILTER NOT EXISTS { body }:
            PUSH "NOT EXISTS { body }"
    RETURN filters
END FUNCTION
`

### 2.2 避免 EXISTS 子块污染主图模式

`pseudocode
FUNCTION STRIP_FILTER_EXISTS_BLOCKS(where_block):
    SCAN chars
    WHEN meet "FILTER EXISTS { ... }" or "FILTER NOT EXISTS { ... }":
        SKIP whole block
    ELSE:
        KEEP char
    RETURN stripped_where
END FUNCTION
`

### 2.3 比较符解析修复（<）

`pseudocode
FUNCTION PARSE_BINARY_OP(expr):
    FOR op IN ["<=", ">=", "=", "<", ">", ...]:
        TRY match operator first
        THEN parse operands
    // 先识别运算符，避免 '<' 被误吸收到 IRI / token
END FUNCTION
`

---

## 3. IR 转换层（ir_converter）

### 3.1 
eeded_vars 收敛规则

`pseudocode
FUNCTION COLLECT_NEEDED_VARS(parsed):
    needed = PROJECTED_VARS

    // 普通 FILTER 中变量要保留
    FOR f IN parsed.filter_expressions:
        IF starts_with(f, "EXISTS") OR starts_with(f, "NOT EXISTS"):
            CONTINUE
        needed += EXTRACT_VARS(f)

    // JOIN 键变量保留（出现在多个三元组）
    counts = COUNT_VAR_OCCURRENCES_IN_MAIN_PATTERNS(parsed.main_patterns)
    FOR (v, cnt) IN counts:
        IF cnt > 1:
            needed += v

    RETURN needed
END FUNCTION
`

### 3.2 相关子查询相关变量识别

`pseudocode
FUNCTION BUILD_SUBQUERY_NODE(core_plan, sub_parsed):
    sub_plan = CONVERT(sub_parsed)
    core_bindings = EXTRACT_VAR_BINDINGS(core_plan)
    sub_vars = COLLECT_QUERY_VARS(sub_parsed)  // 三元组+FILTER+投影

    correlated = FILTER(sub_vars, v => v IN core_bindings)

    IF correlated NOT EMPTY:
        sub_plan = PROMOTE_CORRELATED_VARS(sub_plan, correlated)

    RETURN SubQuery(inner=sub_plan, correlated_vars=correlated)
END FUNCTION
`

`pseudocode
FUNCTION PROMOTE_CORRELATED_VARS(node, correlated):
    MATCH node:
        CASE Construction(projected, bindings, child):
            ENSURE projected contains correlated
            ENSURE bindings contains v -> Variable(v)
            child2 = PROMOTE_CORRELATED_VARS(child, correlated)
            RETURN Construction(projected, bindings, child2)

        CASE Aggregation(group_by, aggs, having, child):
            ENSURE group_by contains correlated
            RETURN Aggregation(group_by, aggs, having, child)

        CASE Filter(expr, child):
            RETURN Filter(expr, PROMOTE_CORRELATED_VARS(child, correlated))

        CASE Limit(limit, offset, order_by, child):
            RETURN Limit(limit, offset, order_by, PROMOTE_CORRELATED_VARS(child, correlated))

        CASE other:
            RETURN other
END FUNCTION
`

---

## 4. SQL 生成层（flat_generator）

### 4.1 JOIN 条件回退策略（修复 CROSS JOIN 漂移）

`pseudocode
FUNCTION HANDLE_JOIN(children, explicit_condition, join_type):
    all_items = TRAVERSE_CHILDREN_AND_COLLECT_SELECT_ITEMS(children)

    FUNCTION INFER_JOIN_CONDITIONS():
        // 1) 跨子计划：同 alias 不同表达式 => 等值条件
        FOR every pair(child_i, child_j):
            FOR each item_i IN child_i:
                FOR each item_j IN child_j:
                    IF item_i.alias == item_j.alias AND item_i.expr != item_j.expr:
                        ADD condition(item_i.expr = item_j.expr)

        // 2) 全局兜底：同 alias 多表达式，统一与首表达式做等值
        alias_exprs = GROUP_BY_ALIAS(ctx.all_available_items)
        FOR each alias with exprs.size > 1:
            FOR e in exprs[1:]:
                ADD WHERE(exprs[0] = e)
    END FUNCTION

    IF explicit_condition IS NONE:
        INFER_JOIN_CONDITIONS()
    ELSE:
        sql_cond = TRANSLATE_EXPR(explicit_condition)
        IF CONDITION_REFERENCES_KNOWN_COLUMNS(sql_cond):
            ADD_JOIN_CONDITION(sql_cond, join_type)
        ELSE:
            // 关键修复：显式条件无法落地时，不再静默丢失，执行推断回退
            INFER_JOIN_CONDITIONS()
END FUNCTION
`

### 4.2 EXISTS 子查询语义保护

`pseudocode
FUNCTION GENERATE_EXISTS_SUBQUERY(exists_ir):
    // 已修复解析侧后，EXISTS/NOT EXISTS 不再误入主图模式
    // 保持相关变量映射，避免恒真/恒假误退化
    BUILD correlated subquery SQL
    RETURN "EXISTS (subquery)" or "NOT EXISTS (subquery)"
END FUNCTION
`

---

## 5. HTTP 服务（listener）

### 5.1 启动流程（后台 worker）

`pseudocode
FUNCTION BGWORKER_MAIN(arg):
    ATTACH_SIGNAL_HANDLERS()

    // 关键修复：在事务上下文中初始化 ENGINE，避免 worker 崩溃
    result = BACKGROUND_WORKER_TRANSACTION(
        SPI_CONNECT(refresh_engine_from_spi)
    )
    LOG init result

    server = HTTP_BIND("0.0.0.0:5820")

    LOOP:
        WAIT_LATCH(timeout=100ms)
        req = RECV_TIMEOUT(server, 100ms)
        IF req:
            DISPATCH(req.path):
                "/ontology" -> handle_ontology
                "/sparql"   -> handle_sparql
                else         -> 404
END FUNCTION
`

---

## 6. 测试框架（tests/python/framework.py）

### 6.1 单用例执行输出恢复

`pseudocode
METHOD TestCaseBase.run():
    PRINT "执行 SPARQL 查询..."
    sparql_result = sparql_query()

    PRINT "执行 SQL 查询..."
    sql_result = sql_query()

    PRINT "比对结果..."
    passed, errors = compare_results(sparql_result, sql_result)
    PRINT pass/fail detail

    RETURN standardized dict
END METHOD
`

### 6.2 结果比对（优先精确列名）

`pseudocode
FUNCTION compare_results(sparql_result, sql_result):
    CHECK row_count first

    BUILD col_matches:
        PRIORITY 1: exact case-insensitive match
        PRIORITY 2: fuzzy contains match

    FOR each comparable column in first row:
        COMPARE values
        IF numeric strings:
            TRY float equality

    RETURN passed, errors
END FUNCTION
`

---

## 7. 已落地的“非 0=0”测试增强（摘要）

`pseudocode
UPDATE TestFilterEquals:
    'John' -> 'First1'  // 由 0=0 变为 1=1

UPDATE TestFilterLessThan:
    salary < 50000 -> salary < 60000  // 由 0=0 变为 5000=5000

UPDATE TestDescribeVariable:
    'Alice' -> 'First1'  // 由 0=0 变为 1=1

UPDATE TestExistsNested:
    project_status 'Active' -> 'In Progress'  // 由 0=0 变为有命中

UPDATE TestExistsWithFilter:
    manager_relations 路径 -> employee.project_id 与 project.budget 相关 EXISTS

UPDATE Geo cases:
    Distance/Within 使用有数据数据集与稳定基线，避免空表/空数据导致 0=0
`

---

## 8. 当前状态快照

`pseudocode
ALL_TESTS = 92
PASSED = 92
FAILED = 0

HTTP_GATEWAY:
    bind 5820 = OK
    /sparql basic query = OK
    stress(1000 req, c=40) = 100% success
`

