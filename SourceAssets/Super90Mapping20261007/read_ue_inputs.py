import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;R='/Game/Weapons/Super90/Cransh20261006';L=u.MaterialEditingLibrary
mesh=u.load_asset(R+'/SK_Super90_V7')
data={'pie':bool(u.EditorLevelLibrary.get_game_world()),'slots':[]}
for s in mesh.materials:
    m=s.material_interface;row={'name':str(s.material_slot_name),'material':m.get_path_name()}
    if isinstance(m,u.MaterialInstanceConstant):
        row['textures']={str(k):(t.get_path_name() if t else None) for k in L.get_texture_parameter_names(m) for t in [L.get_material_instance_texture_parameter_value(m,k)]}
        row['scalars']={k:L.get_material_instance_scalar_parameter_value(m,k) for k in ('SourceColorWeight','MaskUVChannel','Metallic','Roughness')}
    data['slots'].append(row)
(O/'ue_inputs.json').write_text(json.dumps(data,indent=2))
print('SUPER90_UE_INPUTS',json.dumps(data))
