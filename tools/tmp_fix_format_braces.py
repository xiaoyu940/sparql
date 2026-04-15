from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('format!("{\\"error\\":\\"{}\\"}", error_msg)','format!("{{\\"error\\":\\"{}\\"}}", error_msg)',1)
p.write_text(text,encoding='utf-8')
print('fixed panic error format braces')