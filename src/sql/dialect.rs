//! SQL 方言抽象层
//!
//! 支持多数据库方言：PostgreSQL, MySQL, SQLite 等

/// SQL 方言 Trait
///
/// 定义不同数据库的 SQL 语法差异
pub trait SqlDialect: Send + Sync {
    /// 引用标识符（表名、列名等）
    fn quote_identifier(&self, name: &str) -> String;
    
    /// 引用字符串值
    fn quote_string(&self, value: &str) -> String;
    
    /// 类型转换语法
    fn cast_expression(&self, value: &str, target_type: &str) -> String;
    
    /// LIMIT/OFFSET 语法
    fn limit_clause(&self, limit: Option<usize>, offset: Option<usize>) -> String;
    
    /// 是否支持 ILIKE（不区分大小写的 LIKE）
    fn supports_ilike(&self) -> bool;
    
    /// 是否支持窗口函数
    fn supports_window_functions(&self) -> bool;
    
    /// 是否支持 RETURNING 子句
    fn supports_returning(&self) -> bool;
    
    /// 获取方言名称
    fn dialect_name(&self) -> &'static str;
}

/// LIMIT 语法类型
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LimitSyntax {
    /// LIMIT count OFFSET skip
    LimitOffset,
    /// FETCH FIRST count ROWS ONLY
    FetchFirst,
    /// TOP count
    Top,
}

/// PostgreSQL 方言
#[derive(Debug, Clone, Copy, Default)]
pub struct PostgreSqlDialect;

impl SqlDialect for PostgreSqlDialect {
    fn quote_identifier(&self, name: &str) -> String {
        format!("\"{}\"", name.replace('\"', "\"\""))
    }
    
    fn quote_string(&self, value: &str) -> String {
        format!("'{}'", value.replace('\'', "''"))
    }
    
    fn cast_expression(&self, value: &str, target_type: &str) -> String {
        format!("CAST({} AS {})", value, target_type)
    }
    
    fn limit_clause(&self, limit: Option<usize>, offset: Option<usize>) -> String {
        let mut clause = String::new();
        
        if let Some(l) = limit {
            clause.push_str(&format!(" LIMIT {}", l));
        }
        
        if let Some(o) = offset {
            clause.push_str(&format!(" OFFSET {}", o));
        }
        
        clause
    }
    
    fn supports_ilike(&self) -> bool {
        true
    }
    
    fn supports_window_functions(&self) -> bool {
        true
    }
    
    fn supports_returning(&self) -> bool {
        true
    }
    
    fn dialect_name(&self) -> &'static str {
        "postgresql"
    }
}

/// MySQL 方言
#[derive(Debug, Clone, Copy, Default)]
pub struct MySqlDialect;

impl SqlDialect for MySqlDialect {
    fn quote_identifier(&self, name: &str) -> String {
        format!("`{}`", name.replace('`', "``"))
    }
    
    fn quote_string(&self, value: &str) -> String {
        format!("'{}'", value.replace('\'', "''").replace('\\', "\\\\"))
    }
    
    fn cast_expression(&self, value: &str, target_type: &str) -> String {
        format!("CAST({} AS {})", value, target_type)
    }
    
    fn limit_clause(&self, limit: Option<usize>, offset: Option<usize>) -> String {
        match (limit, offset) {
            (Some(l), Some(o)) => format!(" LIMIT {}, {}", o, l),
            (Some(l), None) => format!(" LIMIT {}", l),
            (None, Some(o)) => format!(" LIMIT {}, 18446744073709551615", o), // MySQL max
            (None, None) => String::new(),
        }
    }
    
    fn supports_ilike(&self) -> bool {
        false // MySQL 使用 LOWER() 函数
    }
    
    fn supports_window_functions(&self) -> bool {
        true // MySQL 8.0+
    }
    
    fn supports_returning(&self) -> bool {
        false // MySQL 不支持 RETURNING
    }
    
