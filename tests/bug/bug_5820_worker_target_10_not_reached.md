# BUG: 10 Worker Target Not Reached

## 基本信息
- 日期: 2026-04-15
- 模块: `5820` HTTP Gateway Worker 启动与扩缩
- 严重级别: 中（功能可用但容量未达预期）

## 现象
当 `rs_ontop_core.http_workers = 10` 且 `rs_ontop_core.http_reuseport = on` 时：
- `ontop_http_worker_status()` 返回 `target=10, alive=7`
- `ontop_start_sparql_server()` 返回 `started=0, failed=30, attempts=30`
- `ss -ltnp | grep :5820 | wc -l` 显示监听进程数为 `7`

## 复现步骤
1. 设置参数并重启 PostgreSQL：
   - `ALTER SYSTEM SET rs_ontop_core.http_workers = 10;`
   - `ALTER SYSTEM SET rs_ontop_core.http_reuseport = on;`
   - `systemctl restart postgresql`
2. 重新加载扩展：
   - `DROP EXTENSION IF EXISTS rs_ontop_core CASCADE;`
   - `CREATE EXTENSION rs_ontop_core;`
3. 执行：
   - `SELECT ontop_http_worker_status();`
   - `SELECT ontop_start_sparql_server();`
   - `SELECT ontop_http_worker_status();`

## 预期结果
- `alive` 应收敛到 `10`
- `5820` 应有 `10` 个 worker 监听

## 实际结果
- 仅 `7` 个 worker 存活并监听
- 启动流程达到尝试上限后仍未补齐

## 当前判断
- 该问题发生在高并发 worker 拉起阶段，可能与系统资源限制/套接字绑定时序相关。
- 现有“逐个拉起 + 短暂 sleep + 重试上限”机制已生效，但在目标 `10` 时无法稳定收敛。

## 临时建议
- 生产先使用稳定值（如 `2~7`）
- 后续补充专项排查：
  - 检查每次失败时的 PostgreSQL 日志与内核网络参数
  - 分析 worker 启动失败分布与绑定失败具体原因
  - 评估重试策略（间隔/次数）是否需要按目标 worker 数放大
