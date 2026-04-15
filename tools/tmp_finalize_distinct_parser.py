from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('        eprintln!("[DEBUG parse] distinct={}", distinct);\n','',1)
text=text.replace('SELECT\\s+DISTINC"','SELECT\\s+DISTINCT\\b"',1)
if '#[cfg(test)]\nmod tests {' not in text:
    text += '''

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_select_distinct_with_prefix() {
        let parser = SparqlParserV2::default();
        let q = r#"
PREFIX ex: <http://example.org/>
SELECT DISTINCT ?deptName
WHERE {
    ?emp ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
}
ORDER BY ?deptName
"#;
        let parsed = parser.parse(q).expect("parse should succeed");
        assert!(parsed.distinct, "DISTINCT should be detected");
    }
}
'''
p.write_text(text,encoding='utf-8')
print('cleaned debug, fixed DISTINCT regex, added parser test')