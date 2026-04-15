from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/mapping/r2rml_parser.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('for _class_iri in &self.subject_map.class {','for class_iri in &self.subject_map.class {',1)
text=text.replace('predicate: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string(),','predicate: class_iri.clone(),',1)
p.write_text(text,encoding='utf-8')
print('patched rr:class conversion to class-iri keyed mapping rules')