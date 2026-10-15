"""Transfer accepted sword V5/V6 full FK poses to the identical native arm rig.

The shaft follows the two palm centres. No new elbow poles, wrist corrections,
twist redistribution, bone scaling, or baked camera revolutions are introduced.
"""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=1.82
SOURCE=ROOT/'SourceAssets/Whirlwind20260920/RecoverV6/WhirlwindRecover_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
source_rest={b.name:b.matrix_local.copy() for b in r.data.bones}
source_parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
source_local_rest={n:source_rest[p].inverted()@m if p else m for n,m in source_rest.items() for p in [source_parents[n]]}
frames=[]
for i in range(round(DURATION*FPS)+1):
    f=i/FPS*480;s.frame_set(int(f),subframe=f-int(f))
    frames.append({b.name:b.matrix.copy() for b in r.pose.bones})
source_idle=frames[0]
def palm_anchor(pose,side):
    h=pose['hand_'+side];w=pose['WPN_root'];z=(w.inverted()@h.translation).z
    return h.inverted()@(w@Vector((0,0,z)))
source_anchors={side:palm_anchor(source_idle,side) for side in ('l','r')}

bpy.ops.wm.open_mainfile(filepath=str(P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
anchors={side:palm_anchor(idle,side) for side in ('l','r')}
right_z=(idle['WPN_root'].inverted()@idle['hand_r'].translation).z
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)
    and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
poses=[]
for i,src in enumerate(frames):
    t=i/FPS;w=ease(t/.22)*(1-ease((t-1.54)/.28))
    local={}
    for name in rest:
        a=idle_local[name]
        if name not in src or name=='WPN_root':local[name]=a.copy();continue
        parent=source_parents[name]
        b=src[parent].inverted()@src[name] if parent else src[name]
        # Native rest frames match. Keep the rest-relative motion explicit for
        # non-arm helper bones as well, rather than copying absolute bind poses.
        b=local_rest[name]@source_local_rest[name].inverted()@b
        av,aq,ascale=a.decompose();bv,bq,bscale=b.decompose()
        v=av.lerp(bv,w)
        if name.startswith(('upperarm','lowerarm','hand_','thumb','index','middle','ring','pinky')) and v.length>1e-8:
            v=v.normalized()*(av.length*(1-w)+bv.length*w)
        local[name]=Matrix.LocRotScale(v,aq.slerp(bq,w),ascale)
    world={}
    def resolve(name):
        if name not in world:world[name]=(resolve(parents[name])@local[name]) if parents[name] else local[name]
        return world[name]
    for name in local:resolve(name)
    contact={side:world['hand_'+side]@anchors[side].lerp(source_anchors[side],w) for side in ('l','r')}
    axis=(contact['r']-contact['l']).normalized()
    q=idle['WPN_root'].to_quaternion().slerp(src['WPN_root'].to_quaternion(),w)
    q=(q@Vector((0,0,1))).rotation_difference(axis)@q
    weapon=Matrix.LocRotScale(contact['r']-q@Vector((0,0,right_z)),q,Vector((1,1,1)))
    old_weapon=world['WPN_root'];carry=weapon@old_weapon.inverted()
    for bone in rig.data.bones:
        if bone.name=='WPN_root' or any(p.name=='WPN_root' for p in bone.parent_recursive):world[bone.name]=carry@world[bone.name]
    poses.append(world)
poses[0]=copy.deepcopy(idle);poses[-1]=copy.deepcopy(idle)
name='A_Warhammer_Whirlwind';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Whirlwind_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'source':str(SOURCE),
    'authored_phases':[.5,.8,.52],'camera_turn_baked':False,'entry_adaptation_seconds':.22,
    'return_to_hammer_idle_seconds':.28,'grip':'Right hand keeps its shaft station; left slides to the sword compact spin grip',
    'arm_policy':'Whole accepted sword FK motion; no new arm IK or wrist/twist offsets',
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_WHIRLWIND_AUTHORED '+json.dumps(receipt))
