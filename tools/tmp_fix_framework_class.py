from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
old='''class SparqlTestFramework(TestCaseBase):
    """兼容旧测试代码的框架类别名"""
    pass
'''
new='''class SparqlTestFramework:
    """兼容旧测试代码的轻量框架包装器"""
    def __init__(self, db_config):
        self.db_config = db_config

    def run_test_case(self, test_instance):
        try:
            return test_instance.run()
        finally:
            test_instance.close()
'''
if old not in s:
    raise SystemExit('SparqlTestFramework alias block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('replaced SparqlTestFramework with non-TestCaseBase wrapper to avoid test discovery')
