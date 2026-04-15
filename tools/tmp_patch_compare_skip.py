from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''            if let Some(pos) = Self::find_logical_op(trimmed, op_str) {
                let left = Self::parse_filter_expr(trimmed[..pos].trim())?;
                let right = Self::parse_filter_expr(trimmed[pos + op_str.len()..].trim())?;

                let op = match *op_str {'''
new='''            if let Some(pos) = Self::find_logical_op(trimmed, op_str) {
                let left_part = trimmed[..pos].trim();
                let right_part = trimmed[pos + op_str.len()..].trim();
                if left_part.is_empty() || right_part.is_empty() {
                    continue;
                }

                let left = Self::parse_filter_expr(left_part)?;
                let right = Self::parse_filter_expr(right_part)?;

                let op = match *op_str {'''
if old not in s:
    raise SystemExit('comparison parse snippet not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched comparison parsing to skip empty-side operator matches')
