from pathlib import Path
import re
# patch parser projected vars
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
s=re.sub(r"fn extract_projected_vars\(sparql: &str\) -> Vec<String> \{[\s\S]*?\n\}",'''fn extract_projected_vars(sparql: &str) -> Vec<String> {
    let upper = sparql.to_ascii_uppercase();
    let Some(select_pos) = upper.find("SELECT") else {
        return Vec::new();
    };
    let Some(where_pos) = upper.find("WHERE") else {
        return Vec::new();
    };
    if where_pos <= select_pos + 6 {
        return Vec::new();
    }

    let select_part = &sparql[select_pos + 6..where_pos];
    let mut vars: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();

    let alias_re = regex::Regex::new(r"(?i)AS\s+\?(\w+)").expect("valid regex");
    for cap in alias_re.captures_iter(select_part) {
        let v = cap[1].to_string();
        if seen.insert(v.clone()) {
            vars.push(v);
        }
    }

    let var_re = regex::Regex::new(r"\?(\w+)").expect("valid regex");
    for cap in var_re.captures_iter(select_part) {
        let v = cap[1].to_string();
        if seen.insert(v.clone()) {
            vars.push(v);
        }
    }

    vars
}
''',s,count=1)
p.write_text(s,encoding='utf-8')

# patch subquery output var dedup
p2=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s2=p2.read_text(encoding='utf-8')
old='''        let output_vars = Self::collect_output_vars(inner);'''
new='''        let mut output_vars = Self::collect_output_vars(inner);
        output_vars.sort();
        output_vars.dedup();'''
s2=s2.replace(old,new,1)
p2.write_text(s2,encoding='utf-8')
print('patched extract_projected_vars normalization and subquery output dedup')
