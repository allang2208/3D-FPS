"""Read installed source tracks and export the actual arm meshes for authoring."""
import hashlib,json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent; ROOT=Path(u.Paths.project_dir()).resolve()
def unpack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
families={
 'Standard':('/Game/Weapons/AzureRunesword20260913','/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms'),
 'LongGrip':('/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations','/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')}
summary={}
for variant,(folder,mesh_path) in families.items():
    out=P/variant;out.mkdir(parents=True,exist_ok=True)
    mesh=u.load_asset(mesh_path);component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
    names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    parents={n:str(component.get_parent_bone(n)) for n in names}
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
    data={'variant':variant,'mesh':mesh_path,'parents':parents,'clips':{}}
    for clip in ('Idle','Thrust','Overhead','SprintOverhead'):
        path=folder+('/TacticalSprint20260921' if clip=='SprintOverhead' else '')+'/A_RuneSword_'+clip
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Missing source '+path)
        frames=u.AnimationLibrary.get_num_frames(asset);duration=asset.get_play_length();rows=[]
        for i in range(1 if clip=='Idle' else frames+1):
            t=i*duration/max(1,frames);pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
            if 'rest' not in data:data['rest']={n:unpack(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
            rows.append({'seconds':t,'world':{n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        data['clips'][clip]={'asset':asset.get_path_name(),'intervals':frames,'seconds':duration,
            'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'samples':rows}
    (out/'source.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(out/'SourceArms.fbx')
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption()
    task.options.ascii=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Arm mesh export failed '+variant)
    summary[variant]={n:{k:c[k] for k in ('asset','intervals','seconds')} for n,c in data['clips'].items()}
    u.log('ARM_OPENING_SOURCE '+variant)
(P/'source_manifest.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
u.log('ARM_OPENING_SOURCE_COMPLETE')
