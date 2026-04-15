# SPARQL 1.1 语法全覆盖验证清单

本文档穷举 SPARQL 1.1 所有语法特性，用于系统测试覆盖评估。

## 1. 查询形式 (Query Forms)

### 1.1 SELECT 查询 ⭐已实现
- [x] 基础 SELECT
- [x] SELECT DISTINCT
- [x] SELECT REDUCED (SPARQL 1.1)
- [x] SELECT * (通配符)
- [x] 投影表达式 SELECT (?x AS ?y)
- [x] 聚合投影 SELECT (COUNT(*) AS ?count)

### 1.2 CONSTRUCT 查询 ⬜未测试
- [ ] 基础 CONSTRUCT WHERE
- [ ] CONSTRUCT 模板
- [ ] CONSTRUCT * (SPARQL 1.1)

### 1.3 ASK 查询 ⭐部分实现
- [x] 基础 ASK WHERE
- [ ] ASK + 嵌套模式
- [ ] ASK + 复杂过滤器

### 1.4 DESCRIBE 查询 ⬜未测试
- [ ] DESCRIBE <uri>
- [ ] DESCRIBE ?var
- [ ] DESCRIBE * (SPARQL 1.1)

---

## 2. 基础图模式 (Basic Graph Patterns)

### 2.1 三元组模式 ⭐已实现
- [x] 主语-谓语-宾语 (spo)
- [x] 变量主语 ?s
- [x] 变量谓语 ?p
- [x] 变量宾语 ?o
- [x] 常量主语 <uri>
- [x] 常量谓语 <uri>
- [x] 常量宾语 "literal"
- [x] 带类型的字面量 "val"^^xsd:integer
- [x] 带语言标签 "val"@en

### 2.2 简写语法 ⬜未完全测试
- [ ] 分号简写 ; (同一主语)
- [ ] 逗号简写 , (同一主语谓语)
- [ ] 方括号简写 [] (匿名空白节点)
- [ ] 嵌套空白节点 _:b1

---

## 3. 图模式修饰符 (Graph Pattern Modifiers)

### 3.1 可选模式 (OPTIONAL) ⭐已实现
- [x] 基础 OPTIONAL {?pattern}
- [x] OPTIONAL + FILTER
- [ ] OPTIONAL 嵌套
- [ ] 多个 OPTIONAL 链式
- [ ] OPTIONAL + UNION 组合

### 3.2 并集 (UNION) ⭐已实现
- [x] 基础 UNION
- [x] 多分支 UNION {A} UNION {B} UNION {C}
- [ ] UNION + OPTIONAL 组合
- [ ] 嵌套 UNION

### 3.3 否定 (Negation) ⬜部分实现
- [ ] MINUS (SPARQL 1.1) ⭐已测试
- [ ] NOT EXISTS (SPARQL 1.1) ⭐已测试
- [ ] FILTER NOT EXISTS
- [ ] 否定属性路径 !p

### 3.4 存在量词 (Existential) ⭐已实现
- [x] EXISTS (SPARQL 1.1)
- [x] FILTER EXISTS

---

## 4. 属性路径 (Property Paths) ⭐部分实现

### 4.1 序列路径
- [x] / 序列 (p1/p2)
- [ ] ^ 反向 (^p)
- [ ] | 替代 (p1|p2)
- [ ] 组合 (p1/p2|p3/p4)

### 4.2 重复路径
- [ ] * 零次或多次
- [ ] + 一次或多次
- [ ] ? 零次或一次
- [ ] {n} 恰好n次
- [ ] {n,m} n到m次
- [ ] {n,} 至少n次
- [ ] {,m} 最多m次

### 4.3 特殊路径
- [ ] !p 否定路径（非p）
- [ ] !(p1|p2) 否定多个
- [ ] ^ 反向链接
- [ ] a 简写 (rdf:type)

---

## 5. 过滤器 (Filters)

### 5.1 比较运算符 ⭐已实现
- [x] = 等于
- [x] != 不等于
- [x] < 小于
- [x] > 大于
- [x] <= 小于等于
- [x] >= 大于等于

### 5.2 逻辑运算符 ⭐已实现
- [x] && AND
- [x] || OR
- [x] ! NOT

### 5.3 算术运算符 ⭐部分实现
- [x] + 加法
- [x] - 减法
- [x] * 乘法
- [ ] / 除法
- [ ] 一元负号 -x

