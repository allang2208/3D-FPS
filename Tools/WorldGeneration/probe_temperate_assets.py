"""Read-only probe of the imported Black Poplar and selected Normandy FX."""
import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/Saved/TemperateHills')
out.mkdir(parents=True,exist_ok=True)
r=u.AssetRegistryHelpers.get_asset_registry()
r.scan_paths_synchronous(['/Game/Megaplant_Library','/Game/UnrealNormandy'],False)
report={'trees':[],'fx':[],'materials':[]}
for a in r.get_assets_by_path('/Game/Megaplant_Library/Tree_Black_Poplar/Tree_Black_Poplar_01',True):
    if str(a.asset_class_path.asset_name)!='SkeletalMesh':continue
    mesh=a.get_asset(); row={'path':str(a.package_name)}
    bounds=mesh.get_bounds()
    row['bounds']={'origin':str(bounds.origin),'extent':str(bounds.box_extent)}
    row['materials']=[str(m.material_interface.get_path_name()) for m in mesh.materials]
    for prop in ['nanite_settings','skeleton','physics_asset','default_mesh_deformer']:
        try:row[prop]=str(mesh.get_editor_property(prop))
        except Exception as e:row[prop]=str(e)
    report['trees'].append(row)
for a in r.get_assets_by_path('/Game/UnrealNormandy',True):
    path=str(a.package_name);cls=str(a.asset_class_path.asset_name)
    if cls in ['NiagaraSystem','Blueprint']:report['fx'].append({'path':path,'class':cls})
    if cls=='MaterialInstanceConstant' and any(s in path for s in ['Fog','Ground_','Grass_']):
        mat=a.get_asset(); row={'path':path,'scalars':{},'vectors':{},'textures':{}}
        for key in u.MaterialEditingLibrary.get_scalar_parameter_names(mat):
            row['scalars'][str(key)]=u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mat,key)
        for key in u.MaterialEditingLibrary.get_vector_parameter_names(mat):
            row['vectors'][str(key)]=str(u.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mat,key))
        for key in u.MaterialEditingLibrary.get_texture_parameter_names(mat):
            row['textures'][str(key)]=str(u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,key))
        report['materials'].append(row)
(out/'source-probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('TEMPERATE_SOURCE_PROBE_COMPLETE '+str(len(report['trees'])))
