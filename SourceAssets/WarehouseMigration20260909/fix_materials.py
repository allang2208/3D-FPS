import json
from pathlib import Path
import unreal
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseMigration20260909')
dest='/Game/ColdSteelUI/Warehouse20260909'
report=[]
parents={}
def local_parent(source):
 key=source.get_path_name()
 if key in parents:return parents[key]
 if key.startswith(dest+'/SurfaceParents/'):return source
 name='Warehouse_'+source.get_name()
 path=dest+'/SurfaceParents/'+name
 target=unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,dest+'/SurfaceParents',source)
 parents[key]=target
 if isinstance(target,unreal.Material):
  target.set_editor_property('two_sided',True)
  unreal.MaterialEditingLibrary.set_material_usage(target,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
  unreal.MaterialEditingLibrary.recompile_material(target)
 else:target.set_editor_property('parent',local_parent(target.get_editor_property('parent')))
 assert unreal.EditorAssetLibrary.save_loaded_asset(target,only_if_is_dirty=False),path
 return target
for path in unreal.EditorAssetLibrary.list_assets(dest,recursive=True,include_folder=False):
 if '/Materials/' not in path:continue
 source=unreal.EditorAssetLibrary.load_asset(path)
 name='Surface_'+source.get_name()
 copy_path=dest+'/RuntimeSurfaces/'+name
 a=unreal.EditorAssetLibrary.load_asset(copy_path) if unreal.EditorAssetLibrary.does_asset_exist(copy_path) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,dest+'/RuntimeSurfaces',source)
 if isinstance(a,unreal.Material):
  # All eight source GLB materials are explicitly double-sided. Default-material fallback was single-sided.
  a.set_editor_property('two_sided',True)
  unreal.MaterialEditingLibrary.set_material_usage(a,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
  unreal.MaterialEditingLibrary.recompile_material(a)
  assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False),a.get_path_name()
  report.append({'path':a.get_path_name(),'two_sided':True,'skeletal':bool(a.get_editor_property('used_with_skeletal_mesh'))})
 elif isinstance(a,unreal.MaterialInstanceConstant):
  parent=local_parent(a.get_editor_property('parent'));a.set_editor_property('parent',parent)
  overrides=a.get_editor_property('base_property_overrides');overrides.set_editor_property('override_two_sided',True);overrides.set_editor_property('two_sided',True);a.set_editor_property('base_property_overrides',overrides)
  assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False),a.get_path_name()
  base=parent
  while isinstance(base,unreal.MaterialInstanceConstant):base=base.get_editor_property('parent')
  report.append({'path':a.get_path_name(),'two_sided':True,'skeletal':bool(base.get_editor_property('used_with_skeletal_mesh')),'parent':parent.get_path_name()})
assert len(report)==8 and all(r['skeletal'] for r in report),report
(out/'materials_report.json').write_text(json.dumps(report,indent=2))
manifest=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json')
data=json.loads(manifest.read_text());data['materials']={r['path'].split('.')[-1].removeprefix('Surface_'):r['path'] for r in report};manifest.write_text(json.dumps(data,indent=2))
unreal.log('WAREHOUSE_MATERIALS_PASS '+str(len(report)))
