"""Retarget complete source FK chains; no hand IK or synthetic elbow targets."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/GitHubSinglePistol20261022'
DEST='/Game/Characters/JasonPlayer20261003/GitHubSinglePistol20261022'
VARIANT=globals().get('RETARGET_VARIANT','')
d=json.loads((OUT/globals().get('RETARGET_INPUT','source-poses.json')).read_text(encoding='utf8'))
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
source=u.load_asset(d['source']['mesh']);target=u.load_asset(d['target']['mesh'])
def save(asset):
    if isinstance(asset,u.AnimSequence) and not u.WeaponAnimationAuthoring.finalize_authored_animation(asset):raise RuntimeError('Finalize '+asset.get_path_name())
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save '+asset.get_path_name())
def create(name,kind,factory):
    p=DEST+'/Rig/'+name
    return u.load_asset(p) if lib.does_asset_exist(p) else assets.create_asset(name,DEST+'/Rig',kind,factory)
rigs=[]
for donor,mesh in [(True,source),(False,target)]:
    rig=create(('IK_GitHubSource' if donor else 'IK_JasonTarget')+VARIANT,u.IKRigDefinition,u.IKRigDefinitionFactory())
    c=u.IKRigController.get_controller(rig);c.set_skeletal_mesh(mesh);c.set_retarget_root('Pelvis' if donor else 'pelvis')
    chains={'Spine':('Spine1','Spine3') if donor else ('spine_01','spine_05'),
        'Neck':('Neck_Base','Neck_Middle') if donor else ('neck_01','neck_02'),
        'Head':('Head','Head') if donor else ('head','head')}
    for side in ('r','l'):
        p=side.upper()+'_'
        for key,a,b,ta,tb in [('Clavicle','Clavicle','Clavicle','clavicle','clavicle'),('Arm','Arm','Hand','upperarm','hand'),
                ('Leg','Thigh','Ankle','thigh','foot'),('Toe','Toes','Toes','ball','ball')]:
            chains[key+'_'+side]=(p+a,p+b) if donor else (ta+'_'+side,tb+'_'+side)
        for finger in ('thumb','index','middle','ring','pinky'):
            chains[finger+'_'+side]=(p+finger.title()+'1',p+finger.title()+'3') if donor else (finger+'_01_'+side,finger+'_03_'+side)
    names={str(x.chain_name) for x in c.get_retarget_chains()}
    for name,(a,b) in chains.items():
        if name not in names:c.add_retarget_chain(name,a,b,'')
    save(rig);rigs.append(rig)
rtg=create('RTG_GitHubSingle_Jason'+VARIANT,u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,rigs[0]);c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,rigs[1])
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if c.get_num_retarget_ops()==0:c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('SourceAligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET);c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
ops=[]
for i in range(c.get_num_retarget_ops()):
    controller=c.get_op_controller(i);name=controller.get_class().get_name()
    enabled='PelvisMotion' in name or 'FKChains' in name or 'RootMotion' in name
    c.set_retarget_op_enabled(i,enabled)
    if isinstance(controller,u.IKRetargetFKChainsController):
        settings=controller.get_settings();chains=list(settings.chains_to_retarget)
        for chain in chains:
            chain.rotation_mode=u.FKChainRotationMode.INTERPOLATED if str(chain.target_chain_name)=='Spine' else u.FKChainRotationMode.ONE_TO_ONE
            chain.translation_mode=u.FKChainTranslationMode.NONE
        settings.chains_to_retarget=chains;controller.set_settings(settings)
    ops.append(dict(name=name,enabled=enabled))
save(rtg)
p=u.IKRetargetBatchOperationInputs()
PREFIX='J_GitHub_'+VARIANT
pending=[name for name in d['clips'] if not lib.does_asset_exist(DEST+'/Retargeted/'+PREFIX+'A_'+name)]
p.assets_to_retarget=[lib.find_asset_data(d['clips'][name]['asset']) for name in pending]
p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg;p.prefix=PREFIX
p.target_path=DEST+'/Retargeted';p.include_referenced_assets=False;p.overwrite_existing_files=False
if pending:u.IKRetargetBatchOperation.run_batch_retarget(p)
result=dict(source=d['source']['mesh'],target=d['target'],retargeter=rtg.get_path_name(),ops=ops,clips={})
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=target;opt.evaluation_type=u.AnimDataEvalType.SOURCE
def pack(t):
    v,q,s=t.translation,t.rotation,t.scale3d
    return [v.x,v.y,v.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for name in d['clips']:
    clip=u.load_asset(DEST+'/Retargeted/'+PREFIX+'A_'+name)
    if not isinstance(clip,u.AnimSequence):raise RuntimeError('Missing '+name)
    clip.set_preview_skeletal_mesh(target);clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(clip,'SourceRepository','https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets')
    lib.set_metadata_tag(clip,'SourceRevision','f19adc2ece4cab0f89c9236223abb97d4d2badea')
    lib.set_metadata_tag(clip,'NativeSinglePistol','Complete FK arm; no hand IK')
    save(clip);duration=clip.get_play_length();frames=[]
    for i in range(round(duration*30)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30,duration),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.LOCAL)) for b in d['target']['names']])
    result['clips'][name]=dict(asset=clip.get_path_name(),duration=duration,rate=30,frames=frames)
    (OUT/(VARIANT+'retargeted-poses.json')).write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
    print('GITHUB_PISTOL_RETARGET_SAVED',name,duration,flush=True)
(OUT/(VARIANT+'retarget-receipt.json')).write_text(json.dumps(dict(retargeter=result['retargeter'],target=d['target']['mesh'],
    clips={k:v['asset'] for k,v in result['clips'].items()},ops=ops,assets_saved=True,runtime_tested=False),indent=2),encoding='utf8')
