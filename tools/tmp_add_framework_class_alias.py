from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
if 'class SparqlTestFramework(TestCaseBase):' in s:
    print('SparqlTestFramework already exists')
else:
    insert='''

class SparqlTestFramework(TestCaseBase):
    """兼容旧测试代码的框架类别名"""
    pass
'''
    marker='\ndef run_test_case(test_class, db_config):'
    pos=s.find(marker)
    if pos==-1:
        s += insert
    else:
        s = s[:pos] + insert + s[pos:]
    p.write_text(s,encoding='utf-8')
    print('added SparqlTestFramework compatibility class')
