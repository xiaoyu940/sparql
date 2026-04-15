from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
old='''                let path = request.url().to_string();
                let method = request.method().clone();
                consecutive_errors = 0;
'''
new='''                let path = request.url().to_string();
                let method = request.method().clone();
                let requested_cors_headers = request
                    .headers()
                    .iter()
                    .find(|h| h.field.equiv("Access-Control-Request-Headers"))
                    .map(|h| h.value.as_str().to_string());
                consecutive_errors = 0;
'''
if old not in text:
    raise SystemExit('loop variable block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('inserted requested_cors_headers variable')