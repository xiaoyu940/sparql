from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
old = '''            Expr::Compare { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let right_sql = self.translate_expression(right)?;
                let op_sql = self.translate_comparison_op(*op);
                Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
            },
'''
new = '''            Expr::Compare { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let right_sql = self.translate_expression(right)?;
                let op_sql = self.translate_comparison_op(*op);
                if matches!(*op, ComparisonOp::Eq | ComparisonOp::Neq) {
                    Ok(format!("({})::text {} ({})::text", left_sql, op_sql, right_sql))
                } else {
                    Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
                }
            },
'''
if old not in text:
    raise SystemExit('compare block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched compare eq/neq as text-cast')