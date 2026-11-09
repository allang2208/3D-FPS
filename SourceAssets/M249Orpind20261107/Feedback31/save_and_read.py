from pathlib import Path
r=Path(__file__).resolve().parent
for name in ['install.py','read_saved.py']:
 path=r/name
 exec(compile(path.read_text(),str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
