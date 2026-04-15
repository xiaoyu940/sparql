from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
s=p.read_text(encoding='utf-8')
old='''    // [CRITICAL] Initialize engine in bgworker process (ENGINE is process-local)
    log!("rs-ontop-core: Initializing engine in bgworker...");
    if let Err(e) = Spi::connect(|mut client| {
        crate::refresh_engine_from_spi(&mut client);
        Ok::<(), pgrx::spi::SpiError>(())
    }) {
        log!("rs-ontop-core: Engine init failed in bgworker: {}", e);
        // Continue anyway - engine might be initialized on first request
    } else {
        log!("rs-ontop-core: Engine initialized successfully in bgworker");
    }
'''
new='''    log!("rs-ontop-core: Skip eager engine init in bgworker startup");
'''
if old not in s:
    raise SystemExit('target init block not found in listener.rs')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched listener.rs: skip eager bgworker init')
