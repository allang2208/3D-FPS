from pathlib import Path
O=Path(__file__).parent
for name in ['materials.py','install.py']:
 p=O/name;exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
