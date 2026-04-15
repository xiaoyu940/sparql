import argparse
import concurrent.futures as cf
import csv
import pathlib
import re
import subprocess
import time
from datetime import datetime

ROOT = pathlib.Path('/home/yuxiaoyu/rs_ontop_core')
RUNNER = ROOT / 'tests/python/run_all_tests.py'
PY = ROOT / 'tests/python/venv/bin/python'
OUT_DIR = ROOT / 'tests/output'

TOTAL_RE = re.compile(r'^总计:\s*(\d+)', re.M)
PASS_RE = re.compile(r'^通过:\s*(\d+)', re.M)
FAIL_RE = re.compile(r'^失败:\s*(\d+)', re.M)


def parse_num(pattern, text):
    m = pattern.search(text)
    return int(m.group(1)) if m else None


def run_once(run_id):
    t0 = time.time()
    p = subprocess.run([str(PY), str(RUNNER)], cwd=str(ROOT), capture_output=True, text=True)
    dt = round(time.time() - t0, 2)
    out = (p.stdout or '') + '\n' + (p.stderr or '')
    total = parse_num(TOTAL_RE, out)
    passed = parse_num(PASS_RE, out)
    failed = parse_num(FAIL_RE, out)
    return {
        'run': run_id,
        'exit_code': p.returncode,
        'total': total,
        'passed': passed,
        'failed': failed,
        'duration_sec': dt,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total', type=int, default=200)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = OUT_DIR / f'regression_parallel_{args.total}_runs_{args.workers}w_{ts}.csv'

    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(run_once, i): i for i in range(1, args.total + 1)}
        done = 0
        for fut in cf.as_completed(futures):
            row = fut.result()
            rows.append(row)
            done += 1
            print(f"[{done:03d}/{args.total}] run={row['run']} exit={row['exit_code']} total={row['total']} pass={row['passed']} fail={row['failed']} time={row['duration_sec']}s", flush=True)

    rows.sort(key=lambda x: x['run'])
    with summary_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['run', 'exit_code', 'total', 'passed', 'failed', 'duration_sec'])
        writer.writeheader()
        writer.writerows(rows)

    ok = sum(1 for r in rows if r['exit_code'] == 0)
    bad = len(rows) - ok
    print(f'FINISHED total={len(rows)} ok={ok} bad={bad}')
    print(f'SUMMARY_FILE={summary_file}')


if __name__ == '__main__':
    main()
