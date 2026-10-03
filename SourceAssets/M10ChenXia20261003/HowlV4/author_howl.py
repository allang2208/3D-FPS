"""Brace all eight limbs and sustain a wide-mouth vocal pose on the existing skin."""
from pathlib import Path
import ast,json,math
import bpy
from mathutils import Vector,Matrix,Quaternion

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1';OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'CombatV3/Delivery/M10_CombatV3_Editable.blend'))
scene=bpy.context.scene;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');arm=rig.data
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf-8'));rest={b.name:b.matrix_local.copy() for b in arm.bones}
tree=ast.parse((BASE/'build_rig.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(BASE/'build_rig.py'),'exec'))

def howl(t):
    out={n:m.copy() for n,m in rest.items()}
    brace=smooth(t/.36)*(1-smooth((t-3.7)/.5))
    open_weight=smooth((t-.20)/.40)*(1-smooth((t-3.6)/.48))
    voice=smooth((t-.55)/.05)*(1-smooth((t-3.55)/.05))
    pulse=math.sin((t-.6)*math.tau*6)*voice
    inhale=math.sin(math.pi*max(0,min(1,t/.6))) if t<.6 else 0
    for n in ('body_center','body_front','body_rear','rump','head'):
        if n=='head':shift=Vector((.10*open_weight-.035*inhale,0,.16*open_weight+.008*pulse))
        elif n=='body_front':shift=Vector((-.025*brace-.004*pulse,0,.065*open_weight+.015*inhale))
        elif n=='body_center':shift=Vector((-.045*brace,0,-.025*brace+.01*inhale))
        else:shift=Vector((-.025*brace,0,-.025*brace))
        out[n]=Matrix.Translation(shift)@rest[n]
        if n=='head':
            pivot=out[n].translation.copy()
            out[n]=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-9*open_weight-.5*pulse),4,'Y')@Matrix.Translation(-pivot)@out[n]
    for spec in cfg['bones']:
        if spec['region']=='mantle':
            n=spec['name'];p=spec['parent'];out[n]=out[p]@rest[p].inverted()@rest[n]
    jaw=out['head']@rest['head'].inverted()@rest['jaw']
    out['jaw']=Matrix.Translation(jaw.translation)@Quaternion((0,1,0),math.radians(43*open_weight+1.2*pulse)).to_matrix().to_4x4()@jaw.to_3x3().to_4x4()
    out['mouth_socket']=out['head']@rest['head'].inverted()@rest['mouth_socket']
    for leg in cfg['legs']:
        root,knee,ankle,toe=[Vector(p) for p in leg['points']]
        root=out[leg['parent']]@rest[leg['parent']].inverted()@root
        # Hold the original contact points while the chest rises and rear braces.
        joint,end=ik(root,knee,ankle,ankle)
        upper,lower,foot=leg['bones'];out[upper]=aim(upper,root,joint);out[lower]=aim(lower,joint,end);out[foot]=aim(foot,end,toe+(end-ankle))
        for sector in ('inner','outer'):
            n=leg['region']+'_toes_'+sector;out[n]=out[foot]@rest[foot].inverted()@rest[n]
    return out

action=bpy.data.actions.new('M10_Howl_V4');action.use_fake_user=True;rig.animation_data.action=action
for f in range(127):
    scene.frame_set(f+1);targets=howl(f/30.)
    for b in arm.bones:
        local=rest[b.name].inverted()@rest[b.parent.name]@targets[b.parent.name].inverted()@targets[b.name] if b.parent else rest[b.name].inverted()@targets[b.name]
        p=rig.pose.bones[b.name];p.rotation_mode='QUATERNION';p.matrix_basis=local
        for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=f+1)
    if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
scene.frame_start=1;scene.frame_end=127;scene.frame_set(1)
file=OUT/'A_M10_Howl_V4.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,path_mode='AUTO',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_HowlV4_Editable.blend'))

# One-metre-radius curved sound ribbon, UV masked to the gameplay half-angle.
# Static VFX only; it never replaces or modifies the character mesh.
verts=[];uvs=[];faces=[];nx=64;nz=8
for j in range(nz+1):
    v=j/nz
    for i in range(nx+1):
        u=i/nx;a=(u-.5)*math.pi
        verts.append((math.cos(a),math.sin(a),(v-.5)*.4));uvs.append((u,v))
for j in range(nz):
    for i in range(nx):
        a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
data=bpy.data.meshes.new('M10_HowlWave_Ribbon');data.from_pydata(verts,[],faces);data.update()
wave=bpy.data.objects.new('SM_M10_HowlWave',data);scene.collection.objects.link(wave)
uv=data.uv_layers.new(name='UVMap')
for face in data.polygons:
    face.use_smooth=True
    for loop in face.loop_indices:uv.data[loop].uv=uvs[data.loops[loop].vertex_index]
bpy.ops.object.select_all(action='DESELECT');wave.select_set(True);bpy.context.view_layer.objects.active=wave
wave_file=OUT/'SM_M10_HowlWave.fbx'
bpy.ops.export_scene.fbx(filepath=str(wave_file),use_selection=True,bake_anim=False,object_types={'MESH'},axis_forward='-Y',axis_up='Z')
# Keep the VFX source alongside the rig, but hide it in the authoring viewport.
wave.hide_set(True);wave.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M10_HowlV4_Editable.blend'))
(ROOT/'howl_contract.json').write_text(json.dumps({'animation_file':str(file),'wave_file':str(wave_file),'seconds':4.2,'windup':.6,'channel':[.6,3.6],'recovery':[3.6,4.2],'damage_samples':[.6,1.1,1.6,2.1,2.6,3.1],'damage_per_tick':27.5,'damage_type':'ranged_magic','range_cm':1000,'angle_degrees':120,'cooldown_seconds':30,'sanity_loss_per_hit':5,'cripple_seconds':5,'cripple_movement_multiplier':.5,'jaw_open_degrees':43,'root_motion':False,'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('M10_HOWL_SOURCE_SAVED',flush=True)
