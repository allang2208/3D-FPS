from pathlib import Path
r=Path(__file__).resolve().parent
for name in ('read_sources.py','install.py'):
    exec(compile((r/name).read_text(),str(r/name),'exec'),{'__file__':str(r/name)})
