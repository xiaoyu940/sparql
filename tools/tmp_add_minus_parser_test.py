from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
if 'parses_minus_block_patterns' not in text:
    idx=text.rfind('}\n')
    test='''

    #[test]
    fn parses_minus_block_patterns() {
        let parser = SparqlParserV2::default();
        let q = r#"
SELECT ?dept ?name
WHERE {
  ?dept <http://example.org/dept_name> ?name .
  MINUS {
    ?emp <http://example.org/department_id> ?dept .
    ?emp <http://example.org/fired> true .
  }
}
"#;
        let parsed = parser.parse(q).expect("parse should succeed");
        assert_eq!(parsed.minus_blocks.len(), 1);
        assert_eq!(parsed.minus_blocks[0].patterns.len(), 2);
    }
'''
    text=text[:idx]+test+'\n'+text[idx:]
p.write_text(text,encoding='utf-8')
print('added minus parser test')