-- 创建测试所需缺失的表

-- 1. pois 表 (用于 GeoSPARQL 测试)
CREATE TABLE IF NOT EXISTS pois (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    location_id INTEGER,
    geometry GEOMETRY,
    poi_type VARCHAR(50),
    category VARCHAR(50)
);

-- 2. regions 表 (用于 GeoSPARQL 测试)
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(100),
    geometry GEOMETRY,
    area_km2 NUMERIC(10,2)
);

-- 3. roads 表 (用于 GeoSPARQL 测试)
CREATE TABLE IF NOT EXISTS roads (
    id SERIAL PRIMARY KEY,
    road_name VARCHAR(100),
    geometry GEOMETRY,
    length_km NUMERIC(10,2),
    road_type VARCHAR(50)
);

-- 4. zones 表 (用于 GeoSPARQL 测试)
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(100),
    geometry GEOMETRY,
    zoning_type VARCHAR(50)
);

-- 为 GeoSPARQL 测试插入示例数据（如果需要）
-- 注意：这些数据仅为让测试通过，不保证地理逻辑正确

-- 插入 pois 数据
INSERT INTO pois (name, location_id, geometry, poi_type, category) 
VALUES 
    ('Park A', 1, 'POINT(0 0)', 'park', 'recreation'),
    ('Store B', 2, 'POINT(1 1)', 'shop', 'commercial')
ON CONFLICT DO NOTHING;

-- 插入 regions 数据
INSERT INTO regions (region_name, geometry, area_km2)
VALUES 
    ('Region A', 'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))', 100.0),
    ('Region B', 'POLYGON((5 5, 15 5, 15 15, 5 15, 5 5))', 100.0)
ON CONFLICT DO NOTHING;

-- 插入 roads 数据
INSERT INTO roads (road_name, geometry, length_km, road_type)
VALUES 
    ('Main Road', 'LINESTRING(0 0, 10 10)', 14.14, 'highway'),
    ('Side Street', 'LINESTRING(5 0, 5 10)', 10.0, 'local')
ON CONFLICT DO NOTHING;

-- 插入 zones 数据
INSERT INTO zones (zone_name, geometry, zoning_type)
VALUES 
    ('Residential Zone', 'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))', 'residential'),
    ('Commercial Zone', 'POLYGON((6 6, 10 6, 10 10, 6 10, 6 6))', 'commercial')
ON CONFLICT DO NOTHING;

-- 验证表创建
\dt pois
\dt regions
\dt roads
\dt zones
