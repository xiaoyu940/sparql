use serde::{Serialize, Deserialize};
use std::collections::HashMap;

/// 表级别的统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableStatistics {
    pub table_name: String,
    pub row_count: Option<i64>,           // 表中的行数
    pub avg_row_size: Option<f64>,        // 平均行大小（字节）
    pub page_count: Option<i64>,          // 页面数量
    pub last_analyzed: Option<String>,    // 最后分析时间
    pub column_stats: HashMap<String, ColumnStatistics>, // 列统计信息
}

/// 列级别的统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnStatistics {
    pub column_name: String,
    pub data_type: String,                // 数据类型
    pub null_fraction: Option<f64>,       // NULL 值的比例 (0.0-1.0)
    pub distinct_count: Option<i64>,      // 唯一值数量
    pub min_value: Option<String>,        // 最小值
    pub max_value: Option<String>,        // 最大值
    pub histogram: Option<Histogram>,     // 直方图
    pub most_common_vals: Vec<MostCommonValue>, // 最常见的值
}

/// 直方图信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Histogram {
    pub bounds: Vec<String>,             // 边界值
    pub frequencies: Vec<i64>,            // 频率
}

/// 最常见的值及其频率
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MostCommonValue {
    pub value: String,
    pub frequency: i64,
}

impl TableStatistics {
    pub fn new(table_name: String) -> Self {
        Self {
            table_name,
            row_count: None,
            avg_row_size: None,
            page_count: None,
            last_analyzed: None,
            column_stats: HashMap::new(),
        }
    }
    
    /// 估算查询的选择性
    pub fn estimate_selectivity(&self, column: &str, operator: &str, value: &str) -> f64 {
        if let Some(col_stats) = self.column_stats.get(column) {
            match operator {
                "=" => {
                    // 等值查询的选择性
                    if let Some(distinct_count) = col_stats.distinct_count {
                        if let Some(row_count) = self.row_count {
                            if distinct_count > 0 && row_count > 0 {
                                return 1.0 / distinct_count as f64;
                            }
                        }
                    }
                    // 默认选择性
                    0.01
                },
                ">" | "<" | ">=" | "<=" => {
                    // 范围查询的选择性
                    if let (Some(_min_val), Some(_max_val)) = (&col_stats.min_value, &col_stats.max_value) {
                        // 简化估算：假设均匀分布
                        0.33
                    } else {
                        0.33
                    }
                },
                "LIKE" => {
                    // LIKE 查询的选择性（基于前缀匹配）
                    if value.ends_with('%') {
                        0.1 // 前缀匹配
                    } else if value.starts_with('%') && value.ends_with('%') {
                        0.3 // 包含匹配
                    } else {
                        0.01 // 精确匹配
                    }
                },
                _ => 0.1, // 默认选择性
            }
        } else {
            0.1 // 没有统计信息时的默认选择性
        }
    }
    
    /// 估算 JOIN 的选择性
    pub fn estimate_join_selectivity(&self, other_table: &TableStatistics, join_column: &str) -> f64 {
        // 简化的 JOIN 选择性估算
        if let (Some(self_distinct), Some(other_distinct)) = (
            self.column_stats.get(join_column).and_then(|s| s.distinct_count),
            other_table.column_stats.get(join_column).and_then(|s| s.distinct_count)
        ) {
            if let (Some(_self_rows), Some(_other_rows)) = (self.row_count, other_table.row_count) {
                if self_distinct > 0 && other_distinct > 0 {
                    // 基于唯一值数量的估算
                    let selectivity = 1.0 / (self_distinct.max(other_distinct) as f64);
                    return selectivity.min(1.0);
                }
            }
        }
        0.1 // 默认 JOIN 选择性
    }
    
    /// 检查统计信息是否过期
    pub fn is_expired(&self, _max_age_days: i64) -> bool {
        if let Some(_last_analyzed) = &self.last_analyzed {
            // 简化实现：假设时间格式为 "YYYY-MM-DD HH:MM:SS"
            // 实际实现应该解析时间并计算差值
            false // 暂时返回 false，表示未过期
        } else {
            true // 没有分析时间，认为过期
        }
    }
    
    /// 获取列的基数（唯一值数量）
    pub fn get_column_cardinality(&self, column: &str) -> Option<i64> {
        self.column_stats.get(column).and_then(|s| s.distinct_count)
    }
    
