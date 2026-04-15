# rs_ontop_core 多 bgworker 并发方案

## 1. 目标与约束

### 1.1 目标
- 保持产品形态不变：SPARQL 能力继续由 PostgreSQL 扩展提供。
- 将当前 5820 单 worker 串行处理改为多 worker 并发处理。
- 在不引入“独立外部服务”的前提下提升吞吐、降低排队延迟。

### 1.2 约束
- 不在单个 bgworker 内跨线程执行 SPI。
- 每个 worker 独立 `connect_worker_to_spi`，独立事务边界。
- 保持 `/sparql` 与 `/ontology` 接口兼容（URL、返回结构不变）。

## 2. 当前瓶颈

- 当前只有一个 `ontop_sparql_bgworker_main` 监听器，主循环串行：
  - 收包 -> 解析 -> `BackgroundWorker::transaction` -> 执行 -> 返回。
- 任一慢查询会阻塞后续请求，形成队头阻塞。
- 在该模型下，PostgreSQL 的多进程能力无法被充分利用。

## 3. 方案总览

采用“多 bgworker 多进程并发 + 单端口内核分流（优先）+ 多端口兜底”的双模式方案：

1. 优先模式：`N` 个 worker 监听同一端口（5820），通过 `SO_REUSEPORT` 由内核分流连接。
2. 兜底模式：若 `SO_REUSEPORT` 不可用，则每个 worker 监听独立端口（5820+i），用于压测和应急。

> 说明：如 `tiny_http` 无法设置 `SO_REUSEPORT`，需替换监听层（例如基于 `socket2 + hyper/axum` 的最小监听实现），但仍在扩展进程内运行。

## 4. 配置设计

新增 GUC（示例命名，可按现有风格调整）：

- `ontop.http_workers`（int，默认 1）
  - 范围建议：1..32
  - 含义：HTTP bgworker 实例数

- `ontop.http_port`（int，默认 5820）
  - 主监听端口

- `ontop.http_reuseport`（bool，默认 on）
  - 是否尝试同端口复用绑定

- `ontop.http_port_stride`（int，默认 1）
  - 仅在 `reuseport=off` 或不可用时生效，worker_i 监听 `port + i*stride`

- `ontop.http_max_body_kb`（int，默认 256）
  - 现有 query size 限制配置化

- `ontop.http_shutdown_grace_ms`（int，默认 1000）
  - worker 停机优雅退出等待时间

PostgreSQL 参数联动建议：

- `max_worker_processes` >= `ontop.http_workers + 预留值`
- 评估 `max_connections` / 连接池策略，确保并发查询可落到足够 backend 进程

## 5. 架构改造点

### 5.1 Worker 注册
- 在 `_PG_init` 中按 `ontop.http_workers` 循环注册 `BackgroundWorkerBuilder`。
- 每个 worker 传入 `worker_id`（0..N-1）作为参数。

### 5.2 监听绑定策略
- `worker_id` 启动时读取 GUC：
  - `reuseport=true`：尝试绑定同一端口。
  - 失败则记录日志并按策略回退到独立端口（或直接 fail-fast，取决于配置）。

### 5.3 请求处理
- 保持当前 handler 逻辑，但拆分为可复用函数：
  - `parse_request`
  - `execute_sparql_in_spi_tx`
  - `write_response`
- 每个 worker 拥有独立事件循环和错误计数器。

### 5.4 ENGINE 与缓存一致性
- `ENGINE` 是进程内副本，多 worker 下每个进程一份。
- 增加统一刷新机制：
  - `ontop_refresh()` 更新共享版本号（DB 表或共享内存标记）。
  - 每个 worker 在请求前后检查版本，发现变化则本进程重载映射/元数据。
- 避免“某 worker 已刷新、某 worker 未刷新”的读不一致窗口。

### 5.5 可观测性
- 日志增加 `worker_id`、`listen_addr`、`request_id`。
- 新增最小指标（可先日志化）：
  - 每 worker QPS
  - p50/p95 延迟
  - 4xx/5xx
  - 执行超时次数

## 6. 分阶段实施计划

## Phase 0：基础清理（0.5 天）
- 统一监听器代码路径（`listener.rs` 与 `listener/robust.rs` 避免重复实现分叉）。
- 把请求处理主流程抽成公共函数，便于多 worker 复用。

验收：
- 单 worker 行为与当前一致。

## Phase 1：多 worker 框架（1 天）
- 新增 GUC。
- `_PG_init` 按配置注册 N 个 bgworker。
- worker 启动日志包含 `worker_id`。

验收：
- `ontop.http_workers=4` 时能看到 4 个 worker 启动。

## Phase 2：端口策略与并发生效（1~2 天）
- 实现 `reuseport` 模式与多端口兜底模式。
- 同端口模式压测；若库受限，先用多端口模式交付并验证性能提升。

验收：
- 压测下吞吐随 worker 数增长（至少 1->4 提升显著）。

## Phase 3：一致性与稳定性（1 天）
- 增加 ENGINE 版本刷新检查。
- 加入 worker 级健康日志与错误熔断策略。

验收：
- 执行 `ontop_refresh()` 后，多 worker 在可接受窗口内一致生效。

## 7. 兼容性与风险

主要风险：

1. `tiny_http` 可能无法设置 `SO_REUSEPORT`。
- 应对：监听层最小替换，不改变业务处理与 SPI 调用路径。

2. 多进程缓存一致性。
- 应对：引入版本号 + 懒刷新，必要时在关键路径强制检查。

3. worker 数过高导致 PG 资源争用。
- 应对：默认保守值（如 2/4），压测后给推荐区间。

4. 单条慢查询仍占用某 worker。
- 应对：增加 query timeout、请求级超时与错误分级返回。

## 8. 压测与验收标准

压测建议（至少两类）：
- 短查询高并发：验证吞吐线性增长趋势。
- 长查询混合流量：验证队头阻塞缓解情况。

通过标准（示例）：
- worker=4 时，QPS 相比 worker=1 提升 >= 2.0x。
- p95 延迟下降 >= 30%（混合流量场景）。
- 5xx 不高于基线 + 0.5%。

## 9. 回滚方案

- 运行时回滚：`ontop.http_workers=1`，恢复单 worker 模式。
- 监听异常回滚：关闭 `ontop.http_reuseport`，改多端口应急。
- 发布回滚：保留现有单 worker 代码路径，配置开关控制。

## 10. 推荐初始配置

生产初始建议：
- `ontop.http_workers = 4`
- `ontop.http_reuseport = on`
- `ontop.http_port = 5820`
- `max_worker_processes` 至少预留 8+

灰度策略：
- 先在预发压测验证 1->2->4 worker 的收益曲线，再生产逐级放量。

