from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('format!("{\\"error\\":\\"{}\\"}", msg)','format!("{{\\"error\\":\\"{}\\"}}", msg)')
p.write_text(text,encoding='utf-8')
print('fixed json format escaping')