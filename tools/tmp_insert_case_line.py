from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/sparql/test_basic_select.py')
lines=p.read_text(encoding='utf-8').splitlines()
out=[]
inserted=False
for ln in lines:
    out.append(ln)
    if ln.strip()=='TestSelectDistinctDepartments(),' and not inserted:
        out.append('            TestSelectDistinctDepartmentsViaJoin(),')
        inserted=True
p.write_text('\n'.join(out)+'\n',encoding='utf-8')
print('inserted=',inserted)