### 5.4 字符串函数 ⭐部分实现
- [x] STR 字符串转换
- [x] LANG 语言标签
- [x] DATATYPE 数据类型
- [ ] STRLEN 字符串长度
- [ ] SUBSTR 子字符串
- [ ] UCASE 转大写
- [ ] LCASE 转小写
- [ ] STRSTARTS 开始于
- [ ] STRENDS 结束于
- [ ] CONTAINS 包含 ⭐已测试
- [ ] STRBEFORE 前部
- [ ] STRAFTER 后部
- [ ] ENCODE_FOR_URI URL编码
- [ ] CONCAT 拼接 ⭐已测试
- [ ] langMatches 语言匹配
- [ ] regex 正则匹配
- [ ] REPLACE 替换

### 5.5 数学函数 ⬜未测试
- [ ] abs 绝对值
- [ ] round 四舍五入
- [ ] ceil 向上取整
- [ ] floor 向下取整
- [ ] rand 随机数

### 5.6 日期时间函数 ⬜未测试
- [ ] now 当前时间
- [ ] year 年份
- [ ] month 月份
- [ ] day 日期
- [ ] hours 小时
- [ ] minutes 分钟
- [ ] seconds 秒
- [ ] timezone 时区
- [ ] tz 时区偏移

### 5.7 IRI/URI 函数 ⬜未测试
- [ ] isIRI / isURI
- [ ] isBLANK 是否空白节点
- [ ] isLITERAL 是否字面量
- [ ] isNUMERIC 是否数值
- [ ] str 转字符串
- [ ] IRI / URI 构造
- [ ] BNODE 生成空白节点

### 5.8 杂项函数 ⬜未测试
- [ ] sameTerm 严格相等
- [ ] in (a, b, c) 多值IN ⭐已测试
- [ ] not in (a, b, c) 多值NOT IN
- [ ] COALESCE 首个非空 ⭐已测试
- [ ] IF 条件表达式 ⭐已测试
- [ ] BOUND 变量是否有绑定
- [ ] EXISTS / NOT EXISTS

---

## 6. 赋值与绑定 (Assignment)

### 6.1 BIND ⭐已实现
- [x] 基础 BIND(expr AS ?var)
- [x] 算术表达式 BIND(?x * 12 AS ?y)
- [x] 字符串函数 BIND(CONCAT(...) AS ?name)
- [ ] 复杂表达式链

### 6.2 VALUES ⭐已实现
- [x] 内联数据 VALUES ?var { val1 val2 }
- [x] 多变量 VALUES (?x ?y) { (a1 b1) (a2 b2) }
- [ ] 与 SERVICE 结合

### 6.3 赋值与聚合组合 ⬜未测试
- [ ] BIND 在聚合查询中
- [ ] VALUES 在子查询中

---

## 7. 聚合 (Aggregation)

### 7.1 聚合函数 ⭐部分实现
- [x] COUNT 计数
- [x] COUNT(DISTINCT ?x)
- [x] SUM 求和
- [x] AVG 平均值
- [x] MIN 最小值
- [x] MAX 最大值
- [ ] GROUP_CONCAT 组内拼接
- [ ] GROUP_CONCAT SEPARATOR
- [ ] SAMPLE 随机采样

### 7.2 分组与过滤 ⭐已实现
- [x] GROUP BY 单列
- [x] GROUP BY 多列 ⭐已测试
- [x] HAVING 聚合后过滤
- [ ] GROUP BY 表达式

### 7.3 复杂聚合场景 ⬜未测试
- [ ] 嵌套聚合
- [ ] 多聚合函数组合
- [ ] 带 FILTER 的聚合

---

## 8. 子查询 (Subqueries)

### 8.1 基础子查询 ⭐部分实现
- [x] SELECT 子查询在 WHERE 中
- [ ] ASK 子查询
- [ ] CONSTRUCT 子查询

### 8.2 相关子查询 ⬜未测试
- [ ] 子查询引用外部变量
- [ ] 子查询投影限制

### 8.3 嵌套层次 ⬜未测试
- [ ] 单层嵌套
- [ ] 多层嵌套
- [ ] 关联多个子查询

---

## 9. 结果修饰 (Solution Modifiers)

