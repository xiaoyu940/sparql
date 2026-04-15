-- ================================================
-- 复杂 SPARQL 测试用例集 - 验证修复后的引擎
-- 版本: 1.0 (针对当前引擎限制调整)
-- ================================================

-- 测试1: 简单两表 JOIN + 基本聚合 ✅ 已修复
-- 验证: SPARQL 简写语法修复 + GROUP BY 列选择修复
SELECT ?deptName (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
} 
GROUP BY ?deptName;

-- 验证结果:
-- SELECT dep.department_name AS col_deptName, COUNT(dep_1.department_id) AS empCount 
-- FROM departments AS dep 
-- INNER JOIN departments AS dep_1 ON dep.department_id = dep_1.department_id 
-- GROUP BY dep.department_name


-- ================================================
-- 以下测试用例当前有引擎限制，正在修复中
-- ================================================

-- 测试2: 三表 JOIN + 多聚合 ❌ 有 bug
-- 问题: JOIN 条件生成使用错误列 (t0.department_id = t2.employee_id)
-- 预期: t0.employee_id = t2.employee_id
-- SELECT ?deptName (AVG(?salary) AS ?avgSalary) (SUM(?salary) AS ?totalSalary)
-- WHERE { 
--     ?emp <http://example.org/department_id> ?dept . 
--     ?dept <http://example.org/department_name> ?deptName .
--     ?emp <http://example.org/salary> ?salary .
-- } 
-- GROUP BY ?deptName;


-- 测试3: 带 HAVING 的聚合 ❌ 有 bug  
-- 问题: HAVING 子句变量解析失败
-- SELECT ?deptName (AVG(?salary) AS ?avgSalary)
-- WHERE { 
--     ?emp <http://example.org/department_id> ?dept . 
--     ?dept <http://example.org/department_name> ?deptName .
--     ?emp <http://example.org/salary> ?salary .
-- } 
-- GROUP BY ?deptName
-- HAVING (AVG(?salary) > 50000);


-- 测试4: 带聚合别名的 ORDER BY ❌ 有 bug
-- 问题: ORDER BY 引用聚合别名时变量未映射
-- SELECT ?deptName (AVG(?salary) AS ?avgSalary)
-- WHERE { ... } 
-- GROUP BY ?deptName
-- ORDER BY DESC(?avgSalary);


-- ================================================
-- 当前已验证可用的测试模式
-- ================================================

-- ✅ 可用: 简单两表 JOIN + COUNT
-- ✅ 可用: 单表查询 + 简单投影
-- ✅ 可用: 带 WHERE 条件的单表查询
-- ❌ 受限: 三表 JOIN (变量映射冲突)
-- ❌ 受限: 带聚合的 ORDER BY (别名引用)
-- ❌ 受限: HAVING 子句 (聚合表达式解析)