    fn dialect_name(&self) -> &'static str {
        "mysql"
    }
}

/// SQLite 方言
#[derive(Debug, Clone, Copy, Default)]
pub struct SqliteDialect;

impl SqlDialect for SqliteDialect {
    fn quote_identifier(&self, name: &str) -> String {
        format!("\"{}\"", name.replace('\"', "\"\""))
    }
    
    fn quote_string(&self, value: &str) -> String {
        format!("'{}'", value.replace('\'', "''"))
    }
    
    fn cast_expression(&self, value: &str, target_type: &str) -> String {
        format!("CAST({} AS {})", value, target_type)
    }
    
    fn limit_clause(&self, limit: Option<usize>, offset: Option<usize>) -> String {
        let mut clause = String::new();
        
        if let Some(l) = limit {
            clause.push_str(&format!(" LIMIT {}", l));
        }
        
        if let Some(o) = offset {
            if clause.is_empty() {
                clause.push_str(" LIMIT -1"); // SQLite 需要 LIMIT 才能使用 OFFSET
            }
            clause.push_str(&format!(" OFFSET {}", o));
        }
        
        clause
    }
    
    fn supports_ilike(&self) -> bool {
        false // SQLite 使用 LOWER() 函数
    }
    
    fn supports_window_functions(&self) -> bool {
        true // SQLite 3.25+
    }
    
    fn supports_returning(&self) -> bool {
        true // SQLite 3.35+
    }
    
    fn dialect_name(&self) -> &'static str {
        "sqlite"
    }
}

/// 方言工厂
pub fn get_dialect(name: &str) -> Box<dyn SqlDialect> {
    match name.to_lowercase().as_str() {
        "postgresql" | "postgres" | "pg" => Box::new(PostgreSqlDialect),
        "mysql" | "mariadb" => Box::new(MySqlDialect),
        "sqlite" | "sqlite3" => Box::new(SqliteDialect),
        _ => {
            log::warn!("Unknown dialect '{}', defaulting to PostgreSQL", name);
            Box::new(PostgreSqlDialect)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_postgresql_quote() {
        let dialect = PostgreSqlDialect;
        assert_eq!(dialect.quote_identifier("table"), "\"table\"");
        assert_eq!(dialect.quote_identifier("ta\"ble"), "\"ta\"\"ble\"");
    }
    
    #[test]
    fn test_mysql_quote() {
        let dialect = MySqlDialect;
        assert_eq!(dialect.quote_identifier("table"), "`table`");
        assert_eq!(dialect.quote_identifier("ta`ble"), "`ta``ble`");
    }
    
    #[test]
    fn test_sqlite_quote() {
        let dialect = SqliteDialect;
        assert_eq!(dialect.quote_identifier("table"), "\"table\"");
    }
    
    #[test]
    fn test_limit_clauses() {
        let pg = PostgreSqlDialect;
        let mysql = MySqlDialect;
        let sqlite = SqliteDialect;
        
        // PostgreSQL: LIMIT 10 OFFSET 5
        assert_eq!(pg.limit_clause(Some(10), Some(5)), " LIMIT 10 OFFSET 5");
        
        // MySQL: LIMIT 5, 10
        assert_eq!(mysql.limit_clause(Some(10), Some(5)), " LIMIT 5, 10");
        
        // SQLite: LIMIT 10 OFFSET 5
        assert_eq!(sqlite.limit_clause(Some(10), Some(5)), " LIMIT 10 OFFSET 5");
    }
    
    #[test]
    fn test_dialect_factory() {
        let pg = get_dialect("postgresql");
        assert_eq!(pg.dialect_name(), "postgresql");
        
        let mysql = get_dialect("MySQL");
        assert_eq!(mysql.dialect_name(), "mysql");
        
        let sqlite = get_dialect("SQLite");
        assert_eq!(sqlite.dialect_name(), "sqlite");
    }
}
