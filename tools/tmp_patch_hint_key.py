from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''                let key = p.subject.trim_start_matches('?').to_string();
                main_subject_hints.entry(key).or_insert(meta.table_name.clone());
'''
new='''                let key = p.subject.clone();
                main_subject_hints.entry(key).or_insert(meta.table_name.clone());
'''
if old not in text:
    raise SystemExit('hint key block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched main_subject_hints key to keep ? prefix')