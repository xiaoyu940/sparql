from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
text = text.replace('for op_str in &["==", ">=", "<=", "=", ">", "<"] {','for op_str in &["!=", "<>", "==", ">=", "<=", "=", ">", "<"] {', 1)
text = text.replace('"==" | "=" => ComparisonOp::Eq,','"!=" | "<>" => ComparisonOp::Neq,\n                    "==" | "=" => ComparisonOp::Eq,', 1)
p.write_text(text, encoding='utf-8')
print('patched != and <> comparison support')