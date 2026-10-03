from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'import_animations.py').read_text().replace('PROJECT=O.parents[1]','PROJECT=O.parents[2]')
exec(compile(code,str(O/'import_index_animations.py'),'exec'))
