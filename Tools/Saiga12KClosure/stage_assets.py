from pathlib import Path
import json
T=Path('D:/FPS3D/FPSGAME/Tools/Saiga12KClosure');O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018')
source=json.loads((O/'Reports/source-check.json').read_text())
if not source['geometry_finite'] or not source['degenerate_free']:raise RuntimeError('Geometry repair incomplete')
for name in ('read_baseline.py','install_assets.py','refine_accessories.py','finish_coating.py','check_saved_assets.py'):
 exec(compile((T/name).read_text(encoding='utf-8'),str(T/name),'exec'),{'__name__':'__main__'})
