#!/usr/bin/env python3
"""
SPARQL-SQL 结果比对验证框架

每个测试案例是一个独立的 Python 文件，包含:
- sparql_query(): 执行 SPARQL 查询返回结果
- sql_query(): 执行对应 SQL 查询返回结果  
- compare_results(): 比对两者结果

用法:
    python -m pytest test_cases/test_basic_join.py -v
    python run_all_tests.py
"""

import os
import sys

# 测试环境全局配置
# 确保 cargo 和 PostgreSQL 命令可用
os.environ['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + os.environ.get('PATH', '')
# 默认 PostgreSQL 密码（可通过环境变量覆盖）
if 'PGPASSWORD' not in os.environ:
    os.environ['PGPASSWORD'] = '123456'
# sudo 密码（用于自动重启 PostgreSQL，可通过环境变量设置）
SUDO_PASSWORD = os.environ.get('SUDO_PASSWORD', 'yudaqi110')

import json
import subprocess
import psycopg2
import psycopg2.extensions
import signal
import urllib.request
import urllib.error
from typing import List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class QueryResult:
    """查询结果标准化格式"""
    columns: List[str] = None
    rows: List[Dict[str, Any]] = None
    row_count: int = 0
    passed: bool = True
    error: str = None
    sql: str = None
    
    def to_dict(self) -> Dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "passed": self.passed,
            "error": self.error,
            "sql": self.sql
        }


