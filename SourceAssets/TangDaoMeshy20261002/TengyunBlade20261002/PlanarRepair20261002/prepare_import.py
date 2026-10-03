"""Keep the uniform-thickness revision's new mesh import separate from live assets."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
T = P.parent
ROOT = P.parents[3]
m = json.loads((T/'blade_manifest.json').read_text(encoding='utf-8'))
if m.get('repair_revision')!='TangDaoTengyunPlanarSolidV4_20261002':
    raise RuntimeError('Finish the planar blade export first')
mesh_path = m['mesh'].split('.')[0]
target = (ROOT/'Content'/mesh_path.removeprefix('/Game/')).with_suffix('.uasset')
if target.exists():
    raise RuntimeError('Preserved an existing mesh package: '+str(target))
(P/'package-plan.json').write_text(json.dumps({'new_package':mesh_path,
    'reused_materials':list(m['materials'].values()),'reused_surface_root':m['surface_ue_root'],
    'existing_mesh_or_surface_packages_overwritten':False,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TENGYUN_PLANAR_NEW_MESH_PREPARED',flush=True)
