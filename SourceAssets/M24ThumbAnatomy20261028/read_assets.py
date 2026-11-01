from pathlib import Path
O=Path(__file__).resolve().parent
code=(O.parent/'M24GripFinish20261028/read_assets.py').read_text()
exec(compile(code,'read_current_m24','exec'))
