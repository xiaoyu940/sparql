from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
old = '''        if impossible_pattern {
            return LogicNode::Values {
                variables: Vec::new(),
                rows: Vec::new(),
            };
        }
'''
new = '''        if impossible_pattern {
            if preserve_on_impossible {
                return LogicNode::Values {
                    variables: vec!["__unit".to_string()],
                    rows: vec![vec![Term::Constant("1".to_string())]],
                };
            }
            return LogicNode::Values {
                variables: Vec::new(),
                rows: Vec::new(),
            };
        }
'''
if old not in text:
    raise SystemExit('impossible block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched impossible block')