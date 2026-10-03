"""Add one planted, rear-up attack to the accepted V5 rig without replacing it."""
from pathlib import Path
import ast,json,math
import bpy
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'SurfaceRigV5'
OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Delivery/M10_SurfaceRigV5_Editable.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf8'))
rest={b.name:b.matrix_local.copy() for b in arm.bones}
# Reuse the accepted bent-knee solver and bind-oriented aiming exactly.
tree=ast.parse((BASE/'build_surface_rig.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('aim','solve')],type_ignores=[]),str(BASE/'build_surface_rig.py'),'exec'))

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def body_pose(name,shift,pitch=0,roll=0,yaw=0):
    pivot=rest[name].translation
    rotate=Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(pitch),4,'Y')@Matrix.Rotation(math.radians(roll),4,'X')
    return Matrix.Translation(Vector(shift)+pivot)@rotate@Matrix.Translation(-pivot)@rest[name]

def pose(t):
    targets={n:m.copy() for n,m in rest.items()}
    ready=smooth(t/.35)*(1-smooth((t-7.2)/.8))
    lift=smooth((t-.50)/.70)*(1-smooth((t-7.2)/.8))
    wind=math.sin(math.tau*t/.8)*math.sin(math.pi*min(1,t/.8)) if t<.8 else 0
    jet=smooth((t-1.2)/.10)*(1-smooth((t-7.1)/.1))
    pulse=math.sin((t-1.2)*math.tau*3.5)*jet
    targets['body_center']=body_pose('body_center',(.012*ready,.014*wind,-.020*ready),2*lift,1.0*wind)
    targets['body_front']=body_pose('body_front',(.025*ready,.008*wind,-.045*ready),2*lift,.6*wind)
    targets['body_rear']=body_pose('body_rear',(.018*ready,.025*wind,.07*lift+.003*pulse),5*lift,1.3*wind,1.8*wind)
    targets['rump']=body_pose('rump',(.020*lift,.038*wind,.12*lift+.007*pulse),13*lift+.6*pulse,1.8*wind,3.0*wind+.35*pulse)
    targets['head']=body_pose('head',(.035*ready,.008*wind,-.05*ready),-2*ready,.4*wind)
    for name in ('jaw','mouth_socket'):
        targets[name]=targets['head']@rest['head'].inverted()@rest[name]
    for spec in cfg['bones']:
        if spec['region']=='mantle':
            n,p=spec['name'],spec['parent'];targets[n]=targets[p]@rest[p].inverted()@rest[n]
    for leg in cfg['legs']:
        pts=[Vector(p) for p in leg['points']];parent=leg['parent'];upper,lower,foot=leg['bones']
        body=targets[parent]@rest[parent].inverted();root=body@pts[0];pole=body@pts[1]
        knee,end=solve(pts,root,pole,pts[2])
        targets[upper]=aim(upper,root,knee);targets[lower]=aim(lower,knee,end)
        targets[foot]=Matrix.Translation(end)@rest[foot].to_3x3().to_4x4()
        for sector in ('inner','outer'):
            n=leg['region']+'_toes_'+sector;targets[n]=targets[foot]@rest[foot].inverted()@rest[n]
        helper=leg['region']+'_socket';base=body@rest[helper]
        q=base.to_quaternion().slerp(targets[upper].to_quaternion(),.45)
        targets[helper]=Matrix.Translation(root)@q.to_matrix().to_4x4()
    return targets

action=bpy.data.actions.new('M10_RearGas_V7');action.use_fake_user=True;rig.animation_data.action=action
for frame in range(241):
    scene.frame_set(frame+1);targets=pose(frame/30.)
    for bone in arm.bones:
        n=bone.name
        local=rest[n].inverted()@rest[bone.parent.name]@targets[bone.parent.name].inverted()@targets[n] if bone.parent else rest[n].inverted()@targets[n]
        p=rig.pose.bones[n];p.rotation_mode='QUATERNION';p.matrix_basis=local
        for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=frame+1)
    if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
scene.frame_start=1;scene.frame_end=241;scene.frame_set(1)
fbx=OUT/'A_M10_RearGas_V7.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_RearGasV7_Editable.blend'))
(ROOT/'export_contract.json').write_text(json.dumps({'animation_file':str(fbx),'seconds':8,'fps':30,'frames':241,'windup':1.2,'emission':[1.2,7.2],'recovery':[7.2,8.0],'base_rig':'SurfaceRigV5','root_motion':False,'rear_pitch_degrees':13,'rump_lift_cm':12,'feet':'V5 bent-knee IK with planted contact and 45% socket tissue rotation','game_tested':False,'preview_rendered':False},indent=2),encoding='utf8')
print('M10_REAR_GAS_V7_SOURCE_SAVED',flush=True)
