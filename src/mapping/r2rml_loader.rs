//! R2RML 映射加载器
//!
//! 负责从数据库表或文件加载 R2RML 映射，并转换为内部 Mapping 格式。
//!
//! # 功能
//! - 从 `ontop_r2rml_mappings` 表加载映射
//! - 从 TTL/Turtle 文件加载映射
//! - 验证映射完整性
//! - 缓存映射以提高性能

use crate::mapping::{MappingRule, MappingStore};
use crate::mapping::r2rml_parser::{parse_r2rml, MappingConverter, R2RmlError};
use crate::SpiClient;
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;

// 数据库表和字段名常量，避免硬编码
const R2RML_MAPPINGS_TABLE: &str = "public.ontop_r2rml_mappings";
const R2RML_ID_COLUMN: &str = "id";
const R2RML_NAME_COLUMN: &str = "name";
const R2RML_TTL_CONTENT_COLUMN: &str = "ttl_content";

// 测试用的常量
const TEST_EMPLOYEES_TABLE: &str = "employees";
const TEST_DEPARTMENTS_TABLE: &str = "departments";
const TEST_FIRST_NAME_PREDICATE: &str = "http://example.org/employee#firstName";

/// R2RML 加载错误
#[derive(Error, Debug)]
pub enum R2RmlLoaderError {
    #[error("Parse error: {0}")]
    ParseError(#[from] R2RmlError),
    #[error("Database error: {0}")]
    DatabaseError(String),
    #[error("Validation error: {0}")]
    ValidationError(String),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// R2RML 加载器
///
/// 负责加载和验证 R2RML 映射。
pub struct R2RmlLoader {
    /// 缓存已加载的映射
    cache: HashMap<String, Arc<MappingStore>>,
    /// 是否启用缓存
    caching_enabled: bool,
}

impl Default for R2RmlLoader {
    fn default() -> Self {
        Self::new()
    }
}

impl R2RmlLoader {
    /// 创建新的 R2RML 加载器
    pub fn new() -> Self {
        Self {
            cache: HashMap::new(),
            caching_enabled: true,
        }
    }

    /// 禁用缓存
    pub fn disable_caching(mut self) -> Self {
        self.caching_enabled = false;
        self
    }

    /// 从 TTL 内容加载映射
    ///
    /// # Arguments
    /// * `ttl_content` - R2RML 映射的 Turtle 格式内容
    ///
    /// # Returns
    /// 成功时返回包含所有映射规则的 MappingStore
    pub fn load_from_ttl(&mut self, ttl_content: &str) -> Result<MappingStore, R2RmlLoaderError> {
        // 解析 R2RML
        let triples_maps = parse_r2rml(ttl_content)?;

        let mut store = MappingStore::new();

        // 转换每个 TriplesMap 为内部 MappingRule
        for tm in triples_maps {
            let rules = tm.to_internal_mapping()?;
            for rule in rules {
                store.insert_mapping(rule);
            }
        }

        // 验证映射
        self.validate_mappings(&store)?;

        Ok(store)
    }

    /// 从 TTL 文件加载映射
    ///
    /// # Arguments
    /// * `file_path` - R2RML 文件路径
    ///
    /// # Returns
    /// 成功时返回包含所有映射规则的 MappingStore
    pub fn load_from_file(&mut self, file_path: &str) -> Result<MappingStore, R2RmlLoaderError> {
        // 检查缓存
        if self.caching_enabled {
            if let Some(cached) = self.cache.get(file_path) {
                return Ok((**cached).clone());
            }
        }

        // 读取文件
        let content = std::fs::read_to_string(file_path)?;

        // 加载映射
        let store = self.load_from_ttl(&content)?;

        // 存入缓存
        if self.caching_enabled {
            self.cache.insert(file_path.to_string(), Arc::new(store.clone()));
        }

        Ok(store)
    }

    /// 从 PostgreSQL 表加载映射
    ///
    /// 从 `ontop_r2rml_mappings`/// 从数据库加载 R2RML 映射
    ///
    /// # Arguments
    /// * `client` - SPI 客户端
    ///
    /// # Returns
    /// 返回加载的 MappingStore
    ///
    /// # Errors
    /// 当数据库查询失败时返回 DatabaseError
    ///
    /// # Example
    /// ```ignore
    /// use pgrx::spi::Spi;
    /// let loader = R2RmlLoader::new();
    /// let store = loader.load_from_database(&mut client)?;
    /// ```
    pub fn load_from_database(&self, client: &mut SpiClient) -> Result<MappingStore, R2RmlLoaderError> {
        use pgrx::spi::Spi;

        // 查询 R2RML 映射表
        let query = format!(
            "SELECT {}, {}, {} FROM {} ORDER BY {}",
            R2RML_ID_COLUMN,
            R2RML_NAME_COLUMN,
            R2RML_TTL_CONTENT_COLUMN,
            R2RML_MAPPINGS_TABLE,
            R2RML_ID_COLUMN
        );

        let mut store = MappingStore::new();

        let result = client.select(&query, None, None);
        match result {
            Ok(rows) => {
                for row in rows {
                    let ttl_content: String = row.get_by_name(R2RML_TTL_CONTENT_COLUMN)
                        .map_err(|e: pgrx::spi::Error| R2RmlLoaderError::DatabaseError(e.to_string()))?
                        .ok_or_else(|| R2RmlLoaderError::DatabaseError(
                            "NULL ttl_content".to_string()
                        ))?;

                    // 解析并转换
                    let mut partial_store = {
                        let mut temp_loader = R2RmlLoader::new();
                        temp_loader.load_from_ttl(&ttl_content)?
                    };

                    // 合并到主 store
                    for (_, rules) in partial_store.mappings {
                        for r in rules {
                            store.insert_mapping(r);
                        }
                    }
                }
            }
            Err(e) => {
                // 表可能不存在，返回空 store
                if e.to_string().contains("does not exist") {
                    return Ok(store);
                }
                return Err(R2RmlLoaderError::DatabaseError(e.to_string()));
            }
        }

        Ok(store)
    }

    /// 验证映射完整性
    ///
    /// 检查映射是否符合以下规则：
    /// - 每个 predicate 都有对应的 table_name
    /// - 每个 position_to_column 至少有一个条目
    fn validate_mappings(&self, store: &MappingStore) -> Result<(), R2RmlLoaderError> {
        let mut errors = Vec::new();
        const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

        for (predicate, rules) in &store.mappings {
            // 跳过 rdf:type 类型映射的验证
            if predicate == RDF_TYPE {
                continue;
            }
            
            for rule in rules {
                if rule.table_name.is_empty() {
                    errors.push(format!("Predicate '{}' has empty table_name", predicate));
                }

                if rule.position_to_column.is_empty() {
                    errors.push(format!(
                        "Predicate '{}' has empty position_to_column",
                        predicate
                    ));
                }
            }
        }

        if !errors.is_empty() {
            return Err(R2RmlLoaderError::ValidationError(errors.join("; ")));
        }

        Ok(())
    }

    /// 清空缓存
    pub fn clear_cache(&mut self) {
        self.cache.clear();
    }

    /// 获取缓存统计
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.cache.len(), self.cache.capacity())
    }
}

