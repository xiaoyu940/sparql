-- SDLC 7-Phase Process Management Database Schema
-- Based on IBM SDLC Methodology (Integrated with AI Tooling)

-- 1. 项目基础表 (Projects)
CREATE TABLE projects (
    project_id INT PRIMARY KEY AUTO_INCREMENT,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    manager_id INT,
    status ENUM('Active', 'Completed', 'On_Hold', 'Archived') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) COMMENT='项目核心信息表';

-- 2. SDLC 阶段定义表 (Lookup Table)
CREATE TABLE sdlc_phases (
    phase_id INT PRIMARY KEY,
    phase_name VARCHAR(50) NOT NULL,
    phase_order INT NOT NULL,
    description TEXT
) COMMENT='SDLC 阶段定义参考表';

-- 初始化 7 个阶段数据
INSERT INTO sdlc_phases (phase_id, phase_name, phase_order, description) VALUES
(1, 'Planning', 1, '定义项目范围、目标和资源分配'),
(2, 'Analysis', 2, '收集用户需求并进行可行性分析'),
(3, 'Design', 3, '系统架构设计、数据结构及 UI/UX 设计'),
(4, 'Development', 4, '编写代码、集成并构建系统'),
(5, 'Testing', 5, '质量保证、漏洞修复及验收测试'),
(6, 'Deployment', 6, '将软件发布到生产或准生产环境'),
(7, 'Maintenance', 7, '系统监控、补丁更新及用户支持');

-- [AI 扩展] AI 交互上下文表 (AI_Context_Logs)
-- 用于记录 AI 在各个阶段的输入输出，便于审计和优化 Prompt
CREATE TABLE ai_interaction_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    phase_id INT NOT NULL,
    ai_tool_name VARCHAR(100), -- 如 'GPT-4', 'Copilot', 'Custom-Agent'
    prompt_text TEXT,
    response_text TEXT,
    token_usage INT,
    user_feedback ENUM('Helpful', 'Not_Helpful', 'Corrected'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (phase_id) REFERENCES sdlc_phases(phase_id)
) COMMENT='AI 工具交互历史记录';

-- 3. 规划阶段 (Planning): AI 辅助估算
CREATE TABLE planning_records (
    plan_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    scope_statement TEXT,
    estimated_budget DECIMAL(15, 2),
    ai_estimated_duration_days INT, -- AI 根据历史数据预估的工期
    resource_count INT,
    approval_status ENUM('Pending', 'Approved', 'Rejected'),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) COMMENT='规划阶段记录';

-- 4. 分析阶段 (Analysis): AI 需求提取
CREATE TABLE requirements (
    req_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    ai_generated_spec TEXT, -- AI 自动生成的 PRD 草案
    priority ENUM('Low', 'Medium', 'High', 'Critical'),
    source VARCHAR(100),
    status ENUM('Draft', 'Reviewed', 'Approved', 'Changed'),
    version INT DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) COMMENT='需求追踪表';

-- 5. 设计阶段 (Design): AI 生成代码框架与图表
CREATE TABLE design_artifacts (
    design_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    design_type ENUM('Architecture', 'Database', 'UI_UX', 'API_Spec'),
    artifact_url VARCHAR(500),
    mermaid_diagram_code TEXT, -- AI 生成的 Mermaid 图表代码
    tech_stack_json JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) COMMENT='设计产出物';

-- 6. 开发阶段 (Development): AI 辅助编码
CREATE TABLE dev_tasks (
    task_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    req_id INT,
    task_name VARCHAR(255),
    developer_id INT,
    ai_contribution_pct INT DEFAULT 0, -- AI 代码占比，用于评估 AI 提效
    repo_branch VARCHAR(100),
    status ENUM('To_Do', 'In_Progress', 'Reviewing', 'Done'),
    commit_hash VARCHAR(64),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (req_id) REFERENCES requirements(req_id)
) COMMENT='开发任务追踪';

-- 7. 测试阶段 (Testing): AI 自动生成用例
CREATE TABLE test_cases (
    case_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    req_id INT,
    is_ai_generated BOOLEAN DEFAULT FALSE, -- 标记是否为 AI 生成的用例
    scenario TEXT,
    expected_result TEXT,
    pre_conditions TEXT,
    FOREIGN KEY (req_id) REFERENCES requirements(req_id)
) COMMENT='测试用例定义';

CREATE TABLE bug_reports (
    bug_id INT PRIMARY KEY AUTO_INCREMENT,
    case_id INT,
    project_id INT NOT NULL,
    title VARCHAR(255),
    ai_suggested_fix TEXT, -- AI 给出的修复建议代码
    severity ENUM('Minor', 'Major', 'Critical', 'Blocker'),
    status ENUM('New', 'Open', 'Fixed', 'Verified', 'Closed'),
    reporter_id INT,
    fixed_by_task_id INT,
    FOREIGN KEY (case_id) REFERENCES test_cases(case_id),
    FOREIGN KEY (fixed_by_task_id) REFERENCES dev_tasks(task_id)
) COMMENT='缺陷/Bug 报告';

-- 8. 部署阶段 (Deployment): AI 自动生成发布日志
CREATE TABLE deployments (
    deploy_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    version_tag VARCHAR(50),
    environment ENUM('Staging', 'UAT', 'Production'),
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployed_by INT,
    changelog TEXT,
    ai_release_summary TEXT, -- AI 自动根据 Git Commits 总结的发布说明
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) COMMENT='发布记录';

-- 9. 维护阶段 (Maintenance): AI 辅助日志分析
CREATE TABLE maintenance_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    issue_type ENUM('Server_Down', 'Performance_Issue', 'Security_Patch', 'User_Request'),
    description TEXT,
    ai_anomaly_score FLOAT, -- AI 检测出的异常分数
    resolution TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) COMMENT='运维及维护日志';

-- 10. 阶段转换审计表 (Stage Transitions)
CREATE TABLE phase_transitions (
    transition_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    from_phase_id INT,
    to_phase_id INT,
    approved_by INT,
    transition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (from_phase_id) REFERENCES sdlc_phases(phase_id),
    FOREIGN KEY (to_phase_id) REFERENCES sdlc_phases(phase_id)
) COMMENT='SDLC 阶段流转审计记录';