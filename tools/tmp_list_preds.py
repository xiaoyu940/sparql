from pathlib import Path
import re
text = Path('/home/yuxiaoyu/rs_ontop_core/correct_mapping.ttl').read_text(encoding='utf-8')
preds = sorted(set(re.findall(r'rr:predicate\s+([^;]+);', text)))
for p in preds:
    if 'manager' in p or 'first_name' in p:
        print(p)