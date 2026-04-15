from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''        if !(pattern.object.starts_with('<') && pattern.object.ends_with('>')) {
            return None;
        }
        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
'''
new='''        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
        if class_iri.is_empty() || class_iri.starts_with('?') {
            return None;
        }
'''
if old in text:
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched rdf:type class table resolver to support iri with/without <>')