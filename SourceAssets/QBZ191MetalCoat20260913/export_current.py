import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/QBZ191/Attachments20260913';(O/'Sources').mkdir(exist_ok=True)
previous=json.loads((O.parent/'QBZ191Attachments20260913/sources.json').read_text());report={}
for key in previous:
 path=D+'/SM_QBZ191_'+key;mesh=u.load_asset(path)
 slots=[{'slot':str(x.material_slot_name),'material':x.material_interface.get_path_name()} for x in mesh.static_materials]
 file=P/'Content'/Path(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/file.relative_to(P)
 if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
 task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'Sources'/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
 opt=u.FbxExportOption();opt.ascii=False;opt.level_of_detail=False;opt.collision=False;task.options=opt
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError(key)
 report[key]={'path':path,'fbx':task.filename,'slots':slots,'source_slots':previous[key]['slots']}
(O/'sources.json').write_text(json.dumps(report,indent=2));u.log('QBZ_CURRENT_SURFACES_EXPORTED')
