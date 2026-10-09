"""Compile only the three faulty-lamp shaders using the actual RHI, no game or asset save."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
report=[]
for name in ('M_FaultFunction','M_ReceptionDiffusers','M_TransitDiffusers'):
    path='/Game/Dungeons/HallLighting20261007/Materials/'+name
    m=u.load_asset(path)
    if not m:raise RuntimeError('Missing '+path)
    stats=u.MaterialEditingLibrary.get_statistics(m)
    report.append(dict(path=path,domain=str(m.material_domain),statistics=str(stats)))
    print('HALL_SHADER_STAT',report[-1])
(ROOT/'Receipts/shader-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
