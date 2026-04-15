from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''            subject_preferred_table
                .entry(pattern.subject.clone())
                .or_insert_with(|| metadata.table_name.clone());
            table_patterns.entry(metadata.table_name.clone()).or_default().push(pattern);'''
new='''            subject_preferred_table
                .entry(pattern.subject.clone())
                .or_insert_with(|| metadata.table_name.clone());
            if pattern.object.starts_with('?') {
                subject_preferred_table
                    .entry(pattern.object.clone())
                    .or_insert_with(|| metadata.table_name.clone());
            }
            table_patterns.entry(metadata.table_name.clone()).or_default().push(pattern);'''
if old not in s:
    raise SystemExit('preferred table insertion block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched variable table hint propagation for object vars')
