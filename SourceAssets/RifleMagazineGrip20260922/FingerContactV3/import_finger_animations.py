"""Import in the existing mutex batches, with V3 backups and receipts."""
from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'import_animations.py').read_text()
code=code.replace('PROJECT=O.parents[1]', 'PROJECT=O.parents[2]')
exec(compile(code,str(O/'import_finger_animations.py'),'exec'))
