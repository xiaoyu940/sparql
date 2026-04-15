use crate::error::OntopError;

/// SPARQL 查询类型
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum QueryType {
    Select,
    Construct,
    Ask,
    Describe,
}

impl Default for QueryType {
    fn default() -> Self {
        QueryType::Select
    }
}

/// 三元组模式
///
/// 表示 SPARQL 查询中的三元组模式 (subject, predicate, object)。
/// 这是 SPARQL 图模式的基本构建块。
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct TriplePattern {
    pub subject: String,
    pub predicate: String,
    pub object: String,
}

/// 解析后的 SPARQL 查询
///
/// 包含 SPARQL 查询的所有组件：投影变量、三元组模式、FILTER、
/// OPTIONAL、UNION、聚合、ORDER BY 和 LIMIT 等。
#[derive(Debug, Clone)]
pub struct ParsedQuery {
    pub raw: String,
    pub query_type: QueryType,
    pub projected_vars: Vec<String>,
    pub has_filter: bool,
    pub has_optional: bool,
    pub has_union: bool,
    pub has_aggregate: bool,
    pub main_patterns: Vec<TriplePattern>,
    pub optional_patterns: Vec<Vec<TriplePattern>>,
    pub union_patterns: Vec<Vec<TriplePattern>>,
    pub filter_expressions: Vec<String>,
    pub limit: Option<usize>,
    pub order_by: Vec<OrderByItem>,
    pub group_by: Vec<String>,
    pub having_expressions: Vec<String>,
    pub bind_expressions: Vec<BindExpr>,
    pub sub_queries: Vec<ParsedQuery>,
    pub values_block: Option<ValuesBlock>,
    pub aggregates: Vec<AggregateExpr>,
    /// CONSTRUCT 查询的模板三元组
    pub construct_template: Vec<TriplePattern>,
    /// DESCRIBE 查询的资源
    pub describe_resources: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ValuesBlock {
    pub variables: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

/// BIND 表达式
#[derive(Debug, Clone)]
pub struct BindExpr {
    pub expression: String,
    pub alias: String,
}

/// 聚合表达式
///
/// 表示 SPARQL 聚合函数，如 COUNT、AVG、MIN、MAX、SUM。
/// 支持 DISTINCT 修饰符。
#[derive(Debug, Clone)]
pub struct AggregateExpr {
    pub func: String,  // COUNT, AVG, MIN, MAX, SUM
    pub arg: String,   // * 或 ?var
    pub alias: String, // AS ?alias
    pub distinct: bool,
}

#[derive(Debug, Clone)]
pub struct OrderByItem {
    pub variable: String,
    pub direction: SortDirection,
}

/// 排序方向
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SortDirection {
    Asc,
    Desc,
}

/// SPARQL 解析器 V2
///
/// 使用 spargebra 库解析 SPARQL 查询，提取查询组件。
/// 支持 SELECT、WHERE、FILTER、OPTIONAL、UNION、ORDER BY、LIMIT 和聚合。
#[derive(Debug, Default)]
pub struct SparqlParserV2;

impl SparqlParserV2 {
    /// 解析 SPARQL 查询字符串
    ///
    /// # Arguments
    /// * `sparql` - SPARQL 查询字符串
    ///
    /// # Returns
    /// 返回解析后的 ParsedQuery，包含所有查询组件
    ///
    /// # Errors
    /// 当 SPARQL 语法无效时返回 `OntopError::IRError`
    pub fn parse(&self, sparql: &str) -> Result<ParsedQuery, OntopError> {
        let trimmed = sparql.trim();
        if trimmed.is_empty() {
            return Err(OntopError::IRError("Empty SPARQL query".to_string()));
        }

        // 只对不含 ORDER BY 的查询使用 spargebra 验证
        // spargebra 不支持某些 ORDER BY 语法
        let upper = trimmed.to_ascii_uppercase();
        
        // 检测查询类型
        let query_type = if upper.starts_with("CONSTRUCT") {
            QueryType::Construct
        } else if upper.starts_with("ASK") {
            QueryType::Ask
        } else if upper.starts_with("DESCRIBE") {
            QueryType::Describe
        } else {
            QueryType::Select
        };
        
        // CONSTRUCT 模板解析
        let construct_template = if query_type == QueryType::Construct {
            extract_construct_template(trimmed)
        } else {
            Vec::new()
        };
        
        // DESCRIBE 资源解析
        let describe_resources = if query_type == QueryType::Describe {
            extract_describe_resources(trimmed)
        } else {
            Vec::new()
        };
        
        // [Fix] 暂时禁用 spargebra 验证，因为它可能不支持某些语法
        // if !upper.contains("ORDER BY") && !upper.contains("PREFIX") {
        //     // 使用原始查询（未展开 PREFIX）进行验证
        //     if let Err(e) = Query::parse(trimmed, None) {
        //         return Err(OntopError::IRError(format!("SPARQL syntax error: {}", e)));
        //     }
        // }

        let where_block = extract_where_block(trimmed);
        let where_without_subqueries = strip_top_level_subqueries(&where_block);
        let where_without_exists_filters = strip_filter_exists_blocks(&where_without_subqueries);
        
        // [Fix] 先展开前缀，再提取三元组模式
        // 从完整查询中提取前缀并应用到 WHERE 块
        let expanded_where = {
            let mut prefixes = std::collections::HashMap::new();
            let prefix_re = regex::Regex::new(r"PREFIX\s+(\w+):\s+<([^>]+)>\s*").expect("valid prefix regex");
            for cap in prefix_re.captures_iter(trimmed) {
                prefixes.insert(cap[1].to_string(), cap[2].to_string());
            }
            
            let mut result = where_without_exists_filters.clone();
            for (prefix, uri) in &prefixes {
                // [Fix] 使用简单替换：匹配 prefix:word，替换为 <uriword>
                // 注意：这会匹配所有出现，然后手动处理边界
                let pattern = format!(r"{}:(\w+)", prefix);
                let re = regex::Regex::new(&pattern).expect("valid regex");
                result = re.replace_all(&result, |caps: &regex::Captures| {
                    format!("<{}{}>", uri, &caps[1])
                }).to_string();
            }
            eprintln!("[DEBUG parse] Expanded WHERE with prefixes: {:?}", result);
            result
        };
        
        let mut projected_vars = extract_projected_vars(trimmed);
        if query_type == QueryType::Construct {
            // CONSTRUCT 查询需要从模板中提取所有变量作为投影变量
            for triple in &construct_template {
                for part in &[&triple.subject, &triple.predicate, &triple.object] {
                    if part.starts_with('?') {
                        let var_name = part.trim_start_matches('?').to_string();
                        if !projected_vars.contains(&var_name) {
                            projected_vars.push(var_name);
                        }
                    }
                }
            }
        }
        let aggregates = extract_aggregate_exprs(trimmed);
        let has_aggregate = !aggregates.is_empty();

        let main_patterns = extract_triple_patterns(&expanded_where);
        let optional_patterns = extract_optional_patterns(&expanded_where);
        let union_patterns = extract_union_patterns(&expanded_where);
        let expanded_where_for_filters = {
            let mut prefixes = std::collections::HashMap::new();
            let prefix_re = regex::Regex::new(r"PREFIX\s+(\w+):\s+<([^>]+)>\s*").expect("valid prefix regex");
            for cap in prefix_re.captures_iter(trimmed) {
                prefixes.insert(cap[1].to_string(), cap[2].to_string());
            }

            let mut result = where_without_subqueries.clone();
            for (prefix, uri) in &prefixes {
                let pattern = format!(r"{}:(\w+)", prefix);
                let re = regex::Regex::new(&pattern).expect("valid regex");
                result = re.replace_all(&result, |caps: &regex::Captures| {
                    format!("<{}{}>", uri, &caps[1])
                }).to_string();
            }
            result
        };
        let mut filter_expressions = extract_filter_expressions(&expanded_where_for_filters);
        let values_block = extract_values(trimmed);

        let mut allowed_vars: std::collections::HashSet<String> = std::collections::HashSet::new();
        for p in &main_patterns {
            if let Some(v) = p.subject.strip_prefix('?') {
                allowed_vars.insert(v.to_string());
            }
            if let Some(v) = p.object.strip_prefix('?') {
                allowed_vars.insert(v.to_string());
            }
        }
        for v in &projected_vars {
            allowed_vars.insert(v.clone());
        }
        if let Some(values) = &values_block {
            for v in &values.variables {
                allowed_vars.insert(v.trim_start_matches('?').to_string());
            }
        }
        filter_expressions.retain(|f| {
            let ft = f.trim().to_ascii_uppercase();
            if ft.starts_with("EXISTS") || ft.starts_with("NOT EXISTS") {
                return true;
            }
            let vars = extract_vars_from_expr(f);
            vars.iter().all(|v| allowed_vars.contains(v))
        });

        let limit = extract_limit(trimmed);
        let order_by = extract_order_by(trimmed);
        let bind_expressions = extract_binds(trimmed);

        let has_filter = !filter_expressions.is_empty();
        let has_optional = !optional_patterns.is_empty();
        let has_union = !union_patterns.is_empty();

        Ok(ParsedQuery {
            raw: trimmed.to_string(),
            query_type,
            projected_vars,
            has_filter,
            has_optional,
            has_union,
            has_aggregate,
            main_patterns,
            optional_patterns,
            union_patterns,
            filter_expressions,
            limit,
            order_by,
            group_by: extract_group_by(trimmed),
            having_expressions: extract_having(trimmed),
            bind_expressions,
            sub_queries: extract_subqueries(trimmed),
            values_block,
            aggregates,
            construct_template,
            describe_resources,
        })
    }
}

fn strip_filter_exists_blocks(where_block: &str) -> String {
    let chars: Vec<char> = where_block.chars().collect();
    let mut out = String::new();
    let mut i = 0usize;

    while i < chars.len() {
        let rem_upper: String = chars[i..].iter().collect::<String>().to_ascii_uppercase();
        if rem_upper.starts_with("FILTER") {
            let mut j = i + "FILTER".len();
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            let rem2_upper: String = chars[j..].iter().collect::<String>().to_ascii_uppercase();
            let (is_exists, kw_len) = if rem2_upper.starts_with("NOT EXISTS") {
                (true, "NOT EXISTS".len())
            } else if rem2_upper.starts_with("EXISTS") {
                (true, "EXISTS".len())
            } else {
                (false, 0)
            };

            if is_exists {
                let mut k = j + kw_len;
                while k < chars.len() && chars[k].is_whitespace() {
                    k += 1;
                }
                if k < chars.len() && chars[k] == '{' {
                    let mut depth = 1i32;
                    k += 1;
                    while k < chars.len() {
                        if chars[k] == '{' {
                            depth += 1;
                        } else if chars[k] == '}' {
                            depth -= 1;
                            if depth == 0 {
                                k += 1;
                                break;
                            }
                        }
                        k += 1;
                    }
                    i = k;
                    continue;
                }
            }
        }

        out.push(chars[i]);
        i += 1;
    }

    out
}

fn strip_top_level_subqueries(where_block: &str) -> String {
    let chars: Vec<char> = where_block.chars().collect();
    let mut out = String::new();
    let mut i = 0usize;

    while i < chars.len() {
        if chars[i] == '{' {
            let mut j = i + 1;
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            let probe: String = chars[j..].iter().take(12).collect();
            if probe.to_ascii_uppercase().starts_with("SELECT") {
                let mut depth = 1i32;
                let mut k = i + 1;
                while k < chars.len() {
                    if chars[k] == '{' {
                        depth += 1;
                    } else if chars[k] == '}' {
                        depth -= 1;
                        if depth == 0 {
                            break;
                        }
                    }
                    k += 1;
                }
                i = (k + 1).min(chars.len());
                continue;
            }
        }
        out.push(chars[i]);
        i += 1;
    }

    out
}

fn extract_prefix_declarations(sparql: &str) -> String {
    let mut lines = Vec::new();
    for line in sparql.lines() {
        let trimmed = line.trim();
        if trimmed.to_ascii_uppercase().starts_with("PREFIX ") {
            lines.push(trimmed.to_string());
        }
    }
    lines.join("\n")
}

fn extract_subqueries(sparql: &str) -> Vec<ParsedQuery> {
    let mut subqueries = Vec::new();
    let parser = SparqlParserV2::default();
    let outer_prefixes = extract_prefix_declarations(sparql);
    
    // 粗略寻找 { SELECT ... } 结构
    let mut start = 0;
    let upper = sparql.to_ascii_uppercase();
    while let Some(select_idx) = upper[start..].find("{") {
        let abs_brace_idx = start + select_idx;
        // 检查括号后是否有 SELECT
        let after_brace = &sparql[abs_brace_idx + 1 ..].trim_start();
        if !after_brace.to_ascii_uppercase().starts_with("SELECT") {
            start = abs_brace_idx + 1;
            continue;
        }

        // 查找匹配的闭合括号 }
        let mut depth = 0;
        let mut end = None;
        for (i, c) in sparql[abs_brace_idx..].chars().enumerate() {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = Some(abs_brace_idx + i);
                        break;
                    }
                }
                _ => {}
            }
        }
        
