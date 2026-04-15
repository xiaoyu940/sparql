from pathlib import Path
import re

# Patch extract_filter_expressions
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
start=s.find('fn extract_filter_expressions(where_block: &str) -> Vec<String> {')
end=s.find('fn extract_values(', start)
if start==-1 or end==-1:
    raise SystemExit('extract_filter_expressions block markers not found')
new_fn='''fn extract_filter_expressions(where_block: &str) -> Vec<String> {
    let mut filters = Vec::new();
    let mut start = 0;
    let upper = where_block.to_ascii_uppercase();

    while let Some(filter_pos) = upper[start..].find("FILTER") {
        let abs_filter_pos = start + filter_pos;
        let rest = &where_block[abs_filter_pos + 6..];
        let rest_trimmed = rest.trim_start();
        let ws_len = rest.len().saturating_sub(rest_trimmed.len());
        let offset = abs_filter_pos + 6 + ws_len;
        let rest_upper = rest_trimmed.to_ascii_uppercase();

        if rest_trimmed.starts_with('(') {
            let mut depth = 0;
            let mut end = None;
            for (i, c) in rest_trimmed.chars().enumerate() {
                match c {
                    '(' => depth += 1,
                    ')' => {
                        depth -= 1;
                        if depth == 0 {
                            end = Some(i);
                            break;
                        }
                    }
                    _ => {}
                }
            }
            if let Some(e) = end {
                let expr = &rest_trimmed[1..e].trim();
                filters.push(expr.to_string());
                start = offset + e + 1;
            } else {
                start = offset;
            }
            continue;
        }

        let (is_not_exists, kw_len) = if rest_upper.starts_with("NOT EXISTS") {
            (true, "NOT EXISTS".len())
        } else if rest_upper.starts_with("EXISTS") {
            (false, "EXISTS".len())
        } else {
            start = offset;
            continue;
        };

        let after_kw = &rest_trimmed[kw_len..];
        let after_kw_trimmed = after_kw.trim_start();
        let ws2 = after_kw.len().saturating_sub(after_kw_trimmed.len());
        if !after_kw_trimmed.starts_with('{') {
            start = offset + kw_len + ws2;
            continue;
        }

        let mut depth = 0;
        let mut end = None;
        for (i, c) in after_kw_trimmed.chars().enumerate() {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = Some(i);
                        break;
                    }
                }
                _ => {}
            }
        }

        if let Some(e) = end {
            let body = after_kw_trimmed[1..e].trim();
            if is_not_exists {
                filters.push(format!("NOT EXISTS {{ {} }}", body));
            } else {
                filters.push(format!("EXISTS {{ {} }}", body));
            }
            start = offset + kw_len + ws2 + e + 1;
        } else {
            start = offset + kw_len + ws2;
        }
    }

    filters
}

'''
s=s[:start]+new_fn+s[end:]
p.write_text(s,encoding='utf-8')

# Patch ManagerRelationMapping for ex:manages
m=Path('/home/yuxiaoyu/rs_ontop_core/correct_mapping.ttl')
ms=m.read_text(encoding='utf-8')
old_block='''<#ManagerRelationMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "manager_relations" ];
    rr:subjectMap [
        rr:template "http://example.org/manager_relations{emp_id}";
        rr:class ex:ManagerRelation
    ];
.
'''
new_block='''<#ManagerRelationMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "manager_relations" ];
    rr:subjectMap [
        rr:template "http://example.org/emp{mgr_id}";
        rr:class ex:ManagerRelation
    ];
    rr:predicateObjectMap [
        rr:predicate ex:manages;
        rr:objectMap [ rr:column "employee_id" ]
    ].

'''
if old_block not in ms:
    raise SystemExit('ManagerRelationMapping block not found in expected shape')
ms=ms.replace(old_block,new_block,1)
m.write_text(ms,encoding='utf-8')

print('patched FILTER EXISTS parser and manager relation mapping for ex:manages')
