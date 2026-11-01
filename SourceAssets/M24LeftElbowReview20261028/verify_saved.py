import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;receipt=json.loads((O/'install_receipt.json').read_text());mesh=u.load_asset(receipt['path'])
task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'m24_after.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX()
opt=u.FbxExportOption();opt.set_editor_property('export_morph_targets',True);opt.set_editor_property('level_of_detail',False);task.options=opt
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Saved mesh export failed')
names=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
if any(n not in names for n in receipt['added_morphs']):raise RuntimeError('Saved morph missing')
receipt['fresh_process_morph_readback']=True;receipt['readback_fbx']='m24_after.fbx';(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('M24_ELBOW_FRESH_READBACK',len(names),flush=True)