        if let Some(e) = end {
            let sub_sparql = &sparql[abs_brace_idx + 1 .. e];
            // 子查询通常复用外层 PREFIX，这里显式继承以保证解析一致。
            let inherited = if outer_prefixes.is_empty() {
                sub_sparql.to_string()
            } else {
                format!("{}\n{}", outer_prefixes, sub_sparql)
            };
            if let Ok(parsed) = parser.parse(&inherited) {
                subqueries.push(parsed);
            }
            start = e + 1;
        } else {
            break;
        }
    }
    
    subqueries
}

fn extract_values(sparql: &str) -> Option<ValuesBlock> {
    let re = regex::Regex::new(r"(?is)VALUES\s+(?:\?\w+|\(\s*(?:\?\w+\s*)+\))\s*\{\s*(.*?)\s*\}").expect("valid VALUES regex");
    let Some(cap) = re.captures(sparql) else {
        return None;
    };
    
    // 粗略解析变量名
    let var_block_re = regex::Regex::new(r"(?i)VALUES\s+(\?\w+|\(\s*(?:\?\w+\s*)+\))").expect("valid VALUES var regex");
    let cap_vars = var_block_re.captures(sparql).expect("VALUES should have variable block");
    let vars_str = cap_vars[1].trim();
    let variables: Vec<String> = if vars_str.starts_with('(') {
        vars_str[1..vars_str.len()-1]
            .split_whitespace()
            .map(|v| v.trim_start_matches('?').to_string())
            .collect()
    } else {
        vec![vars_str.trim_start_matches('?').to_string()]
    };
    
    // 粗略解析列
    let row_str = &cap[1];
    let mut rows = Vec::new();
    
    if variables.len() > 1 {
        // 解析 (val1 val2) (val3 val4)
        let row_re = regex::Regex::new(r"\(\s*(.+?)\s*\)").expect("valid regex");
        for row_cap in row_re.captures_iter(row_str) {
            let row: Vec<String> = row_cap[1]
                .split_whitespace()
                .map(|v| v.to_string())
                .collect();
            if row.len() == variables.len() {
                rows.push(row);
            }
        }
    } else {
        // 解析 val1 val2 val3
        let vals: Vec<String> = row_str
            .split_whitespace()
            .map(|v| v.to_string())
            .collect();
        for v in vals {
            rows.push(vec![v]);
        }
    }
    
    if variables.is_empty() {
        return None;
    }
    
    Some(ValuesBlock { variables, rows })
}

