"""Native UE retarget of Mutant3's existing full-body claw motion to M27."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV3')
DEST='/Game/Monsters/MantisM27/ClawV3'
RIG=DEST+'/Rig';RAW=DEST+'/Raw'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
source=u.load_asset('/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw')
target=u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
chains={'Spine':(('Spine02','Spine'),('spine_01','spine_05')),
        'Neck':(('neck','neck'),('neck_01','neck_02')),
        'Head':(('Head','Head'),('head','head'))}
for label,src,side in [('Left','Left','l'),('Right','Right','r')]:
    chains['Arm'+label]=((src+'Arm',src+'Hand'),('upperarm_'+side,'hand_'+side))
    chains['Clavicle'+label]=((src+'Shoulder',src+'Arm'),('clavicle_'+side,'upperarm_'+side))
    chains['Leg'+label]=((src+'UpLeg',src+'Foot'),('thigh_'+side,'foot_'+side))
    chains['Toes'+label]=((src+'Foot',src+'ToeBase'),('foot_'+side,'ball_'+side))

def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
def create(name,cls,factory):return u.load_asset(RIG+'/'+name) or TOOLS.create_asset(name,RIG,cls,factory)
def ik(name,mesh,which,root):
    rig=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(rig);ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root(root)
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,pair in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,*pair[which],'')
    save(rig);return rig
src=ik('IK_Mutant3_ClawSource',source,0,'Hips')
dst=ik('IK_M27_ClawTarget',target,1,'pelvis')
rtg=create('RTG_Mutant3_M27_ClawV3',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
for i in range(ctl.get_num_retarget_ops()):
    op=ctl.get_op_controller(i)
    if isinstance(op,u.IKRetargetRootMotionController):ctl.set_retarget_op_enabled(i,False)
    if isinstance(op,u.IKRetargetFKChainsController):
        settings=op.get_settings();rows=list(settings.chains_to_retarget)
        for row in rows:
            row.rotation_mode=u.FKChainRotationMode.INTERPOLATED if str(row.target_chain_name) in ['Spine','Neck'] else u.FKChainRotationMode.ONE_TO_ONE
        settings.chains_to_retarget=rows;op.set_settings(settings)
pose_name=ctl.create_retarget_pose('M27_ClawAnatomyAligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose_name,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(target)
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.RAW;opt.optional_skeletal_mesh=target
opt.set_editor_property('should_retarget',False);opt.set_editor_property('extract_root_motion',False)
def transform(t):
    p=t.translation;q=t.rotation
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z]}
record={'retargeter':rtg.get_path_name(),'target':target.get_path_name(),'fps':60,'clips':{}}
for role in ['ClawA','ClawB','ClawC','FeralIdle']:
    clip=u.load_asset('/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_'+role)
    params=u.IKRetargetBatchOperationInputs()
    params.assets_to_retarget=[LIB.find_asset_data(clip.get_path_name())]
    params.source_mesh=source;params.target_mesh=target;params.ik_retarget_asset=rtg
    params.search=clip.get_name();params.replace='A_M27_Raw_'+role;params.target_path=RAW
    params.include_referenced_assets=False;params.overwrite_existing_files=True
    results=u.IKRetargetBatchOperation.run_batch_retarget(params)
    result=next((r.get_asset() for r in results if isinstance(r.get_asset(),u.AnimSequence)),None)
    if not result:raise RuntimeError('Native retarget did not produce '+role)
    result.set_preview_skeletal_mesh(target);result.set_editor_property('enable_root_motion',False)
    result.set_editor_property('force_root_lock',False);save(result)
    length=result.get_play_length();frames=[]
    times=[0.] if role=='FeralIdle' else [min(i/60,length) for i in range(round(length*60)+1)]
    for t in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(result,t,opt)
        frames.append({b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
    ref={b:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
    record['clips'][role]={'source':clip.get_path_name(),'raw_asset':result.get_path_name(),'seconds':length,'frames':frames,'reference':ref}
    print('M27_NATIVE_CLAW_AUTHORED '+role,flush=True)
(ROOT/'native_claw_poses.json').write_text(json.dumps(record),encoding='utf-8')
print('M27_NATIVE_CLAW_INPUTS_SAVED',flush=True)
