from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
old='''        let main_patterns = extract_triple_patterns(&where_without_optional);
        let union_patterns = extract_union_patterns(&where_without_optional);
'''
new='''        let mut main_patterns = extract_triple_patterns(&where_without_optional);
        if main_patterns.is_empty() {
            let fallback_patterns = extract_triple_patterns(&where_without_subqueries);
            if !fallback_patterns.is_empty() {
                main_patterns = fallback_patterns;
            }
        }
        let union_patterns = extract_union_patterns(&where_without_optional);
'''
if old in text:
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched parser main pattern fallback extraction')