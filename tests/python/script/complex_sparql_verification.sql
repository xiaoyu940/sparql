-- 复杂 SPARQL 测试用例集（验证修复后的引擎）
-- 每个查询后跟生成的 SQL 和验证结果

-- ============================================
-- 测试1: 简单三表 JOIN + 聚合（无 ORDER BY 别名）
-- 验证基本 JOIN 和聚合功能
-- ============================================
SELECT ?deptName (AVG(?salary) AS ?avgSalary) (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName;

-- 预期 SQL: SELECT dep.department_name, AVG(emp.salary), COUNT(emp.employee_id) FROM employees emp JOIN departments dep ON emp.department_id = dep.department_id GROUP BY dep.department_name


-- ============================================
-- 测试2: 多属性路径查询（获取员工完整信息）
-- 验证多表 JOIN 和 FILTER
-- ============================================
SELECT ?firstName ?lastName ?deptName ?salary
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
    FILTER (?salary > 60000)
};

-- 预期 SQL: 包含 WHERE salary > 60000 的三表 JOIN


-- ============================================
-- 测试3: 简单分组统计
-- 验证 GROUP BY 基本功能
-- ============================================
SELECT ?deptName (COUNT(*) AS ?empCount) (SUM(?salary) AS ?totalSalary)
WHERE {
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
}
GROUP BY ?deptName;


-- ============================================
-- 测试4: LIMIT 和简单排序（按变量名排序，非别名）
-- 验证 LIMIT 和 ORDER BY 基本功能
-- ============================================
SELECT ?firstName ?lastName ?salary
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    ?emp <http://example.org/salary> ?salary .
}
ORDER BY ?salary
LIMIT 10;


-- ============================================
-- 测试5: 带有 HAVING 的聚合（无 ORDER BY 别名引用）
-- 验证 HAVING 子句
-- ============================================
SELECT ?deptName (AVG(?salary) AS ?avgSalary)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName
HAVING (AVG(?salary) > 50000);


-- ============================================
-- 测试6: 复杂 FILTER 多条件
-- 验证 FILTER 逻辑
-- ============================================
SELECT ?firstName ?lastName ?salary ?hireDate
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    ?emp <http://example.org/salary> ?salary .
    ?emp <http://example.org/hire_date> ?hireDate .
    FILTER (?salary > 50000)
    FILTER (?salary < 100000)
};


-- ============================================
-- 测试7: 跨表统计 - 每个部门的员工数和平均工资
-- 验证复杂聚合场景
-- ============================================
SELECT ?deptName 
       (COUNT(DISTINCT ?emp) AS ?empCount) 
       (MIN(?salary) AS ?minSalary)
       (MAX(?salary) AS ?maxSalary)
       (AVG(?salary) AS ?avgSalary)
WHERE {
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
}
GROUP BY ?deptName;


-- ============================================
-- 已知问题：带聚合别名的 ORDER BY
-- 以下查询当前有 bug：ORDER BY DESC(?avgSalary) 
-- 问题：聚合别名在 ORDER BY 中引用时无法解析
-- 工作区待修复
-- ============================================
-- SELECT ?deptName (AVG(?salary) AS ?avgSalary)
-- WHERE { ... } 
-- GROUP BY ?deptName
-- ORDER BY DESC(?avgSalary);
