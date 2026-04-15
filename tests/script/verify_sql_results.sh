#!/bin/bash
# SQL执行结果验证脚本 - 支持密码认证

echo "=== PostgreSQL SQL执行结果验证 ==="
echo ""

# 设置密码（如果需要通过环境变量）
# export PGPASSWORD="your_password"
# 或者使用 .pgpass 文件

# 1. 检查PostgreSQL连接
echo "1. 检查PostgreSQL连接..."
if pg_isready -h localhost -p 5432 -U yuxiaoyu > /dev/null 2>&1; then
    echo "   ✅ PostgreSQL连接正常"
else
    echo "   ⚠️  PostgreSQL可能需要启动或配置"
    echo "   尝试启动PostgreSQL..."
    sudo service postgresql start 2>/dev/null || sudo systemctl start postgresql 2>/dev/null
    sleep 2
fi

# 2. 验证免密访问配置
echo ""
echo "2. 验证免密访问..."
if psql -U yuxiaoyu -d rs_ontop_core -c "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ 免密访问已配置"
else
    echo "   ⚠️  需要密码，请配置 ~/.pgpass 文件或 pg_hba.conf"
    echo ""
    echo "   配置方案A - 修改pg_hba.conf为trust模式:"
    echo "   sudo sed -i 's/scram-sha-256/trust/g' /etc/postgresql/*/main/pg_hba.conf"
    echo "   sudo service postgresql restart"
    echo ""
    echo "   配置方案B - 创建.pgpass文件:"
    echo "   echo 'localhost:5432:rs_ontop_core:yuxiaoyu:你的密码' > ~/.pgpass"
    echo "   chmod 600 ~/.pgpass"
    exit 1
fi

# 2. 验证employees表数据
echo ""
echo "2. 验证employees表数据..."
psql -U yuxiaoyu -d rs_ontop_core -c "SELECT COUNT(*) as total FROM employees;"

# 3. 验证简单查询
echo ""
echo "3. 验证简单SELECT查询..."
psql -U yuxiaoyu -d rs_ontop_core -c "SELECT employee_id, first_name FROM employees LIMIT 3;"

# 4. 验证JOIN查询
echo ""
echo "4. 验证JOIN查询..."
psql -U yuxiaoyu -d rs_ontop_core -c "
SELECT e.employee_id, e.first_name, d.department_name 
FROM employees e 
JOIN departments d ON e.department_id = d.department_id 
LIMIT 3;"

# 5. 验证FILTER查询
echo ""
echo "5. 验证FILTER查询 (salary > 5000)..."
psql -U yuxiaoyu -d rs_ontop_core -c "
SELECT employee_id, first_name, salary 
FROM employees 
WHERE salary > 5000 
LIMIT 3;"

echo ""
echo "=== 基础SQL验证完成 ==="
