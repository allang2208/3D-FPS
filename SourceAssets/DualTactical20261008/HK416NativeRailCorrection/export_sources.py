"""Read the actual HK416 source assemblies and current fitted variants."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;X=O/'Inputs';X.mkdir(exist_ok=True)
paths={'host':'/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny',
       'laser':'/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_laser',
       'flashlight':'/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_flashlight',
       'blessed_laser':'/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Models/SM_BlessedLaser_HK416'}
paths.update({f'{kind}-{side}':f'/Game/Weapons/TacticalDevices20260913/DualFit20261008/HK416/SM_{kind}_{side}' for kind in ('laser','flashlight','blessed_laser') for side in (1,2)})
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths.values()):raise RuntimeError('HK416 assets contain unsaved edits; preserve them')
report={}
for name,path in paths.items():
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing '+path)
    task=u.AssetExportTask();task.object=asset;task.filename=str(X/(name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX() if name=='host' else u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if name=='host':
        # Reuse the previous live-editor skeletal export only while its exact
        # source package remains unchanged. Commandlet skeletal FBX export
        # requires a render MeshObject that is absent in this engine build.
        cached=O.parent/'FitReview/Inputs/HK416-host.fbx'
        package=O.parents[2]/'Content/Weapons/HK416/Reworked20260930/SK_HK416_Manny.uasset'
        if package.stat().st_mtime>cached.stat().st_mtime:raise RuntimeError('Host changed after cached live export')
        shutil.copy2(cached,task.filename)
    elif not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+path)
    sockets={}
    if name!='host':
        for label in ('Emitter','AimGuide'):
            socket=asset.find_socket(label);v=socket.relative_location;sockets[label]=[v.x,v.y,v.z]
    mats=asset.get_editor_property('materials') if name=='host' else asset.static_materials
    report[name]={'path':path,'fbx':task.filename,'sockets':sockets,'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else ''} for s in mats]}
(O/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HK416_NATIVE_SOURCES',len(report))
