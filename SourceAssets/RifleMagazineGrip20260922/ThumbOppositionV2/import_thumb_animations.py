"""Use the established short-batch import with independent V2 receipts/backups."""
from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'import_animations.py').read_text()
code=code.replace('PROJECT=O.parents[1]', 'PROJECT=O.parents[2]')
exec(compile(code,str(O/'import_thumb_animations.py'),'exec'))
