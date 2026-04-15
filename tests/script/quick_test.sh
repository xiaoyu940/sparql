#!/bin/bash
# RDF映射验证测试脚本

echo "=========================================="
echo "RS Ontop Core V2.0 - RDF映射验证测试"
echo "=========================================="
echo ""

# 1. 检查SQL数据
echo "【测试1】SQL基准数据验证"
echo "--------------------------"
psql -U yuxiaoyu -d rs_ontop_core -c "SELECT 'Employees' as table_name, COUNT(*) as count FROM employees UNION ALL SELECT 'Departments', COUNT(*) FROM departments UNION ALL SELECT 'Positions', COUNT(*) FROM positions;"

echo ""
echo "【测试2】SPARQL端点可用性检查"
echo "--------------------------"
curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n响应时间: %{time_total}s\n" http://localhost:5820/

echo ""
echo "【测试3】基本SPARQL查询测试"
echo "--------------------------"
echo "查询1: SELECT * WHERE {?s ?p ?o} LIMIT 1"
curl -s -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * WHERE {?s ?p ?o} LIMIT 1"}' | head -c 200

echo ""
echo ""
echo "查询2: 员工计数"
curl -s -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT (COUNT(*) AS ?c) WHERE {?e <http://example.org/employee_id> ?id}"}' | python3 -m json.tool 2>/dev/null || echo "解析失败"

echo ""
echo "【测试4】映射文件检查"
echo "--------------------------"
ls -lh mapping.r2rml.ttl ontology.owl 2>/dev/null || echo "映射文件不存在"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
