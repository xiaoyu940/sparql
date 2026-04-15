from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/run_all_tests.py')
s=p.read_text(encoding='utf-8')
old='''        # 实例化并运行
        test = test_class(db_config)
        try:
            result = test.run()
            results.append(result)
        except Exception as e:
            results.append({
                'test_name': test_class.__name__,
                'passed': False,
                'errors': [f'测试执行异常: {str(e)}']
            })
        finally:
            test.close()'''
new='''        # 实例化并运行
        test = test_class(db_config)
        try:
            result = test.run()
            results.append(result)
            if result.get('passed'):
                print(f"✓ {test_class.__name__}")
            else:
                print(f"✗ {test_class.__name__}")
                for err in result.get('errors', []):
                    print(f"  - {err}")
        except Exception as e:
            err_result = {
                'test_name': test_class.__name__,
                'passed': False,
                'errors': [f'测试执行异常: {str(e)}']
            }
            results.append(err_result)
            print(f"✗ {test_class.__name__}")
            print(f"  - {err_result['errors'][0]}")
        finally:
            test.close()'''
if old not in s:
    raise SystemExit('target run loop block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched run_all_tests.py to print per-case pass/fail lines')
