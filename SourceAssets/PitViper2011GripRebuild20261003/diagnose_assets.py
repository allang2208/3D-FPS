import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
w=next(w for w in catalog['weapons'] if w['id']=='ue_pit_viper2011')
binding=w['pistol_grip_surface'];out={'binding':binding,'meshes':{},'materials':{}}
for path in [binding['mesh']]+[v['mesh'] for v in binding.get('variants',{}).values()]:
    mesh=u.load_asset(path)
    if not mesh:out['meshes'][path]={'missing':True};continue
    out['meshes'][path]={'bounds':str(mesh.get_bounds()),'lods':mesh.get_num_lods(),
       'slots':[(str(s.material_slot_name),s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.static_materials]}
for part in ('pistol_grip_granular','pistol_grip_diamond','pistol_grip_quickdot','pit_viper_vip_scales'):
    path=binding.get('variants',{}).get(part,{}).get('material','/Game/Weapons/PistolGripSurface20260927/Materials/M_'+part)
    mat=u.load_asset(path)
    out['materials'][part]={'path':path,'loaded':bool(mat)}
    if mat:out['materials'][part].update(two_sided=mat.get_editor_property('two_sided'),tangent_space_normal=mat.get_editor_property('tangent_space_normal'))
(O/'asset_diagnosis.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print('PIT_VIPER_GRIP_DIAGNOSIS '+json.dumps(out,ensure_ascii=False))
