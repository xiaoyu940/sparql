from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text=p.read_text(encoding='utf-8')

text=text.replace('''            Expr::Compare { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let right_sql = self.translate_expression(right)?;
                let op_sql = self.translate_comparison_op(*op);
                if matches!(*op, ComparisonOp::Eq | ComparisonOp::Neq) {
                    Ok(format!("({})::text {} ({})::text", left_sql, op_sql, right_sql))
                } else {
                    Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
                }
            },
''','''            Expr::Compare { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let right_sql = match right.as_ref() {
                    Expr::Function { name, args } if name.eq_ignore_ascii_case("SPARQL_SCALAR_SUBQUERY") => {
                        self.translate_scalar_subquery_expr(args, &left_sql)?
                    }
                    _ => self.translate_expression(right)?,
                };
                let op_sql = self.translate_comparison_op(*op);
                if matches!(*op, ComparisonOp::Eq | ComparisonOp::Neq) {
                    Ok(format!("({})::text {} ({})::text", left_sql, op_sql, right_sql))
                } else {
                    Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
                }
            },
''',1)

helper='''    fn translate_scalar_subquery_expr(
        &self,
        args: &[Expr],
        outer_expr: &str,
    ) -> Result<String, GenerationError> {
        let raw = if let Some(Expr::Term(Term::Constant(s))) = args.first() {
            s.trim()
        } else {
            return Err(GenerationError::Other("Invalid scalar subquery expression".to_string()));
        };

        let agg_re = regex::Regex::new(r"(?is)SELECT\s*\(\s*([A-Z]+)\s*\(")
            .map_err(|e| GenerationError::Other(format!("Invalid scalar subquery regex: {}", e)))?;
        let agg = agg_re
            .captures(raw)
            .and_then(|c| c.get(1).map(|m| m.as_str().to_ascii_uppercase()))
            .ok_or_else(|| GenerationError::Other("Unsupported scalar subquery format".to_string()))?;

        let col_re = regex::Regex::new(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)")
            .map_err(|e| GenerationError::Other(format!("Invalid outer expr regex: {}", e)))?;
        let caps = col_re
            .captures(outer_expr)
            .ok_or_else(|| GenerationError::Other("Scalar subquery requires comparable outer column".to_string()))?;
        let outer_alias = caps.get(1).map(|m| m.as_str()).unwrap_or("");
        let outer_col = caps.get(2).map(|m| m.as_str()).unwrap_or("");

        let table_name = self
            .ctx
            .from_tables
            .iter()
            .find_map(|t| {
                let alias_main = t.alias.split('(').next().unwrap_or("");
                if alias_main == outer_alias {
                    Some(t.table_name.clone())
                } else {
                    None
                }
            })
            .ok_or_else(|| GenerationError::Other("Cannot infer table for scalar subquery".to_string()))?;

        let inner_alias = "sq";
        Ok(format!(
            "(SELECT {}({}.{}) FROM {} AS {})",
            agg,
            inner_alias,
            outer_col,
            table_name,
            inner_alias
        ))
    }

'''
if 'fn translate_scalar_subquery_expr(' not in text:
    idx=text.find('fn normalize_predicate(predicate: &str) -> String {')
    if idx<0:
        raise SystemExit('normalize_predicate signature not found')
    text=text[:idx]+helper+text[idx:]

p.write_text(text,encoding='utf-8')
print('patched flat scalar compare + helper')