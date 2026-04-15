from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
if '\ndef run_test_case(test_class, db_config):' in s:
    print('module-level run_test_case already exists')
else:
    s += '''

def run_test_case(test_class, db_config):
    """模块级兼容入口：运行单个测试类/实例"""
    if isinstance(test_class, type):
        test_instance = test_class(db_config)
    else:
        test_instance = test_class
    try:
        return test_instance.run()
    finally:
        test_instance.close()
'''
    p.write_text(s, encoding='utf-8')
    print('added module-level run_test_case compatibility function')
