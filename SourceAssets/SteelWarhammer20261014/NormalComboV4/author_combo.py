"""Restore the complete pre-V2 joint poses; retime and carry the entire rig together.

No arm IK, wrist offsets, new elbow poles or twist redistribution. Source poses
are the old RhythmClearanceV2 family, before the rejected V2/V3 remodels.
"""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'RhythmClearanceV2/Warhammer_Clearance_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)
    and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<existing_baker>','exec'))

FPS=300;SOURCE_FPS=150;LOAD=.85;CONTACT=.97;DURATION=1.75;HIT_STOP=.07;RECOVERY=.80
actions=[bpy.data.actions['A_Warhammer_Clearance_'+n] for n in ('Slash1','Slash2','Swing')]
rig.animation_data.action=actions[0];rig.animation_data.action_slot=actions[0].slots[0]
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
pivot=(idle['clavicle_l'].translation+idle['clavicle_r'].translation)*.5

def curve(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    for i in range(1,len(keys)):
        a,b=keys[i-1],keys[i]
        if t<=b[0]:
            span=b[0]-a[0];u=(t-a[0])/span
            return (2*u**3-3*u*u+1)*a[1]+(u**3-2*u*u+u)*span*a[2]+(-2*u**3+3*u*u)*b[1]+(u**3-u*u)*span*b[2]
    return keys[-1][1]

# Keep the old long load and the present gameplay contact. Monotonic follow-
# through replaces the old source clock's extra brake hold; no mining pry layer.
SWING=[(0,0,0),(.15,.009,.10),(.38,.058,.24),(.62,.128,.27),(.76,.173,.22),
    (LOAD,.188,0),(CONTACT,.24,.78),(1.10,.307,.40),(1.30,.43,.60),(DURATION,.68,0)]
RETURN=[(0,.24,0),(HIT_STOP,.24,0),(.20,.307,.60),(.38,.43,.60),(RECOVERY,.68,0)]

def sample(action,seconds):
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    f=max(0,min(.68,seconds))*SOURCE_FPS;frame=int(f)
    scene.frame_set(frame,subframe=f-frame)
    return {b.name:b.matrix.copy() for b in rig.pose.bones}

def body_carry(pose,stage,t,hit=False):
    if hit:
        load=0.;follow=1-ease((t-HIT_STOP)/(RECOVERY-HIT_STOP))
    else:
        cut=ease((t-LOAD)/(CONTACT-LOAD))
        load=ease(t/LOAD)*(1-cut)
        follow=cut*(1-ease((t-1.10)/(DURATION-1.10)))
    side=1 if stage==0 else -1 if stage==1 else 0
    # A small chest-driven sweep: every shoulder, elbow, wrist, twist, finger
    # and weapon receives the SAME rigid transform. Local joint poses survive
    # exactly, and both original hand-to-handle contacts stay unchanged.
    yaw=math.radians(side*4*(follow-load))
    roll=math.radians(side*2*(follow-load))
    pitch=math.radians((2 if stage<2 else 3)*(load-follow))
    q=Quaternion((0,0,1),yaw)@Quaternion((0,1,0),roll)@Quaternion((1,0,0),pitch)
    shift=Vector((0,-.01*(load+follow),0))
    delta=Matrix.Translation(pivot+shift)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    return {n:delta@m for n,m in pose.items()}

sequences={}
for stage,action in enumerate(actions):
    swing=[body_carry(sample(action,curve(SWING,i/FPS)),stage,i/FPS)
        for i in range(round(DURATION*FPS)+1)]
    recovery=[body_carry(sample(action,curve(RETURN,i/FPS)),stage,i/FPS,True)
        for i in range(round(RECOVERY*FPS)+1)]
    # All cuts return to the original common ready pose. Buffered input starts
    # the next original cut from it; do not splice V3's opposed arm solutions.
    swing[0]=copy.deepcopy(idle);swing[-1]=copy.deepcopy(idle);recovery[-1]=copy.deepcopy(idle)
    recovery[0]=copy.deepcopy(swing[round(CONTACT*FPS)])
    sequences[f'A_Warhammer_Slash{stage+1}']=swing
    sequences[f'A_Warhammer_Slash{stage+1}Recover']=recovery

for name,poses in sequences.items():bake(name,poses,FPS)
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1']
rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Combo_Restored_Editable.blend'))
receipt={'clips':list(sequences),'fps':FPS,'source':str(SOURCE),'source_fps':SOURCE_FPS,
    'source_actions':[a.name for a in actions],'load_seconds':LOAD,'contact_seconds':CONTACT,
    'swing_seconds':DURATION,'hit_stop_seconds':HIT_STOP,'hit_recovery_seconds':RECOVERY,
    'joint_policy':'Original complete joint poses; common rigid carry only, no IK or wrist/twist edits',
    'carry_yaw_degrees':4,'carry_roll_degrees':2,'carry_pitch_degrees':[2,2,3],
    'return_policy':'Original swing follow-through, no mining hold/tug clip; common idle endpoint',
    'source_time_keys':{'swing':SWING,'recovery':RETURN},'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_COMBO_RESTORED '+json.dumps(receipt))
