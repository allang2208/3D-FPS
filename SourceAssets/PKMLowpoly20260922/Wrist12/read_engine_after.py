from pathlib import Path
REPORT_NAME='engine_after.json'
script=Path(__file__).with_name('read_engine_pose.py')
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'))
