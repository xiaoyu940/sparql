from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_filter.py')
s=p.read_text(encoding='utf-8')
s=s.replace('FILTER(?salary < 50000)','FILTER(?salary < 60000)',1)
s=s.replace('WHERE salary < 50000','WHERE salary < 60000',1)
p.write_text(s,encoding='utf-8')
print('patched TestFilterLessThan threshold 50000 -> 60000')