    /// 检查列是否具有高选择性
    pub fn is_high_selectivity_column(&self, column: &str, threshold: f64) -> bool {
        if let Some(col_stats) = self.column_stats.get(column) {
            if let (Some(distinct_count), Some(row_count)) = (col_stats.distinct_count, self.row_count) {
                if row_count > 0 {
                    let selectivity = distinct_count as f64 / row_count as f64;
                    return selectivity > threshold;
                }
            }
        }
        false
    }
}

/// 统计信息管理器
#[derive(Debug, Clone)]
pub struct StatisticsManager {
    pub table_stats: HashMap<String, TableStatistics>,
    pub default_selectivity: f64,
    pub max_age_days: i64,
}

impl StatisticsManager {
    pub fn new() -> Self {
        Self {
            table_stats: HashMap::new(),
            default_selectivity: 0.1,
            max_age_days: 7, // 默认7天后过期
        }
    }
    
    /// 添加表统计信息
    pub fn add_table_statistics(&mut self, stats: TableStatistics) {
        self.table_stats.insert(stats.table_name.clone(), stats);
    }
    
    /// 获取表统计信息
    pub fn get_table_statistics(&self, table_name: &str) -> Option<&TableStatistics> {
        self.table_stats.get(table_name)
    }
    
    /// 估算查询成本
    pub fn estimate_query_cost(&self, tables: &[String], joins: &[(String, String, String)]) -> f64 {
        let mut total_cost = 0.0;
        
        // 基础表扫描成本
        for table_name in tables {
            if let Some(stats) = self.get_table_statistics(table_name) {
                if let Some(row_count) = stats.row_count {
                    // 成本 = 行数 * log(页数)
                    let page_cost = if let Some(page_count) = stats.page_count {
                        (page_count as f64).ln()
                    } else {
                        (row_count as f64 / 100.0).ln() // 假设每页100行
                    };
                    total_cost += row_count as f64 * page_cost;
                } else {
                    // 默认成本
                    total_cost += 1000.0;
                }
            } else {
                total_cost += 1000.0; // 默认表扫描成本
            }
        }
        
        // JOIN 成本
        for (left_table, right_table, join_column) in joins {
            if let (Some(left_stats), Some(right_stats)) = (
                self.get_table_statistics(left_table),
                self.get_table_statistics(right_table)
            ) {
                let join_selectivity = left_stats.estimate_join_selectivity(right_stats, join_column);
                let join_cost = left_stats.row_count.unwrap_or(1000) as f64 * 
                               right_stats.row_count.unwrap_or(1000) as f64 * 
                               join_selectivity;
                total_cost += join_cost;
            } else {
                total_cost += 5000.0; // 默认 JOIN 成本
            }
        }
        
        total_cost
    }
    
    /// 选择最佳的 JOIN 顺序
    pub fn choose_join_order(&self, tables: &[String], _join_conditions: &[(String, String, String)]) -> Vec<String> {
        if tables.len() <= 2 {
            return tables.to_vec();
        }
        
        // 简化实现：基于行数选择 JOIN 顺序
        let mut sorted_tables: Vec<_> = tables.iter()
            .map(|table| {
                let row_count = self.get_table_statistics(table)
                    .and_then(|s| s.row_count)
                    .unwrap_or(1000);
                (table.clone(), row_count)
            })
            .collect();
        
        // 按行数排序，小表优先
        sorted_tables.sort_by_key(|(_, count)| *count);
        
        sorted_tables.into_iter().map(|(table, _)| table).collect()
    }
    
    /// 检查是否应该使用索引
    pub fn should_use_index(&self, table: &str, column: &str, operator: &str, _value: &str) -> bool {
        if let Some(stats) = self.get_table_statistics(table) {
            // 高选择性列适合使用索引
            if stats.is_high_selectivity_column(column, 0.1) {
                return true;
            }
            
            // 等值查询通常适合使用索引
            if operator == "=" {
                return true;
            }
            
            // 范围查询在有统计信息时可能适合使用索引
            if (operator == ">" || operator == "<" || operator == ">=" || operator == "<=") &&
               stats.column_stats.get(column).is_some() {
                return true;
            }
        }
        
        false
    }
}

impl Default for StatisticsManager {
    fn default() -> Self {
        Self::new()
    }
}
