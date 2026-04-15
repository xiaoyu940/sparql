#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成完整的R2RML映射，覆盖所有数据库表和关系
"""

import subprocess
import os

env = os.environ.copy()
env['PGPASSWORD'] = '123456'

def run_sql(sql):
    cmd = ['bash', '-c', f"export PGPASSWORD=123456 && psql -h localhost -p 5432 -U yuxiaoyu -d rs_ontop_core -t -c \"{sql}\""]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout.strip()

def escape_sql_string(s):
    return s.replace("'", "''")

# 生成完整的R2RML映射TTL内容
def generate_complete_r2rml():
    ttl_content = """@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .
@prefix emp: <http://example.org/employee#> .
@prefix dept: <http://example.org/department#> .
@prefix pos: <http://example.org/position#> .
@prefix sal: <http://example.org/salary#> .
@prefix proj: <http://example.org/project#> .
@prefix soc: <http://example.org/social#> .
@prefix man: <http://example.org/manager#> .
@prefix fam: <http://example.org/family#> .
@prefix road: <http://example.org/road#> .
@prefix city: <http://example.org/city#> .
@prefix reg: <http://example.org/region#> .
@prefix store: <http://example.org/store#> .
@prefix addr: <http://example.org/address#> .
@prefix attend: <http://example.org/attendance#> .
@prefix contact: <http://example.org/contact#> .
@prefix loc: <http://example.org/location#> .
@prefix zone: <http://example.org/zone#> .
@prefix poi: <http://example.org/poi#> .

