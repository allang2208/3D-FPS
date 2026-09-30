from pathlib import Path
O=Path(__file__).parent
for script in ['materials.py','install.py']:
 p=O/script
 exec(compile(p.read_text(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
