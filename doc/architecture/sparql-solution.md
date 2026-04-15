# rs-ontop-core: 内置 SPARQL 原生网关架构方案 (Background Worker Model)

## 1. 业务愿景与核心需求 (Requirements)
目前 `rs-ontop-core` 已经完成了底层的 TBox 解析映射与 SPARQL-to-SQL 的查询重写引擎。为了完全取代传统的 Java 联邦虚拟知识图谱引擎（如 Ontop 或 Stardog），我们需要提供一个开箱即用的**异构协议聚合网关**。

**核心需求：**
1. **端点暴露**：在 PostgreSQL 启动时，系统自动在宿主机上启动并监听标准的 SPARQL HTTP 端口（如 `5820` 端口）。
2. **协议兼容**：接收客户端发来的 HTTP 协议的 SPARQL 1.1 Query 请求（支持 `GET` 参数以及 `POST /sparql` 报文）。
3. **零通信损耗 (Zero-Data Movement)**：接收到请求后，不得再发起任何对本地或远程数据库的 TCP 连接，直接调用 PostgreSQL 内核（Spi 机制）与内存中的引擎进行查询重写与 SQL 执行。
4. **结果封装**：获取到的数据库底层执行结果能当场封装成标准 `SPARQL Query Results XML/JSON Format` 返回给调用方前端。

---

## 2. 总体实现方案 (Solutions)

利用 Rust 的 `pgrx` 框架中极其强悍的 **Background Worker (后台守护进程，BGW)** 机制，结合 Rust 优秀的网络生态来完成。

**工作流架构图：**
```text
[HTTP Client] (e.g. 5820)
       ↓
(1) HTTP Request (SPARQL)
       ↓
[PostgreSQL 主进程 (Postmaster)]
  └──┬ [Background Worker (Rust HTTP Server, e.g. tiny_http / axum)]
     │    (2) 解析 HTTP 请求
     │    (3) 交给 rs-ontop-core 翻译为 SQL (Unfolding & Rewriting)
     │    (4) 通过消息通道推给内部数据库访问器
     │
     └──┬ [SPI 事务守护者 (PostgreSQL 内存上下文隔离)]
          (5) 执行 `Spi::connect` 与数据库通信，获得 JSONB 结果集
          (6) 返回数据，HTTP Worker 构建响应并返回客户端
```

---

## 3. 核心深坑与应对措施 (Pitfalls & Countermeasures)

给 PostgreSQL 挂接内置异步网络服务是技术难度极其高的一环。前人踩过无数的坑，以下是必须在架构期就防御的致命问题：

### 💣 坑 1: PostgreSQL 并发模型 vs 异步运行时 (SPI 线程安全爆炸)
**灾难现象**：
如果在异步运行时（如多线程的 `tokio` 或 `axum`）中，有多个并发的网络请求同时调用了 PostgreSQL 内部的 API（如 `pgrx::Spi::connect`），将瞬间引发 PostgreSQL `SIGSEGV` 崩溃。因为 PostgreSQL 的 SPI (Server Programming Interface) 及 MemoryContext 是**绝对单线程/非线程安全**的（严格绑定单个 OS 线程）。
**🩺 应对方案**：
**隔离与消息机制**。网络监听可以使用异步 Tokio，**但绝不能在 Tokio 的工作线程池里直接连数据库**。
必须设计一套**双架构隔离**：
- 前台起一个 Tokio 监听 HTTP，解析 SPARQL。
- 后台预留一个唯一绑死在 PostgreSQL BGW 主线程上的死循环（专门处理事务）。
- 它们之间通过 `std::sync::mpsc::channel` 或 `tokio::sync::mpsc` 通信：Tokio 收到请求后，把生 SQL 发给 Channel；单线程的 SPI 守护者收到 SQL 取出执行，再把结果扔回 Channel 返回。

### 💣 坑 2: 背景进程的数据库连接与事务丧失 (Transaction Context Miss)
**灾难现象**：
当后台进程直接试图跑 SQL 时会报错："SPI_connect failed" 或 "cannot execute SQL without a transaction"。因为 Background Worker 启动时，它只是一个脱离了用户会话的孤儿进程。
**🩺 应对方案**：
必须利用 `BackgroundWorker::transaction()` 显式挂载数据库会话。
```rust
BackgroundWorker::transaction(|| {
    Spi::connect(|client| {
        // 在这里执行 SQL 才是安全的
    });
});
```

### 💣 坑 3: 内存泄漏与 `MemoryContext` 堆积
**灾难现象**：
由于该 HTTP 网关是伴随数据库长年（几个月不重启）运行的，如果用 Rust 申请了内存并通过 FFI 扔给了 PG，或者从 PG 拿了大的结果集忘记清理，会导致 PG 的上下文内存吃满，直至数据库 OOM 宕机。
**🩺 应对方案**：
- 在 HTTP 网络层，严格**全量使用 Rust 原生内存分配器 (Global Allocator)**，避免在网络报文拼接时触碰 `palloc`（PG内存）。
- 不建议直接序列化上 GB 的数据集返回。应该基于 SPI 游标 (`SpiCursor`) 分批取数，并运用 HTTP Chunked 机制流式 (`Stream`) 推送结网络果，确保内存稳定。

### 💣 坑 4: 随系统优雅重启的信号量处理 (SIGTERM Hang)
**灾难现象**：
用户执行 `sudo systemctl restart postgresql`，数据库等待几分钟后强制关机（报错卡死）。原因是您创建的 HTTP 网关里包含一个 `while (true)` 的监听死循环或阻塞的 TCP `accept()`，阻挡了 PG 主进程回收子进程。
**🩺 应对方案**：
不要写死循环等待。必须将 HTTP 请求事件机制与 PostgreSQL 的 **Latch (门闩)** 绑定，或者周期性检查 `pgrx::check_for_interrupts()` 与 `BackgroundWorker::worker_is_running()`。必须确保在收到数据库主进程关闭信号时，安全释放 HTTP 套接字端口，优雅退出。

---

## 4. 技术栈实施选型建议

考虑到稳定压倒一切，在 `rs-ontop-core` 的落地上，我们推荐：

*   **HTTP 引擎**：**`tiny_http`**（轻量级、高可控，不携带庞大的 Tokio 运行时。避免了重异步和单线程数据库底层的架构摩擦。最适合写数据库后台插件，且其阻塞的事件循环更好适配 PG Interrupts）。
*   **路由解析**：纯手动匹配 `/sparql` 或简单利用 `rouille` 库，提取 `query` 字符串和 `Accept` 标头（决定给客户端返回 JSON 还是 XML）。
*   **通信模式**：单线程下，网络收到请求 -> 调用 `ontop_translate` -> `Spi::execute` 获取 JSON -> 回写网络流，一次性线性完成上下文极度安全。

---
**附录**：接下来，可以在独立划分出的 `src/listener/mod.rs` 目录模块中搭起这段 BGW 的骨架代码。只要越过了这些坑，一个彻底颠覆现有 JVM 大数据集群的新流派 “All-in-PG” RDF 知识图谱数据库服务器将成为现实！
