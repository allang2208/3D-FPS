import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/material_v04/fab_source');out.mkdir(parents=True,exist_ok=True)
rows=[]
for path in unreal.EditorAssetLibrary.list_assets('/Game/ZombiSkinMaterial',recursive=True):
 a=unreal.load_asset(path)
 if not a:continue
 row={'asset':path,'class':a.get_class().get_name()}
 if isinstance(a,unreal.Texture2D):
  t=unreal.AssetExportTask();t.object=a;t.filename=str(out/(a.get_name()+'.png'));t.automated=True;t.prompt=False;t.replace_identical=True
  row['exported']=unreal.Exporter.run_asset_export_task(t);row['file']=t.filename
 rows.append(row)
(out/'assets.json').write_text(json.dumps(rows,indent=2))
unreal.log('FAB_SKIN_EXPORT_COMPLETE')
