"""Finish the saved joint-repair metadata and restrict UE import to fresh packages."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
T = P.parent
ROOT = P.parents[3]
file = T/'blade_manifest.json'
m = json.loads(file.read_text(encoding='utf-8'))
if m.get('repair_revision') != 'TangDaoTengyunJointSolidV3_20261002':
    raise RuntimeError('Finish the joint geometry export before importing')
m.update(surface_ue_root=m['ue_root']+'/JointRepair20261002',
    material_name='M_TangDaoBladeRuneSurface_CloudTengyunJoint',
    material_source='/Game/Weapons/TangDao20261002/CloudRune20261002/Materials/M_TangDaoBladeRuneSurface_CloudTengyun',
    preserve_ui_icon=True)
path = m['surface_ue_root']+'/Materials/'+m['material_name']
m['materials'] = {'M_TangDaoTengyunSteel': path+'.'+m['material_name']}
packages = [m['mesh'].split('.')[0], path, path+'_Whirlwind']
packages += [m['surface_ue_root']+'/Textures/T_TangDao_Tengyun_'+key for key in ['BaseColor','Normal','ORM']]
existing = [p for p in packages if (ROOT/'Content'/p.removeprefix('/Game/')).with_suffix('.uasset').exists()]
if existing:
    raise RuntimeError('Preserved existing target packages: '+str(existing))
file.write_text(json.dumps(m, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(P/'package-plan.json').write_text(json.dumps({'new_packages': packages,
    'existing_packages_overwritten': [], 'old_editor_packages_preserved': True,
    'source_material': m['material_source'], 'runtime_tested': False}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('TENGYUN_JOINT_FRESH_PACKAGES_PREPARED', flush=True)
