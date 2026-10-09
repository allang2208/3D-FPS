"""Read saved Super90 binding and source clocks for grip-layer authoring."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];R='/Game/Weapons/Super90/Cransh20261006'
mesh=u.load_asset(R+'/SK_Super90_V7')
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read Super90 binding')
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
names=[str(b.name) for b in bones]
data={'mesh':mesh.get_path_name(),'parents':{n:str(component.get_parent_bone(n)) for n in names},'rest':{str(b.name):pack(b.world_transform) for b in bones},'clips':{}}
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh;options.should_retarget=False
for kind in ('idle','walk','run','fire','fire_last','equip','inspect','quick_melee','reload_one','reload_full','reload_empty','reload_continuous'):
    clip=u.load_asset(R+'/Animations/A_Super90_'+kind)
    if not clip:raise RuntimeError('Missing authoring input '+kind)
    duration=clip.get_play_length();steps=max(1,round(duration*60));rows=[]
    for i in range(steps+1):
        t=duration*i/steps;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
        rows.append({'time':t,'local':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    data['clips'][kind]={'asset':clip.get_path_name(),'duration':duration,'samples':rows}
    print('SUPER90_GRIP_AUTHORING_INPUT',kind,len(rows),flush=True)
(O/'native.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('SUPER90_GRIP_INPUTS_SAVED',flush=True)
