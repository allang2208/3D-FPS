from pathlib import Path
p=Path(__file__).parent/'import_revision06.py'
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'WITCH_REVISION06_FINISH_ONLY':True})
