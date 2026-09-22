from pathlib import Path
folder=Path(__file__).parent
for name in ('read_retirement10_inputs.py','retire_assets10.py'):
 p=folder/name
 exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p)})
