use serde::{Serialize, Deserialize};

pub mod statistics;

pub use statistics::*;

/// Metadata about a physical PostgreSQL table.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct TableMetadata {
    pub table_name: String,
    pub columns: Vec<String>,
    pub primary_keys: Vec<String>,
    pub foreign_keys: Vec<ForeignKey>,
    pub unique_constraints: Vec<UniqueConstraint>,
    pub check_constraints: Vec<CheckConstraint>,
    pub not_null_columns: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForeignKey {
    pub local_columns: Vec<String>,
    pub target_table: String,
    pub target_columns: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UniqueConstraint {
    pub columns: Vec<String>,
    pub name: Option<String>, // 约束名称
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckConstraint {
    pub name: String,
    pub condition: String, // CHECK 条件表达式
}

impl TableMetadata {
    /// 检查列是否参与唯一约束（包括主键）
    pub fn is_unique_column(&self, column: &str) -> bool {
        // 检查主键
        if self.primary_keys.contains(&column.to_string()) {
            return true;
        }
        
        // 检查唯一约束
        for unique in &self.unique_constraints {
            if unique.columns.contains(&column.to_string()) {
                return true;
            }
        }
        
        false
    }
    
    /// 检查列是否可以为空
    pub fn is_nullable(&self, column: &str) -> bool {
        !self.not_null_columns.contains(&column.to_string())
    }
    
    /// 获取列的外键关系（如果存在）
    pub fn get_foreign_key_for_column(&self, column: &str) -> Option<&ForeignKey> {
        self.foreign_keys.iter().find(|fk| fk.local_columns.contains(&column.to_string()))
    }
    
    /// 检查是否存在指向指定表的外键
    pub fn has_foreign_key_to(&self, target_table: &str) -> bool {
        self.foreign_keys.iter().any(|fk| fk.target_table == target_table)
    }
}
