//! Statistics for Query Optimization (Cost Model)
//!
//! Stores table cardinalities, column distinct counts, null fractions, 
//! most common values, and equi-depth histograms.

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// Equi-depth histogram definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Histogram {
    /// Upper bounds for each bucket. Size of buckets is implicitly total / buckets.len()
    pub boundaries: Vec<String>,
}

/// Statistics for a single column
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnStatistics {
    pub null_fraction: f64,
    pub distinct_values: u64,
    pub histogram: Option<Histogram>,
    /// List of most common values and their frequency (fraction 0.0 to 1.0)
    pub most_common_values: Vec<(String, f64)>,
}

impl Default for ColumnStatistics {
    fn default() -> Self {
        Self {
            null_fraction: 0.0,
            distinct_values: 1,
            histogram: None,
            most_common_values: Vec::new(),
        }
    }
}

/// Statistics for a single physical table or view
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableStatistics {
    pub table_name: String,
    pub row_count: u64,
    pub column_stats: HashMap<String, ColumnStatistics>,
}

impl TableStatistics {
    pub fn new(table_name: &str, row_count: u64) -> Self {
        Self {
            table_name: table_name.to_string(),
            row_count,
            column_stats: HashMap::new(),
        }
    }
}

/// Catalog holding all loaded statistics
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Statistics {
    pub tables: HashMap<String, TableStatistics>,
}

impl Statistics {
    pub fn is_available(&self) -> bool {
        !self.tables.is_empty()
    }

    pub fn get_table_stats(&self, table: &str) -> Option<&TableStatistics> {
        self.tables.get(table)
    }

    pub fn insert_table_stats(&mut self, stats: TableStatistics) {
        self.tables.insert(stats.table_name.clone(), stats);
    }
}
