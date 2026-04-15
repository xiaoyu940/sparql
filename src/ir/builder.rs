use std::collections::HashMap;
use std::sync::Arc;

use crate::error::OntopError;
use crate::ir::node::LogicNode;
use crate::mapping::MappingStore;
use crate::metadata::TableMetadata;
use crate::parser::{IRConverter, ParsedQuery};

/// IR 构建器
/// 
/// 负责将解析后的 SPARQL 查询转换为内部中间表示 (IR) 逻辑计划。
/// 支持通过映射配置解析主表，并构建查询的 IR 表示。
#[derive(Debug, Default)]
pub struct IRBuilder;

impl IRBuilder {
    /// 创建新的 IRBuilder 实例
    ///
    /// # Returns
    /// 返回默认配置的 IRBuilder
    pub fn new() -> Self { Self }

    /// 构建 IR 逻辑计划（无映射版本）
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `metadata_map` - 表元数据映射
    ///
    /// # Returns
    /// 返回构建的 LogicNode，或在缺少元数据时返回错误
    ///
    /// # Errors
    /// 当无法解析主表元数据时返回 `OntopError::MissingMetadata`
    pub fn build(
        &self,
        parsed: &ParsedQuery,
        metadata_map: &HashMap<String, Arc<TableMetadata>>,
    ) -> Result<LogicNode, OntopError> {
        self.build_with_mappings(parsed, metadata_map, None)
    }

    /// 构建 IR 逻辑计划（带映射配置）
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `metadata_map` - 表元数据映射
    /// * `mappings` - 可选的 RDF 映射配置
    ///
    /// # Returns
    /// 返回构建的 LogicNode，包含完整的查询逻辑计划
    ///
    /// # Errors
    /// 当无法解析主表元数据时返回 `OntopError::MissingMetadata`
    ///
    /// # Example
    /// ```ignore
    /// let builder = IRBuilder::new();
    /// let plan = builder.build_with_mappings(&parsed, &metadata, Some(&mappings))?;
    /// ```
    pub fn build_with_mappings(
        &self,
        parsed: &ParsedQuery,
        metadata_map: &HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Result<LogicNode, OntopError> {
        // 直接传递整个 metadata_map 给 IRConverter
        // IRConverter 会根据每个三元组的谓词查找对应的表
        Ok(IRConverter::convert_with_mappings(parsed, metadata_map, mappings))
    }

    /// 从查询中提取所有谓词 IRI
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    ///
    /// # Returns
    /// 返回谓词 IRI 字符串列表（过滤掉变量谓词）
    ///
    /// # Note
    /// 只提取不以 '?' 开头的谓词（即非变量谓词）
    fn extract_predicates(parsed: &ParsedQuery) -> Vec<String> {
        let mut predicates = Vec::new();
        
        // 从主模式提取
        for pattern in &parsed.main_patterns {
            if !pattern.predicate.starts_with('?') {
                let iri = pattern.predicate
                    .trim_start_matches('<')
                    .trim_end_matches('>')
                    .to_string();
                predicates.push(iri);
            }
        }
        
        predicates
    }

    /// 根据查询和映射解析主表元数据
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `mappings` - 可选的 RDF 映射配置
    /// * `metadata_map` - 表元数据映射
    ///
    /// # Returns
    /// 返回解析到的主表元数据 Arc 引用
    ///
    /// # Errors
    /// 当无法找到匹配的表元数据时返回 `OntopError::MissingMetadata`
    ///
    /// # Algorithm
    /// 1. 从查询中提取所有谓词 IRI
    /// 2. 尝试从映射配置中找到匹配的表名
    /// 3. 回退到 metadata_map 中的第一个表
    fn resolve_primary_table(
        parsed: &ParsedQuery,
        mappings: Option<&MappingStore>,
        metadata_map: &HashMap<String, Arc<TableMetadata>>,
    ) -> Result<Arc<TableMetadata>, OntopError> {
        let predicates = Self::extract_predicates(parsed);
        
        // 1. 尝试从映射配置找到表名
        if let Some(store) = mappings {
            for pred in &predicates {
                if let Some(rules) = store.mappings.get(pred) {
                    // 使用第一个规则
                    let rule = &rules[0];
                    let table_name = &rule.table_name;
                    if let Some(metadata) = metadata_map.get(table_name) {
                        return Ok(Arc::clone(metadata));
                    }
                }
            }
        }
        
        // 2. 回退：使用metadata_map中的第一个表
        if let Some((_name, metadata)) = metadata_map.iter().next() {
            return Ok(Arc::clone(metadata));
        }
        
        // 3. 错误：没有可用的表元数据
        Err(OntopError::MissingMetadata(
            "No table metadata available".to_string()
        ))
    }
}
