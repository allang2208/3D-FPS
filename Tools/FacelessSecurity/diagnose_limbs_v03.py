"""Read the reported missing-extremity assets, without running the game."""
import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V03')
for d in ['Diagnosis','Native','Motion','Delivery','Logs','Before']:(ROOT/d).mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/FacelessSecurity'
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
report={'mesh':mesh.get_path_name(),'properties':{},'poses':{}}
for p in ['idle_clip','walk_clip','attack_clip','walk_speed','contact_time','contact_end','recovery_time']:
    x=cdo.get_editor_property(p);report['properties'][p]=x.get_path_name() if hasattr(x,'get_path_name') else x
report['materials']=[x.material_interface.get_path_name() if x.material_interface else None for x in mesh.get_editor_property('materials')]
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(mesh)
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.RAW;opts.optional_skeletal_mesh=mesh
def pack(t):return {'p':[t.translation.x,t.translation.y,t.translation.z],'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
for label,path in {'V02idle':report['properties']['idle_clip'],'V02walk':report['properties']['walk_clip'],'V02attack':report['properties']['attack_clip'],'V01idle':DEST+'/Animations/A_Security_idle','V02raw':DEST+'/Animations/V02Raw/A_Security_Raw_V02_idle'}.items():
    a=u.load_asset(path);rows=[]
    for t in [0.,min(.6,a.get_play_length()),a.get_play_length()*.5]:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts)
        rows.append({'time':t,'world':{b:pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones},'local':{b:pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.LOCAL)) for b in bones}})
    report['poses'][label]=rows
report['reference']={b:pack(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
(ROOT/'Diagnosis/ue_limbs_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
task=u.AssetExportTask();task.object=mesh;task.filename=str(ROOT/'Diagnosis/SK_Security_Before.fbx')
task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption()
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Diagnostic mesh export failed')
print('SECURITY_LIMBS_CAPTURED '+json.dumps({'mesh':report['mesh'],'bones':len(bones),'clips':report['properties']}))