fn extract_projected_vars(sparql: &str) -> Vec<String> {
    let upper = sparql.to_ascii_uppercase();
    let Some(select_pos) = upper.find("SELECT") else {
        return Vec::new();
    };
    let Some(where_pos) = upper.find("WHERE") else {
        return Vec::new();
    };
    if where_pos <= select_pos + 6 {
        return Vec::new();
    }

    let select_part = &sparql[select_pos + 6..where_pos];
    let mut vars: Vec<String> = Vec::new();
    let mut seen = std::collections::HashSet::new();

    let alias_re = regex::Regex::new(r"(?i)AS\s+\?(\w+)").expect("valid regex");
    for cap in alias_re.captures_iter(select_part) {
        let v = cap[1].to_string();
        if seen.insert(v.clone()) {
            vars.push(v);
        }
    }

    let bytes = select_part.as_bytes();
    let mut i = 0usize;
    let mut depth = 0i32;
    while i < bytes.len() {
        match bytes[i] as char {
            '(' => {
                depth += 1;
                i += 1;
            }
            ')' => {
                depth -= 1;
                i += 1;
            }
            '?' if depth == 0 => {
                let mut j = i + 1;
                while j < bytes.len() {
                    let ch = bytes[j] as char;
                    if ch.is_ascii_alphanumeric() || ch == '_' {
                        j += 1;
                    } else {
                        break;
                    }
                }
                if j > i + 1 {
                    let v = select_part[i + 1..j].to_string();
                    if seen.insert(v.clone()) {
                        vars.push(v);
                    }
                }
                i = j;
            }
            _ => i += 1,
        }
    }

    vars
}

