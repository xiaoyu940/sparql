from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
needle='        let expanded_where = expand_sparql_shorthand(&where_without_subqueries);'
if '[DBG WHERE]' not in text:
    repl='''        let expanded_where = expand_sparql_shorthand(&where_without_subqueries);
        if trimmed.contains("geof:distance") {
            eprintln!("[DBG WHERE_RAW] {}", where_without_subqueries.replace('\n', " "));
            eprintln!("[DBG WHERE_EXPANDED] {}", expanded_where.replace('\n', " "));
        }
'''
    text=text.replace(needle,repl,1)
p.write_text(text,encoding='utf-8')
print('added temp geof debug')