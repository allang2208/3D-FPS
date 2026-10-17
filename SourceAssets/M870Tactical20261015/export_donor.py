"""Export the installed donor bind, skin, and source animation keys for production."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent; D=O/'Donor'; D.mkdir(exist_ok=True)
root='/Game/Weapons/Super90/Cransh20261006'
mesh=u.load_asset(root+'/SK_Super90_V7')
if not mesh: raise RuntimeError('Installed shotgun donor is missing')
task=u.AssetExportTask();task.object=mesh;task.filename=str(D/'installed_super90.fbx');task.automated=True;task.prompt=False;task.replace_identical=True
task.exporter=u.SkeletalMeshExporterFBX();options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.export_morph_targets=False;task.options=options
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export installed donor mesh')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents={n:str(component.get_parent_bone(n)) for n in names}
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.should_retarget=False;options.evaluation_type=u.AnimDataEvalType.SOURCE
data=dict(names=names,parents=parents,mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),materials=[dict(slot=str(x.material_slot_name),asset=x.material_interface.get_path_name() if x.material_interface else '') for x in mesh.materials],clips={})
for role in ('idle','walk','run','fire','reload_continuous','reload_full','equip','inspect','quick_melee'):
    clip=u.load_asset(root+'/Animations/A_Super90_'+role)
    if not clip:raise RuntimeError('Missing donor '+role)
    duration=clip.get_play_length();frames=max(1,round(duration*60));times=[i*duration/frames for i in range(frames+1)];rows=[]
    for time in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,options);row={}
        for n in names:
            t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)
            row[n]=[*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
        rows.append(row)
    data['clips'][role]=dict(path=clip.get_path_name(),duration=duration,times=times,rows=rows)
    print('M870_DONOR',role,duration)
(D/'animation_inputs.json').write_text(json.dumps(data,separators=(',',':')))
print('M870_DONOR_EXPORTED',str(D))
