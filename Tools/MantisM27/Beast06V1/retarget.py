"""Native UE retarget inputs for the user-requested Beast06 action upgrade."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1')
ROOT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/MantisM27/Beast06V1'
RIG=DEST+'/Rig'; LIB=u.EditorAssetLibrary; TOOLS=u.AssetToolsHelpers.get_asset_tools()
source=u.load_asset('/Game/SciFi_Beast06/Mesh/SK_SciFi_Beast06_Skin1')
target=u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
assert source and target
chains={'Spine':(('spine_01','spine_03'),('spine_01','spine_05')),
        'Neck':(('neck_01','neck_01'),('neck_01','neck_02')),
        'Head':(('head','head'),('head','head'))}
for label,side in [('Left','l'),('Right','r')]:
    for part,start,end in [('Arm','upperarm','hand'),('Clavicle','clavicle','upperarm'),
                           ('Leg','thigh','foot'),('Toes','foot','ball')]:
        chains[part+label]=((start+'_'+side,end+'_'+side),)*2

def save(a):
    if not LIB.save_loaded_asset(a,False): raise RuntimeError('Save failed '+a.get_path_name())
def create(name,cls,factory):
    return u.load_asset(RIG+'/'+name) or TOOLS.create_asset(name,RIG,cls,factory)
def ik(name,mesh,which):
    rig=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(rig); ctl.set_skeletal_mesh(mesh); ctl.set_retarget_root('pelvis')
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,pair in chains.items():
        if chain not in existing: ctl.add_retarget_chain(chain,*pair[which],'')
    save(rig); return rig
src=ik('IK_Beast06_Source',source,0); dst=ik('IK_M27_Beast06_Target',target,1)
rtg=create('RTG_Beast06_M27',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
for side,rig,mesh in [(u.RetargetSourceOrTarget.SOURCE,src,source),(u.RetargetSourceOrTarget.TARGET,dst,target)]:
    ctl.set_ik_rig(side,rig); ctl.set_preview_mesh(side,mesh)
if ctl.get_num_retarget_ops()==0: ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
for i in range(ctl.get_num_retarget_ops()):
    op=ctl.get_op_controller(i)
    if isinstance(op,u.IKRetargetRootMotionController): ctl.set_retarget_op_enabled(i,False)
    if isinstance(op,u.IKRetargetFKChainsController):
        settings=op.get_settings(); rows=list(settings.chains_to_retarget)
        for row in rows:
            row.rotation_mode=u.FKChainRotationMode.INTERPOLATED if str(row.target_chain_name) in ['Spine','Neck'] else u.FKChainRotationMode.ONE_TO_ONE
        settings.chains_to_retarget=rows; op.set_settings(settings)
pose=ctl.create_retarget_pose('M27_Beast06_Anatomy',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET); save(rtg)
component=u.new_object(u.SkeletalMeshComponent); component.set_skeletal_mesh_asset(target)
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
opt=u.AnimPoseEvaluationOptions(); opt.evaluation_type=u.AnimDataEvalType.RAW; opt.optional_skeletal_mesh=target
opt.should_retarget=False; opt.extract_root_motion=False
def transform(t):
    p=t.translation; q=t.rotation
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z]}
record={'retargeter':rtg.get_path_name(),'target':target.get_path_name(),'fps':60,'clips':{}}
for role in ['Attack1','Attack6','GetHitF','GetHitB','GetHitL','GetHitR','Idle1','JumpStart','JumpLoop','JumpEnd']:
    clip=u.load_asset('/Game/SciFi_Beast06/Animations/Anim_SciFi_Beast06_'+role)
    if not clip: raise RuntimeError('Missing source '+role)
    params=u.IKRetargetBatchOperationInputs()
    params.assets_to_retarget=[LIB.find_asset_data(clip.get_path_name())]
    params.source_mesh=source; params.target_mesh=target; params.ik_retarget_asset=rtg
    params.search=clip.get_name(); params.replace='A_M27_Raw_'+role+'_Beast06V1'; params.target_path=DEST+'/Raw'
    params.include_referenced_assets=False; params.overwrite_existing_files=True
    results=u.IKRetargetBatchOperation.run_batch_retarget(params)
    result=next((r.get_asset() for r in results if isinstance(r.get_asset(),u.AnimSequence)),None)
    if not result: raise RuntimeError('Native retarget failed '+role)
    result.set_preview_skeletal_mesh(target); result.set_editor_property('enable_root_motion',False)
    result.set_editor_property('force_root_lock',False); save(result)
    length=result.get_play_length(); frames=[]
    for i in range(round(length*60)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(result,min(i/60,length),opt)
        frames.append({b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
    ref={b:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
    record['clips'][role]={'source':clip.get_path_name(),'raw_asset':result.get_path_name(),'seconds':length,'frames':frames,'reference':ref}
    (ROOT/'native_poses.json').write_text(json.dumps(record),encoding='utf-8')
    print('M27_BEAST06_RETARGET_SAVED '+role,flush=True)
print('M27_BEAST06_NATIVE_INPUTS_COMPLETE',flush=True)
