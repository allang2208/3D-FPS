"""Task-scoped, read-only asset/contract inspection. No game, map, render or saves."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir())
DEST='/Game/Fluids/FurnaceCasting20260926/'
L=u.MaterialEditingLibrary
result={'runtime_tested':False,'rendered':False}
mesh=u.load_asset(DEST+'SM_FurnaceCastingSurface')
if not mesh:raise RuntimeError('Missing saved casting surface')
b=mesh.get_bounds()
result['bounds_cm']={'origin':[b.origin.x,b.origin.y,b.origin.z],
                     'extent':[b.box_extent.x,b.box_extent.y,b.box_extent.z]}
# Detect axis/unit mistakes from the actual imported package, not just the FBX manifest.
assert 34<2*b.box_extent.x<36, result['bounds_cm']
assert 7<2*b.box_extent.y<9, result['bounds_cm']
assert 37<2*b.box_extent.z<41, result['bounds_cm']
assert 34<b.origin.x<36 and 44<b.origin.z<47, result['bounds_cm']
result['materials']={}
for name in ['M_CastingStream','M_CastingPool','M_CastingDroplet']:
    m=u.load_asset(DEST+name)
    if not m:raise RuntimeError('Missing '+name)
    front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
    assert front, name+' missing Substrate output'
    result['materials'][name]={'blend':str(m.get_editor_property('blend_mode')),
                              'front_material':front.get_class().get_name()}
    prop=u.MaterialProperty.MP_OPACITY if name.endswith('Droplet') else u.MaterialProperty.MP_OPACITY_MASK
    assert L.get_material_property_input_node(m,prop), name+' missing opacity/mask'
    if name.endswith('Droplet'):
        assert m.get_editor_property('used_with_niagara_sprites')
    else:
        params={str(n.get_editor_property('parameter_name')):n for n in L.get_material_expressions(m)
                if isinstance(n,u.MaterialExpressionScalarParameter)}
        for parameter,index in [('CastingStartTime',0),('CastingSeed',1)]:
            assert params[parameter].get_editor_property('use_custom_primitive_data')
            assert params[parameter].get_editor_property('primitive_data_index')==index
result['slots']=[str(s.get_editor_property('material_interface').get_path_name())
                 for s in mesh.get_editor_property('static_materials')]
assert len(result['slots'])==2
assert all(s.startswith(DEST) for s in result['slots'])
ns=u.load_asset(DEST+'NS_CastingDroplets')
assert ns
api=u.get_default_object(u.NiagaraToolset_System)
variables=str(api.call_method('GetUserVariables',(ns,)).export_text())
for name in ['Flow','SparkGate','DetailReduction','ImpactHeight']:
    assert 'User.'+name in variables, name
result['niagara_parameters']=variables
result['status']='saved asset contracts passed; no runtime or visual acceptance'
(ROOT/'SourceAssets/FurnaceCasting20260926/asset-inspection.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('FURNACE_CASTING_ASSET_INSPECTION_PASSED',json.dumps(result['bounds_cm']),flush=True)
