#!/usr/bin/env python3
"""
Sprint 9 P1 GeoSPARQL 度量函数测试 - GEOF:DISTANCE 和 GEOF:BUFFER

测试目标：验证GeoSPARQL度量函数在OBDA架构下的SQL生成
注意：需要PostGIS扩展支持
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestGeofDistance(TestCaseBase):
    """测试 geof:distance 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
          PREFIX geo: <http://www.opengis.net/ont/geosparql#>
          PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
          PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>

          SELECT ?store ?dist
          WHERE {
            ?store a <http://example.org/Store> .
            ?store <http://example.org/geometry> ?wkt .
            BIND(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) AS ?dist)
            FILTER(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) < 10000)
          }
          ORDER BY ?store
          LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P1-2] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Distance"""
        baseline_sql = """
          SELECT store_id AS store,
                 ST_Distance(
                   ST_SetSRID(ST_SetSRID(geometry, 4326), 4326),
                   ST_GeomFromText('POINT(116.4074 39.9042)', 4326)
                 ) AS dist
          FROM stores
          WHERE ST_Distance(ST_SetSRID(ST_SetSRID(geometry, 4326), 4326), ST_GeomFromText('POINT(116.4074 39.9042)', 4326)) < 10000
          ORDER BY store
          LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeofBuffer(TestCaseBase):
    """测试 geof:buffer 函数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?poi
        WHERE {
          ?poi a <http://example.org/POI> .
          ?poi geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfWithin(?wkt, geof:buffer("POINT(116.4 39.9)"^^geo:wktLiteral, 5000)))
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Buffer + ST_Within"""
        baseline_sql = """
        SELECT poi_id AS poi
        FROM pois
        WHERE ST_Within(
          ST_SetSRID(geometry, 4326),
          ST_Buffer(ST_GeomFromText('POINT(116.4 39.9)', 4326), 5000)
        )
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeofDistanceWithVar(TestCaseBase):
    """测试 geof:distance 动态点"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
          PREFIX geo: <http://www.opengis.net/ont/geosparql#>
          PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
          PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>

          SELECT ?dist
          WHERE {
            BIND(geof:distance("POINT(116.4074 39.9042)"^^geo:wktLiteral, "POINT(116.4174 39.9142)"^^geo:wktLiteral, uom:metre) AS ?dist)
          }
          LIMIT 20
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Distance 动态计算"""
        baseline_sql = """
          SELECT ST_Distance(
              ST_GeomFromText('POINT(116.4074 39.9042)', 4326),
              ST_GeomFromText('POINT(116.4174 39.9142)', 4326)
          ) AS dist
          LIMIT 20
        """
        return self.execute_sql_query(baseline_sql)


class TestGeofBufferWithUnit(TestCaseBase):
    """测试 geof:buffer 带单位参数"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
        
        SELECT ?city
        WHERE {
          ?city a <http://example.org/City> .
            ?city geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfIntersects(?wkt, geof:buffer("POINT(116.4 39.9)"^^geo:wktLiteral, 10000, uom:metre)))
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Buffer 带单位"""
        baseline_sql = """
        SELECT city_id AS city
        FROM cities
        WHERE ST_Intersects(
          ST_SetSRID(geometry, 4326),
          ST_Buffer(ST_GeomFromText('POINT(116.4 39.9)', 4326), 10000)
        )
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': os.environ.get('PGUSER', 'yuxiaoyu'),
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("S9-P1 GeoSPARQL - geof:distance", TestGeofDistance),
        ("S9-P1 GeoSPARQL - geof:buffer", TestGeofBuffer),
        ("S9-P1 GeoSPARQL - distance with var", TestGeofDistanceWithVar),
        ("S9-P1 GeoSPARQL - buffer with unit", TestGeofBufferWithUnit),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class(db_config))
        if not result['passed']:
            all_passed = False
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
