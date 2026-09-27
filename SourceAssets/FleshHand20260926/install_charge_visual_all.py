"""Install the revised charge animation, followed by its cosmetic assets and BP bindings."""
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ['install_charge.py','install_charge_visual.py']:
    script=root/name
    exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
