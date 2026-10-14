"""Retarget the locally licensed Mesh2Motion Dizzy take onto Jason, offline."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/PlayerStun20261006'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Characters/JasonPlayer20261003/Stun20261006'
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source=u.load_asset('/Game/Monsters/FatZombieMeshy/Sources/SK_M2M_Source')
target=u.load_asset(cfg['body_mesh'])
clip=u.load_asset('/Game/Monsters/HumanoidStun/Sources/A_M2M_Dizzy')
source_rig=u.load_asset('/Game/Monsters/HumanoidKnockdown/Rig/IK_M2M')
def save(a):
    if not lib.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def create(name,cls,factory):
    path=DEST+'/Rig/'+name
    return u.load_asset(path) or assets.create_asset(name,DEST+'/Rig',cls,factory)
chains={'Spine':('spine_01','spine_05'),'Neck':('neck_01','neck_02'),'Head':('head','head')}
for side,suffix in [('Left','l'),('Right','r')]:
    for name,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
        chains[name+side]=(start+'_'+suffix,end+'_'+suffix)
target_rig=create('IK_Jason_Stun',u.IKRigDefinition,u.IKRigDefinitionFactory())
ctl=u.IKRigController.get_controller(target_rig);ctl.set_skeletal_mesh(target);ctl.set_retarget_root('pelvis')
existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
for name,(start,end) in chains.items():
    if name not in existing:ctl.add_retarget_chain(name,start,end,'')
save(target_rig)
rtg=create('RTG_M2M_Jason_Stun',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,source_rig)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,target_rig)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('Jason_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
args=u.IKRetargetBatchOperationInputs();args.assets_to_retarget=[lib.find_asset_data(clip.get_path_name())]
args.source_mesh=source;args.target_mesh=target;args.ik_retarget_asset=rtg
args.prefix='J_';args.target_path=DEST+'/Donor';args.include_referenced_assets=False;args.overwrite_existing_files=False
donor=next(a.get_asset() for a in u.IKRetargetBatchOperation.run_batch_retarget(args) if isinstance(a.get_asset(),u.AnimSequence))
save(donor)
def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
ref=target.skeleton.get_reference_pose()
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(target)
parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=target;options.evaluation_type=u.AnimDataEvalType.SOURCE
def sample(anim,t):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,options)
    return [pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
length=donor.get_play_length()
data=dict(mesh=target.get_path_name(),skeleton=target.skeleton.get_path_name(),names=names,parents=parents,
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
    idle=sample(u.load_asset(cfg['clips']['Unarmed.Idle']),0),
    frames=[sample(donor,min(i/30,length)) for i in range(round(length*30)+1)],rate=30,
    source=clip.get_path_name(),donor=donor.get_path_name(),duration=length)
(OUT/'retargeted.json').write_text(json.dumps(data,separators=(',',':')))
print('STUN_DONOR_SAVED '+donor.get_path_name())
