"""Single owned headless asset import batch; no map, PIE or gameplay test."""
from pathlib import Path
P=Path(__file__).resolve().parent
for name in ('import_modules.py','import_icons.py'):
    script=P/name
    exec(compile(script.read_text(encoding='utf-8-sig'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
