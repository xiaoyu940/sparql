from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
marker='fn parses_select_distinct_with_prefix() {'
if 'parses_geof_distance_main_patterns' not in text:
    insert='''

    #[test]
    fn parses_geof_distance_main_patterns() {
        let parser = SparqlParserV2::default();
        let q = r#"
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
SELECT ?store ?dist
WHERE {
  ?store a <http://example.org/Store> .
  ?store <http://example.org/geometry> ?wkt .
  BIND(geof:distance(?wkt, \"POINT(116.4074 39.9042)\"^^geo:wktLiteral, uom:metre) AS ?dist)
  FILTER(geof:distance(?wkt, \"POINT(116.4074 39.9042)\"^^geo:wktLiteral, uom:metre) < 10000)
}
ORDER BY ?store
LIMIT 10
"#;
        let parsed = parser.parse(q).expect("parse should succeed");
        assert!(!parsed.main_patterns.is_empty(), "main patterns should not be empty");
    }
'''
    idx=text.rfind('}\n')
    text=text[:idx]+insert+'\n'+text[idx:]
p.write_text(text,encoding='utf-8')
print('added geof parser regression test')