# Python SPARQL-SQL 结果比对测试框架

每个 Python 文件一个测试案例，独立验证 SPARQL 翻译的正确性。

## 结构

```
tests/python/
├── framework.py           # 测试框架基类
├── run_all_tests.py       # 运行所有测试
├── test_cases/            # 测试案例目录
│   ├── test_basic_join.py        # JOIN 测试
│   ├── test_aggregation_count.py # 聚合测试
│   ├── test_having.py           # HAVING 测试
│   ├── test_order_by.py         # ORDER BY 测试
│   ├── test_filter.py           # FILTER 测试
│   ├── test_sprint7_construct.py # CONSTRUCT 测试 [S7-P0-1]
│   ├── test_sprint7_ask.py       # ASK 测试 [S7-P0-2]
│   ├── test_sprint7_describe.py  # DESCRIBE 测试 [S7-P1-1]
│   ├── test_sprint7_dialect.py   # 方言框架测试 [S7-P0-3]
│   └── test_your_case.py        # 添加你的测试
└── README.md             # 本文档

tests/output/              # 测试报告输出目录（自动创建）
├── test_report_YYYYMMDD_HHMMSS.json   # JSON 格式报告
└── test_report_YYYYMMDD_HHMMSS.md     # Markdown 格式报告
```

## 快速开始

### 数据库配置

测试默认连接以下 PostgreSQL 数据库：

| 参数 | 默认值 |
|------|--------|
| 主机 | `localhost` |
| 端口 | `5432` |
| 数据库名 | `rs_ontop_core` |
| 用户名 | `yuxiaoyu` |
| 密码 | 空（可通过环境变量 `PGPASSWORD` 设置）|

可通过命令行参数覆盖默认配置，见下方示例。

### 1. 安装依赖

```bash
cd tests/python
pip install psycopg2-binary
```

### 2. 运行单个测试

```bash
# 直接运行测试文件
python test_cases/test_basic_join.py

# 使用环境变量传递密码
PGPASSWORD=your_password python test_cases/test_basic_join.py
```

### 3. 运行所有测试

```bash
# 运行所有测试
python run_all_tests.py --password your_password

# 生成 JSON 报告
python run_all_tests.py --password your_password --report

# 指定数据库连接
python run_all_tests.py \
    --host localhost \
    --port 5432 \
    --database rs_ontop_core \
    --user yuxiaoyu \
    --password your_password \
    --report
```

## 添加新测试案例

创建一个新的 Python 文件 `test_cases/test_your_feature.py`:

```python
#!/usr/bin/env python3
"""
测试案例: [你的测试名称]

验证 [描述要验证的功能]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestYourFeature(TestCaseBase):
    """测试 [功能描述]"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询函数
        
        1. 构造 SPARQL 查询
        2. 调用 self.translate_sparql(sparql) 获取 SQL
        3. 执行 SQL 并返回结果
        """
        sparql = """
        SELECT ?var1 ?var2
        WHERE {
            ?s <http://example.org/predicate> ?var1 .
            ?s <http://example.org/other> ?var2 .
        }
        LIMIT 10
        """
        
        # 翻译 SPARQL 为 SQL
        sql = self.translate_sparql(sparql)
        
        # 执行并返回标准化结果
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        SQL 查询函数（基准）
        
        1. 构造等价的基准 SQL
        2. 执行并返回结果
        
        注意：这是"正确答案"，不依赖 SPARQL 翻译
        """
        baseline_sql = """
        SELECT col1 AS var1, col2 AS var2
        FROM your_table
        WHERE condition = 'value'
        LIMIT 10
        """
        
        return self.execute_sql_query(baseline_sql)


# 独立运行测试
if __name__ == '__main__':
    import json
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    print(f"\n{'='*80}")
    print(f"测试: [你的测试名称]")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestYourFeature, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
```

## 工作原理

每个测试案例包含三个核心函数：

### 1. `sparql_query()` 
- 构造 SPARQL 查询
- 调用 `translate_sparql()` 获取生成的 SQL
- 执行 SQL 返回 `QueryResult`

### 2. `sql_query()`
- 构造基准 SQL（手动验证正确的 SQL）
- 执行返回 `QueryResult`
- 这是"黄金标准"，不依赖 SPARQL 翻译

### 3. `compare_results()`
框架自动比对：
- **行数**是否相同
- **列名**是否匹配（SPARQL 变量 ↔ SQL 别名）
- **数据内容**是否一致

## 验证逻辑

框架自动执行以下检查：

1. **翻译验证**: SPARQL 能否正确翻译为可执行的 SQL
2. **执行验证**: 生成的 SQL 能否在数据库成功执行
3. **结果比对**: SPARQL 结果与基准 SQL 结果是否一致

## 调试技巧

```python
# 打印生成的 SQL
sql = self.translate_sparql(sparql)
print(f"生成的 SQL: {sql}")

# 打印查询结果
result = self.execute_sql_query(sql)
print(f"列: {result.columns}")
print(f"行数: {result.row_count}")
for row in result.rows[:3]:
    print(f"  {row}")
```

## 优势

- **模块化**: 每个测试独立，易于理解和维护
- **快速迭代**: Python 无需编译，修改即运行
- **清晰对比**: SPARQL 函数 vs SQL 函数，一目了然
- **自动发现**: `run_all_tests.py` 自动发现新添加的测试
- **标准化结果**: `QueryResult` 统一格式，便于比对
