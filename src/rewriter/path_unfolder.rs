//! Property Path 展开模块 (Sprint 9 P0)
//!
//! 将 LogicNode::Path 展开为 Join/Union/ExtensionalData 的组合
//! 在OBDA架构下，路径被展开为关系表之间的JOIN链

use std::collections::HashMap;
use std::sync::Arc;

use crate::ir::expr::{Expr, Term};
use crate::ir::node::{JoinType, LogicNode, PropertyPath};
use crate::mapping::MappingStore;
use crate::metadata::TableMetadata;

/// 路径展开错误类型
#[derive(Debug, thiserror::Error)]
pub enum PathUnfoldError {
    #[error("Mapping not found for predicate: {0}")]
    MappingNotFound(String),
    
    #[error("Empty property path sequence")]
    EmptyPath,
    
    #[error("Unsupported path type: {0}")]
    UnsupportedPath(String),
    
    #[error("Failed to resolve FK relationship between {from_table} and {to_table}")]
    ForeignKeyResolutionFailed {
        from_table: String,
        to_table: String,
    },
    
    #[error("Path nesting too deep: {depth}")]
    PathTooDeep { depth: usize },
}

/// 路径展开结果
#[derive(Debug, Clone)]
pub struct PathMapping {
    /// 谓词URI
    pub predicate: String,
    /// 表名
    pub table_name: String,
    /// subject列（映射到RDF subject）
    pub subject_col: String,
    /// object列（映射到RDF object）
    pub object_col: String,
    /// 表别名
    pub alias: String,
}

/// 路径展开器
/// 
/// 负责将 Property Path 展开为关系代数表达式
pub struct PathUnfolder<'a> {
    mapping_store: &'a MappingStore,
    metadata_cache: &'a HashMap<String, Arc<TableMetadata>>,
    /// 路径ID计数器，用于生成唯一别名
    path_id_counter: usize,
    /// 别名计数器，用于同一表内的多个实例
    alias_counter: usize,
    /// 最大递归深度，防止无限递归
    max_depth: usize,
}

impl<'a> PathUnfolder<'a> {
    /// 创建新的 PathUnfolder 实例
    pub fn new(
        mapping_store: &'a MappingStore,
        metadata_cache: &'a HashMap<String, Arc<TableMetadata>>,
    ) -> Self {
        Self {
            mapping_store,
            metadata_cache,
            path_id_counter: 0,
            alias_counter: 0,
            max_depth: 10,
        }
    }
    
    /// 生成唯一的中间变量名
    fn generate_intermediate_var(&mut self, step_idx: usize) -> Term {
        Term::Variable(format!("__path_var_{}_{}", self.path_id_counter, step_idx))
    }
    
    /// 生成表别名
    fn generate_alias(&mut self, table_name: &str) -> String {
        let alias = format!("{}_path{}_{}", table_name, self.alias_counter, self.path_id_counter);
        self.alias_counter += 1;
        alias
    }
    
    /// 从 MappingStore 解析谓词映射
    /// 
    /// 返回表名、subject列、object列
    fn resolve_predicate_mapping(&self, predicate: &str) -> Result<(String, String, String), PathUnfoldError> {
        let clean_predicate = predicate.trim_start_matches('<').trim_end_matches('>');
        let rules = self.mapping_store
            .mappings
            .get(clean_predicate)
            .ok_or_else(|| PathUnfoldError::MappingNotFound(predicate.to_string()))?;
        
        // 使用第一个映射规则
        let rule = &rules[0];
        
        // 从 subject_template 提取 subject 列
        let subject_col = if let Some(template) = &rule.subject_template {
            Self::extract_column_from_template(template)
                .unwrap_or_else(|| "id".to_string())
        } else {
            "id".to_string()
        };
        
        // 从 position_to_column 获取 object 列
        // 在二元谓词中，位置1对应object
        let object_col = rule.position_to_column
            .get(&1)
            .cloned()
            .unwrap_or_else(|| "id".to_string());
        
        Ok((rule.table_name.clone(), subject_col, object_col))
    }
    
    /// 从模板字符串提取列名，如 "http://example.org/emp/{employee_id}" -> "employee_id"
    fn extract_column_from_template(template: &str) -> Option<String> {
        let start = template.find('{')?;
        let end = template.find('}')?;
        if start < end {
            Some(template[start + 1..end].to_string())
        } else {
            None
        }
    }
    
