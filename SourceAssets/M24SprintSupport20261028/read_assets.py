from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O.parent/'M24GripFinish20261028/read_assets.py').read_text(),'read_live_m24','exec'))
