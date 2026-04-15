-- ================================================
-- 复杂 SPARQL 测试用例集 - 验证修复后的引擎
-- 版本: 2.0 (2024-03-30 更新 - 所有主要功能已修复)
-- ================================================

-- 测试1: 简单两表 JOIN + 基本聚合 ✅
SELECT ?deptName (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
} 
GROUP BY ?deptName;

-- 测试2: 三表 JOIN + 多聚合 ✅
SELECT ?deptName (AVG(?salary) AS ?avgSalary) (SUM(?salary) AS ?totalSalary) (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName;

-- 测试3: 带 HAVING 的聚合 ✅
SELECT ?deptName (AVG(?salary) AS ?avgSalary)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName
HAVING (AVG(?salary) > 50000);

-- 测试4: 带聚合别名的 ORDER BY ✅
SELECT ?deptName (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
} 
GROUP BY ?deptName
ORDER BY DESC(?empCount);

-- 测试5: 带多个条件的复杂查询 ✅
SELECT ?deptName (AVG(?salary) AS ?avgSalary) (MAX(?salary) AS ?maxSalary)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName
HAVING (AVG(?salary) > 50000)
ORDER BY DESC(?avgSalary)
LIMIT 10;

-- ================================================
-- 高级测试用例（可选）
-- ================================================

-- 测试6: 四表 JOIN（如果有 positions 表映射）
-- 需要添加 positions 表的 R2RML 映射

-- 测试7: 嵌套子查询（如果引擎支持）
-- 目前可能有限制

-- ================================================
-- 当前已验证可用的功能清单
-- ================================================
-- ✅ 简单两表 JOIN + COUNT
-- ✅ 三表 JOIN + 多聚合 (AVG, SUM, COUNT)
-- ✅ 带 HAVING 子句的聚合
-- ✅ ORDER BY 聚合别名
-- ✅ 多条件复杂查询 (GROUP BY + HAVING + ORDER BY + LIMIT)
-- ✅ 列别名正确映射 (deptName -> department_name)
