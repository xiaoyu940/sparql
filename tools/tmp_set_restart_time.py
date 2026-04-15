from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/lib.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('.enable_spi_access()\n          .load();','.enable_spi_access()\n          .set_restart_time(std::time::Duration::from_secs(1))\n          .load();',1)
text=text.replace('.enable_spi_access()\n          .load_dynamic();','.enable_spi_access()\n          .set_restart_time(std::time::Duration::from_secs(1))\n          .load_dynamic();',1)
p.write_text(text,encoding='utf-8')
print('inserted restart_time on bgworker builders')