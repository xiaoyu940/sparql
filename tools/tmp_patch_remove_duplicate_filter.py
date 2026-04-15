from pathlib import Path
import re

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
pattern = r'\n\s*for filter_str in &parsed\.filter_expressions \{[\s\S]*?\n\s*\}\n\n\s*node\n\s*\}'
new = '\n\n        node\n    }'
text2, n = re.subn(pattern, new, text, count=1)
if n != 1:
    raise SystemExit(f'pattern replace failed: {n}')
p.write_text(text2, encoding='utf-8')
print('removed duplicate filter loop')