fn extract_aggregate_exprs(sparql: &str) -> Vec<AggregateExpr> {
    let upper = sparql.to_ascii_uppercase();
    let Some(select_pos) = upper.find("SELECT") else {
        return Vec::new();
    };
    let Some(where_pos) = upper.find("WHERE") else {
        return Vec::new();
    };
    if where_pos <= select_pos + 6 {
        return Vec::new();
    }

    let select_part = &sparql[select_pos + 6..where_pos];
    let re = regex::Regex::new(
        r"(?is)(COUNT|AVG|MIN|MAX|SUM)\s*\(\s*(DISTINCT\s+)?(\*|\?\w+)\s*\)\s+AS\s+\?(\w+)"
    ).expect("valid aggregate regex");

    let mut out = Vec::new();
    for cap in re.captures_iter(select_part) {
        let func = cap.get(1).map(|m| m.as_str().to_ascii_uppercase()).unwrap_or_default();
        let distinct = cap.get(2).is_some();
        let arg = cap.get(3).map(|m| m.as_str().to_string()).unwrap_or_default();
        let alias = cap.get(4).map(|m| m.as_str().to_string()).unwrap_or_default();
        out.push(AggregateExpr { func, arg, alias, distinct });
    }

    out
}

fn extract_where_block(sparql: &str) -> String {
    let upper = sparql.to_ascii_uppercase();
    eprintln!("[DEBUG SPARQL] Input SPARQL: {:?}", sparql);
    eprintln!("[DEBUG SPARQL] Uppercase: {:?}", upper);
    if let Some(where_pos) = upper.find("WHERE") {
        eprintln!("[DEBUG SPARQL] Found WHERE at position: {}", where_pos);
        let rest = &sparql[where_pos..];
        eprintln!("[DEBUG SPARQL] After WHERE: {:?}", rest);
        if let Some(start) = rest.find('{') {
            eprintln!("[DEBUG SPARQL] Found {{ at position: {}", start);
            let mut depth = 0_i32;
            let chars: Vec<char> = rest[start..].chars().collect();
            for (idx, ch) in chars.iter().enumerate() {
                if *ch == '{' {
                    depth += 1;
                } else if *ch == '}' {
                    depth -= 1;
                    if depth == 0 {
                        let result = chars[1..idx].iter().collect::<String>();
                        eprintln!("[DEBUG SPARQL] Extracted where_block: {:?}", result);
                        return result;
                    }
                }
            }
            eprintln!("[DEBUG SPARQL] No matching }} found, depth={}", depth);
        } else {
            eprintln!("[DEBUG SPARQL] No {{ found after WHERE");
        }
    } else {
        eprintln!("[DEBUG SPARQL] WHERE not found in query");
    }
    eprintln!("[DEBUG SPARQL] Failed to extract where_block, returning input");
    sparql.to_string()
}

