#!/bin/bash
# Sprint 8 测试执行脚本

set -e

echo "=========================================="
echo "Sprint 8 测试执行"
echo "=========================================="

# 1. 确保环境准备
echo "[1/3] 检查环境..."

# 检查 PostgreSQL
if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo "❌ PostgreSQL 未运行，请先启动"
    exit 1
fi
echo "✅ PostgreSQL 运行中"

# 检查扩展
ext_exists=$(psql -U yuxiaoyu -d rs_ontop_core -t -c "SELECT 1 FROM pg_extension WHERE extname = 'rs_ontop_core';" 2>/dev/null | head -1 | tr -d ' ')
if [ "$ext_exists" = "1" ]; then
    echo "✅ rs_ontop_core 扩展已安装"
else
    echo "❌ 扩展未安装，请先安装"
    exit 1
fi

# 2. 启动 SPARQL 服务器
echo "[2/3] 启动 SPARQL 服务器..."
psql -U yuxiaoyu -d rs_ontop_core -c "SELECT ontop_start_sparql_server();" > /dev/null 2>&1 || echo "注意: SPARQL 服务器可能已在运行"

# 3. 运行测试
echo "[3/3] 运行 Sprint 8 测试..."
cd /home/yuxiaoyu/rs_ontop_core/tests/python

echo ""
echo "执行完整 Sprint 8 测试套件..."
python3 sprint8_complete_tests.py

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