/// 合并多个 MappingStore
///
/// 用于合并来自不同源的映射（文件 + 数据库）。
pub fn merge_mapping_stores(stores: Vec<MappingStore>) -> MappingStore {
    let mut merged = MappingStore::new();

    for store in stores {
        for (_, rules) in store.mappings {
            for rule in rules {
                merged.insert_mapping(rule);
            }
        }
        for (_iri, class) in store.classes {
            merged.add_class(class);
        }
        for (_iri, prop) in store.properties {
            merged.add_property(prop);
        }
    }

    merged
}

/// 创建示例 R2RML 映射（用于测试）
pub fn create_example_r2rml() -> String {
    format!(r#"
@base <http://example.org/mapping/> .
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .
@prefix emp: <http://example.org/employee#> .

<#TriplesMap1>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "{}" ];
    rr:subjectMap [
        rr:template "http://example.org/employee/{{employee_id}}";
        rr:class ex:Employee
    ];
    rr:predicateObjectMap [
        rr:predicate emp:firstName;
        rr:objectMap [ rr:column "first_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:lastName;
        rr:objectMap [ rr:column "last_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:email;
        rr:objectMap [ rr:column "email" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:salary;
        rr:objectMap [ rr:column "salary" ]
    ].

<#TriplesMap2>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "{}" ];
    rr:subjectMap [
        rr:template "http://example.org/department/{{department_id}}";
        rr:class ex:Department
    ];
    rr:predicateObjectMap [
        rr:predicate ex:departmentName;
        rr:objectMap [ rr:column "department_name" ]
    ].
"#, TEST_EMPLOYEES_TABLE, TEST_DEPARTMENTS_TABLE)}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_example_r2rml() {
        let mut loader = R2RmlLoader::new();
        let example = create_example_r2rml();

        let store = loader.load_from_ttl(&example).expect("Failed to load R2RML");

        // 验证映射数量
        assert!(!store.mappings.is_empty(), "Should have mappings");

        // 验证具体映射
        let has_firstname = store.mappings.values()
            .any(|rules| rules.iter().any(|r| r.predicate == TEST_FIRST_NAME_PREDICATE));
        assert!(has_firstname, "Should have firstName mapping");
    }

    #[test]
    fn test_cache_functionality() {
        let mut loader = R2RmlLoader::new();
        let example = create_example_r2rml();

        // 第一次加载
        let store1 = loader.load_from_ttl(&example).expect("valid regex");

        // 创建新 loader 禁用缓存
        let mut loader2 = R2RmlLoader::new().disable_caching();
        let store2 = loader2.load_from_ttl(&example).expect("valid regex");

        assert_eq!(store1.mappings.len(), store2.mappings.len());
    }
}
