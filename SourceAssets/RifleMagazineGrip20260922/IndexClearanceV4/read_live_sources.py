from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'read_sources.py').read_text()
exec(compile(code,str(O/'read_live_sources.py'),'exec'))
