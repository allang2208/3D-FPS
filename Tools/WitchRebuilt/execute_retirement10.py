from pathlib import Path
p=Path(__file__).with_name('retire_assets10.py')
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'WITCH_RETIRE_EXECUTE':True})
