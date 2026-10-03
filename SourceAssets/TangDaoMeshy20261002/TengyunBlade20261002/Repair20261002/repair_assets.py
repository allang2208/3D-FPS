"""Fresh import into a new mesh package; preserve the empty old package."""
import json, shutil, runpy
from pathlib import Path
P = Path(__file__).resolve().parent
S = P.parent
manifest = S/'blade_manifest.json'
for path in [manifest,S/'import_receipt.json',S/'import_assets.py']:
    target = P/('Before_'+path.name)
    if not target.exists():shutil.copy2(path,target)
m = json.loads(manifest.read_text(encoding='utf-8'))
n = m['mesh_name']+'_SolidV2'
m['mesh'] = m['ue_root']+'/Meshes/'+n+'.'+n
m['repair_revision'] = 'TangDaoTengyunSolidV2_20261002'
manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
runpy.run_path(str(S/'import_assets.py'),run_name='__main__')
