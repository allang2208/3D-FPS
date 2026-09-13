"""Export existing shared attachments and read the active pistol clips for authoring."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent; (O/'Sources').mkdir(exist_ok=True)
paths={'holographic':'/Game/Weapons/M4Holographic/SM_M4_Holographic',
       'panoramic_red_dot':'/Game/Weapons/PanoramicRedDot/SM_PanoramicRedDot',
       'suppressor':'/Game/Weapons/M4MuzzlesV1/SM_M4_suppressor'}
parts={}
for key,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError(path)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'Sources'/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    opt=u.FbxExportOption();opt.ascii=False;opt.level_of_detail=False;opt.collision=False;task.options=opt
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError(key)
    parts[key]={'path':path,'fbx':task.filename,'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]}
clips={}
for key in ['reload','reload_empty','equip_charge','equip_charge_empty','idle','aim']:
    path='/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_'+key
    clip=u.load_asset(path)
    if not clip:raise RuntimeError(path)
    clips[key]={'path':path,'duration':clip.get_play_length()}
(O/'sources.json').write_text(json.dumps({'parts':parts,'clips':clips},indent=2))
u.log('M1911_ATTACHMENT_SOURCES_EXPORTED '+json.dumps(clips))
