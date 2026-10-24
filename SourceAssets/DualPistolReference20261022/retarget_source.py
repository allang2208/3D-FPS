"""Bake complete Twinblast FK chains onto Jason, retaining the original takes.

No hand targets, synthetic elbow poles, mirrored single-gun arms or runtime tests.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/DualPistolReference20261022'
DEST = '/Game/Characters/JasonPlayer20261003/TwinblastDual20261022'
d = json.loads((OUT/'source-poses.json').read_text(encoding='utf-8'))
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
source = u.load_asset(d['source']['mesh'])
target = u.load_asset(d['target']['mesh'])
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE is active; source authoring requires the existing editor outside play.')

def save(a):
    if isinstance(a,u.AnimSequence) and not u.WeaponAnimationAuthoring.finalize_authored_animation(a):
        raise RuntimeError('Finalize failed: '+a.get_path_name())
    if not lib.save_loaded_asset(a,False):
        raise RuntimeError('Save failed: '+a.get_path_name())

def create(name,cls,factory):
    path=DEST+'/Rig/'+name
    return u.load_asset(path) if lib.does_asset_exist(path) else assets.create_asset(name,DEST+'/Rig',cls,factory)

# Include the source's two upper-arm and two lower-arm twist stations explicitly.
# Unmapped Jason corrective branches keep their own local bind; no solver resets
# or rotates those helpers afterwards.
helpers = [n for n in d['source']['names'] if n in d['target']['names'] and
           n.startswith(('upperarm_twist_','lowerarm_twist_'))]
rigs=[]
for label,mesh,skeleton in [('Twinblast',source,d['source']),('Jason',target,d['target'])]:
    ik=create('IK_'+label+'_Dual',u.IKRigDefinition,u.IKRigDefinitionFactory())
    c=u.IKRigController.get_controller(ik)
    c.set_skeletal_mesh(mesh);c.set_retarget_root('pelvis')
    names=skeleton['names']
    spines=[n for n in names if n.startswith('spine_') and n[-2:].isdigit()]
    necks=[n for n in names if n.startswith('neck_') and n[-2:].isdigit()]
    chains={'Spine':(spines[0],spines[-1]),'Head':('head','head')}
    if necks:chains['Neck']=(necks[0],necks[-1])
    for side in ('r','l'):
        for key,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
            chains[key+'_'+side]=(start+'_'+side,end+'_'+side)
        for finger in ('thumb','index','middle','ring','pinky'):
            chains[finger+'_'+side]=(finger+'_01_'+side,finger+'_03_'+side)
    chains.update({n:(n,n) for n in helpers})
    existing={str(ch.chain_name) for ch in c.get_retarget_chains()}
    for name,(start,end) in chains.items():
        if name not in existing:c.add_retarget_chain(name,start,end,'')
    save(ik);rigs.append(ik)

rtg=create('RTG_Twinblast_Jason_Dual',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,rigs[0])
c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,rigs[1])
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if c.get_num_retarget_ops()==0:c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('Jason_Twinblast_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
ops=[]
for i in range(c.get_num_retarget_ops()):
    controller=c.get_op_controller(i)
    name=controller.get_class().get_name()
    # FK owns the complete source arm. No goal matching or post-retarget IK.
    enabled='PelvisMotion' in name or 'FKChains' in name or 'RootMotion' in name
    c.set_retarget_op_enabled(i,enabled)
    if isinstance(controller,u.IKRetargetFKChainsController):
        settings=controller.get_settings()
        chains=list(settings.chains_to_retarget)
        for chain in chains:
            chain.rotation_mode=u.FKChainRotationMode.INTERPOLATED if str(chain.target_chain_name) in ('Spine','Neck') else u.FKChainRotationMode.ONE_TO_ONE
            chain.translation_mode=u.FKChainTranslationMode.NONE
        settings.chains_to_retarget=chains
        controller.set_settings(settings)
    ops.append(dict(name=name,enabled=enabled))
save(rtg)
selected=['Idle','Walk_Fwd','Jog_Fwd','Sprint_Fwd','Primary_Fire_Med_A','Primary_Fire_Med_B',
          'DoubleShot_Fire_Rt','DoubleShot_Fire_Lft']
p=u.IKRetargetBatchOperationInputs()
pending=[n for n in selected if not lib.does_asset_exist(DEST+'/Retargeted/J_Twinblast_'+n)]
p.assets_to_retarget=[lib.find_asset_data(d['clips'][n]['asset']) for n in pending]
p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
p.prefix='J_Twinblast_';p.target_path=DEST+'/Retargeted';p.include_referenced_assets=False;p.overwrite_existing_files=False
if pending:u.IKRetargetBatchOperation.run_batch_retarget(p)

def pack(t):
    v,q,s=t.translation,t.rotation,t.scale3d
    return [v.x,v.y,v.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]

result=dict(rig=d['target'],clips={},ops=ops,source=d['source']['mesh'],retargeter=rtg.get_path_name())
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=target;opt.evaluation_type=u.AnimDataEvalType.SOURCE
for name in selected:
    clip=u.load_asset(DEST+'/Retargeted/J_Twinblast_'+name)
    if not isinstance(clip,u.AnimSequence):raise RuntimeError('Missing retarget '+name)
    clip.set_preview_skeletal_mesh(target)
    lib.set_metadata_tag(clip,'DualPistolSource',d['clips'][name]['asset'])
    lib.set_metadata_tag(clip,'AuthoringScript','SourceAssets/DualPistolReference20261022/retarget_source.py')
    # Runtime gait synchronization uses L/R, with the exact original contact times.
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    u.AnimationLibrary.add_animation_notify_track(clip,'TwinblastFootsteps')
    for marker in d['clips'][name]['markers']:
        if marker['name'] in ('LeftPlant','RightPlant'):
            u.AnimationLibrary.add_animation_sync_marker(clip,'L' if marker['name']=='LeftPlant' else 'R',marker['time'],'TwinblastFootsteps')
    save(clip)
    duration=clip.get_play_length();frames=[]
    for i in range(round(duration*30)+1):
        frame=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30,duration),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(frame,b,u.AnimPoseSpaces.LOCAL)) for b in d['target']['names']])
    result['clips'][name]=dict(asset=clip.get_path_name(),source=d['clips'][name]['asset'],rate=30,duration=duration,frames=frames)
    (OUT/'retargeted-poses.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print('TWINBLAST_RETARGET_SAVED',name,duration,flush=True)
(OUT/'retarget-receipt.json').write_text(json.dumps(dict(retargeter=result['retargeter'],ops=ops,clips={k:v['asset'] for k,v in result['clips'].items()},runtime_tested=False),indent=2),encoding='utf-8')
