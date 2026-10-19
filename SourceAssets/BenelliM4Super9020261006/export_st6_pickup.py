"""Export the native-body ST6 display source and its 3x3 icon."""
from pathlib import Path
TASK=Path(__file__).parent.parent/'ST6Reset20261017'
file=TASK/'render_icon.py'
exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file)})
