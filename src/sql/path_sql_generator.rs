use crate::ir::node::{PropertyPath, LogicNode};
use crate::ir::expr::Term;
use crate::sql::flat_generator::{FlatSQLGenerator, GenerationError};

/// 属性路径 SQL 生成器
/// 
/// 将属性路径转换为递归 CTE 查询
pub struct PropertyPathSQLGenerator;

impl PropertyPathSQLGenerator {
    /// 生成属性路径的 SQL
    /// 
    /// # Arguments
    /// * `subject` - 主题变量或常量
    /// * `path` - 属性路径
    /// * `object` - 对象变量或常量
    /// * `alias` - 表别名
    ///
    /// # Returns
    /// 生成的 SQL 子查询字符串
    pub fn generate(
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
        alias: &str,
    ) -> Result<String, GenerationError> {
        let mut generator = PathGenerator::new(alias);
        generator.generate_path_query(subject, path, object)
    }
}

/// 内部路径生成器
struct PathGenerator<'a> {
    alias: &'a str,
    cte_counter: usize,
}

impl<'a> PathGenerator<'a> {
    fn new(alias: &'a str) -> Self {
        Self {
            alias,
            cte_counter: 0,
        }
    }

    /// 生成完整的路径查询
    fn generate_path_query(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<String, GenerationError> {
        // 生成递归 CTE
        let cte_sql = self.generate_recursive_cte(subject, path, object)?;
        let cte_name = format!("{}_path_{}", self.alias, self.cte_counter);
        
        // 包装为子查询
        Ok(format!(
            "WITH RECURSIVE {}\nSELECT * FROM {}",
            cte_sql,
            cte_name
        ))
    }

    /// 生成递归 CTE
    fn generate_recursive_cte(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<String, GenerationError> {
        self.cte_counter += 1;
        let cte_name = format!("{}_path_{}", self.alias, self.cte_counter);
        
        // 基础查询（锚点成员）
        let base_query = self.generate_base_query(subject, path)?;
        
        // 递归查询（递归成员）
        let recursive_query = self.generate_recursive_member(&cte_name, path, object)?;
        
        Ok(format!(
            "{} AS (\n  {}\n  UNION ALL\n  {}\n)",
            cte_name,
            base_query,
            recursive_query
        ))
    }

    /// 生成基础查询（锚点成员）
    fn generate_base_query(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
    ) -> Result<String, GenerationError> {
        let subject_is_var = matches!(subject, Term::Variable(_));
        let subject_sql = if subject_is_var {
            "s".to_string()
        } else {
            self.term_to_literal_sql(subject)?
        };
        
        // 从根节点开始的初始查询
        match path {
            PropertyPath::Predicate(pred) => {
                let predicate = Self::normalize_predicate(pred);
                // 简单谓词：SELECT subject as start, object as end FROM table WHERE predicate = pred
                if subject_is_var {
                    Ok(format!(
                        "SELECT DISTINCT s AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples \
                         WHERE p = '{}'",
                        predicate
                    ))
                } else {
                    Ok(format!(
                        "SELECT DISTINCT {} AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples \
                         WHERE p = '{}' AND s = {}",
                        subject_sql, predicate, subject_sql
                    ))
                }
            }
            PropertyPath::Star(_) | PropertyPath::Plus(_) => {
                // 对于 * 和 +，锚点是起始节点本身（深度为0）
                if subject_is_var {
                    Ok("SELECT DISTINCT s AS start_node, s AS end_node, 0 AS depth FROM rdf_triples".to_string())
                } else {
                    Ok(format!(
                        "SELECT {} AS start_node, {} AS end_node, 0 AS depth",
                        subject_sql, subject_sql
                    ))
                }
            }
            PropertyPath::Alternative(alts) => {
                let predicates: Vec<String> = alts.iter()
                    .filter_map(|p| match p {
                        PropertyPath::Predicate(pred) => Some(Self::normalize_predicate(pred)),
                        _ => None,
                    })
                    .collect();
                if predicates.is_empty() {
                    return Err(GenerationError::Other(
                        "Empty alternative path".to_string()
                    ));
                }
                let pred_list = predicates
                    .iter()
                    .map(|p| format!("'{}'", p))
                    .collect::<Vec<_>>()
                    .join(", ");
                if subject_is_var {
                    Ok(format!(
                        "SELECT DISTINCT s AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples WHERE p IN ({})",
                        pred_list
                    ))
                } else {
                    Ok(format!(
                        "SELECT DISTINCT {} AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples WHERE p IN ({}) AND s = {}",
                        subject_sql, pred_list, subject_sql
                    ))
                }
            }
            PropertyPath::Sequence(seq) => {
                let first_pred = match seq.first() {
                    Some(PropertyPath::Predicate(p)) => Self::normalize_predicate(p),
                    _ => return Err(GenerationError::Other(
                        "Complex paths in sequence not yet supported".to_string()
                    )),
                };
                if subject_is_var {
                    Ok(format!(
                        "SELECT DISTINCT s AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples WHERE p = '{}'",
                        first_pred
                    ))
                } else {
                    Ok(format!(
                        "SELECT DISTINCT {} AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples WHERE p = '{}' AND s = {}",
                        subject_sql, first_pred, subject_sql
                    ))
                }
            }
            _ => {
                // 其他复杂路径：分解为基础组件
                if subject_is_var {
                    Ok("SELECT DISTINCT s AS start_node, o AS end_node, 1 AS depth FROM rdf_triples".to_string())
                } else {
                    Ok(format!(
                        "SELECT DISTINCT {} AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples WHERE s = {}",
                        subject_sql, subject_sql
                    ))
                }
            }
        }
    }

    /// 生成递归成员查询
    fn generate_recursive_member(
        &mut self,
        cte_name: &str,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<String, GenerationError> {
        let object_condition = if matches!(object, Term::Variable(_)) {
            // 变量对象，不添加限制，返回所有可达节点
            "true".to_string()
        } else {
            // 常量对象，添加终止条件
            format!("t.end_node = {}", self.term_to_literal_sql(object)?)
        };

        match path {
            PropertyPath::Predicate(pred) => {
                let predicate = Self::normalize_predicate(pred);
                // 简单谓词的递归：沿着相同谓词继续
                Ok(format!(
                    "SELECT t.start_node, r.o AS end_node, t.depth + 1 \
                     FROM {} t \
                     JOIN rdf_triples r ON t.end_node = r.s \
                     WHERE r.p = '{}' AND t.depth < 10 AND {}",
                    cte_name, predicate, object_condition
                ))
            }
            PropertyPath::Star(inner) => {
                // p*：零次或多次，需要处理 Kleene 星
                self.generate_star_recursive(cte_name, inner, &object_condition)
            }
            PropertyPath::Plus(inner) => {
                // p+：一次或多次
                self.generate_plus_recursive(cte_name, inner, &object_condition)
            }
            PropertyPath::Sequence(seq) => {
                // 序列：p1/p2/.../pn
                self.generate_sequence_recursive(cte_name, seq, &object_condition)
            }
            PropertyPath::Alternative(alts) => {
                // 选择：p1|p2|...|pn
                self.generate_alternative_recursive(cte_name, alts, &object_condition)
            }
            _ => {
                // 默认递归
                Ok(format!(
                    "SELECT t.start_node, r.o AS end_node, t.depth + 1 \
                     FROM {} t \
                     JOIN rdf_triples r ON t.end_node = r.s \
                     WHERE t.depth < 10 AND {}",
                    cte_name, object_condition
                ))
            }
        }
    }

    /// 生成 Kleene 星的递归
    fn generate_star_recursive(
        &mut self,
        cte_name: &str,
        inner: &PropertyPath,
        object_condition: &str,
    ) -> Result<String, GenerationError> {
        let inner_pred = match inner {
            PropertyPath::Predicate(p) => Self::normalize_predicate(p),
            _ => return Err(GenerationError::Other(
                "Complex nested paths in * not yet supported".to_string()
            )),
        };

        Ok(format!(
            "SELECT DISTINCT t.start_node, r.o AS end_node, t.depth + 1 \
             FROM {} t \
             JOIN rdf_triples r ON t.end_node = r.s \
             WHERE r.p = '{}' AND t.depth < 10 AND {}",
            cte_name, inner_pred, object_condition
        ))
    }

    /// 生成 Kleene 加号的递归
    fn generate_plus_recursive(
        &mut self,
        cte_name: &str,
        inner: &PropertyPath,
        object_condition: &str,
    ) -> Result<String, GenerationError> {
        // p+ = p/p*，即至少一次
        let inner_pred = match inner {
            PropertyPath::Predicate(p) => Self::normalize_predicate(p),
            _ => return Err(GenerationError::Other(
                "Complex nested paths in + not yet supported".to_string()
            )),
        };

        Ok(format!(
            "SELECT DISTINCT t.start_node, r.o AS end_node, t.depth + 1 \
             FROM {} t \
             JOIN rdf_triples r ON t.end_node = r.s \
             WHERE r.p = '{}' AND t.depth < 10 AND {}",
            cte_name, inner_pred, object_condition
        ))
    }

    /// 生成序列路径的递归
    fn generate_sequence_recursive(
        &mut self,
        cte_name: &str,
        seq: &[PropertyPath],
        object_condition: &str,
    ) -> Result<String, GenerationError> {
        if seq.is_empty() {
            return Err(GenerationError::Other(
                "Empty sequence path".to_string()
            ));
        }

        // 简化处理：序列的第一个谓词作为基础，后续在递归中处理
        // 完整的序列路径需要更复杂的 CTE 链
        let first_pred = match &seq[0] {
            PropertyPath::Predicate(p) => Self::normalize_predicate(p),
            _ => return Err(GenerationError::Other(
                "Complex paths in sequence not yet supported".to_string()
            )),
        };

        // 对于序列 p1/p2，我们需要先完成 p1 的传递闭包，然后应用 p2
        // 这里简化处理为第一个谓词的递归
        Ok(format!(
            "SELECT DISTINCT t.start_node, r.o AS end_node, t.depth + 1 \
             FROM {} t \
             JOIN rdf_triples r ON t.end_node = r.s \
             WHERE r.p = '{}' AND t.depth < 10 AND {}",
            cte_name, first_pred, object_condition
        ))
    }

    /// 生成选择路径的递归
    fn generate_alternative_recursive(
        &mut self,
        cte_name: &str,
        alts: &[PropertyPath],
        object_condition: &str,
    ) -> Result<String, GenerationError> {
        // 选择路径在递归中是多个谓词的联合
        let predicates: Vec<String> = alts.iter()
            .filter_map(|p| match p {
                PropertyPath::Predicate(pred) => Some(Self::normalize_predicate(pred)),
                _ => None,
            })
            .collect();

        if predicates.is_empty() {
            return Err(GenerationError::Other(
                "Empty alternative path".to_string()
            ));
        }

        let pred_list = predicates
            .iter()
            .map(|p| format!("r.p = '{}'", p))
            .collect::<Vec<_>>()
            .join(" OR ");

        Ok(format!(
            "SELECT DISTINCT t.start_node, r.o AS end_node, t.depth + 1 \
             FROM {} t \
             JOIN rdf_triples r ON t.end_node = r.s \
             WHERE ({}) AND t.depth < 10 AND {}",
            cte_name, pred_list, object_condition
        ))
    }

    /// 将 Term 转换为 SQL
    fn term_to_literal_sql(&self, term: &Term) -> Result<String, GenerationError> {
        match term {
            Term::Variable(_) => Err(GenerationError::Other(
                "Variable term not supported for literal SQL conversion".to_string()
            )),
            Term::Constant(c) => Ok(format!("'{}'", Self::normalize_constant(c))),
            Term::Literal { value, .. } => Ok(format!("'{}'", value.replace("'", "''"))),
            Term::Column { table: _, column } => Ok(column.clone()),
            Term::BlankNode(b) => Ok(format!("'{}'", b.replace("'", "''"))),
        }
    }

    fn normalize_predicate(predicate: &str) -> String {
        let trimmed = predicate.trim();
        if let (Some(start), Some(end)) = (trimmed.find('<'), trimmed.find('>')) {
            if end > start + 1 {
                return trimmed[start + 1..end].to_string();
            }
        }
        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            return trimmed[1..trimmed.len() - 1].to_string();
        }
        trimmed.to_string()
    }

    fn normalize_constant(constant: &str) -> String {
        let trimmed = constant.trim();
        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            trimmed[1..trimmed.len() - 1].replace("'", "''")
        } else {
            trimmed.replace("'", "''")
        }
    }
}

/// 为 LogicNode::Path 生成 SQL 的辅助函数
pub fn generate_path_sql(
    node: &LogicNode,
    _generator: &mut FlatSQLGenerator,
) -> Result<String, GenerationError> {
    if let LogicNode::Path { subject, path, object } = node {
        let alias = "path_0";
        PropertyPathSQLGenerator::generate(subject, path, object, alias)
    } else {
        Err(GenerationError::Other(
            "Expected Path node".to_string()
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ir::node::PropertyPath;
    use crate::ir::expr::Term;

    #[test]
    fn test_simple_predicate_generation() {
        let subject = Term::Variable("s".to_string());
        let path = PropertyPath::Predicate("foaf:knows".to_string());
        let object = Term::Variable("o".to_string());
        
        let sql = PropertyPathSQLGenerator::generate(&subject, &path, &object, "p0").expect("valid regex");
        assert!(sql.contains("WITH RECURSIVE"));
        assert!(sql.contains("foaf:knows"));
    }

    #[test]
    fn test_star_path_generation() {
        let subject = Term::Variable("s".to_string());
        let path = PropertyPath::Star(Box::new(PropertyPath::Predicate(
            "foaf:knows".to_string()
        )));
        let object = Term::Variable("o".to_string());
        
        let sql = PropertyPathSQLGenerator::generate(&subject, &path, &object, "p0").expect("valid regex");
        assert!(sql.contains("WITH RECURSIVE"));
        assert!(sql.contains("UNION ALL"));
    }
}
