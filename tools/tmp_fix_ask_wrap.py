from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/lib.rs')
s=p.read_text(encoding='utf-8')
old='''        let mut generator = FlatSQLGenerator::new_with_mappings(Arc::clone(&self.mappings));
        generator
            .generate(&logic_plan)
            .map_err(|e| format!("SQL generation failed: {}", e))       
    }
'''
new='''        let mut generator = FlatSQLGenerator::new_with_mappings(Arc::clone(&self.mappings));
        let sql = generator
            .generate(&logic_plan)
            .map_err(|e| format!("SQL generation failed: {}", e))?;

        if parsed.query_type == QueryType::Ask {
            return Ok(format!("SELECT EXISTS ({}) AS result", sql));
        }

        Ok(sql)
    }
'''
if old not in s:
    raise SystemExit('target generator return block not found in lib.rs')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched ASK translation to wrap generated SQL with SELECT EXISTS')