# Employees表映射
<#EmployeesMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "employees" ];
    rr:subjectMap [
        rr:template "http://example.org/employee/{employee_id}";
        rr:class ex:Employee
    ];
    rr:predicateObjectMap [
        rr:predicate emp:first_name;
        rr:objectMap [ rr:column "first_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:last_name;
        rr:objectMap [ rr:column "last_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:email;
        rr:objectMap [ rr:column "email" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:hire_date;
        rr:objectMap [ rr:column "hire_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:salary;
        rr:objectMap [ rr:column "salary" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:department_id;
        rr:objectMap [ rr:column "department_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:position_id;
        rr:objectMap [ rr:column "position_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:manager_id;
        rr:objectMap [ rr:column "manager_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:name;
        rr:objectMap [ rr:column "name" ]
    ].

# Departments表映射
<#DepartmentsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "departments" ];
    rr:subjectMap [
        rr:template "http://example.org/department/{department_id}";
        rr:class ex:Department
    ];
    rr:predicateObjectMap [
        rr:predicate dept:department_name;
        rr:objectMap [ rr:column "department_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate dept:location;
        rr:objectMap [ rr:column "location" ]
    ];
    rr:predicateObjectMap [
        rr:predicate dept:budget;
        rr:objectMap [ rr:column "budget" ]
    ];
    rr:predicateObjectMap [
        rr:predicate dept:id;
        rr:objectMap [ rr:column "department_id" ]
    ].

# Positions表映射
<#PositionsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "positions" ];
    rr:subjectMap [
        rr:template "http://example.org/position/{position_id}";
        rr:class ex:Position
    ];
    rr:predicateObjectMap [
        rr:predicate pos:position_title;
        rr:objectMap [ rr:column "position_title" ]
    ];
    rr:predicateObjectMap [
        rr:predicate pos:department_id;
        rr:objectMap [ rr:column "department_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate pos:salary_min;
        rr:objectMap [ rr:column "salary_min" ]
    ];
    rr:predicateObjectMap [
        rr:predicate pos:salary_max;
        rr:objectMap [ rr:column "salary_max" ]
    ];
    rr:predicateObjectMap [
        rr:predicate pos:id;
        rr:objectMap [ rr:column "position_id" ]
    ].

# Salaries表映射
<#SalariesMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "salaries" ];
    rr:subjectMap [
        rr:template "http://example.org/salary/{salary_id}";
        rr:class ex:Salary
    ];
    rr:predicateObjectMap [
        rr:predicate sal:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate sal:amount;
        rr:objectMap [ rr:column "amount" ]
    ];
    rr:predicateObjectMap [
        rr:predicate sal:effective_date;
        rr:objectMap [ rr:column "effective_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate sal:department_id;
        rr:objectMap [ rr:column "department_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate sal:id;
        rr:objectMap [ rr:column "salary_id" ]
    ].

# Projects表映射
<#ProjectsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "projects" ];
    rr:subjectMap [
        rr:template "http://example.org/project/{project_id}";
        rr:class ex:Project
    ];
    rr:predicateObjectMap [
        rr:predicate proj:project_name;
        rr:objectMap [ rr:column "project_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:start_date;
        rr:objectMap [ rr:column "start_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:end_date;
        rr:objectMap [ rr:column "end_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:budget;
        rr:objectMap [ rr:column "budget" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:id;
        rr:objectMap [ rr:column "project_id" ]
    ].

# Employee_Projects表映射
<#EmployeeProjectsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "employee_projects" ];
    rr:subjectMap [
        rr:template "http://example.org/employee_project/{employee_id}_{project_id}";
        rr:class ex:EmployeeProject
    ];
    rr:predicateObjectMap [
        rr:predicate proj:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:project_id;
        rr:objectMap [ rr:column "project_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate proj:role;
        rr:objectMap [ rr:column "role" ]
    ].

# Social_Connections表映射
<#SocialConnectionsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "social_connections" ];
    rr:subjectMap [
        rr:template "http://example.org/social/{connection_id}";
        rr:class ex:SocialConnection
    ];
    rr:predicateObjectMap [
        rr:predicate soc:person_id;
        rr:objectMap [ rr:column "person_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate soc:connection_type;
        rr:objectMap [ rr:column "connection_type" ]
    ];
    rr:predicateObjectMap [
        rr:predicate soc:connection_date;
        rr:objectMap [ rr:column "connection_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate soc:id;
        rr:objectMap [ rr:column "connection_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate soc:department_id;
        rr:objectMap [ rr:column "department_id" ]
    ].

# Manager_Relations表映射
<#ManagerRelationsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "manager_relations" ];
    rr:subjectMap [
        rr:template "http://example.org/manager/{manager_id}_{employee_id}";
        rr:class ex:ManagerRelation
    ];
    rr:predicateObjectMap [
        rr:predicate man:manager_id;
        rr:objectMap [ rr:column "manager_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate man:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate man:relation_type;
        rr:objectMap [ rr:column "relation_type" ]
    ].

# Family_Relations表映射
<#FamilyRelationsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "family_relations" ];
    rr:subjectMap [
        rr:template "http://example.org/family/{relation_id}";
        rr:class ex:FamilyRelation
    ];
    rr:predicateObjectMap [
        rr:predicate fam:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate fam:relation_type;
        rr:objectMap [ rr:column "relation_type" ]
    ];
    rr:predicateObjectMap [
        rr:predicate fam:id;
        rr:objectMap [ rr:column "relation_id" ]
    ].

# Persons表映射
<#PersonsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "persons" ];
    rr:subjectMap [
        rr:template "http://example.org/person/{person_id}";
        rr:class ex:Person
    ];
    rr:predicateObjectMap [
        rr:predicate emp:name;
        rr:objectMap [ rr:column "name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:email;
        rr:objectMap [ rr:column "email" ]
    ];
    rr:predicateObjectMap [
        rr:predicate emp:hire_date;
        rr:objectMap [ rr:column "hire_date" ]
    ].

# Roads表映射
<#RoadsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "roads" ];
    rr:subjectMap [
        rr:template "http://example.org/road/{id}";
        rr:class ex:Road
    ];
    rr:predicateObjectMap [
        rr:predicate road:name;
        rr:objectMap [ rr:column "road_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate road:length_km;
        rr:objectMap [ rr:column "length_km" ]
    ];
    rr:predicateObjectMap [
        rr:predicate road:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# Cities表映射
<#CitiesMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "cities" ];
    rr:subjectMap [
        rr:template "http://example.org/city/{city_id}";
        rr:class ex:City
    ];
    rr:predicateObjectMap [
        rr:predicate city:name;
        rr:objectMap [ rr:column "city_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate city:population;
        rr:objectMap [ rr:column "population" ]
    ];
    rr:predicateObjectMap [
        rr:predicate city:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# Regions表映射
<#RegionsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "regions" ];
    rr:subjectMap [
        rr:template "http://example.org/region/{region_id}";
        rr:class ex:Region
    ];
    rr:predicateObjectMap [
        rr:predicate reg:region_name;
        rr:objectMap [ rr:column "region_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate reg:area_km2;
        rr:objectMap [ rr:column "area_km2" ]
    ];
    rr:predicateObjectMap [
        rr:predicate reg:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# Stores表映射
<#StoresMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "stores" ];
    rr:subjectMap [
        rr:template "http://example.org/store/{store_id}";
        rr:class ex:Store
    ];
    rr:predicateObjectMap [
        rr:predicate store:store_name;
        rr:objectMap [ rr:column "store_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate store:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# Addresses表映射
<#AddressesMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "addresses" ];
    rr:subjectMap [
        rr:template "http://example.org/address/{address_id}";
        rr:class ex:Address
    ];
    rr:predicateObjectMap [
        rr:predicate addr:street;
        rr:objectMap [ rr:column "street" ]
    ];
    rr:predicateObjectMap [
        rr:predicate addr:city;
        rr:objectMap [ rr:column "city" ]
    ];
    rr:predicateObjectMap [
        rr:predicate addr:postal_code;
        rr:objectMap [ rr:column "postal_code" ]
    ].

# Attendance表映射
<#AttendanceMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "attendance" ];
    rr:subjectMap [
        rr:template "http://example.org/attendance/{attendance_id}";
        rr:class ex:Attendance
    ];
    rr:predicateObjectMap [
        rr:predicate attend:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate attend:attendance_date;
        rr:objectMap [ rr:column "attendance_date" ]
    ];
    rr:predicateObjectMap [
        rr:predicate attend:status;
        rr:objectMap [ rr:column "status" ]
    ].

# Employee_Contacts表映射
<#EmployeeContactsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "employee_contacts" ];
    rr:subjectMap [
        rr:template "http://example.org/contact/{contact_id}";
        rr:class ex:EmployeeContact
    ];
    rr:predicateObjectMap [
        rr:predicate contact:employee_id;
        rr:objectMap [ rr:column "employee_id" ]
    ];
    rr:predicateObjectMap [
        rr:predicate contact:contact_type;
        rr:objectMap [ rr:column "contact_type" ]
    ];
    rr:predicateObjectMap [
        rr:predicate contact:contact_value;
        rr:objectMap [ rr:column "contact_value" ]
    ].

# Locations表映射
<#LocationsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "locations" ];
    rr:subjectMap [
        rr:template "http://example.org/location/{location_id}";
        rr:class ex:Location
    ];
    rr:predicateObjectMap [
        rr:predicate loc:location_name;
        rr:objectMap [ rr:column "location_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate loc:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# Zones表映射
<#ZonesMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "zones" ];
    rr:subjectMap [
        rr:template "http://example.org/zone/{zone_id}";
        rr:class ex:Zone
    ];
    rr:predicateObjectMap [
        rr:predicate zone:zone_name;
        rr:objectMap [ rr:column "zone_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate zone:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].

# POIs表映射
<#POIsMapping>
    a rr:TriplesMap;
    rr:logicalTable [ rr:tableName "pois" ];
    rr:subjectMap [
        rr:template "http://example.org/poi/{poi_id}";
        rr:class ex:POI
    ];
    rr:predicateObjectMap [
        rr:predicate poi:poi_name;
        rr:objectMap [ rr:column "poi_name" ]
    ];
    rr:predicateObjectMap [
        rr:predicate poi:geometry;
        rr:objectMap [ rr:column "geometry" ]
    ].
"""
    return ttl_content

# 清空现有R2RML映射并插入完整映射
print("=== 清空现有R2RML映射 ===")
result = run_sql("DELETE FROM ontop_r2rml_mappings;")
print(result)

print("\n=== 生成完整R2RML映射 ===")
ttl_content = generate_complete_r2rml()
escaped_content = escape_sql_string(ttl_content)

print(f"映射内容长度: {len(ttl_content)} 字符")

print("\n=== 插入完整R2RML映射 ===")
insert_sql = f"""
INSERT INTO ontop_r2rml_mappings (name, ttl_content, created_at, updated_at)
VALUES ('complete_mapping', '{escaped_content}', NOW(), NOW());
"""

result = run_sql(insert_sql)
print(result)

print("\n=== 验证插入结果 ===")
count = run_sql("SELECT COUNT(*) FROM ontop_r2rml_mappings;")
print(f"R2RML映射数量: {count}")

size = run_sql("SELECT LENGTH(ttl_content) FROM ontop_r2rml_mappings WHERE name = 'complete_mapping';")
print(f"完整映射大小: {size} 字符")

print("\n✅ 完整R2RML映射已插入！")
print("请运行 ontops_refresh() 刷新引擎，然后重新测试。")