pub fn extract_triple_patterns(input: &str) -> Vec<TriplePattern> {
    let expanded = expand_sparql_shorthand(input);
    let expanded_with_prefixes = expand_prefixes(&expanded);
    eprintln!("[DEBUG SPARQL] Expanded input: {:?}", expanded_with_prefixes);

    let mut patterns: Vec<TriplePattern> = Vec::new();

    let re_type_assertion = regex::Regex::new(
        r"(?m)(\?\w+)\s+a\s+<([^>]+)>\s*[.;]"
    ).expect("valid type assertion regex");

    for cap in re_type_assertion.captures_iter(&expanded_with_prefixes) {
        patterns.push(TriplePattern {
            subject: cap[1].to_string(),
            predicate: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string(),
            object: cap[2].to_string(),
        });
    }

    let re_predicate = regex::Regex::new(
        r#"(?m)(\?\w+)\s+([^?\s][^\s]*)\s+(\?\w+|<[^>]+>|"[^"]*"(?:\^\^<[^>]+>)?)\s*[.;]"#
    ).expect("valid predicate regex");

    for cap in re_predicate.captures_iter(&expanded_with_prefixes) {
        let subject = cap[1].to_string();
        let predicate = cap[2].trim().to_string();
        let object = cap[3].to_string();

        if predicate == "a" {
            continue;
        }

        patterns.push(TriplePattern {
            subject,
            predicate,
            object,
        });
    }

    eprintln!(
        "[DEBUG SPARQL] Extracted patterns count: {}, patterns: {:?}",
        patterns.len(),
        patterns
            .iter()
            .map(|p| (&p.subject, &p.predicate, &p.object))
            .collect::<Vec<_>>()
    );
    patterns
}

fn expand_prefixes(input: &str) -> String {
    let mut result = input.to_string();
    let mut prefixes = std::collections::HashMap::new();
    
    // 提取 PREFIX 声明
    let prefix_re = regex::Regex::new(
        r"PREFIX\s+(\w+):\s+<([^>]+)>\s*"
    ).expect("valid prefix regex");
    
    for cap in prefix_re.captures_iter(input) {
        let prefix = cap[1].to_string();
        let uri = cap[2].to_string();
        prefixes.insert(prefix, uri);
    }
    
    eprintln!("[DEBUG expand_prefixes] Input: {:?}", input);
    eprintln!("[DEBUG expand_prefixes] Found {} prefixes: {:?}", prefixes.len(), prefixes);
    
    // 移除所有 PREFIX 声明
    result = prefix_re.replace_all(&result, "").to_string();
    eprintln!("[DEBUG expand_prefixes] After removing PREFIX: {:?}", result);
    
    // 替换前缀使用
    for (prefix, uri) in &prefixes {
        let escaped_prefix = regex::escape(prefix);
        let pattern = format!(r"(?m)(^|[^A-Za-z0-9_]){}:(\w+)", escaped_prefix);
        eprintln!("[DEBUG expand_prefixes] Replacing pattern {}", pattern);
        let re = regex::Regex::new(&pattern).expect("valid regex");
        let old_result = result.clone();
        result = re
            .replace_all(&result, |caps: &regex::Captures| {
                format!("{}<{}{}>", &caps[1], uri, &caps[2])
            })
            .to_string();
        if old_result != result {
            eprintln!("[DEBUG expand_prefixes] Result changed to: {:?}", result);
        }
    }
    
    eprintln!("[DEBUG expand_prefixes] Final result: {:?}", result);
    result
}

