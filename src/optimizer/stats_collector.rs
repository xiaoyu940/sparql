//! PostgreSQL 统计信息采集器
//!
//! 从 PostgreSQL 系统表 `pg_stats` 和 `pg_class` 采集统计信息，
//! 用于查询优化器的成本模型和选择性估计。
//!
//! # 采集的统计信息
//! - 表级：行数、页数
//! - 列级：NULL 比例、不同值数量、最常用值 (MCV)、等深直方图

use crate::optimizer::statistics::{Statistics, TableStatistics, ColumnStatistics, Histogram};

/// 统计信息采集器错误
#[derive(Debug, Clone)]
pub enum StatsCollectorError {
    DatabaseError(String),
    InvalidStats(String),
}

impl std::fmt::Display for StatsCollectorError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StatsCollectorError::DatabaseError(msg) => write!(f, "Database error: {}", msg),
            StatsCollectorError::InvalidStats(msg) => write!(f, "Invalid stats: {}", msg),
        }
    }
}

impl std::error::Error for StatsCollectorError {}

/// PostgreSQL 统计信息采集器
///
/// 负责从 PostgreSQL 系统表采集统计信息。
pub struct PgStatsCollector;

impl PgStatsCollector {
    /// 创建新的采集器
    pub fn new() -> Self {
        Self
    }

    /// 采集所有表的统计信息
    ///
    /// # Arguments
    /// * `client` - PostgreSQL SPI 客户端
    ///
    /// # Returns
    /// 成功时返回包含所有表统计信息的 Statistics 对象
    #[cfg(feature = "pgrx")]
    pub fn collect_all_stats(
        &self,
        client: &mut pgrx::spi::SpiClient,
    ) -> Result<Statistics, StatsCollectorError> {
        let mut stats = Statistics::default();

        // 获取所有表名和行数
        let table_rows = self.collect_table_stats(client)?;

        for (table_name, row_count) in table_rows {
            let mut table_stats = TableStatistics::new(&table_name, row_count);

            // 采集列级统计
            match self.collect_column_stats(client, &table_name) {
                Ok(col_stats) => {
                    for (col_name, col_stat) in col_stats {
                        table_stats.column_stats.insert(col_name, col_stat);
                    }
                }
                Err(e) => {
                    eprintln!("Warning: Failed to collect column stats for {}: {}", table_name, e);
                }
            }

            stats.insert_table_stats(table_stats);
        }

        Ok(stats)
    }

    /// 采集表级统计（行数）
    #[cfg(feature = "pgrx")]
    fn collect_table_stats(
        &self,
        client: &mut pgrx::spi::SpiClient,
    ) -> Result<HashMap<String, u64>, StatsCollectorError> {
        let mut table_rows = HashMap::new();

        // 查询 pg_class 获取表行数估计
        let query = r#"
            SELECT 
                c.relname AS table_name,
                c.reltuples::bigint AS row_estimate
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'  -- 普通表
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY c.relname
        "#;

        let result = client.select(query, None, None);
        match result {
            Ok(rows) => {
                for row in rows.iter() {
                    let table_name: &str = row.get_by_name("table_name")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?
                        .unwrap_or("unknown");

                    let row_count: i64 = row.get_by_name("row_estimate")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?
                        .unwrap_or(0);

                    table_rows.insert(table_name.to_string(), row_count.max(0) as u64);
                }
            }
            Err(e) => {
                return Err(StatsCollectorError::DatabaseError(e.to_string()));
            }
        }

        Ok(table_rows)
    }

    /// 采集列级统计信息
    #[cfg(feature = "pgrx")]
    fn collect_column_stats(
        &self,
        client: &mut pgrx::spi::SpiClient,
        table_name: &str,
    ) -> Result<HashMap<String, ColumnStatistics>, StatsCollectorError> {
        let mut col_stats = HashMap::new();

        // 查询 pg_stats 获取列统计
        let query = format!(
            r#"
                SELECT 
                    attname AS column_name,
                    null_frac,
                    n_distinct,
                    most_common_vals::text,
                    most_common_freqs::text,
                    histogram_bounds::text
                FROM pg_stats
                WHERE tablename = '{}'
                  AND schemaname = current_schema()
            "#,
            table_name
        );

        let result = client.select(&query, None, None);
        match result {
            Ok(rows) => {
                for row in rows.iter() {
                    let col_name: &str = row.get_by_name("column_name")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?
                        .unwrap_or("unknown");

                    let null_frac: f64 = row.get_by_name("null_frac")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?
                        .unwrap_or(0.0);

                    let n_distinct: f64 = row.get_by_name("n_distinct")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?
                        .unwrap_or(0.0);

                    let most_common_vals: Option<&str> = row.get_by_name("most_common_vals")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?;

                    let most_common_freqs: Option<&str> = row.get_by_name("most_common_freqs")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?;

                    let histogram_bounds: Option<&str> = row.get_by_name("histogram_bounds")
                        .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?;

                    let mut col_stat = ColumnStatistics {
                        null_fraction: null_frac,
                        distinct_values: n_distinct.abs() as u64,
                        histogram: None,
                        most_common_values: Vec::new(),
                    };

                    // 解析最常用值 (MCV)
                    if let (Some(vals), Some(freqs)) = (most_common_vals, most_common_freqs) {
                        col_stat.most_common_values = self.parse_mcv(vals, freqs);
                    }

                    // 解析直方图边界
                    if let Some(bounds) = histogram_bounds {
                        col_stat.histogram = self.parse_histogram(bounds);
                    }

                    col_stats.insert(col_name.to_string(), col_stat);
                }
            }
            Err(e) => {
                // pg_stats 可能不包含此表的统计
                return Err(StatsCollectorError::DatabaseError(format!(
                    "Failed to query pg_stats for {}: {}",
                    table_name, e
                )));
            }
        }

        Ok(col_stats)
    }

