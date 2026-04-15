from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/property_path_parser.rs')
text=p.read_text(encoding='utf-8')

insert='''        if trimmed.starts_with('(') && trimmed.ends_with(')') && Self::is_fully_wrapped_parens(trimmed) {
            return Self::parse(&trimmed[1..trimmed.len() - 1]);
        }

'''
anchor='''        if trimmed.is_empty() {
            return None;
        }

'''
if insert not in text:
    if anchor not in text:
        raise SystemExit('anchor not found for parse insert')
    text=text.replace(anchor,anchor+insert,1)

helper='''    fn is_fully_wrapped_parens(path: &str) -> bool {
        let mut depth = 0i32;
        for (i, ch) in path.chars().enumerate() {
            if ch == '(' {
                depth += 1;
            } else if ch == ')' {
                depth -= 1;
                if depth == 0 && i != path.len() - 1 {
                    return false;
                }
            }
            if depth < 0 {
                return false;
            }
        }
        depth == 0
    }

'''
if 'fn is_fully_wrapped_parens(path: &str) -> bool {' not in text:
    idx=text.find('/// 分割路径字符串，考虑括号平衡')
    if idx<0:
        raise SystemExit('insert point for helper not found')
    text=text[:idx]+helper+text[idx:]

p.write_text(text,encoding='utf-8')
print('patched property path parser outer parens support')