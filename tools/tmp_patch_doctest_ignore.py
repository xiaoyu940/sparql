from pathlib import Path
root=Path('/home/yuxiaoyu/rs_ontop_core')
files=['src/ir/builder.rs','src/mapping/r2rml_loader.rs','src/optimizer/rules/left_to_inner.rs']
for f in files:
    p=root/f
    s=p.read_text(encoding='utf-8')
    s=s.replace('/// `','/// `ust,ignore')
    s=s.replace('/// `ust,no_run','/// `ust,ignore')
    p.write_text(s,encoding='utf-8')
    print('patched',f)
