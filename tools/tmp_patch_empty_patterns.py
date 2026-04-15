from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''        if patterns.is_empty() {
            // 绌烘ā寮忔椂浣跨敤绗竴涓彲鐢ㄨ〃浣滀负fallback
            if let Some((_, metadata)) = metadata_map.iter().next() {
                return LogicNode::ExtensionalData {
                    table_name: metadata.table_name.clone(),
                    column_mapping: Self::fallback_mapping(&metadata),
                    metadata: Arc::clone(metadata),
                };
            }
            // 娌℃湁浠讳綍鍏冩暟鎹椂鐨刦allback
            return LogicNode::ExtensionalData {
                table_name: "ontop_mappings".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(TableMetadata::default()),
            };
        }'''
new='''        if patterns.is_empty() {
            let metadata = Arc::new(TableMetadata {
                table_name: "(SELECT 1)".to_string(),
                columns: Vec::new(),
                primary_keys: Vec::new(),
                foreign_keys: HashMap::new(),
            });
            return LogicNode::ExtensionalData {
                table_name: "(SELECT 1)".to_string(),
                column_mapping: HashMap::new(),
                metadata,
            };
        }'''
if old not in s:
    raise SystemExit('empty patterns block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched empty pattern fallback to one-row virtual table')