    fn create_extensional_data(
        &self,
        table_name: &str,
        _alias: &str,
        subject_var: &Term,
        object_var: &Term,
        subject_col: &str,
        object_col: &str,
    ) -> Result<LogicNode, PathUnfoldError> {
        let metadata = self.metadata_cache
            .get(table_name)
            .ok_or_else(|| PathUnfoldError::MappingNotFound(format!("Metadata for table: {}", table_name)))?;
        
        let mut column_mapping = HashMap::new();
        let mut filters = Vec::new();

        // 映射 subject
        match subject_var {
            Term::Variable(var) => {
                column_mapping.insert(var.clone(), subject_col.to_string());
            }
            _ => {
                // 如果是常量，使用内部变量并添加过滤
                let internal_subj = format!("__subj_{}", subject_col);
                column_mapping.insert(internal_subj.clone(), subject_col.to_string());
                filters.push(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(internal_subj))),
                    op: crate::ir::expr::ComparisonOp::Eq,
                    right: Box::new(Expr::Term(subject_var.clone())),
                });
            }
        }
        
        // 映射 object
        match object_var {
            Term::Variable(var) => {
                column_mapping.insert(var.clone(), object_col.to_string());
            }
            _ => {
                let internal_obj = format!("__obj_{}", object_col);
                column_mapping.insert(internal_obj.clone(), object_col.to_string());
                filters.push(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(internal_obj))),
                    op: crate::ir::expr::ComparisonOp::Eq,
                    right: Box::new(Expr::Term(object_var.clone())),
                });
            }
        }
        
        let scan = LogicNode::ExtensionalData {
            table_name: table_name.to_string(),
            column_mapping,
            metadata: Arc::clone(metadata),
        };

        if filters.is_empty() {
            Ok(scan)
        } else {
            let combined = if filters.len() > 1 {
                Expr::Logical {
                    op: crate::ir::expr::LogicalOp::And,
                    args: filters,
                }
            } else {
                filters[0].clone()
            };
            Ok(LogicNode::Filter {
                expression: combined,
                child: Box::new(scan),
            })
        }
    }
    
    /// 展开 Path 节点为关系代数表达式
    /// 
    /// 这是主入口函数
    pub fn unfold_path(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        match path {
            PropertyPath::Predicate(pred) => {
                self.unfold_predicate(subject, pred, object)
            }
            PropertyPath::Inverse(inner) => {
                self.unfold_inverse(subject, inner, object)
            }
            PropertyPath::Sequence(seq) => {
                self.unfold_sequence(subject, seq, object)
            }
            PropertyPath::Alternative(alts) => {
                self.unfold_alternative(subject, alts, object)
            }
            PropertyPath::Star(inner) => {
                self.unfold_star(subject, inner, object)
            }
            PropertyPath::Plus(inner) => {
                self.unfold_plus(subject, inner, object)
            }
            PropertyPath::Optional(inner) => {
                self.unfold_optional(subject, inner, object)
            }
            PropertyPath::Negated(_) => {
                Err(PathUnfoldError::UnsupportedPath(format!(
                    "Negated paths (!) not yet implemented"
                )))
            }
        }
    }
    
    /// 展开简单谓词路径
    /// 
    /// 直接映射为 ExtensionalData 节点
    fn unfold_predicate(
        &mut self,
        subject: &Term,
        predicate: &str,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        let (table_name, subject_col, object_col) = self.resolve_predicate_mapping(predicate)?;
        let alias = self.generate_alias(&table_name);
        
        self.create_extensional_data(
            &table_name,
            &alias,
            subject,
            object,
            &subject_col,
            &object_col,
        )
    }
    
    /// 展开反向路径
    /// 
    /// 反向路径 ^p 等价于交换 subject 和 object 的正向路径
    fn unfold_inverse(
        &mut self,
        subject: &Term,
        inner: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        // 交换 subject 和 object 后递归展开
        self.unfold_path(object, inner, subject)
    }
    
    /// 展开序列路径
    /// 
    /// 序列 p1/p2/.../pn 展开为 N 元 Join 链
    fn unfold_sequence(
        &mut self,
        subject: &Term,
        seq: &[PropertyPath],
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        if seq.is_empty() {
            return Err(PathUnfoldError::EmptyPath);
        }
        
        if seq.len() > self.max_depth {
            return Err(PathUnfoldError::PathTooDeep { depth: seq.len() });
        }
        
        // 保存当前路径ID，用于生成唯一中间变量
        let _path_id = self.path_id_counter;
        self.path_id_counter += 1;
        
        // 1. 展开第一个谓词，创建基础扫描
        let first_path = &seq[0];
        let first_var = self.generate_intermediate_var(0);
        let mut current_node = self.unfold_path(subject, first_path, &first_var)?;
        
        // 2. 依次展开后续谓词，创建 Join 链
        let mut last_var = first_var;
        
        for (idx, path) in seq[1..].iter().enumerate() {
            let is_last = idx == seq.len() - 2;
            let next_var = if is_last {
                // 最后一个路径使用原始 object
                object.clone()
            } else {
                self.generate_intermediate_var(idx + 1)
            };
            
            // 展开当前路径段
            let next_node = self.unfold_path(&last_var, path, &next_var)?;
            
            // 创建 Join 节点
            // 注意：JOIN条件通过列映射隐含，不需要显式条件
            current_node = LogicNode::Join {
                children: vec![current_node, next_node],
                condition: None,
                join_type: JoinType::Inner,
            };
            
            last_var = next_var;
        }
        
        Ok(current_node)
    }
    
    /// 展开选择路径
    /// 
    /// 选择 p1|p2|...|pn 展开为 Union 节点
    fn unfold_alternative(
        &mut self,
        subject: &Term,
        alts: &[PropertyPath],
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        if alts.is_empty() {
            return Err(PathUnfoldError::EmptyPath);
        }
        
        let mut branches = Vec::new();
        
        for path in alts {
            // 每个分支独立展开，使用新的路径ID
            let branch = self.unfold_path(subject, path, object)?;
            branches.push(branch);
        }
        
        Ok(LogicNode::Union(branches))
    }
    
    /// 展开可选路径 (P2)
    /// 
    /// ? 修饰符表示路径可出现0次或1次
    /// 实现为 LEFT JOIN 或 UNION
    fn unfold_optional(
        &mut self,
        subject: &Term,
        inner: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        // 1. 展开内部路径
        let inner_unfolded = self.unfold_path(subject, inner, object)?;
        
        // 2. 创建subject恒等映射作为备选（当路径无匹配时）
        // 使用 Union 实现可选语义: p? = p UNION (subject = subject)
        let identity_node = LogicNode::Construction {
            projected_vars: vec![match subject {
                Term::Variable(v) => v.clone(),
                _ => "__subj".to_string(),
            }],
            bindings: {
                let mut map = HashMap::new();
                if let Term::Variable(v) = subject {
                    map.insert(v.clone(), Expr::Term(subject.clone()));
                }
                map
            },
            child: Box::new(LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(subject.clone())),
                    op: crate::ir::expr::ComparisonOp::Eq,
                    right: Box::new(Expr::Term(subject.clone())),
                },
                child: Box::new(LogicNode::ExtensionalData {
                    table_name: "dual".to_string(),
                    column_mapping: HashMap::new(),
                    metadata: Arc::new(crate::metadata::TableMetadata::default()),
                }),
            }),
        };
        
        Ok(LogicNode::Union(vec![inner_unfolded, identity_node]))
    }
    
    /// 展开星号路径 (P2)
    /// 
    /// * 修饰符表示路径可出现0次或多次
    /// 需要在SQL生成阶段使用递归CTE，这里创建标记节点
    fn unfold_star(
        &mut self,
        subject: &Term,
        inner: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        // 先展开内部路径为子计划
        let inner_plan = self.unfold_path(subject, inner, object)?;
        
        // 创建递归路径标记节点，SQL生成器将据此生成递归CTE
        Ok(LogicNode::RecursivePath {
            base_path: Box::new(inner_plan.clone()),
            recursive_path: Box::new(inner_plan),
            subject: subject.clone(),
            object: object.clone(),
            min_depth: 0, // * 包含0长度路径
            max_depth: 10, // 限制递归深度
        })
    }
    
    /// 展开加号路径 (P2)
    /// 
    /// + 修饰符表示路径可出现1次或多次
    /// 与 * 类似但最小深度为1
    fn unfold_plus(
        &mut self,
        subject: &Term,
        inner: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, PathUnfoldError> {
        // 先展开内部路径为子计划
        let inner_plan = self.unfold_path(subject, inner, object)?;
        
        // 创建递归路径标记节点，最小深度为1
        Ok(LogicNode::RecursivePath {
            base_path: Box::new(inner_plan.clone()),
            recursive_path: Box::new(inner_plan),
            subject: subject.clone(),
            object: object.clone(),
            min_depth: 1, // + 要求至少1次出现
            max_depth: 10,
        })
    }
}

