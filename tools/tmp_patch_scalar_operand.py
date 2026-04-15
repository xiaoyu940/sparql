from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
if 'fn parse_filter_operand(token: &str)' not in text:
    text=text.replace('fn parse_filter_expr(filter: &str) -> Option<Expr> {','fn parse_filter_operand(token: &str) -> Option<Expr> {\n        let t = token.trim();\n        let up = t.to_ascii_uppercase();\n        if up.starts_with("(SELECT") && t.ends_with(\')\') {\n            return Some(Expr::Function {\n                name: "SPARQL_SCALAR_SUBQUERY".to_string(),\n                args: vec![Expr::Term(Term::Constant(t.to_string()))],\n            });\n        }\n        Self::parse_filter_expr(t)\n    }\n\n    fn parse_filter_expr(filter: &str) -> Option<Expr> {',1)
pattern=r'let left = Self::parse_filter_expr\(left_part\)\?;\s*\n\s*let right = Self::parse_filter_expr\(right_part\)\?;'
repl='let left = Self::parse_filter_operand(left_part)?;\n                  let right = Self::parse_filter_operand(right_part)?;'
new,n=re.subn(pattern,repl,text,count=1)
if n!=1:
    raise SystemExit(f'compare operand replace failed {n}')
p.write_text(new,encoding='utf-8')
print('patched scalar operand parse with regex')