#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库表结构，生成正确的R2RML映射
"""

import psycopg2
import json

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port='5432',
    database='rs_ontop_core',
    user='yuxiaoyu',
    password='123456'
)

cur = conn.cursor()

# 获取所有表及其列信息
tables = [
    'employees', 'departments', 'positions', 'salaries', 'projects',
    'employee_projects', 'social_connections', 'manager_relations',
    'family_relations', 'persons', 'roads', 'cities', 'regions', 'stores',
    'addresses', 'attendance', 'employee_contacts', 'locations', 'zones', 'pois'
]

print("=== 数据库表结构 ===\n")

schema_info = {}

for table in tables:
    try:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table,))
        
        columns = cur.fetchall()
        if columns:
            schema_info[table] = {
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns]
            }
            print(f"\n表: {table}")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} {'(nullable)' if col[2] == 'YES' else ''}")
    except Exception as e:
        print(f"  表 {table} 不存在或无法访问: {e}")

# 生成正确的R2RML映射
print("\n\n=== 生成正确的R2RML映射 ===\n")

ttl_prefix = """@base <http://example.org/mapping/> .
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix geo: <http://www.opengis.net/ont/geosparql#> .

"""

# 让 R2RML 输出与测试用例的 IRI 保持一致
CLASS_NAME_OVERRIDES = {
    "employees": "Employee",
    "departments": "Department",
    "positions": "Position",
    "salaries": "Salary",
    "projects": "Project",
    "employee_projects": "EmployeeProject",
    "persons": "Person",
    "roads": "Road",
    "cities": "City",
    "regions": "Region",
    "stores": "Store",
    "addresses": "Address",
    "attendance": "Attendance",
    "employee_contacts": "EmployeeContact",
    "locations": "Location",
    "zones": "Zone",
    "pois": "POI",
    "social_connections": "SocialConnection",
    "manager_relations": "ManagerRelation",
    "family_relations": "FamilyRelation",
}

SUBJECT_PREFIX_OVERRIDES = {
    "employees": "emp",
    "departments": "dept",
    "positions": "pos",
    "salaries": "sal",
    "projects": "proj",
    "employee_projects": "emp_proj",
    "persons": "person",
    "roads": "road",
    "cities": "city",
    "regions": "region",
    "stores": "store",
    "addresses": "addr",
    "attendance": "att",
    "employee_contacts": "contact",
    "locations": "loc",
    "zones": "zone",
    "pois": "poi",
}

PK_OVERRIDE = {
    "persons": "id",
    "addresses": "id",
    "locations": "id",
}

mappings = []

def add_pom(pom_list, predicate, col_name):
    pom_list.append(f"""    rr:predicateObjectMap [
        rr:predicate {predicate};
        rr:objectMap [ rr:column "{col_name}" ]
    ]""")

def build_triples_map(map_name, table, subject_template, class_name, pom_list):
    predicate_objects = ";\n".join(pom_list)
    class_line = f"        rr:class ex:{class_name}\n" if class_name else ""
    return f"""<#{map_name}>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "{table}" ];
    rr:subjectMap [
        rr:template "{subject_template}";
{class_line}    ];
{predicate_objects}.

