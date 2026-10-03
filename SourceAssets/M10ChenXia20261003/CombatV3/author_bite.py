"""Author a visible preload, mouth opening, snap lunge and recovery on the existing rig."""
from pathlib import Path
import ast,json,math
import bpy
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1';OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'TurningV2/Delivery/M10_TurningV2_Editable.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf-8'));rest={b.name:b.matrix_local.copy() for b in arm.bones}
tree=ast.parse((BASE/'build_rig.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(BASE/'build_rig.py'),'exec'))
DURATION=1.6;CONTACT=.70
def bite(t):
    out={n:m.copy() for n,m in rest.items()}
    preload=smooth(t/.27)*(1-smooth((t-.30)/.22))
    s=max(0,min(1,(t-.50)/.20));thrust=(1-(1-s)**3)*(1-smooth((t-.84)/.61))
    opening=smooth((t-.25)/.29)*(1-smooth((t-.55)/.15))
    clamp=smooth((t-.57)/.13)*(1-smooth((t-.82)/.34))
    profiles={'body_center':(.13,.055,.025),'body_front':(.24,.075,.035),'body_rear':(.075,.04,.015),'rump':(.035,.025,.01),'head':(.39,.045,.08)}
    for n,(forward,down,up) in profiles.items():
        shift=Vector((forward*thrust-.085*preload,0,-down*preload+up*thrust+.06*opening*(n=='head')))
        out[n]=Matrix.Translation(shift)@rest[n]
        if n=='head':
            p=out[n].translation.copy();out[n]=Matrix.Translation(p)@Matrix.Rotation(math.radians(-7*opening-3*thrust),4,'Y')@Matrix.Translation(-p)@out[n]
    for spec in cfg['bones']:
        if spec['region']=='mantle':
            n=spec['name'];parent=spec['parent'];out[n]=out[parent]@rest[parent].inverted()@rest[n]
    jaw=out['head']@rest['head'].inverted()@rest['jaw']
    angle=math.radians(32*opening-10*clamp)
    out['jaw']=Matrix.Translation(jaw.translation)@Quaternion((0,1,0),angle).to_matrix().to_4x4()@jaw.to_3x3().to_4x4()
    out['mouth_socket']=out['head']@rest['head'].inverted()@rest['mouth_socket']
    steps={1:(.36,.70,.14),2:(.90,1.17,.065),3:(.73,1.00,.07),4:(.62,.90,.055)}
    for leg in cfg['legs']:
        root,knee,ankle,toe=[Vector(p) for p in leg['points']]
        root=out[leg['parent']]@rest[leg['parent']].inverted()@root
        a,b,height=steps[leg['pair']];q=max(0,min(1,(t-a)/(b-a)))
        target=ankle.copy()
        if a<t<b:
            target.z+=height*math.sin(math.pi*q)**2
            target.x+=(.08 if leg['pair']==1 else -.055)*math.sin(math.pi*q)
        joint,end=ik(root,knee,ankle,target)
        upper,lower,foot=leg['bones'];out[upper]=aim(upper,root,joint);out[lower]=aim(lower,joint,end);out[foot]=aim(foot,end,toe+(end-ankle))
        for sector in ('inner','outer'):
            n=leg['region']+'_toes_'+sector;out[n]=out[foot]@rest[foot].inverted()@rest[n]
    return out
action=bpy.data.actions.new('M10_BiteSnap_V3');action.use_fake_user=True;rig.animation_data.action=action
for f in range(49):
    scene.frame_set(f+1);targets=bite(f/30.)
    for b in arm.bones:
        local=rest[b.name].inverted()@rest[b.parent.name]@targets[b.parent.name].inverted()@targets[b.name] if b.parent else rest[b.name].inverted()@targets[b.name]
        p=rig.pose.bones[b.name];p.rotation_mode='QUATERNION';p.matrix_basis=local
        for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=f+1)
    if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
scene.frame_start=1;scene.frame_end=49;scene.frame_set(1)
file=OUT/'A_M10_BiteSnap_V3.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_CombatV3_Editable.blend'))
(ROOT/'bite_contract.json').write_text(json.dumps({'file':str(file),'seconds':DURATION,'contact_seconds':CONTACT,'contact_frame_zero_based':21,'preload':[0,.30],'open':[.25,.55],'snap':[.52,.70],'recovery':[.84,1.45],'actor_lunge_cm':35,'head_pose_thrust_cm':39,'max_jaw_open_degrees':32,'loops':False,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('M10_BITE_SOURCE_SAVED',flush=True)
