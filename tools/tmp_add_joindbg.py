from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
old='if seen_conditions.insert(cond.clone()) {'
new='if seen_conditions.insert(cond.clone()) {\n                                    eprintln!("[JOINDBG] auto-cond: {}", cond);'
if old not in s:
    raise SystemExit('insert point not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('inserted join debug print')