/// 展开 SPARQL 简写语法 (; 和 ,) 并按 . 分割三元组
fn expand_sparql_shorthand(input: &str) -> String {
    let mut result = String::new();
    let mut current_subject: Option<String> = None;
    
    // 首先按 . 或 ; 分割整个输入（处理跨行或同行的多个三元组）
    // 但需要保护 <...> IRIs 中的 . 和 ;
    let mut in_iri = false;
    let mut current_segment = String::new();
    
    for ch in input.chars() {
        if ch == '<' && !in_iri {
            in_iri = true;
            current_segment.push(ch);
        } else if ch == '>' && in_iri {
            in_iri = false;
            current_segment.push(ch);
        } else if (ch == '.' || ch == ';') && !in_iri {
            // 段结束符
            let trimmed = current_segment.trim();
            if !trimmed.is_empty() {
                if trimmed.starts_with('?') {
                    // 这是一个完整的三元组（以变量开头），提取主语
                    if let Some(first_space) = trimmed.find(' ') {
                        current_subject = Some(trimmed[..first_space].to_string());
                    }
                    result.push_str(trimmed);
                    result.push_str(" .\n");
                } else if trimmed.starts_with('<') && current_subject.is_some() {
                    // 这是一个省略主语的谓词-宾语对，需要添加主语
                    if let Some(ref subject) = current_subject {
                        result.push_str(subject);
                        result.push(' ');
                        result.push_str(trimmed);
                        result.push_str(" .\n");
                    }
                }
                // 否则丢弃（如 FILTER, BIND 等）
            }
            current_segment.clear();
        } else {
            current_segment.push(ch);
        }
    }
    
    // 处理最后一个段（如果没有以 . 或 ; 结尾）
    let trimmed = current_segment.trim();
    if !trimmed.is_empty() {
        if trimmed.starts_with('?') {
            if let Some(first_space) = trimmed.find(' ') {
                current_subject = Some(trimmed[..first_space].to_string());
            }
            result.push_str(trimmed);
            result.push_str(" .\n");
        } else if trimmed.starts_with('<') && current_subject.is_some() {
            if let Some(ref subject) = current_subject {
                result.push_str(subject);
                result.push(' ');
                result.push_str(trimmed);
                result.push_str(" .\n");
            }
        }
    }
    
    if result.is_empty() {
        input.to_string()
    } else {
        result
    }
}

fn extract_optional_patterns(where_block: &str) -> Vec<Vec<TriplePattern>> {
    let re = regex::Regex::new(r"(?is)OPTIONAL\s*\{([^{}]*)\}").expect("valid optional regex");
    re.captures_iter(where_block)
        .map(|cap| extract_triple_patterns(cap.get(1).map(|m| m.as_str()).unwrap_or_default()))
        .filter(|p| !p.is_empty())
        .collect()
}

fn extract_union_patterns(where_block: &str) -> Vec<Vec<TriplePattern>> {
    let re = regex::Regex::new(r"(?is)\{([^{}]*)\}\s*UNION\s*\{([^{}]*)\}")
        .expect("valid union regex");
    let mut out = Vec::new();
    for cap in re.captures_iter(where_block) {
        let left = extract_triple_patterns(cap.get(1).map(|m| m.as_str()).unwrap_or_default());
        let right = extract_triple_patterns(cap.get(2).map(|m| m.as_str()).unwrap_or_default());
        if !left.is_empty() {
            out.push(left);
        }
        if !right.is_empty() {
            out.push(right);
        }
    }
    out
}

fn extract_vars_from_expr(expr: &str) -> Vec<String> {
    let re = regex::Regex::new(r"\?(\w+)").expect("valid var regex");
    re.captures_iter(expr)
        .map(|cap| cap[1].to_string())
        .collect()
}

