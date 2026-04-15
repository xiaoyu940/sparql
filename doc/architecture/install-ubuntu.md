# rust-ontop: Ubuntu 安装指南

本指南详细说明了如何在 Ubuntu 系统（如 22.04 或 24.04）上将 `rust-ontop` 作为 PostgreSQL 原生扩展进行编译和安装。

## 1. 系统准备与依赖安装

首先，你需要安装 PostgreSQL 及其开发头文件。假设你使用的是 PostgreSQL 16。

```bash
sudo apt update
# 安装基础编译环境
sudo apt install build-essential libreadline-dev zlib1g-dev flex bison \
                 libxml2-dev libxslt-dev libssl-dev libxml2-utils \
                 xsltproc icu-devtools libicu-dev pkg-config libclang-dev

# 安装 PostgreSQL 核心及开发包（对应你的 PG 版本）
sudo apt install postgresql-16 postgresql-server-dev-16
```

## 2. 安装 Rust 工具链

如果还没安装 Rust，可以通过官方脚本安装并确保包含 `cargo`：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

## 3. 安装并初始化 `cargo-pgrx`

`pgrx` 是将 Rust 编译为 PostgreSQL 插件的关键工具。

```bash
# 安装管理工具
cargo install --locked cargo-pgrx

# 初始化 pgrx 以识别系统已有的 PostgreSQL (pg_config)
# 请根据你的实际版本调整路径参数
cargo pgrx init --pg16=$(which pg_config)
```

## 4. 编译与安装插件

切换到项目根目录，通过 `pgrx` 自动完成编译和 .so 库文件的分发。

```bash
# 确保 Cargo.toml 中的 features = ["pg16"]
# 这会将对应的二进制库拷贝到 /usr/lib/postgresql/16/lib/
cargo pgrx install --release
```

## 5. 数据库内配置

安装成功后，你可以通过 `psql` 或任何 SQL 客户端连接数据库并启用。

```sql
-- 1. 在数据库中启用插件
CREATE EXTENSION ontop;

-- 2. 创建映射信息表（存放 SPARQL 到 Relational 的映射）
CREATE TABLE IF NOT EXISTS ontop_mappings (
    mapping_id SERIAL PRIMARY KEY,
    predicate TEXT NOT NULL,
    table_name TEXT NOT NULL,
    subject_col TEXT NOT NULL,
    object_col TEXT NOT NULL
);

-- 3. (可选) 插入示例映射
-- 假设你有一张 employees 表，包含 employee_id 和 first_name 字段
INSERT INTO ontop_mappings (predicate, table_name, subject_col, object_col) 
VALUES ('http://example.org/firstName', 'employees', 'employee_id', 'first_name');

-- 4. 执行翻译测试
SELECT ontop_translate('SELECT * WHERE { ?s :firstName ?f }');
```

## 6. 维护命令

如果你修改了 Rust 源代码并需要更新插件：

```bash
# 重新编译安装
cargo pgrx install --release

# 在数据库中让新逻辑生效 (调用我们自定义的缓存刷新函数)
SELECT ontop_refresh();
```

## 7. 故障排除

* **Permission Denied**: `cargo pgrx install` 写入系统库可能需要 `sudo` 权限，或者确认当前用户在 postgres 相关的 lib 目录有写权限。
* **Version Mismatch**: 检查 `Cargo.toml` 的 `default = ["pg16"]` 必须与 `pg_config --version` 返回的主版本一致。
* **Shared Libraries**: 如遇到找不到库的错误，尝试运行 `sudo ldconfig` 更新共享库缓存。
