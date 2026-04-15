#!/bin/bash
# Sprint 8 测试启动脚本
# 按测试环境文档步骤执行

set -e

echo "=========================================="
echo "Sprint 8 测试环境启动与验证"
echo "=========================================="

DB_NAME="rs_ontop_core"
DB_USER="yuxiaoyu"
DB_HOST="localhost"

# 1. 检查并启动 PostgreSQL
echo ""
echo "[1/4] 检查 PostgreSQL 服务..."
if ! pg_isready -h $DB_HOST > /dev/null 2>&1; then
    echo "  PostgreSQL 未运行，尝试启动..."
    sudo systemctl start postgresql || sudo service postgresql start || echo "请手动启动 PostgreSQL"
    sleep 2
fi

if pg_isready -h $DB_HOST > /dev/null 2>&1; then
    echo "  ✅ PostgreSQL 运行中"
else
    echo "  ❌ PostgreSQL 启动失败，请手动检查"
    exit 1
fi

# 2. 检查扩展
echo ""
echo "[2/4] 检查 rs_ontop_core 扩展..."
ext_exists=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT 1 FROM pg_extension WHERE extname = 'rs_ontop_core';" 2>/dev/null | head -1 | tr -d ' ')

if [ "$ext_exists" = "1" ]; then
    echo "  ✅ 扩展已安装"
else
    echo "  ⚠️ 扩展未安装，尝试安装..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS rs_ontop_core;" 2>/dev/null || echo "  请手动安装: cargo pgrx install"
fi

# 3. 检查 SPARQL 服务器
echo ""
echo "[3/4] 检查 SPARQL 服务器..."
if curl -s http://localhost:5820/ > /dev/null 2>&1; then
    echo "  ✅ SPARQL 服务器运行中"
else
    echo "  ⚠️ SPARQL 服务器未启动，尝试启动..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT ontop_start_sparql_server();" > /dev/null 2>&1 || echo "  请在 psql 中手动执行: SELECT ontop_start_sparql_server();"
    sleep 2
fi

# 4. 运行 Sprint 8 测试
echo ""
echo "[4/4] 运行 Sprint 8 Python 测试..."
echo "=========================================="

cd /home/yuxiaoyu/rs_ontop_core/tests/python

echo ""
echo ">>> 运行 test_sprint8_subquery_001.py"
python3 test_cases/test_sprint8_subquery_001.py

echo ""
echo ">>> 运行 test_sprint8_values_001.py"
python3 test_cases/test_sprint8_values_001.py

echo ""
echo ">>> 运行 test_sprint8_minus_001.py"
python3 test_cases/test_sprint8_minus_001.py

echo ""
echo ">>> 运行 test_sprint8_exists_001.py"
python3 test_cases/test_sprint8_exists_001.py

echo ""
echo "=========================================="
echo "Sprint 8 测试完成"
echo "=========================================="
