# RS Ontop Core Python 测试指南

本文档说明如何运行 `/tests/python` 目录下的 SPARQL-to-SQL 测试案例。

## 目录结构

```
tests/python/
├── framework.py              # 测试框架基类
├── run_all_tests.py          # 运行所有测试的主脚本
├── sprint8_complete_tests.py # Sprint 8 完整测试套件
└── test_cases/               # 各 Sprint 测试案例目录
    ├── test_basic_join.py
    ├── test_filter.py
    ├── test_having.py
    ├── test_sprint8_*.py     # Sprint 8 测试
    ├── test_sprint9_*.py     # Sprint 9 测试
    └── test_unified_*.py     # 统一测试案例
```

## 前置要求

1. **Python 3.12+** 已安装
2. **PostgreSQL 16** 运行且已创建数据库
3. **psycopg2** Python 库
4. **rs_ontop_core** PostgreSQL 扩展已安装

### 安装依赖

```bash
cd tests/python

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install psycopg2-binary
```

## 配置数据库

测试使用 `rs_ontop_core` 数据库，确保以下配置正确：

```python
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rs_ontop_core',
    'user': 'yuxiaoyu',
    'password': ''  # 或设置 PGPASSWORD 环境变量
}
```

可通过环境变量覆盖：
```bash
export PGUSER=yuxiaoyu
export PGPASSWORD=your_password
```

## 运行测试

### 1. 运行单个测试文件

```bash
cd tests/python
source venv/bin/activate

# 运行单个测试模块
python3 test_cases/test_basic_join.py

# 运行 Sprint 9 P1 测试
python3 test_cases/test_sprint9_p1_bind_001.py
```

### 2. 运行所有测试

```bash
cd tests/python
source venv/bin/activate
python3 run_all_tests.py
```

### 3. 使用 pytest 运行

```bash
cd tests/python
source venv/bin/activate

# 运行所有测试
python3 -m pytest test_cases/ -v

# 运行特定 Sprint 测试
python3 -m pytest test_cases/test_sprint9_*.py -v
```

**注意**: 部分测试类使用 `__init__` 构造函数，pytest 可能无法直接收集。建议使用 `python3 <test_file>.py` 方式运行。

### 4. 运行 Sprint 8 完整测试

```bash
cd tests/python
source venv/bin/activate
python3 sprint8_complete_tests.py
```

## 测试框架说明

### 编写新测试案例

继承 `TestCaseBase` 并实现以下方法：

```python
from framework import TestCaseBase, QueryResult

class TestMyFeature(TestCaseBase):
    def sparql_query(self) -> QueryResult:
        """实现 SPARQL 查询，返回 QueryResult"""
        sparql = """
        PREFIX ex: <http://example.org/>
        SELECT ?name ?salary
        WHERE {
          ?emp ex:name ?name ;
               ex:salary ?salary .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """实现基准 SQL 查询，返回 QueryResult"""
        baseline_sql = """
        SELECT name, salary 
        FROM employees 
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

# 运行测试
if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': ''
    }
    
    framework = SparqlTestFramework(db_config)
    test = TestMyFeature(db_config)
    result = framework.run_test_case(test)
    print(result)
```

### 测试输出说明

测试运行时会输出：

```
================================================================================
测试: TestBasicJoin
================================================================================
  执行 SPARQL 查询...
  ✓ SPARQL 返回 10 行
  执行 SQL 查询...
  ✓ SQL 返回 10 行
  比对结果...
  ✓ 测试通过
```

失败时显示具体错误：

```
  ✗ 测试失败:
    - 行数不匹配: SPARQL=5, SQL=10
    - 数据不匹配 [name]: SPARQL='Alice', SQL='Bob'
```

## 常见问题

### 1. 扩展函数不存在

错误：`function ontop_translate does not exist`

解决：
```bash
# 重新安装扩展
cd /home/yuxiaoyu/rs_ontop_core
cargo pgrx install --release

# 在数据库中重新创建
psql -d rs_ontop_core -c "DROP EXTENSION IF EXISTS rs_ontop_core; CREATE EXTENSION rs_ontop_core;"
```

### 2. 缺少 psycopg2

```bash
pip install psycopg2-binary
```

### 3. 数据库连接失败

检查：
- PostgreSQL 服务是否运行：`sudo service postgresql status`
- 数据库是否存在：`psql -c "CREATE DATABASE rs_ontop_core;"`
- 用户权限是否正确

## 测试分类说明

| 测试类别 | 文件模式 | 说明 |
|---------|---------|------|
| 基础测试 | `test_basic_*.py` | JOIN、FILTER、ORDER BY 等基础功能 |
| Sprint 8 | `test_sprint8_*.py` | EXISTS、VALUES、SUBQUERY、GeoSPARQL |
| Sprint 9 | `test_sprint9_*.py` | BIND、IF、COALESCE、路径表达式 |
| 统一测试 | `test_unified_*.py` | 综合功能验证 |

## 批量运行脚本

项目根目录提供辅助脚本：

```bash
# 运行 Sprint 8 测试
./tests/run_sprint8.sh

# 自动验证
./tests/auto_verify.sh
```
