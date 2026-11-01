"""Save independent M24 optic variants; preserve source geometry and optical slots."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent
spec=json.loads((O/'fit_recipe.json').read_text())
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
D='/Game/Weapons/M24/CommonOptics20261028'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('Unsaved M24 optic assets retained')
R={'complete':False,'saved':[],'meshes':{},'gameplay_tested':False}
def receipt():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    R['saved'].append(asset.get_path_name());receipt();return asset
def copy(src,dst):
    asset=u.load_asset(dst) if E.does_asset_exist(dst) else E.duplicate_asset(src,dst)
    if not asset:raise RuntimeError('Missing asset '+src)
    return asset
materials={}
for key,row in spec['assets'].items():
    if row['source'] in dirty:raise RuntimeError('Unsaved shared optic source retained: '+row['source'])
    mesh=copy(row['source'],row['target'])
    # These body instances already contain authored metal/polymer masks, normal
    # maps and matte inner-tube treatment. Keep that graph/UV contract rather
    # than applying the M24 body atlas to unrelated UVs.
    for i,slot in enumerate(row['materials']):
        source=slot['material'];m=u.load_asset(source)
        if isinstance(m,u.MaterialInstanceConstant) and 'R01_Roughness' in slot.get('scalars',{}):
            if source not in materials:
                target=D+'/Materials/MI_M24_'+key+'_Body'
                m=copy(source,target)
                L.set_material_instance_scalar_parameter_value(m,'R01_Roughness',.39)
                L.set_material_instance_scalar_parameter_value(m,'R01_Grain',.008)
                L.set_material_instance_scalar_parameter_value(m,'R01_Variation',.004)
                L.update_material_instance(m);save(m);materials[source]=m
            m=materials[source]
        mesh.set_material(i,m)
    for name,pose in row['sockets'].items():
        s=mesh.find_socket(name)
        if not s:
            s=u.StaticMeshSocket(outer=mesh);s.set_editor_property('socket_name',name);mesh.add_socket(s)
        s.set_editor_property('relative_location',u.Vector(*pose['location']))
        s.set_editor_property('relative_rotation',u.Rotator())
    E.set_metadata_tag(mesh,'M24OpticFit','Native shared optic geometry; measured M24 rail; SourceAssets/M24CommonOptics20261028/fit_recipe.json')
    save(mesh)
    R['meshes'][key]={'asset':mesh.get_path_name(),'source':row['source'],'sockets':row['sockets'],'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]}
    receipt()
R['complete']=True;receipt();print('M24_COMMON_OPTICS_SAVED',len(R['meshes']),flush=True)
