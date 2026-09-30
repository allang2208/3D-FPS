from pathlib import Path
O=Path(__file__).parent
for name in ['install.py','check_assets.py']:
 p=O/name;exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
