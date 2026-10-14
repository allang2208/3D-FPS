"""Read/export the eleven live long-gun asset families for contact inspection."""
import json,re,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[2];X=O/'Inputs';X.mkdir(exist_ok=True)
base=json.loads((P/'SourceAssets/BlessedLaser20261006/Model/Sources/mount-sources.json').read_text())
hosts={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
       'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
       'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny'}
for family,header in {'HK416':'HK416','ASH12':'ASH12','M16':'M16','A762':'A762','SVD':'SVD','PKM':'PKMLowpoly','LMG201':'LMG201','Super90':'Super90'}.items():
    hosts[family]=re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)"\)',(P/'Source/FPSGAME/Weapons'/(header+'WeaponAssets.h')).read_text(encoding='utf-8-sig'))[1]
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
def export(asset,path,skinned=False):
    task=u.AssetExportTask();task.object=asset;task.filename=str(path);task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX() if skinned else u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+asset.get_path_name())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report={'families':{},'dirty_source_packages':sorted(dirty),'mode':'read-only current editor assets'}
for family,path in hosts.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError(path)
    fbx=X/(family+'-host.fbx');export(mesh,fbx,True)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    h={'path':mesh.get_path_name(),'fbx':str(fbx),'bones':{str(b.name):pack(b.world_transform) for b in bones if str(b.name).startswith('WPN_')}}
    row={'host':h,'devices':{}}
    for kind in ('laser','flashlight','blessed_laser'):
        if family=='Super90':path='/Game/Weapons/Super90/Tactical20261008/SM_Super90_'+kind
        elif kind=='blessed_laser':path='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Models/SM_BlessedLaser_'+family
        else:
            path=base[family]['source'].replace('laser',kind)
            if kind=='flashlight' and family in ('M4','AKM','QBZ191'):path=path.replace('TacticalDevices20260913/','TacticalDevices20260913/HunyuanV3/')
        mesh=u.load_asset(path)
        if not mesh:raise RuntimeError(path)
        fbx=X/(family+'-'+kind+'.fbx');export(mesh,fbx)
        sockets={}
        for name in ('Emitter','AimGuide'):
            sock=mesh.find_socket(name)
            if not sock:raise RuntimeError('Missing socket '+path+'/'+name)
            p=sock.relative_location;sockets[name]=[p.x,p.y,p.z]
        row['devices'][kind]={'path':path,'fbx':str(fbx),'sockets':sockets,'materials':[{ 'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else ''} for s in mesh.static_materials]}
    report['families'][family]=row
    (O/'current-assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('TACTICAL_FIT_EXPORTED '+family,flush=True)
print('TACTICAL_FIT_EXPORT_COMPLETE '+str(len(report['families'])),flush=True)
