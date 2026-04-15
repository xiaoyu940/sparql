from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''            let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&pattern.subject),
                metadata_map,
                mappings,
            );'''
new='''            let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&pattern.subject),
                None,
                metadata_map,
                mappings,
            );'''
if old not in s:
    raise SystemExit('call snippet not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched resolve_metadata_for_predicate_with_context call args')
