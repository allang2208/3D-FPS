import unreal as u,json
from pathlib import Path
out=Path(__file__).parent/'Review/native_cases.json'
u.SystemLibrary.execute_console_command(None,'fps.m24.ReviewBipod '+str(out).replace('\\','/'))
if not out.exists():raise RuntimeError('Native bipod review did not run')
report=json.loads(out.read_text(encoding='utf-16' if out.read_bytes()[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'))
print('M24_BIPOD_NATIVE_CASES',json.dumps(report),flush=True)
if report['failures']:raise RuntimeError('M24 bipod review failures: '+str(report['failures']))
