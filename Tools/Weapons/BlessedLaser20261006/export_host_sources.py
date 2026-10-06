"""Read current host meshes and native bind frames, without modifying UE assets."""
import unreal as u,json,re
from pathlib import Path
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model/MountRepair/Hosts';O.mkdir(parents=True,exist_ok=True)
paths={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny',
 'M1911':'/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny'}
for family,header in {'HK416':'HK416','G18':'G18','PitViper2011':'PitViper2011','DanWesson715':'DanWesson715','RSH12':'RSH12','ASH12':'ASH12','M16':'M16','A762':'A762','SVD':'SVD','PKM':'PKMLowpoly','LMG201':'LMG201'}.items():
    paths[family]=re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)"\)',(P/'Source/FPSGAME/Weapons'/(header+'WeaponAssets.h')).read_text(encoding='utf-8-sig'))[1]
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
report=json.loads((O/'hosts.json').read_text()) if (O/'hosts.json').exists() else {}
for family,path in paths.items():
    if family in report:continue
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError(path)
    target=O/(family+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(target);task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption();task.options.export_morph_targets=False;task.options.level_of_detail=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Host export failed '+family)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    report[family]=dict(mesh=mesh.get_path_name(),fbx=str(target),bones={str(b.name):pack(b.world_transform) for b in bones if str(b.name).startswith('WPN_')})
    (O/'hosts.json').write_text(json.dumps(report,indent=2));print('BLESSED_HOST_EXPORTED',family,flush=True)
