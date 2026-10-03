"""Add turning clips to the accepted rig. No mesh/weight edits or preview renders."""
from pathlib import Path
import ast,json,math
import bpy
from mathutils import Vector,Matrix,Quaternion

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1';OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Delivery/M10_Rigged_Editable.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf-8'))
rest={b.name:b.matrix_local.copy() for b in arm.bones}
# Reuse the accepted straight-walk authoring functions without rerunning skinning.
tree=ast.parse((BASE/'build_rig.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(BASE/'build_rig.py'),'exec'))
DURATION=1.2;STANCE=.75;SPEED=.46153846;OMEGA=math.radians(10.)
def flow(point,seconds,speed,omega):
    travel=Vector((speed/omega*math.sin(omega*seconds),speed/omega*(1-math.cos(omega*seconds)),0))
    return Matrix.Rotation(-omega*seconds,3,'Z')@(point-travel)

def turning_pose(role,t):
    # FBX handedness maps Blender positive Z rotation to UE negative yaw.
    sign=1 if role.endswith('Left') else -1
    speed=0 if role.startswith('Pivot') else SPEED
    omega=sign*OMEGA
    out=poses('Walk' if speed else 'Idle',t,DURATION)
    old={n:m.copy() for n,m in out.items()}
    bend={'body_center':1.,'body_front':3.,'head':3.,'body_rear':-2.,'rump':-1.}
    for name in bend:
        parent=arm.bones[name].parent.name
        out[name]=out[parent]@old[parent].inverted()@old[name]
        p=out[name].translation.copy()
        out[name]=Matrix.Translation(p)@Matrix.Rotation(math.radians(bend[name]*sign),4,'Z')@Matrix.Translation(-p)@out[name]
    for spec in cfg['bones']:
        if spec['region']=='mantle' or spec['name'] in ('jaw','mouth_socket'):
            n=spec['name'];p=spec['parent'];out[n]=out[p]@old[p].inverted()@old[n]
    for leg in cfg['legs']:
        root,knee,ankle,toe=[Vector(p) for p in leg['points']]
        root=out[leg['parent']]@rest[leg['parent']].inverted()@root
        offset=[0.,.5,.25,.75][leg['pair']-1]+(.5 if leg['side']=='R' else 0)
        ph=(t/DURATION+offset)%1.;half=STANCE*DURATION*.5
        if ph<STANCE:
            target=flow(ankle,(ph/STANCE-.5)*STANCE*DURATION,speed,omega)
            yaw=-omega*(ph/STANCE-.5)*STANCE*DURATION
        else:
            q=(ph-STANCE)/(1-STANCE);a=smooth(q)
            target=flow(ankle,half,speed,omega).lerp(flow(ankle,-half,speed,omega),a)
            target.z+=.09*math.sin(math.pi*q)**2
            yaw=(-half+2*half*a)*omega
        joint,end=ik(root,knee,ankle,target)
        upper,lower,foot=leg['bones'];out[upper]=aim(upper,root,joint);out[lower]=aim(lower,joint,end)
        toe_direction=Matrix.Rotation(yaw,3,'Z')@(toe-ankle)
        out[foot]=aim(foot,end,end+toe_direction)
        for sector in ('inner','outer'):
            n=leg['region']+'_toes_'+sector;out[n]=out[foot]@rest[foot].inverted()@rest[n]
    return out

clips={}
for role in ('CurveLeft','CurveRight','PivotLeft','PivotRight'):
    action=bpy.data.actions.new('M10_'+role+'_V2');action.use_fake_user=True;rig.animation_data.action=action
    for f in range(37):
        scene.frame_set(f+1);targets=turning_pose(role,f/30.)
        for b in arm.bones:
            local=rest[b.name].inverted()@rest[b.parent.name]@targets[b.parent.name].inverted()@targets[b.name] if b.parent else rest[b.name].inverted()@targets[b.name]
            p=rig.pose.bones[b.name];p.rotation_mode='QUATERNION';p.matrix_basis=local
            for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=f+1)
        if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
    clips[role]={'file':str(OUT/f'A_M10_{role}_V2.fbx'),'action':action.name,'seconds':DURATION,'stance_fraction':STANCE,'angular_speed_deg_s':10.,'forward_speed_cm_s':0 if role.startswith('Pivot') else SPEED*100}
    print('M10_TURN_AUTHORED',role,flush=True)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for role,row in clips.items():
    action=bpy.data.actions[row['action']];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_start=1;scene.frame_end=37;scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=row['file'],use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
rig.animation_data.action=bpy.data.actions['M10_Idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_end=97;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_TurningV2_Editable.blend'))
(ROOT/'turn_contract.json').write_text(json.dumps({'clips':clips,'cycle_seconds':DURATION,'straight_stance_fraction':.65,'turn_stance_fraction':STANCE,'rig_and_weights':'unchanged RigV1','runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('M10_TURN_SOURCE_SAVED',flush=True)