class TestCaseBase(ABC):
    """测试案例基类"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.conn = None
        
    def connect(self):
        """连接数据库"""
        if not self.conn:
            self.conn = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database', 'rs_ontop_core'),
                user=self.db_config.get('user', 'yuxiaoyu'),
                password=self.db_config.get('password', os.environ.get('PGPASSWORD', '123456'))
            )
        return self.conn

    def ensure_rdf_triples_view(self):
        """根据 R2RML 映射生成 rdf_triples 视图"""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS ontop_r2rml_mappings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ttl_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("SELECT ttl_content FROM ontop_r2rml_mappings ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        if not row or not row[0]:
            cur.close()
            return

        ttl_content = row[0]

        def sql_literal(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"

        def expand_iri(token: str) -> str:
            t = token.strip()
            if t.startswith("<") and t.endswith(">"):
                return t[1:-1]
            if t.startswith("ex:"):
                return "http://example.org/" + t.split(":", 1)[1]
            if t.startswith("foaf:"):
                return "http://xmlns.com/foaf/0.1/" + t.split(":", 1)[1]
            if t.startswith("geo:"):
                return "http://www.opengis.net/ont/geosparql#" + t.split(":", 1)[1]
            return t

        import re

        table_re = re.compile(r'rr:tableName\s+"([^"]+)"')
        template_re = re.compile(r'rr:template\s+"([^"]+)"')
        class_re = re.compile(r"rr:class\s+([^;\]]+)")
        pom_re = re.compile(
            r'rr:predicate\s+([^;\s]+)\s*;\s*rr:objectMap\s*\[\s*rr:column\s+"([^"]+)"\s*\]',
            re.S,
        )

        rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        selects = []

        starts = [m.start() for m in re.finditer(r"<#[^>]+>", ttl_content)]
        blocks = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(ttl_content)
            blocks.append(ttl_content[start:end])

        for block in blocks:
            table_match = table_re.search(block)
            template_match = template_re.search(block)

            if not table_match or not template_match:
                continue

            table_name = table_match.group(1)
            template = template_match.group(1)

            subject_expr = sql_literal(template)
            if "{" in template and "}" in template:
                start = template.find("{")
                end = template.find("}")
                if end > start + 1:
                    col_name = template[start + 1:end]
                    subject_expr = f"replace({sql_literal(template)}, '{{{col_name}}}', {col_name}::text)"

            class_matches = class_re.findall(block)
            for class_token in class_matches:
                class_iri = expand_iri(class_token.strip())
                selects.append(
                    f"SELECT {subject_expr} AS s, {sql_literal(rdf_type)} AS p, {sql_literal(class_iri)} AS o "
                    f"FROM {table_name}"
                )

            for pred_token, col_name in pom_re.findall(block):
                pred_iri = expand_iri(pred_token)
                selects.append(
                    f"SELECT {subject_expr} AS s, {sql_literal(pred_iri)} AS p, {col_name}::text AS o "
                    f"FROM {table_name} WHERE {col_name} IS NOT NULL"
                )

        if selects:
            view_sql = "CREATE OR REPLACE VIEW rdf_triples AS " + " UNION ALL ".join(selects)
        else:
            view_sql = "CREATE OR REPLACE VIEW rdf_triples AS SELECT NULL::text AS s, NULL::text AS p, NULL::text AS o WHERE false"

        cur.execute(view_sql)
        conn.commit()
        cur.close()

    def ensure_r2rml_mappings(self):
        """确保 R2RML 映射表存在且已加载"""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS ontop_r2rml_mappings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ttl_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        ttl_path = os.path.join(base_dir, 'correct_mapping.ttl')
        if not os.path.exists(ttl_path):
            cur.close()
            raise FileNotFoundError(f"R2RML 映射文件不存在: {ttl_path}")

        with open(ttl_path, 'r', encoding='utf-8') as f:
            ttl_content = f.read()

        cur.execute("SELECT COUNT(*) FROM ontop_r2rml_mappings WHERE name = 'correct_mapping';")
        exists = cur.fetchone()[0] > 0

        if exists:
            cur.execute(
                "SELECT LENGTH(ttl_content) FROM ontop_r2rml_mappings WHERE name = 'correct_mapping';"
            )
            size = cur.fetchone()[0]
            if size != len(ttl_content):
                cur.execute(
                    "UPDATE ontop_r2rml_mappings SET ttl_content = %s, created_at = NOW() WHERE name = 'correct_mapping';",
                    (ttl_content,)
                )
                conn.commit()
                print(f"  ✓ 已更新 R2RML 映射: {ttl_path}")
        else:
            cur.execute(
                "INSERT INTO ontop_r2rml_mappings (name, ttl_content, created_at) VALUES (%s, %s, NOW())",
                ('correct_mapping', ttl_content)
            )
            conn.commit()
            print(f"  ✓ 已加载 R2RML 映射: {ttl_path}")

        cur.close()
    
    def execute_sparql_http(self, sparql: str, timeout_sec: int = 30, retry_on_engine_error: bool = True) -> QueryResult:
        """
        通过 HTTP (端口5820) 执行 SPARQL 查询
        
        调用 SPARQL HTTP 服务端点 /sparql，返回标准化结果
        
        如果 bgworker 引擎未初始化，会自动调用 ontop_refresh() 重试一次
        """
        self.ensure_r2rml_mappings()
        self.ensure_rdf_triples_view()
        self.ensure_sparql_server()
        
        result = self._do_sparql_http_request(sparql, timeout_sec)
        
        # 如果引擎未初始化，尝试刷新后重试
        if retry_on_engine_error and result.error and 'engine not initialized' in result.error.lower():
            print(f"  ⚠ HTTP worker 引擎未初始化，尝试刷新...")
            if self._refresh_engine():
                print(f"  🔄 重试 SPARQL 查询...")
                result = self._do_sparql_http_request(sparql, timeout_sec, retry_on_engine_error=False)
        
        return result
    
    def execute_sparql_sql(self, sparql: str) -> QueryResult:
        """
        通过 SQL 函数 ontop_translate 执行 SPARQL 查询（跳过 HTTP 5820）
        
        使用 PostgreSQL 扩展提供的翻译函数获取 SQL，然后执行 SQL
        """
        try:
            self.ensure_r2rml_mappings()
            self.ensure_rdf_triples_view()
            # 1. 先刷新引擎
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config.get('password', '')
            refresh_cmd = [
                'psql',
                '-h', self.db_config.get('host', 'localhost'),
                '-p', str(self.db_config.get('port', 5432)),
                '-U', self.db_config.get('user', 'yuxiaoyu'),
                '-d', self.db_config.get('database', 'rs_ontop_core'),
                '-t', '-c', 'SELECT ontop_refresh();'
            ]
            subprocess.run(refresh_cmd, capture_output=True, text=True, env=env, timeout=10)
            
            # 2. 翻译 SPARQL 为 SQL
            escaped = sparql.replace("'", "''")
            translate_cmd = [
                'psql',
                '-h', self.db_config.get('host', 'localhost'),
                '-p', str(self.db_config.get('port', 5432)),
                '-U', self.db_config.get('user', 'yuxiaoyu'),
                '-d', self.db_config.get('database', 'rs_ontop_core'),
                '-t', '-A',
                '-c', f"SELECT ontop_translate('{escaped}');"
            ]
            
            result = subprocess.run(translate_cmd, capture_output=True, text=True, env=env, timeout=30)
            
            if result.returncode != 0:
                return QueryResult(
                    columns=[], rows=[], row_count=0,
                    error=f"SPARQL 翻译失败: {result.stderr}",
                    sql=None
                )
            
            # 3. 解析翻译后的 SQL
            sql = result.stdout.strip()
            if not sql or sql.startswith('--') or 'Error' in sql:
                return QueryResult(
                    columns=[], rows=[], row_count=0,
                    error=f"SPARQL 翻译错误: {sql}",
                    sql=None
                )
            
            # 4. 执行翻译后的 SQL
            return self.execute_sql_query(sql)
                
        except Exception as e:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"SPARQL SQL 执行异常: {e}",
                sql=None
            )
    
    def _refresh_engine(self) -> bool:
        """调用 ontop_refresh() 初始化引擎"""
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config.get('password', '')
            cmd = [
                'psql',
                '-h', self.db_config.get('host', 'localhost'),
                '-p', str(self.db_config.get('port', 5432)),
                '-U', self.db_config.get('user', 'yuxiaoyu'),
                '-d', self.db_config.get('database', 'rs_ontop_core'),
                '-t', '-c', 'SELECT ontop_refresh();'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
            return result.returncode == 0 and 'refreshed' in result.stdout.lower()
        except Exception as e:
            print(f"  ✗ 引擎刷新失败: {e}")
            return False
    
    def _do_sparql_http_request(self, sparql: str, timeout_sec: int, retry_on_engine_error: bool = True) -> QueryResult:
        """实际执行 HTTP SPARQL 请求的内部方法"""
        try:
            # URL 编码 SPARQL 查询
            import urllib.parse
            encoded_query = urllib.parse.quote(sparql)
            
            url = f"http://localhost:5820/sparql?query={encoded_query}"
            
            req = urllib.request.Request(
                url,
                method='GET',
                headers={
                    'Accept': 'application/sparql-results+json'
                }
            )
            
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                # 检查错误响应
                if 'error' in data:
                    return QueryResult(
                        columns=[], rows=[], row_count=0,
                        error=data['error'],
                        sql=None
                    )
                
                # 解析 SPARQL results JSON 格式
                # 格式: {"head": {"vars": [...]}, "results": {"bindings": [...]}}
                if 'boolean' in data:
                    # ASK 查询返回 boolean
                    return QueryResult(
                        columns=['result'],
                        rows=[{'result': data['boolean']}],
                        row_count=1,
                        sql=url
                    )
                
                vars_list = data.get('head', {}).get('vars', [])
                bindings = data.get('results', {}).get('bindings', [])
                
                # 转换 bindings 为行格式
                rows = []
                for binding in bindings:
                    row = {}
                    for var in vars_list:
                        if var in binding:
                            term = binding[var]
                            # 提取值（处理 uri/literal 类型）
                            if term.get('type') == 'uri':
                                row[var] = term.get('value', '')
                            else:
                                row[var] = term.get('value', '')
                        else:
                            row[var] = None
                    rows.append(row)
                
                return QueryResult(
                    columns=vars_list,
                    rows=rows,
                    row_count=len(rows),
                    sql=url
                )
                
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = str(e)
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"HTTP {e.code}: {error_body}",
                sql=None
            )
        except Exception as e:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"SPARQL HTTP 请求失败: {e}",
                sql=None
            )

    def ensure_extension_installed(self, force_rebuild: bool = False, clean_build: bool = False) -> bool:
        """
        检查并安装 rs_ontop_core 扩展到 PostgreSQL
        
        比较 target/release/librs_ontop_core.so 与 PG 共享目录中的文件，
        如果本地文件更新则重新安装
        
        Args:
            force_rebuild: 强制重新编译安装，忽略时间戳比较
            clean_build: 先执行 cargo clean 再编译（类似 make clean install）
        """
        import subprocess
        import os
        from pathlib import Path
        
        # 获取 PG 共享目录
        try:
            result = subprocess.run(
                ['pg_config', '--pkglibdir'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                print("  ⚠ 无法获取 PostgreSQL 共享目录")
                return False
            pg_libdir = result.stdout.strip()
        except Exception as e:
            print(f"  ⚠ pg_config 执行失败: {e}")
            return False
        
        # 检查源文件
        source_so = Path('/home/yuxiaoyu/rs_ontop_core/target/release/librs_ontop_core.so')
        target_so = Path(f'{pg_libdir}/rs_ontop_core.so')
        
        need_install = False
        
        if clean_build:
            print(f"  ℹ 清理编译模式（cargo clean + build）")
            need_install = True
        elif force_rebuild:
            print(f"  ℹ 强制重新编译模式")
            need_install = True
        elif not target_so.exists():
            print(f"  ℹ 扩展未安装: {target_so}")
            need_install = True
        elif not source_so.exists():
            print(f"  ⚠ 源文件不存在: {source_so}，需要编译")
            need_install = True
        else:
            source_mtime = source_so.stat().st_mtime
            target_mtime = target_so.stat().st_mtime
            print(f"  ℹ 源文件时间: {source_mtime}, 目标文件时间: {target_mtime}")
            print(f"  ℹ 时间差: {source_mtime - target_mtime} 秒")
            
            if source_mtime > target_mtime:
                print(f"  ℹ 源文件比安装版本更新，需要重新安装")
                need_install = True
            else:
                print(f"  ✓ 扩展已是最新版本")
        
        if need_install:
            # 如果需要清理，先执行 cargo clean
            if clean_build:
                print(f"  🧹 清理旧编译文件...")
                try:
                    env = os.environ.copy()
                    env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')
                    clean_result = subprocess.run(
                        ['cargo', 'clean'],
                        cwd='/home/yuxiaoyu/rs_ontop_core',
                        capture_output=True, text=True, env=env, timeout=60
                    )
                    if clean_result.returncode != 0:
                        print(f"  ⚠ 清理警告: {clean_result.stderr[:200]}")
                except Exception as e:
                    print(f"  ⚠ 清理异常: {e}")
            
            print(f"  🔨 正在编译并安装扩展...")
            print(f"  ⏳ 这可能需要几分钟时间...")
            try:
                env = os.environ.copy()
                env['PATH'] = '/home/yuxiaoyu/.cargo/bin:' + env.get('PATH', '')
                
                result = subprocess.run(
                    ['cargo', 'pgrx', 'install', '--release'],
                    cwd='/home/yuxiaoyu/rs_ontop_core',
                    capture_output=True, text=True, env=env, timeout=300
                )
                if result.returncode == 0:
                    print(f"  ✓ 扩展安装成功")
                    # 安装后重启 PostgreSQL 以加载新的 .so 文件
                    if not self.restart_postgresql():
                        return False
                    return True
                else:
                    print(f"  ✗ 安装失败: {result.stderr[:500]}")
                    return False
            except Exception as e:
                print(f"  ✗ 安装异常: {e}")
                return False
        
        return True

    def restart_postgresql(self) -> bool:
        """
        重启 PostgreSQL 服务以加载新的扩展库文件
        
        对于 pgrx bgworker 扩展，必须重启才能加载新版本的 .so
        """
        print(f"  🔄 重启 PostgreSQL 服务...")
        try:
            # 先关闭现有数据库连接
            if self.conn:
                self.conn.close()
                self.conn = None
            
            # 尝试多种方式重启 PostgreSQL，使用 sudo -S 提供密码
            restart_cmds = [
                # Ubuntu/Debian 系统服务
                ['sudo', '-S', 'systemctl', 'restart', 'postgresql@16-main'],
                ['sudo', '-S', 'systemctl', 'restart', 'postgresql'],
                # pg_ctlcluster 方式
                ['sudo', '-S', 'pg_ctlcluster', '16', 'main', 'restart'],
            ]
            
            for cmd in restart_cmds:
                try:
                    # 使用 sudo -S 从 stdin 读取密码
                    result = subprocess.run(
                        cmd,
                        input=SUDO_PASSWORD + '\n',
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        print(f"  ✓ PostgreSQL 重启成功")
                        # 等待服务恢复
                        import time
                        time.sleep(2)
                        # 测试连接
                        if self.test_connection():
                            return True
                        else:
                            print(f"  ⚠ 重启后连接测试失败，继续等待...")
                            time.sleep(3)
                            if self.test_connection():
                                return True
                    else:
                        continue  # 尝试下一个命令
                except Exception:
                    continue  # 尝试下一个命令
            
            print(f"  ✗ PostgreSQL 重启失败，请手动重启")
            return False
            
        except Exception as e:
            print(f"  ✗ 重启异常: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试数据库连接是否可用"""
        try:
            conn = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database', 'rs_ontop_core'),
                user=self.db_config.get('user', 'yuxiaoyu'),
                password=self.db_config.get('password', os.environ.get('PGPASSWORD', '123456')),
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception:
            return False

    def restart_sparql_server(self) -> bool:
        """
        单独重启 SPARQL HTTP 服务（无需重启整个 PostgreSQL）
        
        通过找到 bgworker 进程并发送 SIGTERM，让 PostgreSQL 自动重新创建
        """
        print(f"  🔄 重启 SPARQL HTTP 服务 (端口5820)...")
        try:
            import subprocess
            import signal
            import time
            
            # 查找 bgworker 进程
            result = subprocess.run(
                ['pgrep', '-f', 'rs_ontop_core SPARQL Web Gateway'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip().split('\n')[0]
                print(f"  找到 bgworker PID: {pid}，发送终止信号...")
                
                # 发送 SIGTERM 优雅终止
                subprocess.run(['kill', '-TERM', pid], check=False)
                
                # 等待进程终止和端口释放
                time.sleep(2)
                
                # 检查端口是否已释放
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                port_available = sock.connect_ex(('localhost', 5820)) != 0
                sock.close()
                
                if not port_available:
                    print(f"  ⚠ 端口 5820 仍被占用，强制终止...")
                    subprocess.run(['kill', '-9', pid], check=False)
                    time.sleep(1)
                
                print(f"  ✓ 旧 HTTP 服务已终止")
            
            # 重新启动服务
            return self.ensure_sparql_server()
            
        except Exception as e:
            print(f"  ✗ 重启 HTTP 服务失败: {e}")
            return False


    def run(self) -> Dict:
        """执行单个测试用例并打印详细过程"""
        try:
            print("  执行 SPARQL 查询...")
            sparql_result = self.sparql_query()
            print(f"  ✓ SPARQL 返回 {sparql_result.row_count} 行")

            print("  执行 SQL 查询...")
            sql_result = self.sql_query()
            print(f"  ✓ SQL 返回 {sql_result.row_count} 行")

            print("  比对结果...")
            passed, errors = self.compare_results(sparql_result, sql_result)
            if passed:
                print("  ✓ 测试通过")
            else:
                print("  ✗ 测试失败:")
                for err in errors:
                    print(f"    - {err}")

            return {
                'test_name': self.__class__.__name__,
                'passed': passed,
                'errors': errors,
                'sparql_sql': getattr(sparql_result, 'sql', None),
                'sparql_result': sparql_result.to_dict() if hasattr(sparql_result, 'to_dict') else None,
                'sql_result': sql_result.to_dict() if hasattr(sql_result, 'to_dict') else None,
            }
        except Exception as e:
            msg = f'测试执行异常: {str(e)}'
            print(f"  ✗ {msg}")
            return {
                'test_name': self.__class__.__name__,
                'passed': False,
                'errors': [msg],
            }


    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def ensure_sparql_server(self):
        """检查并启动 SPARQL HTTP 服务（端口5820）"""
        import socket
        import time
        
        # 检查端口是否已监听
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5820))
        sock.close()
        
        if result != 0:
            # 端口未监听，启动服务
            print("  启动 SPARQL HTTP 服务 (端口5820)...")
            try:
                env = os.environ.copy()
                env['PGPASSWORD'] = self.db_config.get('password', '')
                
                # 先初始化主进程引擎
                refresh_cmd = [
                    'psql',
                    '-h', self.db_config.get('host', 'localhost'),
                    '-p', str(self.db_config.get('port', 5432)),
                    '-U', self.db_config.get('user', 'yuxiaoyu'),
                    '-d', self.db_config.get('database', 'rs_ontop_core'),
                    '-t', '-c', 'SELECT ontop_refresh();'
                ]
                refresh_result = subprocess.run(refresh_cmd, capture_output=True, text=True, env=env, timeout=10)
                print(f"    ontop_refresh: {refresh_result.stdout.strip() if refresh_result.returncode == 0 else '失败'}")
                
                # 启动 HTTP 服务
                cmd = [
                    'psql',
                    '-h', self.db_config.get('host', 'localhost'),
                    '-p', str(self.db_config.get('port', 5432)),
                    '-U', self.db_config.get('user', 'yuxiaoyu'),
                    '-d', self.db_config.get('database', 'rs_ontop_core'),
                    '-t', '-c', 'SELECT ontop_start_sparql_server();'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
                print(f"    ontop_start_sparql_server: {result.stdout.strip() if result.returncode == 0 else result.stderr[:200]}")
                
                if result.returncode == 0:
                    # 等待服务启动（最多 5 秒）
                    print(f"    等待服务启动 (最多 5 秒)...")
                    for i in range(10):  # 10 次 × 0.5 秒 = 5 秒
                        time.sleep(0.5)
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        if sock.connect_ex(('localhost', 5820)) == 0:
                            sock.close()
                            print(f"    ✓ SPARQL HTTP 服务已启动 (耗时 {(i+1)*0.5:.1f} 秒)")
                            return True
                        sock.close()
                        if (i+1) % 5 == 0:
                            print(f"      ...已等待 {(i+1)*0.5:.0f} 秒")
                    print(f"  ✗ SPARQL HTTP 服务启动超时 (5 秒)")
                    return False
                else:
                    print(f"  ✗ 启动命令失败: {result.stderr}")
                    return False
            except Exception as e:
                print(f"  ✗ 启动异常: {e}")
                import traceback
                traceback.print_exc()
                return False
        return True
    
    @abstractmethod
    def sparql_query(self) -> QueryResult:
        """执行 SPARQL 查询，返回标准化结果"""
        pass
    
    @abstractmethod
    def sql_query(self) -> QueryResult:
        """执行 SQL 查询，返回标准化结果"""
        pass
    
    def translate_sparql(self, sparql: str) -> str:
        """调用 PostgreSQL 扩展翻译 SPARQL"""
        self.ensure_r2rml_mappings()
        self.ensure_rdf_triples_view()
        escaped = sparql.replace("'", "''")
        
        query = f"""
        BEGIN;
        SELECT ontop_refresh();
        SELECT ontop_translate('{escaped}');
        COMMIT;
        """
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config.get('password', '')
        
        cmd = [
            'psql',
            '-h', self.db_config.get('host', 'localhost'),
            '-p', str(self.db_config.get('port', 5432)),
            '-U', self.db_config.get('user', 'yuxiaoyu'),
            '-d', self.db_config.get('database', 'rs_ontop_core'),
            '-t', '-A',
            '-c', query
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            raise Exception(f"Translation failed: {result.stderr}")
        
        # 解析 SQL
        lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        sql_lines = [l for l in lines if not l.startswith('BEGIN') 
                     and not l.startswith('COMMIT')
                     and 'ontop_refresh' not in l
                     and 'Engine refreshed' not in l]
        
        if not sql_lines:
            raise Exception("No SQL generated")
        
        sql = ' '.join(sql_lines)
        if sql.startswith('-- Translation Error') or 'Error' in sql:
            raise Exception(f"Translation error: {sql}")
        
        return sql
    
    def execute_sql_query(self, sql: str, timeout_ms: int = 30000) -> QueryResult:
        """执行 SQL 查询并标准化结果"""
        conn = self.connect()
        
        try:
            # 设置查询超时（30秒）
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = {timeout_ms}")
            
            with conn.cursor() as cur:
                cur.execute(sql)
                
                if cur.description is None:
                    return QueryResult(columns=[], rows=[], row_count=0)
                
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                # 转换为字典列表
                dict_rows = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        # 标准化列名（小写，去掉引号）
                        clean_col = col.lower().strip('"\'`')
                        row_dict[clean_col] = row[i]
                    dict_rows.append(row_dict)
                
                return QueryResult(
                    columns=[c.lower().strip('"\'`') for c in columns],
                    rows=dict_rows,
                    row_count=len(dict_rows),
                    sql=sql
                )
        except psycopg2.extensions.QueryCanceledError:
            conn.rollback()
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"SQL 执行超时（>{timeout_ms}ms）"
            )
    
    def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult) -> Tuple[bool, List[str]]:
        """比对 SPARQL 和 SQL 查询结果"""
        errors = []

        if sparql_result.row_count != sql_result.row_count:
            errors.append(f"行数不匹配: SPARQL={sparql_result.row_count}, SQL={sql_result.row_count}")

        sparql_cols = set(sparql_result.columns)
        sql_cols = set(sql_result.columns)

        unmatched = []
        col_matches = {}
        sql_col_by_lower = {c.lower(): c for c in sql_cols}
        for sparql_col in sparql_cols:
            s_lower = sparql_col.lower()
            if s_lower in sql_col_by_lower:
                col_matches[sparql_col] = sql_col_by_lower[s_lower]
                continue

            fallback = next(
                (sql_col for sql_col in sql_cols
                 if s_lower in sql_col.lower() or sql_col.lower() in s_lower),
                None,
            )
            if fallback is not None:
                col_matches[sparql_col] = fallback
            else:
                unmatched.append(sparql_col)

        if unmatched:
            errors.append(f"未匹配的列: {unmatched}, SQL列: {sql_cols}")

        if sparql_result.rows and sql_result.rows:
            sparql_first = sparql_result.rows[0]
            sql_first = sql_result.rows[0]

            common_checks = 0
            for sparql_col, sparql_val in sparql_first.items():
                sql_col = col_matches.get(sparql_col)
                if sql_col is None:
                    s_lower = sparql_col.lower()
                    if s_lower in sql_first:
                        sql_col = s_lower
                    else:
                        sql_col = next(
                            (c for c in sql_first.keys() if s_lower in c.lower() or c.lower() in s_lower),
                            None,
                        )
                if sql_col is None or sql_col not in sql_first:
                    continue

                common_checks += 1
                sql_val = sql_first[sql_col]
                s_val = str(sparql_val)
                sq_val = str(sql_val)

                if s_val != sq_val:
                    try:
                        if float(s_val) == float(sq_val):
                            continue
                    except (ValueError, TypeError):
                        pass
                    errors.append(f"数据不匹配[{sparql_col}]: SPARQL='{sparql_val}', SQL='{sql_val}'")

            if common_checks == 0:
                errors.append(f"没有可比对的共同列: SPARQL列={list(sparql_first.keys())}, SQL列={list(sql_first.keys())}")

        return len(errors) == 0, errors


    def run_test_case(self, test_instance: "TestCaseBase") -> Dict:
        """运行一个已经实例化的测试案例"""
        try:
            return test_instance.run()
        finally:
            test_instance.close()



class SparqlTestFramework:
    """兼容旧测试代码的轻量框架包装器"""
    def __init__(self, db_config):
        self.db_config = db_config

    def run_test_case(self, test_instance):
        try:
            return test_instance.run()
        finally:
            test_instance.close()

def run_test_case(test_class, db_config):
    """模块级兼容入口：运行单个测试类/实例"""
    if isinstance(test_class, type):
        test_instance = test_class(db_config)
    else:
        test_instance = test_class
    try:
        return test_instance.run()
    finally:
        test_instance.close()
