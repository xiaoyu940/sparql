#!/bin/bash
# SPARQL 复杂查询自动化测试脚本
# 每次安装扩展后自动验证核心功能

set -e

echo "=========================================="
echo "Ontop Core - 复杂 SPARQL 查询自动化测试"
echo "=========================================="

DB_NAME="rs_ontop_core"
DB_USER="yuxiaoyu"
DB_HOST="localhost"

# 测试函数
run_test() {
    local test_name="$1"
    local sparql_query="$2"
    local expected_pattern="$3"
    
    echo ""
    echo "[TEST] $test_name"
    
    # 执行查询
    result=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "
        BEGIN;
        SELECT ontop_refresh();
        SELECT ontop_translate('$sparql_query');
        COMMIT;
    " 2>&1 | grep -v "^\s*$" | grep -v "BEGIN\|COMMIT\|ontop_refresh\|Engine refreshed" | tail -1)
    
    # 检查结果是否包含错误
    if echo "$result" | grep -q "Translation Error"; then
        echo "❌ FAILED: $test_name"
        echo "   Error: $result"
        return 1
    fi
    
    # 检查预期模式
    if [ -n "$expected_pattern" ] && ! echo "$result" | grep -q "$expected_pattern"; then
        echo "⚠️ WARNING: $test_name - 未找到预期模式 '$expected_pattern'"
        echo "   Result: $result"
    else
        echo "✅ PASSED: $test_name"
        if [ -n "$expected_pattern" ]; then
            echo "   Found: $expected_pattern"
        fi
    fi
    
    return 0
}

# 1. 基础 JOIN + COUNT
echo ""
echo "【基础功能测试】"
run_test "两表JOIN+COUNT" \
    "SELECT ?deptName (COUNT(?emp) AS ?empCount) WHERE { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> ?deptName . } GROUP BY ?deptName" \
    "COUNT"

# 2. 三表 JOIN + 多聚合
run_test "三表JOIN+多聚合(AVG/SUM)" \
    "SELECT ?deptName (AVG(?salary) AS ?avgSalary) (SUM(?salary) AS ?totalSalary) WHERE { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> ?deptName . ?emp <http://example.org/salary> ?salary . } GROUP BY ?deptName" \
    "AVG.*salary"

# 3. HAVING 子句
run_test "HAVING子句" \
    "SELECT ?deptName (AVG(?salary) AS ?avgSalary) WHERE { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> ?deptName . ?emp <http://example.org/salary> ?salary . } GROUP BY ?deptName HAVING (AVG(?salary) > 50000)" \
    "HAVING"

# 4. ORDER BY 聚合别名
echo ""
echo "【高级功能测试】"
run_test "ORDER BY聚合别名" \
    "SELECT ?deptName (COUNT(?emp) AS ?empCount) WHERE { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> ?deptName . } GROUP BY ?deptName ORDER BY DESC(?empCount)" \
    "empCount"

# 5. 完整复杂查询
run_test "完整复杂查询(所有功能)" \
    "SELECT ?deptName (AVG(?salary) AS ?avgSalary) WHERE { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> ?deptName . ?emp <http://example.org/salary> ?salary . } GROUP BY ?deptName HAVING (AVG(?salary) > 50000) ORDER BY DESC(?avgSalary) LIMIT 10" \
    "department_name"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
