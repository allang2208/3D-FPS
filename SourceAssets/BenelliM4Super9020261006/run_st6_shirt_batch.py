"""Save the restored ST6 sleeves, native fabric and updated display model."""
from pathlib import Path
TASK=Path(__file__).parent.parent/'ST6Reset20261017'
for name in ('import_sleeves.py','import_pickup_icon.py','publish.py'):
    file=TASK/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file)})