### 9.1 排序 ⭐已实现
- [x] ORDER BY ASC
- [x] ORDER BY DESC
- [x] ORDER BY 多列
- [ ] ORDER BY 表达式

### 9.2 结果限制 ⭐已实现
- [x] LIMIT n
- [x] OFFSET m
- [x] LIMIT + OFFSET 组合

### 9.3 去重 ⭐已实现
- [x] DISTINCT
- [ ] REDUCED (SPARQL 1.1)

---

## 10. 命名图与数据集 (Named Graphs & Datasets)

### 10.1 GRAPH 关键字 ⬜未测试
- [ ] GRAPH ?g { ?s ?p ?o }
- [ ] GRAPH <uri> { ... }
- [ ] 变量图模式

### 10.2 数据集描述 ⬜未测试
- [ ] FROM <uri> 默认图
- [ ] FROM NAMED <uri> 命名图
- [ ] 多 FROM 组合

### 10.3 图模式操作 ⬜未测试
- [ ] GRAPH + OPTIONAL
- [ ] GRAPH + UNION
- [ ] 嵌套 GRAPH

---

## 11. 服务描述 (Federated Query) ⭐部分实现

### 11.1 SERVICE 关键字 ⭐已测试
- [x] SERVICE <endpoint> { ... }
- [ ] SERVICE 变量 ?endpoint
- [ ] SERVICE SILENT (容错)

### 11.2 服务组合 ⬜未测试
- [ ] 多 SERVICE 联合
- [ ] SERVICE + BIND
- [ ] SERVICE + 本地数据 JOIN

---

## 12. 前缀与命名 (Prefix & Names)

### 12.1 前缀声明 ⭐已实现
- [x] PREFIX x: <uri>
- [x] 多个前缀
- [x] 前缀简写使用 x:local
- [x] 默认前缀 :local
- [x] BASE 基础URI

### 12.2 IRI 引用 ⭐已实现
- [x] 绝对 IRI <http://...>
- [x] 相对 IRI <relative>
- [x] 前缀扩展 prefix:local

---

## 13. 注释与格式 (Comments & Formatting)

### 13.1 注释 ⬜未测试
- [ ] # 行注释
- [ ] /* 块注释 */
- [ ] 注释在任意位置

---

## 14. SPARQL 1.1 新增特性

### 14.1 显式隐式连接 ⬜未测试
- [ ] 隐式连接（同一WHERE多个模式）
- [ ] 显式 JOIN（通过变量关联）

### 14.2 属性路径增强 ⬜未测试
- [ ] 复杂路径嵌套
- [ ] 路径长度限制

### 14.3 子查询增强 ⬜未测试
- [ ] 相关子查询优化
- [ ] 子查询结果限制

### 14.4 聚合增强 ⭐部分实现
- [x] GROUP_CONCAT
- [ ] 自定义聚合

### 14.5 绑定增强 ⭐部分实现
- [x] VALUES 数据块
- [ ] BINDINGS (旧语法兼容)

---

## 当前测试覆盖率统计

| 类别 | 已覆盖 | 总计 | 覆盖率 |
|------|--------|------|--------|
| 查询形式 | 3 | 4 | 75% |
| 基础图模式 | 6 | 9 | 67% |
| 图模式修饰符 | 5 | 10 | 50% |
| 属性路径 | 2 | 12 | 17% |
| 过滤器 | 15 | 40 | 38% |
| 赋值与绑定 | 5 | 8 | 63% |
| 聚合 | 6 | 10 | 60% |
| 子查询 | 2 | 6 | 33% |
| 结果修饰 | 5 | 7 | 71% |
| 命名图 | 0 | 6 | 0% |
| 服务描述 | 1 | 4 | 25% |
| 前缀与命名 | 5 | 5 | 100% |
| **总计** | **~55** | **~121** | **~45%** |

---

## 优先级测试补充建议

### 🔴 高优先级（核心功能缺失）
1. 属性路径完整覆盖（* + ? / ^ 等）
2. CONSTRUCT 查询形式
3. 日期时间函数
4. GRAPH 命名图支持

### 🟡 中优先级（常用功能）
1. 字符串函数完整覆盖
2. 数学函数
3. 复杂子查询场景
4. 多 SERVICE 联合

### 🟢 低优先级（边缘特性）
1. REDUCED 修饰符
2. 注释处理
3. 自定义聚合
4. BINDINGS 旧语法
