from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/optimizer/rules/left_to_inner.rs')
s=p.read_text(encoding='utf-8')
marker='''    fn can_convert_to_inner(
        &self,
        right_vars: &HashSet<String>,
        mandatory_vars: &HashSet<String>,
    ) -> bool {
        // 如果右侧变量都在mandatory_vars中，可以转换
        right_vars.iter().all(|v| mandatory_vars.contains(v)) && !right_vars.is_empty()
    }
'''
replacement='''    fn can_convert_to_inner(
        &self,
        right_vars: &HashSet<String>,
        mandatory_vars: &HashSet<String>,
        right: &LogicNode,
    ) -> bool {
        if let LogicNode::ExtensionalData { table_name, .. } = right {
            if table_name == "(SELECT 1)" {
                return false;
            }
        }
        right_vars.iter().all(|v| mandatory_vars.contains(v)) && !right_vars.is_empty()
    }
'''
if marker not in s:
    raise SystemExit('can_convert_to_inner block not found')
s=s.replace(marker,replacement,1)
s=s.replace('if self.can_convert_to_inner(&right_vars, &mandatory_vars) {','if self.can_convert_to_inner(&right_vars, &mandatory_vars, right) {',1)
p.write_text(s,encoding='utf-8')
print('patched left_to_inner guard for synthetic (SELECT 1) right branch')
