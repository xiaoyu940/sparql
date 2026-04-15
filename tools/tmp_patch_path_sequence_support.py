from pathlib import Path
import re

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/path_sql_generator.rs')
text = p.read_text(encoding='utf-8')

pattern = r'fn generate_path_query\([\s\S]*?\n\s*\}\n\n\s*/// 生成递归 CTE'
repl = '''fn generate_path_query(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<String, GenerationError> {
        if let PropertyPath::Sequence(seq) = path {
            if let Some(sql) = self.generate_supported_sequence_query(subject, seq, object)? {
                return Ok(sql);
            }
        }

        // 生成递归 CTE
        let cte_sql = self.generate_recursive_cte(subject, path, object)?;
        let cte_name = format!("{}_path_{}", self.alias, self.cte_counter);

        // 包装为子查询
        Ok(format!(
            "WITH RECURSIVE {}\\nSELECT * FROM {}",
            cte_sql,
            cte_name
        ))
    }

    /// 生成递归 CTE'''
text2, n = re.subn(pattern, repl, text, count=1)
if n != 1:
    raise SystemExit(f'generate_path_query replace failed: {n}')
text = text2

insert_anchor = '    /// 生成递归 CTE\n'
helpers = '''    fn subject_filter_sql(&self, term: &Term, col: &str) -> Result<String, GenerationError> {
        if matches!(term, Term::Variable(_)) {
            Ok("true".to_string())
        } else {
            Ok(format!("{} = {}", col, self.term_to_literal_sql(term)?))
        }
    }

    fn object_filter_sql(&self, term: &Term, col: &str) -> Result<String, GenerationError> {
        if matches!(term, Term::Variable(_)) {
            Ok("true".to_string())
        } else {
            Ok(format!("{} = {}", col, self.term_to_literal_sql(term)?))
        }
    }

    fn generate_supported_sequence_query(
        &mut self,
        subject: &Term,
        seq: &[PropertyPath],
        object: &Term,
    ) -> Result<Option<String>, GenerationError> {
        if seq.len() != 2 {
            return Ok(None);
        }

        let second_pred = match &seq[1] {
            PropertyPath::Predicate(p) => Self::normalize_predicate(p),
            _ => return Ok(None),
        };

        match &seq[0] {
            PropertyPath::Predicate(first) => {
                let first_pred = Self::normalize_predicate(first);
                let subject_filter = self.subject_filter_sql(subject, "t1.s")?;
                let object_filter = self.object_filter_sql(object, "t2.o")?;
                Ok(Some(format!(
                    "SELECT DISTINCT t1.s AS start_node, t2.o AS end_node, 1 AS depth \\
                     FROM rdf_triples t1 \\
                     JOIN rdf_triples t2 ON t1.o = t2.s \\
                     WHERE t1.p = '{}' AND t2.p = '{}' AND {} AND {}",
                    first_pred, second_pred, subject_filter, object_filter
                )))
            }
            PropertyPath::Optional(inner) => {
                let first_pred = match &**inner {
                    PropertyPath::Predicate(p) => Self::normalize_predicate(p),
                    _ => return Ok(None),
                };
                let subject_filter_zero = self.subject_filter_sql(subject, "z.s")?;
                let object_filter_zero = self.object_filter_sql(object, "z.o")?;
                let subject_filter_one = self.subject_filter_sql(subject, "t1.s")?;
                let object_filter_one = self.object_filter_sql(object, "t2.o")?;

                Ok(Some(format!(
                    "SELECT DISTINCT z.s AS start_node, z.o AS end_node, 0 AS depth \\
                     FROM rdf_triples z \\
                     WHERE z.p = '{}' AND {} AND {} \\
                     UNION \\
                     SELECT DISTINCT t1.s AS start_node, t2.o AS end_node, 1 AS depth \\
                     FROM rdf_triples t1 \\
                     JOIN rdf_triples t2 ON t1.o = t2.s \\
                     WHERE t1.p = '{}' AND t2.p = '{}' AND {} AND {}",
                    second_pred,
                    subject_filter_zero,
                    object_filter_zero,
                    first_pred,
                    second_pred,
                    subject_filter_one,
                    object_filter_one
                )))
            }
            PropertyPath::Plus(inner) => {
                let first_pred = match &**inner {
                    PropertyPath::Predicate(p) => Self::normalize_predicate(p),
                    _ => return Ok(None),
                };

                self.cte_counter += 1;
                let cte_name = format!("{}_path_{}", self.alias, self.cte_counter);
                let subject_filter = self.subject_filter_sql(subject, "r.s")?;
                let object_filter = self.object_filter_sql(object, "r2.o")?;

                Ok(Some(format!(
                    "WITH RECURSIVE {} AS ( \\
                       SELECT DISTINCT r.s AS start_node, r.o AS end_node, 1 AS depth \\
                       FROM rdf_triples r \\
                       WHERE r.p = '{}' AND {} \\
                       UNION ALL \\
                       SELECT DISTINCT t.start_node, r.o AS end_node, t.depth + 1 \\
                       FROM {} t \\
                       JOIN rdf_triples r ON t.end_node = r.s \\
                       WHERE r.p = '{}' AND t.depth < 10 \\
                     ) \\
                     SELECT DISTINCT t.start_node, r2.o AS end_node, t.depth \\
                     FROM {} t \\
                     JOIN rdf_triples r2 ON t.end_node = r2.s \\
                     WHERE r2.p = '{}' AND {}",
                    cte_name,
                    first_pred,
                    subject_filter,
                    cte_name,
                    first_pred,
                    cte_name,
                    second_pred,
                    object_filter
                )))
            }
            _ => Ok(None),
        }
    }

'''
if insert_anchor not in text:
    raise SystemExit('insert anchor not found')
text = text.replace(insert_anchor, helpers + insert_anchor, 1)

p.write_text(text, encoding='utf-8')
print('patched path sequence support')