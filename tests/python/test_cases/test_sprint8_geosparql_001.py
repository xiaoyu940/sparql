#!/usr/bin/env python3
"""
Sprint 8 GeoSPARQL 基础测试

测试目标：验证 GeoSPARQL 空间函数的正确翻译
使用 PostGIS 函数映射
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestGeoSparqlWithin(TestCaseBase):
    """GeoSPARQL sfWithin 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?city ?name
        WHERE {
          ?city a <http://example.org/POI> .
          ?city <http://example.org/poi_name> ?name .
          ?city geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfWithin(?wkt, "POLYGON((-1 -1, 2 -1, 2 2, -1 2, -1 -1))"^^geo:wktLiteral))
        }
        ORDER BY ?city
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Within"""
        baseline_sql = """
        SELECT poi_id AS "city", poi_name AS "name"
        FROM pois
        WHERE ST_Within(
            ST_SetSRID(geometry, 4326),
            ST_GeomFromText('POLYGON((-1 -1, 2 -1, 2 2, -1 2, -1 -1))', 4326)
        )
        ORDER BY poi_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeoSparqlContains(TestCaseBase):
    """GeoSPARQL sfContains 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?region ?name
        WHERE {
          ?region a <http://example.org/Region> .
          ?region <http://example.org/region_name> ?name .
          ?region geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfContains(?wkt, "POINT(1 1)"^^geo:wktLiteral))
        }
        ORDER BY ?region
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Contains"""
        baseline_sql = """
        SELECT region_id AS "region", region_name AS "name"
        FROM regions
        WHERE ST_Contains(
            ST_SetSRID(geometry, 4326),
            ST_GeomFromText('POINT(1 1)', 4326)
        )
        ORDER BY region_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeoSparqlIntersects(TestCaseBase):
    """GeoSPARQL sfIntersects 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?road ?name
        WHERE {
          ?road a <http://example.org/Road> .
          ?road <http://example.org/road_name> ?name .
          ?road geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfIntersects(?wkt, "LINESTRING(0 5, 10 5)"^^geo:wktLiteral))
        }
        ORDER BY ?road
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Intersects"""
        baseline_sql = """
        SELECT road_id AS "road", road_name AS "name"
        FROM roads
        WHERE ST_Intersects(
            ST_SetSRID(geometry, 4326),
            ST_GeomFromText('LINESTRING(0 5, 10 5)', 4326)
        )
        ORDER BY road_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeoSparqlDistance(TestCaseBase):
    """GeoSPARQL distance 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
        
        SELECT ?city ?name ?dist
        WHERE {
          ?city a <http://example.org/Region> .
          ?city <http://example.org/region_name> ?name .
          ?city geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          BIND(geof:distance(?wkt, "POINT(1 1)"^^geo:wktLiteral, uom:metre) AS ?dist)
        }
        ORDER BY ?dist
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Distance"""
        baseline_sql = """
        SELECT region_id AS "city", region_name AS "name",
               ST_Distance(ST_SetSRID(ST_SetSRID(geometry, 4326), 4326), ST_GeomFromText('POINT(1 1)', 4326)) AS "dist"
        FROM regions
        ORDER BY "dist"
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeoSparqlBuffer(TestCaseBase):
    """GeoSPARQL buffer 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?poi ?name
        WHERE {
          ?poi a <http://example.org/POI> .
          ?poi <http://example.org/poi_name> ?name .
          ?poi geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfWithin(?wkt, geof:buffer("POINT(0 0)"^^geo:wktLiteral, 5000, <http://www.opengis.net/def/uom/OGC/1.0/metre>)))
        }
        ORDER BY ?poi
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Buffer + ST_Within"""
        baseline_sql = """
        SELECT poi_id AS "poi", poi_name AS "name"
        FROM pois
        WHERE ST_Within(
            ST_SetSRID(geometry, 4326),
            ST_Buffer(ST_GeogFromText('POINT(0 0)'), 5000)::geometry
        )
        ORDER BY poi_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestGeoSparqlOverlaps(TestCaseBase):
    """GeoSPARQL sfOverlaps 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?zone ?name
        WHERE {
          ?zone a <http://example.org/Zone> .
          ?zone <http://example.org/zone_name> ?name .
          ?zone geo:hasGeometry ?geom .
          ?geom geo:asWKT ?wkt .
          FILTER(geof:sfOverlaps(?wkt, "POLYGON((4 4, 8 4, 8 8, 4 8, 4 4))"^^geo:wktLiteral))
        }
        ORDER BY ?zone
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - ST_Overlaps"""
        baseline_sql = """
        SELECT zone_id AS "zone", zone_name AS "name"
        FROM zones
        WHERE ST_Overlaps(
            ST_SetSRID(geometry, 4326),
            ST_GeomFromText('POLYGON((4 4, 8 4, 8 8, 4 8, 4 4))', 4326)
        )
        ORDER BY zone_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("GeoSPARQL - sfWithin 点在面内", TestGeoSparqlWithin),
        ("GeoSPARQL - sfContains 面含点", TestGeoSparqlContains),
        ("GeoSPARQL - sfIntersects 相交", TestGeoSparqlIntersects),
        ("GeoSPARQL - distance 距离", TestGeoSparqlDistance),
        ("GeoSPARQL - buffer 缓冲区", TestGeoSparqlBuffer),
        ("GeoSPARQL - sfOverlaps 重叠", TestGeoSparqlOverlaps),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class())
        if not result['passed']:
            all_passed = False
            print(f"✗ 失败: {result.get('errors', [])}")
        else:
            print(f"✓ 测试通过")
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
