from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

if 'fn is_rdf_type_predicate(predicate: &str) -> bool' not in s:
    anchor='    fn resolve_metadata_for_predicate(\n'
    idx=s.find(anchor)
    if idx==-1:
        raise SystemExit('anchor not found')
    helper='''    fn is_rdf_type_predicate(predicate: &str) -> bool {
        predicate == "a"
            || predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            || predicate.ends_with("rdf-syntax-ns#type")
    }

'''
    s=s[:idx]+helper+s[idx:]

old='''let mut table_patterns: HashMap<String, Vec<&super::TriplePattern>> = HashMap::new();
        let mut table_metadata: HashMap<String, Arc<TableMetadata>> = HashMap::new();

        eprintln!("[DEBUG IRConverter] Starting grouping loop, normal_patterns len: {}", normal_patterns.len());
        for (idx, pattern) in normal_patterns.iter().enumerate() {
            eprintln!("[DEBUG IRConverter] Processing pattern[{}]: predicate={}", idx, pattern.predicate);
            let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&pattern.subject),
                metadata_map,
                mappings
            );'''
new='''let mut table_patterns: HashMap<String, Vec<&super::TriplePattern>> = HashMap::new();
        let mut table_metadata: HashMap<String, Arc<TableMetadata>> = HashMap::new();
        let mut subject_preferred_table: HashMap<String, String> = HashMap::new();
        let mut ordered_patterns: Vec<&super::TriplePattern> = normal_patterns.iter().collect();
        ordered_patterns.sort_by_key(|p| if Self::is_rdf_type_predicate(&p.predicate) { 1 } else { 0 });

        eprintln!("[DEBUG IRConverter] Starting grouping loop, normal_patterns len: {}", normal_patterns.len());
        for (idx, pattern) in ordered_patterns.iter().enumerate() {
            eprintln!("[DEBUG IRConverter] Processing pattern[{}]: predicate={}", idx, pattern.predicate);
            let preferred_table = subject_preferred_table.get(&pattern.subject).map(|s| s.as_str());
            let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&pattern.subject),
                preferred_table,
                metadata_map,
                mappings
            );'''
if old not in s:
    raise SystemExit('loop block not found')
s=s.replace(old,new,1)

old2='''            eprintln!("[DEBUG IRConverter] Pattern[{}] mapped to table: {}", idx, metadata.table_name);
            table_patterns.entry(metadata.table_name.clone()).or_default().push(pattern);
            table_metadata.entry(metadata.table_name.clone()).or_insert_with(|| Arc::clone(&metadata));'''
new2='''            eprintln!("[DEBUG IRConverter] Pattern[{}] mapped to table: {}", idx, metadata.table_name);
            subject_preferred_table
                .entry(pattern.subject.clone())
                .or_insert_with(|| metadata.table_name.clone());
            table_patterns.entry(metadata.table_name.clone()).or_default().push(pattern);
            table_metadata.entry(metadata.table_name.clone()).or_insert_with(|| Arc::clone(&metadata));'''
if old2 not in s:
    raise SystemExit('save block not found')
s=s.replace(old2,new2,1)

sig_old='''    fn resolve_metadata_for_predicate_with_context(
        predicate: &str,
        subject: Option<&str>,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Option<Arc<TableMetadata>> {'''
sig_new='''    fn resolve_metadata_for_predicate_with_context(
        predicate: &str,
        subject: Option<&str>,
        preferred_table: Option<&str>,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Option<Arc<TableMetadata>> {'''
if sig_old not in s:
    raise SystemExit('signature not found')
s=s.replace(sig_old,sig_new,1)

anchor2='''        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        if let Some(subj) = subject {'''
ins='''        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        if let Some(pref_table) = preferred_table {
            for rule in &matching_rules {
                if rule.table_name == pref_table {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        if let Some(subj) = subject {'''
if anchor2 not in s:
    raise SystemExit('disambiguation anchor not found')
s=s.replace(anchor2,ins,1)

p.write_text(s,encoding='utf-8')
print('patched ok')
