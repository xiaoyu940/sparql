from pathlib import Path
import re

# Patch lib.rs describe class IRI handling
p=Path('/home/yuxiaoyu/rs_ontop_core/src/lib.rs')
s=p.read_text(encoding='utf-8')
old='''                if is_type_predicate {
                    if pattern.object.starts_with('<') && pattern.object.ends_with('>') {
                        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');'''
new='''                if is_type_predicate {
                    let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
                    if !class_iri.is_empty() {'''
if old not in s:
    raise SystemExit('describe type block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# Patch ir_converter.rs correlated var detection
p2=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s2=p2.read_text(encoding='utf-8')
old_loop='''        for sub_parsed in &parsed.sub_queries {
            let sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);
            let core_bindings = Self::extract_var_bindings(&core);
            let sub_bindings = Self::extract_var_bindings(&sub_plan);
            let correlated_vars: Vec<String> = sub_bindings
                .keys()
                .filter(|v| core_bindings.contains_key(*v))
                .cloned()
                .collect();

            eprintln!("[SUBQDBG] correlated_vars={:?}", correlated_vars);
            let sub_node = LogicNode::SubQuery {
                inner: Box::new(sub_plan),
                correlated_vars,
            };'''
new_loop='''        for sub_parsed in &parsed.sub_queries {
            let sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);
            let core_bindings = Self::extract_var_bindings(&core);
            let sub_vars = Self::collect_query_vars(sub_parsed);
            let correlated_vars: Vec<String> = sub_vars
                .into_iter()
                .filter(|v| core_bindings.contains_key(v))
                .collect();

            let sub_node = LogicNode::SubQuery {
                inner: Box::new(sub_plan),
                correlated_vars,
            };'''
if old_loop not in s2:
    raise SystemExit('sub_queries loop block not found')
s2=s2.replace(old_loop,new_loop,1)

if 'fn collect_query_vars(parsed: &ParsedQuery) -> HashSet<String>' not in s2:
    ins=s2.find('fn extract_var_bindings(node: &LogicNode) -> HashMap<String, String> {')
    if ins==-1:
        raise SystemExit('extract_var_bindings marker not found')
    helper='''    fn collect_query_vars(parsed: &ParsedQuery) -> HashSet<String> {
        let mut vars = HashSet::new();

        for p in &parsed.main_patterns {
            if let Some(v) = p.subject.strip_prefix('?') {
                vars.insert(v.to_string());
            }
            if let Some(v) = p.predicate.strip_prefix('?') {
                vars.insert(v.to_string());
            }
            if let Some(v) = p.object.strip_prefix('?') {
                vars.insert(v.to_string());
            }
        }

        let re = regex::Regex::new(r"\?([A-Za-z_][A-Za-z0-9_]*)").expect("valid var regex");
        for f in &parsed.filter_expressions {
            for cap in re.captures_iter(f) {
                vars.insert(cap[1].to_string());
            }
        }

        for v in &parsed.projected_vars {
            vars.insert(v.trim_start_matches('?').to_string());
        }

        vars
    }

'''
    s2=s2[:ins]+helper+s2[ins:]

p2.write_text(s2,encoding='utf-8')
print('patched describe type handling and correlated vars detection for subqueries')
