"""Import only the five A762 empty-reload assets, retaining their runtime paths."""
from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'RifleMagazineGrip20260922/import_animations.py').read_text()
exec(compile(code,str(O/'import_animations.py'),'exec'))
