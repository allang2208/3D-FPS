import json
from pathlib import Path
import unreal as u
out=Path(__file__).parent;dest='/Game/ColdSteelUI/Warehouse20260909/OrnamentsV7'
task=u.AssetImportTask()
for k,v in {'filename':str(out/'warehouse_chest_rigid.glb'),'destination_path':dest,'automated':True,'replace_existing':False,'save':True}.items():task.set_editor_property(k,v)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
assets=[u.EditorAssetLibrary.load_asset(p) for p in u.EditorAssetLibrary.list_assets(dest,recursive=True,include_folder=False)]
meshes=[a for a in assets if isinstance(a,u.SkeletalMesh)]
assert len(meshes)==1
result={'mesh':meshes[0].get_path_name()}
for a in assets:
 if isinstance(a,u.AnimSequence):
  for key,duration in [('open',.9),('close',.7)]:
   if key in a.get_name().lower():
    assert abs(a.get_play_length()-duration)<.001
    result[key]=a.get_path_name()
assert len(result)==3,result
(out/'import_report.json').write_text(json.dumps(result,indent=2))
u.log('CHEST_ORNAMENTS_IMPORT_PASS '+str(result))