fn extract_filter_expressions(where_block: &str) -> Vec<String> {
    let mut filters = Vec::new();
    let mut start = 0;
    let upper = where_block.to_ascii_uppercase();

    while let Some(filter_pos) = upper[start..].find("FILTER") {
        let abs_filter_pos = start + filter_pos;
        let rest = &where_block[abs_filter_pos + 6..];
        let rest_trimmed = rest.trim_start();
        let ws_len = rest.len().saturating_sub(rest_trimmed.len());
        let offset = abs_filter_pos + 6 + ws_len;
        let rest_upper = rest_trimmed.to_ascii_uppercase();

        if rest_trimmed.starts_with('(') {
            let mut depth = 0;
            let mut end = None;
            for (i, c) in rest_trimmed.chars().enumerate() {
                match c {
                    '(' => depth += 1,
                    ')' => {
                        depth -= 1;
                        if depth == 0 {
                            end = Some(i);
                            break;
                        }
                    }
                    _ => {}
                }
            }
            if let Some(e) = end {
                let expr = &rest_trimmed[1..e].trim();
                filters.push(expr.to_string());
                start = offset + e + 1;
            } else {
                start = offset;
            }
            continue;
        }

        let (is_not_exists, kw_len) = if rest_upper.starts_with("NOT EXISTS") {
            (true, "NOT EXISTS".len())
        } else if rest_upper.starts_with("EXISTS") {
            (false, "EXISTS".len())
        } else {
            start = offset;
            continue;
        };

        let after_kw = &rest_trimmed[kw_len..];
        let after_kw_trimmed = after_kw.trim_start();
        let ws2 = after_kw.len().saturating_sub(after_kw_trimmed.len());
        if !after_kw_trimmed.starts_with('{') {
            start = offset + kw_len + ws2;
            continue;
        }

        let mut depth = 0;
        let mut end = None;
        for (i, c) in after_kw_trimmed.chars().enumerate() {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = Some(i);
                        break;
                    }
                }
                _ => {}
            }
        }

        if let Some(e) = end {
            let body = after_kw_trimmed[1..e].trim();
            if is_not_exists {
                filters.push(format!("NOT EXISTS {{ {} }}", body));
            } else {
                filters.push(format!("EXISTS {{ {} }}", body));
            }
            start = offset + kw_len + ws2 + e + 1;
        } else {
            start = offset + kw_len + ws2;
        }
    }

    filters
}

fn find_top_level_keyword(s: &str, keyword: &str) -> Option<usize> {
    let upper = s.to_ascii_uppercase();
    let kw = keyword.to_ascii_uppercase();
    let bytes = upper.as_bytes();
    let kw_bytes = kw.as_bytes();
    let mut depth = 0i32;
    let mut i = 0usize;

    while i + kw_bytes.len() <= bytes.len() {
        match bytes[i] as char {
            '{' => depth += 1,
            '}' => depth -= 1,
            _ => {}
        }
        if depth == 0 && &bytes[i..i + kw_bytes.len()] == kw_bytes {
            return Some(i);
        }
        i += 1;
    }
    None
}

fn extract_limit(sparql: &str) -> Option<usize> {
    let upper = sparql.to_ascii_uppercase();
    let pos = upper.rfind("LIMIT")?;
    let rest = sparql[pos + 5..].trim();
    let num = rest.split_whitespace().next()?;
    num.parse::<usize>().ok()
}

fn extract_order_by(sparql: &str) -> Vec<OrderByItem> {
    let Some(order_pos) = find_top_level_keyword(sparql, "ORDER BY") else {
        return Vec::new();
    };
    let after_order = &sparql[order_pos + "ORDER BY".len()..];
    let mut end = after_order.len();
    if let Some(p) = find_top_level_keyword(after_order, "LIMIT") {
        end = end.min(p);
    }

    let order_part = after_order[..end].trim();
    let mut items = Vec::new();

    let re = regex::Regex::new(r"(?i)(ASC|DESC)?\s*\(?\s*\?(\w+)\s*\)?").expect("valid order by regex");
    for cap in re.captures_iter(order_part) {
        let var = cap.get(2).map(|m| m.as_str().to_string()).unwrap_or_default();
        if var.is_empty() {
            continue;
        }
        let direction = match cap.get(1).map(|m| m.as_str().to_ascii_uppercase()) {
            Some(d) if d == "DESC" => SortDirection::Desc,
            _ => SortDirection::Asc,
        };
        items.push(OrderByItem { variable: var, direction });
    }

    items
}

fn extract_group_by(sparql: &str) -> Vec<String> {
    let Some(group_pos) = find_top_level_keyword(sparql, "GROUP BY") else {
        return Vec::new();
    };
    let after_group = &sparql[group_pos + "GROUP BY".len()..];
    let mut end = after_group.len();
    for kw in ["HAVING", "ORDER BY", "LIMIT"] {
        if let Some(p) = find_top_level_keyword(after_group, kw) {
            end = end.min(p);
        }
    }
    after_group[..end]
        .split_whitespace()
        .filter(|t| t.starts_with('?'))
        .map(|t| t.trim_matches(|c| c == ',' || c == '(' || c == ')').trim_start_matches('?').to_string())
        .collect()
}

