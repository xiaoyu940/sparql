# BUG: 合法 SPARQL 查询触发 PANIC，导致 5820 服务中断并引发 PostgreSQL 重启

## 基本信息
- 日期: 2026-04-16
- 模块: `5820` SPARQL Gateway / `ontop_query`
- 严重级别: 高（可导致网关中断，影响数据库实例稳定性）

## 现象
在 `/sparql` 执行以下语法合法的查询时，出现多次 `SPARQL_REQUEST_PANIC`，随后触发 PostgreSQL `PANIC`：
- `SELECT DISTINCT ?class WHERE { ?s a ?class . FILTER(isIRI(?class)) } LIMIT 50`
- `SELECT DISTINCT ?p WHERE { ?s ?p ?o . FILTER(isIRI(?o)) FILTER(isIRI(?p)) } LIMIT 50`
- `SELECT DISTINCT ?p WHERE { ?s ?p ?o . FILTER(!isIRI(?o)) FILTER(isIRI(?p)) } LIMIT 50`
- `SELECT DISTINCT ?s WHERE { ?s ?p ?o . FILTER(isIRI(?s)) } LIMIT 50`

日志关键片段：
- `SPARQL_REQUEST_PANIC ... Internal error: Unknown panic`
- `PANIC: ERRORDATA_STACK_SIZE exceeded`
- `background worker ... was terminated by signal 6: Aborted`
- PostgreSQL 自动恢复（recovery）

## 已确认边界
- 语法错误输入（例如 `Person`）已被 parser 校验拦截，返回 `HTTP 400`，并不会直接导致此次崩溃。
- 本次崩溃由“语法合法但触发执行链内部异常”的查询引发。

## 复现步骤
1. 保证 5820 已启动。
2. 调用上述任一（建议按顺序）`FILTER(isIRI(...))` 查询到 `/sparql`。
3. 观察 PostgreSQL 日志出现 `SPARQL_REQUEST_PANIC`，随后可能升级为 `PANIC` 并自动重启。

## 预期结果
- 合法 SPARQL 查询应返回业务错误或空结果，不能触发进程级 PANIC。

## 实际结果
- 合法查询在某些路径下触发内部 panic，严重时导致数据库实例重启恢复。

## 当前判断
- 根因位于 `ontop_query` 执行链（SPARQL -> IR/SQL 生成或执行）的异常处理深层路径。
- 表现上与 `FILTER(isIRI(...))` 类模式高度相关。

## 临时止血建议
- 前端暂时禁用“本体树自动探测”中的上述 `isIRI` 过滤模板。
- Agent 自动规划阶段避免生成该类查询模板。
- 保留语法 parser 校验（已完成），继续减少无效输入冲击。

## 后续修复建议
- 在 `ontop_query` 执行链增加更内层的 panic 保护与错误降级，确保返回可控 `5xx` 而不是触发数据库级 `PANIC`。
- 为上述 4 条查询模式增加回归测试，纳入稳定性测试集。
