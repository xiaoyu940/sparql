from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
pattern=r"\n\s*if pattern\.object\.starts_with\('\?'\) \{\n\s*let canonical_object = Self::resolve_var_alias\(&pattern\.object, &var_aliases\);\n\s*subject_preferred_table\n\s*\.entry\(canonical_object\)\n\s*\.or_insert\(table_name_hint\.clone\(\)\);\n\s*\}\n"
new, n = re.subn(pattern, "\n", text, count=1)
if n != 1:
    raise SystemExit(f'remove block failed: {n}')
p.write_text(new, encoding='utf-8')
print('removed object hint block')