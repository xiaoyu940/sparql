from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text=p.read_text(encoding='utf-8')
old='''    fn generate_union_sql(&self, children: &[LogicNode]) -> Result<String, GenerationError> {
        if children.is_empty() {
            return Err(GenerationError::Other("UNION requires at least one branch".to_string()));
        }

        let mut parts = Vec::with_capacity(children.len());
        for child in children {
            let mut branch_generator = self.child_generator();
            let sql = branch_generator.generate(child)?;
            parts.push(sql);
        }

        Ok(parts.join(" UNION ALL "))
    }
'''
new='''    fn generate_union_sql(&self, children: &[LogicNode]) -> Result<String, GenerationError> {
        if children.is_empty() {
            return Err(GenerationError::Other("UNION requires at least one branch".to_string()));
        }

        let target_cols = children
            .iter()
            .map(|c| c.used_variables().len())
            .max()
            .unwrap_or(0);

        let mut parts = Vec::with_capacity(children.len());
        for child in children {
            let child_vars = child.used_variables();
            let mut branch_generator = self.child_generator();
            let sql = branch_generator.generate(child)?;
            if child_vars.is_empty() && target_cols > 0 {
                let null_cols = (0..target_cols)
                    .map(|i| format!("NULL AS __u{}", i))
                    .collect::<Vec<_>>()
                    .join(", ");
                parts.push(format!("SELECT {} WHERE FALSE", null_cols));
            } else {
                parts.push(sql);
            }
        }

        Ok(parts.join(" UNION ALL "))
    }
'''
if old not in text:
    raise SystemExit('generate_union_sql block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched union sql column-shape normalization')