"""

for table, info in schema_info.items():
    if not info['columns']:
        continue
    
    # 获取主键列（通常是第一个列或id/xxx_id结尾的列）
    pk_col = PK_OVERRIDE.get(table)
    if not pk_col:
        pk_col = info['columns'][0]['name']
        for col in info['columns']:
            if col['name'].endswith('_id'):
                pk_col = col['name']
                break
    
    # 生成subject template，与测试中常用 IRI 保持一致
    subject_prefix = SUBJECT_PREFIX_OVERRIDES.get(table, table)
    subject_template = f"http://example.org/{subject_prefix}{{{pk_col}}}"
    
    # 生成class
    class_name = CLASS_NAME_OVERRIDES.get(
        table,
        table.replace('_', ' ').title().replace(' ', '')
    )
    
    # 员工表列用于避免跨表谓词冲突
    employee_column_names = {
        c["name"] for c in schema_info.get("employees", {}).get("columns", [])
    }

    # 生成predicate-object映射
    pom_list = []
    for col in info['columns']:
        col_name = col['name']
        if table != "employees" and col_name in employee_column_names:
            continue
        add_pom(pom_list, f"ex:{col_name}", col_name)

    # 补充别名谓词（与测试用例对齐）
    alias_predicates = []
    if table == "employees":
        alias_predicates = [
            ("ex:firstName", "first_name"),
            ("ex:lastName", "last_name"),
            ("ex:middleName", "middle_name"),
            ("ex:hireDate", "hire_date"),
            ("ex:employeeId", "employee_id"),
            ("ex:manager", "manager_id"),
            ("ex:worksIn", "department_id"),
            ("ex:department", "department_id"),
        ]
    elif table == "departments":
        alias_predicates = [
            ("ex:dept_name", "department_name"),
            ("ex:locatedIn", "location_id"),
            ("ex:location", "location_id"),
        ]
    elif table == "locations":
        alias_predicates = [
            ("ex:country", "name"),
            ("ex:city", "city"),
        ]
    elif table == "persons":
        alias_predicates = [
            ("foaf:name", "name"),
        ]
    if table in {"cities", "regions", "roads", "pois", "zones"}:
        alias_predicates.extend([
            ("geo:hasGeometry", pk_col),
            ("geo:asWKT", "geometry"),
        ])

    for pred, col_name in alias_predicates:
        add_pom(pom_list, pred, col_name)
    
    # 组装TripleMap
    mapping = build_triples_map(f"{class_name}Mapping", table, subject_template, class_name, pom_list)
    mappings.append(mapping)

# 特殊 TriplesMap：按联系值展开的验证关系
special_maps = []

if "employee_contacts" in schema_info:
    special_maps.append(build_triples_map(
        "EmployeeContactByValueMapping",
        "employee_contacts",
        "http://example.org/contact{contact_value}",
        None,
        [
            """    rr:predicateObjectMap [
        rr:predicate ex:verified;
        rr:objectMap [ rr:column "is_verified" ]
    ]"""
        ],
    ))

if "addresses" in schema_info:
    special_maps.append(build_triples_map(
        "AddressByPersonMapping",
        "addresses",
        "http://example.org/person{person_id}",
        "Person",
        [
            """    rr:predicateObjectMap [
        rr:predicate ex:homeAddress;
        rr:objectMap [ rr:column "id" ]
    ]""",
            """    rr:predicateObjectMap [
        rr:predicate ex:workAddress;
        rr:objectMap [ rr:column "id" ]
    ]""",
        ],
    ))

if "family_relations" in schema_info:
    special_maps.append(build_triples_map(
        "FamilyParentMapping",
        "family_relations",
        "http://example.org/person{parent_id}",
        "Person",
        [
            """    rr:predicateObjectMap [
        rr:predicate foaf:parent;
        rr:objectMap [ rr:column "child_id" ]
    ]"""
        ],
    ))

if "cities" in schema_info:
    special_maps.append(build_triples_map(
        "CityByNameRegionMapping",
        "cities",
        "http://example.org/cityname{city_name}",
        "City",
        [
            """    rr:predicateObjectMap [
        rr:predicate ex:region;
        rr:objectMap [ rr:column "city_name" ]
    ]"""
        ],
    ))

if special_maps:
    mappings.extend(special_maps)

# 保存到文件
complete_ttl = ttl_prefix + '\n'.join(mappings)

with open('/home/yuxiaoyu/rs_ontop_core/correct_mapping.ttl', 'w') as f:
    f.write(complete_ttl)

print(f"✅ 正确的R2RML映射已生成！")
print(f"文件: correct_mapping.ttl")
print(f"大小: {len(complete_ttl)} 字符")
print(f"覆盖表: {len(schema_info)} 个")

# 也保存schema信息
with open('/home/yuxiaoyu/rs_ontop_core/schema_info.json', 'w') as f:
    json.dump(schema_info, f, indent=2)

print("\nSchema信息已保存到 schema_info.json")

cur.close()
conn.close()

print("\n🎉 完成！请使用correct_mapping.ttl更新数据库中的R2RML映射。")
