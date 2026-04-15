from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/lib.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('.set_restart_time(std::time::Duration::from_secs(1))','.set_restart_time(Some(std::time::Duration::from_secs(1)))')
p.write_text(text,encoding='utf-8')
print('fixed restart_time Option signature')