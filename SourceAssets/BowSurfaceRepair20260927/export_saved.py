"""Read back the four engine assets for the requested surface diagnosis."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;OUT=P/'SavedAssetReadback';OUT.mkdir(exist_ok=True)
saved=json.loads((P/'import-receipt.json').read_text())['saved']
for name,path in saved.items():
    task=u.AssetExportTask();task.object=u.load_asset(path);task.filename=str(OUT/(name+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Could not read back '+name)
print('BOW_SAVED_ASSET_READBACK',len(saved))
