-- 复杂 SPARQL 测试用例集
-- 用于验证 Ontop 引擎正确性

-- 测试1: 三表 JOIN + 聚合 + 排序
SELECT ?deptName (AVG(?salary) AS ?avgSalary) (COUNT(?emp) AS ?empCount)
WHERE { 
    ?emp <http://example.org/department_id> ?dept . 
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/salary> ?salary .
} 
GROUP BY ?deptName
HAVING (AVG(?salary) > 50000)
ORDER BY DESC(?avgSalary)
LIMIT 10;

-- 测试2: 多属性路径查询（获取员工完整信息）
SELECT ?firstName ?lastName ?deptName ?positionName ?salary
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/position_id> ?pos .
    ?pos <http://example.org/position_name> ?positionName .
    ?emp <http://example.org/salary> ?salary .
    FILTER (?salary > 60000)
}
ORDER BY ?lastName;

-- 测试3: 嵌套聚合 - 部门最高工资与平均工资对比
SELECT ?deptName ?maxSalary ?avgSalary ((?maxSalary - ?avgSalary) AS ?diff)
WHERE {
    {
        SELECT ?deptName (MAX(?salary) AS ?maxSalary) (AVG(?salary) AS ?avgSalary)
        WHERE {
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
            ?emp <http://example.org/salary> ?salary .
        }
        GROUP BY ?deptName
    }
}
ORDER BY DESC(?diff);

-- 测试4: UNION 查询 - 获取所有项目或部门信息
SELECT ?name ?type
WHERE {
    { ?project <http://example.org/project_name> ?name . BIND("project" AS ?type) }
    UNION
    { ?dept <http://example.org/department_name> ?name . BIND("department" AS ?type) }
}
ORDER BY ?type ?name;

-- 测试5: OPTIONAL 查询 - 员工及其可选的项目分配
SELECT ?firstName ?lastName ?projectName
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    OPTIONAL {
        ?empProj <http://example.org/employee_id> ?emp .
        ?empProj <http://example.org/project_id> ?proj .
        ?proj <http://example.org/project_name> ?projectName .
    }
}
ORDER BY ?lastName;

-- 测试6: 复杂 FILTER - 多条件筛选
SELECT ?firstName ?lastName ?salary ?hireDate
WHERE {
    ?emp <http://example.org/first_name> ?firstName .
    ?emp <http://example.org/last_name> ?lastName .
    ?emp <http://example.org/salary> ?salary .
    ?emp <http://example.org/hire_date> ?hireDate .
    FILTER (?salary > 50000 && ?salary < 100000)
    FILTER (YEAR(?hireDate) > 2020)
}
ORDER BY DESC(?salary);

-- 测试7: 多级 JOIN + 分组统计
SELECT ?deptName ?positionName (COUNT(*) AS ?count) (SUM(?salary) AS ?totalSalary)
WHERE {
    ?emp <http://example.org/department_id> ?dept .
    ?dept <http://example.org/department_name> ?deptName .
    ?emp <http://example.org/position_id> ?pos .
    ?pos <http://example.org/position_name> ?positionName .
    ?emp <http://example.org/salary> ?salary .
}
GROUP BY ?deptName ?positionName
ORDER BY ?deptName DESC(?count);