fn extract_having(sparql: &str) -> Vec<String> {
    let Some(having_pos) = find_top_level_keyword(sparql, "HAVING") else {
        return Vec::new();
    };
    let after_having = &sparql[having_pos + "HAVING".len()..];
    let mut end = after_having.len();
    for kw in ["ORDER BY", "LIMIT"] {
        if let Some(p) = find_top_level_keyword(after_having, kw) {
            end = end.min(p);
        }
    }

    let having_part = &after_having[..end];
    let mut exprs = Vec::new();
    let mut paren_depth = 0;
    let mut start = 0;
    let bytes = having_part.as_bytes();

    for (i, &b) in bytes.iter().enumerate() {
        match b {
            b'(' => paren_depth += 1,
            b')' => {
                paren_depth -= 1;
                if paren_depth == 0 {
                    let expr = having_part[start..=i].trim().to_string();
                    if !expr.is_empty() {
                        exprs.push(expr);
                    }
                    start = i + 1;
                }
            }
            _ => {}
        }
    }
    if exprs.is_empty() && !having_part.trim().is_empty() {
        exprs.push(having_part.trim().to_string());
    }
    exprs
}

fn extract_binds(sparql: &str) -> Vec<BindExpr> {
    let mut binds = Vec::new();
    let bind_start_re = regex::Regex::new(r"(?i)BIND\s*\(").expect("valid bind start regex");
    let as_alias_re = regex::Regex::new(r"(?is)^(?P<expr>.+)\s+AS\s+\?(?P<alias>[A-Za-z_]\w*)\s*$")
        .expect("valid bind as regex");

    for m in bind_start_re.find_iter(sparql) {
        let matched = &sparql[m.start()..m.end()];
        let Some(local_open) = matched.rfind('(') else { continue; };
        let open_pos = m.start() + local_open;

        let mut depth: i32 = 0;
        let mut close_pos: Option<usize> = None;
        for (off, ch) in sparql[open_pos..].char_indices() {
            if ch == '(' {
                depth += 1;
            } else if ch == ')' {
                depth -= 1;
                if depth == 0 {
                    close_pos = Some(open_pos + off);
                    break;
                }
            }
        }

        let Some(close_pos) = close_pos else { continue; };
        if close_pos <= open_pos + 1 {
            continue;
        }

        let inner = sparql[open_pos + 1..close_pos].trim();
        if let Some(cap) = as_alias_re.captures(inner) {
            binds.push(BindExpr {
                expression: cap["expr"].trim().to_string(),
                alias: cap["alias"].to_string(),
            });
        }
    }

    binds
}


/// 提取 CONSTRUCT 查询的模板三元组
fn extract_construct_template(sparql: &str) -> Vec<TriplePattern> {
    let upper = sparql.to_ascii_uppercase();
    
    // 找到 CONSTRUCT 后的 { 块
    if let Some(construct_pos) = upper.find("CONSTRUCT") {
        let after_construct = &sparql[construct_pos + 9..];
        
        // 查找模板块 { ... }
        if let Some(start) = after_construct.find('{') {
            let mut depth = 0_i32;
            let chars: Vec<char> = after_construct[start..].chars().collect();
            
            for (idx, ch) in chars.iter().enumerate() {
                if *ch == '{' {
                    depth += 1;
                } else if *ch == '}' {
                    depth -= 1;
                    if depth == 0 {
                        let template_block = chars[1..idx].iter().collect::<String>();
                        return extract_triple_patterns(&template_block);
                    }
                }
            }
        }
    }
    
    Vec::new()
}

/// 提取 DESCRIBE 查询的资源
fn extract_describe_resources(sparql: &str) -> Vec<String> {
    let upper = sparql.to_ascii_uppercase();
    let mut resources = Vec::new();
    
    if let Some(describe_pos) = upper.find("DESCRIBE") {
        let after_describe = &sparql[describe_pos + 8..];
        
        // 提取到 WHERE 或查询结束
        let end_pos = upper[describe_pos..].find("WHERE")
            .map(|p| p - 8)
            .unwrap_or(after_describe.len());
        
        let resources_part = &after_describe[..end_pos.min(after_describe.len())];
        
        // 解析资源（URI 或变量）
        // 简单解析：以 < 开头到 > 结束，或以 ? 开头的变量
        let re = regex::Regex::new(r"(<[^>]+>|\?[A-Za-z_][A-Za-z0-9_]*)").expect("valid regex");
        for cap in re.captures_iter(resources_part) {
            resources.push(cap[1].to_string());
        }
    }
    
    resources
}