/// 公开接口：从 LogicNode::Path 展开
pub fn unfold_property_path(
    subject: &Term,
    path: &PropertyPath,
    object: &Term,
    mapping_store: &MappingStore,
    metadata_cache: &HashMap<String, Arc<TableMetadata>>,
) -> Result<LogicNode, PathUnfoldError> {
    let mut unfolder = PathUnfolder::new(mapping_store, metadata_cache);
    unfolder.unfold_path(subject, path, object)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ir::node::PropertyPath;
    use crate::mapping::{MappingRule, MappingStore, OntologyClass, OntologyProperty};
    use std::collections::HashMap;
    
    /// 创建测试用的 MappingStore
    fn create_test_mapping_store() -> MappingStore {
        let mut mappings = HashMap::new();
        
        // :manager 谓词映射 - employees表自连接
        let manager_rule = MappingRule {
            predicate: "http://example.org/manager".to_string(),
            table_name: "employees".to_string(),
            subject_template: Some("http://example.org/emp/{employee_id}".to_string()),
            object_constant: None,
            position_to_column: {
                let mut m = HashMap::new();
                m.insert(1, "manager_id".to_string()); // object列
                m
            },
        };
        mappings.insert("http://example.org/manager".to_string(), vec![manager_rule]);
        
        // :name 谓词映射
        let name_rule = MappingRule {
            predicate: "http://example.org/name".to_string(),
            table_name: "employees".to_string(),
            subject_template: Some("http://example.org/emp/{employee_id}".to_string()),
            object_constant: None,
            position_to_column: {
                let mut m = HashMap::new();
                m.insert(1, "name".to_string());
                m
            },
        };
        mappings.insert("http://example.org/name".to_string(), vec![name_rule]);
        
        // :email 谓词映射
        let email_rule = MappingRule {
            predicate: "http://example.org/email".to_string(),
            table_name: "employees".to_string(),
            subject_template: Some("http://example.org/emp/{employee_id}".to_string()),
            object_constant: None,
            position_to_column: {
                let mut m = HashMap::new();
                m.insert(1, "email".to_string());
                m
            },
        };
        mappings.insert("http://example.org/email".to_string(), vec![email_rule]);
        
        // :phone 谓词映射
        let phone_rule = MappingRule {
            predicate: "http://example.org/phone".to_string(),
            table_name: "employees".to_string(),
            subject_template: Some("http://example.org/emp/{employee_id}".to_string()),
            object_constant: None,
            position_to_column: {
                let mut m = HashMap::new();
                m.insert(1, "phone".to_string());
                m
            },
        };
        mappings.insert("http://example.org/phone".to_string(), vec![phone_rule]);
        
        MappingStore {
            classes: HashMap::new(),
            properties: HashMap::new(),
            mappings,
        }
    }
    
    /// 创建测试用的 TableMetadata
    fn create_test_metadata() -> HashMap<String, Arc<TableMetadata>> {
        let mut metadata = HashMap::new();
        
        let employees_meta = TableMetadata {
            table_name: "employees".to_string(),
            columns: vec!["employee_id".to_string(), "name".to_string(), "email".to_string(), "phone".to_string(), "manager_id".to_string()],
            primary_keys: vec!["employee_id".to_string()],
            foreign_keys: vec![],
            unique_constraints: vec![],
            check_constraints: vec![],
            not_null_columns: vec!["employee_id".to_string()],
        };
        metadata.insert("employees".to_string(), Arc::new(employees_meta));
        
        metadata
    }
    
    #[test]
    fn test_unfold_simple_predicate() {
        let mappings = create_test_mapping_store();
        let metadata = create_test_metadata();
        let mut unfolder = PathUnfolder::new(&mappings, &metadata);
        
        let subject = Term::Variable("emp".to_string());
        let object = Term::Variable("mgr".to_string());
        let path = PropertyPath::Predicate("http://example.org/manager".to_string());
        
        let result = unfolder.unfold_path(&subject, &path, &object);
        
        assert!(result.is_ok());
        match result.expect("unfold_path should succeed") {
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                assert_eq!(table_name, "employees");
                assert!(column_mapping.contains_key("emp")); // subject映射到employee_id
                assert!(column_mapping.contains_key("mgr")); // object映射到manager_id
            }
            _ => panic!("Expected ExtensionalData node"),
        }
    }
    
    #[test]
    fn test_unfold_inverse_path() {
        let mappings = create_test_mapping_store();
        let metadata = create_test_metadata();
        let mut unfolder = PathUnfolder::new(&mappings, &metadata);
        
        // ^:manager 即反向路径，应该交换subject/object
        let subject = Term::Variable("subordinate".to_string());
        let object = Term::Variable("manager".to_string());
        let path = PropertyPath::Inverse(Box::new(
            PropertyPath::Predicate("http://example.org/manager".to_string())
        ));
        
        let result = unfolder.unfold_path(&subject, &path, &object);
        
        assert!(result.is_ok());
        match result.expect("unfold_path should succeed") {
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                assert_eq!(table_name, "employees");
                // 反向路径交换后：
                // subject (subordinate) 应该映射到 manager_id (原object列)
                // object (manager) 应该映射到 employee_id (原subject列)
                assert!(column_mapping.contains_key("subordinate"));
                assert!(column_mapping.contains_key("manager"));
            }
            _ => panic!("Expected ExtensionalData node"),
        }
    }
    
    #[test]
    fn test_unfold_sequence_path() {
        let mappings = create_test_mapping_store();
        let metadata = create_test_metadata();
        let mut unfolder = PathUnfolder::new(&mappings, &metadata);
        
        // :manager/:name 序列路径
        let subject = Term::Variable("emp".to_string());
        let object = Term::Variable("mgrName".to_string());
        let path = PropertyPath::Sequence(vec![
            PropertyPath::Predicate("http://example.org/manager".to_string()),
            PropertyPath::Predicate("http://example.org/name".to_string()),
        ]);
        
        let result = unfolder.unfold_path(&subject, &path, &object);
        
        assert!(result.is_ok());
        match result.expect("unfold_path should succeed") {
            LogicNode::Join { children, join_type, .. } => {
                assert_eq!(children.len(), 2);
                assert!(matches!(join_type, JoinType::Inner));
                // 两个子节点都应该是ExtensionalData
                match &children[0] {
                    LogicNode::ExtensionalData { table_name, .. } => {
                        assert_eq!(table_name, "employees");
                    }
                    _ => panic!("Expected ExtensionalData as first child"),
                }
            }
            _ => panic!("Expected Join node"),
        }
    }
    
    #[test]
    fn test_unfold_alternative_path() {
        let mappings = create_test_mapping_store();
        let metadata = create_test_metadata();
        let mut unfolder = PathUnfolder::new(&mappings, &metadata);
        
        // :email|:phone 选择路径
        let subject = Term::Variable("emp".to_string());
        let object = Term::Variable("contact".to_string());
        let path = PropertyPath::Alternative(vec![
            PropertyPath::Predicate("http://example.org/email".to_string()),
            PropertyPath::Predicate("http://example.org/phone".to_string()),
        ]);
        
        let result = unfolder.unfold_path(&subject, &path, &object);
        
        assert!(result.is_ok());
        match result.expect("unfold_path should succeed") {
            LogicNode::Union(branches) => {
                assert_eq!(branches.len(), 2);
                // 两个分支都应该是ExtensionalData
                for branch in &branches {
                    match branch {
                        LogicNode::ExtensionalData { table_name, .. } => {
                            assert_eq!(table_name, "employees");
                        }
                        _ => panic!("Expected ExtensionalData in union branch"),
                    }
                }
            }
            _ => panic!("Expected Union node"),
        }
    }
    
    #[test]
    fn test_unfold_mapping_not_found() {
        let mappings = create_test_mapping_store();
        let metadata = create_test_metadata();
        let mut unfolder = PathUnfolder::new(&mappings, &metadata);
        
        // 不存在的谓词
        let subject = Term::Variable("x".to_string());
        let object = Term::Variable("y".to_string());
        let path = PropertyPath::Predicate("http://example.org/nonexistent".to_string());
        
        let result = unfolder.unfold_path(&subject, &path, &object);
        
        assert!(result.is_err());
        match result.unwrap_err() {
            PathUnfoldError::MappingNotFound(pred) => {
                assert_eq!(pred, "http://example.org/nonexistent");
            }
            _ => panic!("Expected MappingNotFound error"),
        }
    }
}
