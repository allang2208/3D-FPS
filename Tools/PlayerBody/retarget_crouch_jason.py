"""Bake local GASP crouch donors to Jason; save only this task's new assets."""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonCrouch20261005'
DEST = '/Game/Characters/JasonPlayer20261003/CrouchGASP20261005'
donors=json.loads((OUT/'donors.json').read_text(encoding='utf-8'))
samples=json.loads((OUT/'source-poses.json').read_text(encoding='utf-8'))
cfg_path=ROOT/'Content/ColdSteelData/player_body.json'
cfg=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
source=u.load_asset('/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin')
target=u.load_asset(cfg['body_mesh'])
lib=u.EditorAssetLibrary
at=u.AssetToolsHelpers.get_asset_tools()
def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def create(name,cls,factory):
    path=DEST+'/Rig/'+name
    if lib.does_asset_exist(path):raise RuntimeError('Candidate already exists: '+path)
    return at.create_asset(name,DEST+'/Rig',cls,factory)
def make_ik(name,mesh):
    ik=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(ik)
    ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root('pelvis')
    names={str(n) for n in u.AnimPoseExtensions.get_bone_names(mesh.skeleton.get_reference_pose())}
    spines=sorted(n for n in names if n.startswith('spine_') and n[-2:].isdigit())
    necks=sorted(n for n in names if n.startswith('neck_') and n[-2:].isdigit())
    chains={'Spine':(spines[0],spines[-1]),'Neck':(necks[0],necks[-1]),'Head':('head','head')}
    for side in ('l','r'):
        for label,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
            chains[label+'_'+side]=(start+'_'+side,end+'_'+side)
        for digit in ('thumb','index','middle','ring','pinky'):
            chains[digit+'_'+side]=(digit+'_01_'+side,digit+'_03_'+side)
    for chain,(start,end) in chains.items():
        if start in names and end in names:ctl.add_retarget_chain(chain,start,end,'')
    save(ik);return ik
src=make_ik('IK_GASP_Crouch_Source',source)
dst=make_ik('IK_Jason_Crouch_Target',target)
rtg=create('RTG_GASP_Jason_Crouch',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('Jason_Crouch_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET);save(rtg)
inputs=u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget=[lib.find_asset_data(p) for p in donors['clips'].values()]
inputs.source_mesh=source;inputs.target_mesh=target;inputs.ik_retarget_asset=rtg
inputs.prefix='J_';inputs.target_path=DEST+'/Animations'
inputs.include_referenced_assets=False;inputs.overwrite_existing_files=False
outputs=u.IKRetargetBatchOperation.run_batch_retarget(inputs)
saved={};markers={}
for data in outputs:
    clip=data.get_asset()
    if not isinstance(clip,u.AnimSequence):continue
    name=clip.get_name().removeprefix('J_')
    clip.set_preview_skeletal_mesh(target)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ANIM_FIRST_FRAME)
    if 'Crouch_Loop_' in name:
        # Each donor contains four strides. Infer touchdown from the actual
        # world-space planted ankle, not equal seconds or the file name's foot.
        rows=samples['clips'][name]['samples'];dt=rows[1]['t']-rows[0]['t']
        events=[]
        for side in ('l','r'):
            points=[r['bones']['foot_'+side]['p'] for r in rows]
            speeds=[math.dist(a[:2],b[:2])/dt for a,b in zip(points,points[1:])]
            contacts=[rows[i]['t'] for i,v in enumerate(speeds) if v<70 and speeds[(i-1)%len(speeds)]>=70]
            if len(contacts)!=4:raise RuntimeError('Review contact extraction: '+name+' '+side)
            events.extend((t,side.upper()) for t in contacts)
        u.AnimationLibrary.remove_all_animation_sync_markers(clip)
        u.AnimationLibrary.add_animation_notify_track(clip,'CrouchContacts')
        for time,side in sorted(events):u.AnimationLibrary.add_animation_sync_marker(clip,side,time,'CrouchContacts')
        markers[name]=sorted(events)
    save(clip);saved[name]=clip.get_path_name()
if len(saved)!=len(donors['clips']):raise RuntimeError('Retarget did not finish all crouch donors')
mapping={'Crouch.Idle':saved['M_Neutral_Crouch_Idle_Loop']}
for direction,suffix in {'Fwd':'F','Fwd_Right':'FR','Right':'RR','Bwd_Right':'BR','Bwd':'B','Bwd_Left':'BL','Left':'LL','Fwd_Left':'FL'}.items():
    mapping['Crouch.Walk.'+direction]=saved['M_Neutral_Crouch_Loop_'+suffix]
# Keep unselected side variants and transitions as authored candidates, not
# active runtime entries. The existing movement controller keeps its timing.
(OUT/'assets-saved.json').write_text(json.dumps({'retargeter':rtg.get_path_name(),'assets':saved,'markers':markers,'runtime_clips':mapping},indent=2),encoding='utf-8')
print('CROUCH_ASSETS_SAVED '+json.dumps(mapping))
