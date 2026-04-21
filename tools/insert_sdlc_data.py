import random
from datetime import datetime, timedelta

# 配置参数
NUM_PROJECTS = 10
REQ_PER_PROJECT = 50   # 每个项目 50 条需求
TASKS_PER_REQ = 10     # 每个需求 10 个任务
TESTS_PER_REQ = 100    # 每个需求增加至 100 条测试用例 (10 * 50 * 100 = 50,000 条测试数据)
BUGS_PER_PROJECT = 200 # 相应增加每个项目的 Bug 数量
AI_LOGS_PER_PROJECT = 150 # 每个项目 150 条 AI 日志

def generate_sql():
    sql_lines = []
    
    # 1. 项目数据 (Projects)
    sql_lines.append("-- 插入项目数据")
    for p_id in range(1, NUM_PROJECTS + 1):
        name = f"智能系统项目_{p_id:03d}"
        desc = f"这是关于项目 {p_id} 的详细描述，涉及智能算法与自动化流程。"
        start_date = (datetime(2024, 1, 1) + timedelta(days=p_id * 10)).strftime('%Y-%m-%d')
        sql_lines.append(f"INSERT INTO projects (project_id, project_name, description, start_date, manager_id, status) VALUES ({p_id}, '{name}', '{desc}', '{start_date}', {100 + p_id}, 'Active');")

    # 2. 规划记录 (Planning)
    sql_lines.append("\n-- 插入规划记录")
    for p_id in range(1, NUM_PROJECTS + 1):
        budget = random.randint(100000, 1000000)
        duration = random.randint(90, 300)
        sql_lines.append(f"INSERT INTO planning_records (project_id, scope_statement, estimated_budget, ai_estimated_duration_days, resource_count, approval_status) VALUES ({p_id}, '范围定义-{p_id}', {budget}, {duration}, {random.randint(5, 20)}, 'Approved');")

    # 3. 需求数据 (Requirements)
    sql_lines.append("\n-- 插入需求数据")
    req_global_id = 1
    project_req_map = {} # 用于后续关联
    for p_id in range(1, NUM_PROJECTS + 1):
        project_req_map[p_id] = []
        for r in range(1, REQ_PER_PROJECT + 1):
            title = f"功能需求_{p_id}_{r}"
            priority = random.choice(['Low', 'Medium', 'High', 'Critical'])
            spec = f"AI 生成的关于 {title} 的技术规格说明..."
            sql_lines.append(f"INSERT INTO requirements (req_id, project_id, title, description, ai_generated_spec, priority, source, status) VALUES ({req_global_id}, {p_id}, '{title}', '描述内容', '{spec}', '{priority}', 'Customer', 'Approved');")
            project_req_map[p_id].append(req_global_id)
            req_global_id += 1

    # 4. 设计产出 (Design)
    sql_lines.append("\n-- 插入设计产出")
    for p_id in range(1, NUM_PROJECTS + 1):
        types = ['Architecture', 'Database', 'UI_UX', 'API_Spec']
        for t in types:
            mermaid = f"graph TD; AI_{p_id} --> Module_{t};"
            sql_lines.append(f"INSERT INTO design_artifacts (project_id, design_type, artifact_url, mermaid_diagram_code, tech_stack_json) VALUES ({p_id}, '{t}', 'http://cdn.dev/{p_id}/{t}', '{mermaid}', '{{\"tech\": \"Stack_{p_id}\"}}');")

    # 5. 开发任务 (Development)
    sql_lines.append("\n-- 插入开发任务")
    task_global_id = 1
    for p_id, reqs in project_req_map.items():
        for r_id in reqs:
            for t in range(1, TASKS_PER_REQ + 1):
                pct = random.randint(10, 80)
                status = random.choice(['To_Do', 'In_Progress', 'Reviewing', 'Done'])
                sql_lines.append(f"INSERT INTO dev_tasks (task_id, project_id, req_id, task_name, developer_id, ai_contribution_pct, status) VALUES ({task_global_id}, {p_id}, {r_id}, '开发子任务_{task_global_id}', {200 + p_id}, {pct}, '{status}');")
                task_global_id += 1

    # 6. 测试用例 (Testing) - 已更新为每个需求 100 条
    sql_lines.append("\n-- 插入测试用例 (每个需求 100 条)")
    case_global_id = 1
    project_case_map = {}
    for p_id, reqs in project_req_map.items():
        project_case_map[p_id] = []
        for r_id in reqs:
            for c in range(1, TESTS_PER_REQ + 1):
                sql_lines.append(f"INSERT INTO test_cases (case_id, project_id, req_id, is_ai_generated, scenario, expected_result) VALUES ({case_global_id}, {p_id}, {r_id}, {random.choice(['TRUE', 'FALSE'])}, '测试场景_需求{r_id}_用例{c}', '预期结果_通过验证');")
                project_case_map[p_id].append(case_global_id)
                case_global_id += 1

    # 7. 缺陷报告 (Bugs)
    sql_lines.append("\n-- 插入缺陷报告")
    for p_id, cases in project_case_map.items():
        for b in range(1, BUGS_PER_PROJECT + 1):
            c_id = random.choice(cases) # 从该项目数千条用例中随机抽取
            severity = random.choice(['Minor', 'Major', 'Critical', 'Blocker'])
            sql_lines.append(f"INSERT INTO bug_reports (project_id, case_id, title, severity, status, ai_suggested_fix) VALUES ({p_id}, {c_id}, '缺陷_{p_id}_{b}', '{severity}', 'Open', 'AI 修复建议: 优化逻辑处理');")

    # 8. AI 日志 (AI Logs)
    sql_lines.append("\n-- 插入 AI 交互日志")
    for p_id in range(1, NUM_PROJECTS + 1):
        for l in range(1, AI_LOGS_PER_PROJECT + 1):
            phase = random.randint(1, 7)
            tokens = random.randint(100, 3000)
            sql_lines.append(f"INSERT INTO ai_interaction_logs (project_id, phase_id, ai_tool_name, prompt_text, response_text, token_usage) VALUES ({p_id}, {phase}, 'Gemini-Pro', 'Prompt_{l}', 'Response_{l}', {tokens});")

    # 9. 部署记录
    sql_lines.append("\n-- 插入部署记录")
    for p_id in range(1, NUM_PROJECTS + 1):
        sql_lines.append(f"INSERT INTO deployments (project_id, version_tag, environment, changelog) VALUES ({p_id}, 'v1.{p_id}.0', 'Production', '常规发布');")

    return sql_lines

# 执行生成并写入文件
full_sql = generate_sql()
with open("massive_sdlc_data.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(full_sql))

print(f"成功生成 SQL 文件，包含约 {len(full_sql)} 条指令。")