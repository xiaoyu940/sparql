//! SQL 生成和方言支持模块

pub mod dialect;
pub mod flat_generator;
pub mod join_optimizer;
pub mod path_sql_generator;
pub mod alias_manager;

pub use dialect::{SqlDialect, PostgreSqlDialect, MySqlDialect, SqliteDialect, get_dialect};
pub use flat_generator::FlatSQLGenerator;