    /// 解析最常用值 (Most Common Values)
    ///
    /// PostgreSQL 格式: `{val1,val2,val3}`
    fn parse_mcv(&self, values: &str, freqs: &str) -> Vec<(String, f64)> {
        let mut mcv_list = Vec::new();

        // 解析值列表
        let vals = self.parse_pg_array(values);

        // 解析频率列表
        let frequencies: Vec<f64> = self.parse_pg_array(freqs)
            .iter()
            .filter_map(|s| s.parse().ok())
            .collect();

        // 配对
        for (i, val) in vals.iter().enumerate() {
            let freq = frequencies.get(i).copied().unwrap_or(0.0);
            mcv_list.push((val.clone(), freq));
        }

        mcv_list
    }

    /// 解析 PostgreSQL 数组格式
    ///
    /// 格式: `{item1,item2,item3}`
    fn parse_pg_array(&self, array_str: &str) -> Vec<String> {
        let trimmed = array_str.trim();
        if !trimmed.starts_with('{') || !trimmed.ends_with('}') {
            return Vec::new();
        }

        let inner = &trimmed[1..trimmed.len()-1];
        if inner.is_empty() {
            return Vec::new();
        }

        inner
            .split(',')
            .map(|s| {
                let s = s.trim();
                // 去除引号
                if (s.starts_with('"') && s.ends_with('"')) ||
                   (s.starts_with('\'') && s.ends_with('\'')) {
                    s[1..s.len()-1].to_string()
                } else {
                    s.to_string()
                }
            })
            .collect()
    }

    /// 解析直方图边界
    ///
    /// PostgreSQL 格式: `{bound1,bound2,...}`
    fn parse_histogram(&self, bounds_str: &str) -> Option<Histogram> {
        let boundaries = self.parse_pg_array(bounds_str);
        if boundaries.is_empty() {
            return None;
        }

        Some(Histogram { boundaries })
    }
}

impl Default for PgStatsCollector {
    fn default() -> Self {
        Self::new()
    }
}

/// 统计信息刷新器
///
/// 提供刷新统计信息的功能。
pub struct StatsRefresher;

impl StatsRefresher {
    /// 刷新指定表的统计信息
    ///
    /// 执行 PostgreSQL 的 ANALYZE 命令更新统计。
    #[cfg(feature = "pgrx")]
    pub fn refresh_table_stats(
        client: &mut pgrx::spi::SpiClient,
        table_name: &str,
    ) -> Result<(), StatsCollectorError> {
        let query = format!("ANALYZE {}", table_name);

        client.select(&query, None, None)
            .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?;

        Ok(())
    }

    /// 刷新所有表的统计信息
    #[cfg(feature = "pgrx")]
    pub fn refresh_all_stats(
        client: &mut pgrx::spi::SpiClient,
    ) -> Result<(), StatsCollectorError> {
        client.select("ANALYZE", None, None)
            .map_err(|e| StatsCollectorError::DatabaseError(e.to_string()))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_pg_array() {
        let collector = PgStatsCollector::new();

        // 测试字符串数组
        let result = collector.parse_pg_array("{a,b,c}");
        assert_eq!(result, vec!["a", "b", "c"]);

        // 测试带引号的字符串
        let result = collector.parse_pg_array(r#"{"hello world","test"}"#);
        assert_eq!(result, vec!["hello world", "test"]);

        // 测试空数组
        let result = collector.parse_pg_array("{}");
        assert!(result.is_empty());
    }

    #[test]
    fn test_parse_mcv() {
        let collector = PgStatsCollector::new();

        let values = "{A,B,C}";
        let freqs = "{0.5,0.3,0.2}";

        let result = collector.parse_mcv(values, freqs);

        assert_eq!(result.len(), 3);
        assert_eq!(result[0], ("A".to_string(), 0.5));
        assert_eq!(result[1], ("B".to_string(), 0.3));
        assert_eq!(result[2], ("C".to_string(), 0.2));
    }
}
