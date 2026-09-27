"""Author the legacy sprite choreography on the custom Meshy hand rig. No rendering."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector, Quaternion, Matrix

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Animations';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LocalRig/FleshHand_Green_WithLODs.blend'))
scene=bpy.context.scene;scene.render.fps=60
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for o in scene.objects:o.hide_set(False)
axes={b.name:b.matrix_local.to_3x3().inverted() for b in rig.data.bones}
def rotate(name,axis,degrees):
    p=rig.pose.bones[name];p.rotation_mode='QUATERNION'
    # The generated palm faces +Y (nails/back face -Y). Reflect the old
    # -Y choreography's axial vectors across Y: (-x, y, -z). Keep the bind
    # and mesh unchanged so finger curl and slams bend toward the real palm.
    palm_axis=Vector((-axis[0],axis[1],-axis[2]))
    p.rotation_quaternion=Quaternion((axes[name]@palm_axis).normalized(),math.radians(degrees))
def reset():
    for p in rig.pose.bones:p.location=(0,0,0);p.rotation_mode='QUATERNION';p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
def fingers(curl,spread=0):
    for k,digit in enumerate(('index','middle','ring','little')):
        rotate(digit+'_metacarpal',(0,1,0),(k-1.5)*spread)
        for n,weight in enumerate((.82,1,.7),1):rotate(digit+'_%02d'%n,(1,0,0),curl*weight)
    rotate('thumb_01',(0,1,-.4),curl*.48-spread*.9)
    rotate('thumb_02',(1,-.8,0),curl*.6)
    rotate('thumb_03',(1,-.6,0),curl*.4)
def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:
            f=(t-a)/(b-a);f=f*f*(3-2*f);return x+(y-x)*f
    return keys[-1][1]
def ground():
    bpy.context.view_layer.update()
    evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    low=min((mesh.matrix_world@v.co).z for v in evaluated.data.vertices)
    # The root's local Y points up; local Z is horizontal. Convert the world
    # support correction through the object and bind-bone bases before baking.
    correction=rig.matrix_world.inverted().to_3x3()@Vector((0,0,-low))
    rig.pose.bones['root'].location+=axes['root']@correction
def export(path,animation=False):
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
        add_leaf_bones=False,use_armature_deform_only=False,use_mesh_modifiers=not animation,
        bake_anim=animation,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_step=1,bake_anim_simplify_factor=0,
        mesh_smooth_type='OFF',path_mode='AUTO')
clips={}
for role,duration in [('Idle',2),('Walk',16/14),('Hammer',1.5),('Slam',2),('GrandSlam',2),('Hit',.7),('Dizzy',2),('Death',1.8)]:
    reset();action=bpy.data.actions.new('A_FleshHand_'+role);rig.animation_data_create();rig.animation_data.action=action
    action.use_fake_user=True;frames=round(duration*60);scene.frame_start=0;scene.frame_end=frames
    for frame in range(frames+1):
        scene.frame_set(frame);reset();t=frame/frames*duration;phase=2*math.pi*t/duration
        if role=='Idle':
            rotate('wrist',(1,0,0),math.sin(phase)*1.6);fingers(2+math.sin(phase)*1.2,.5)
        elif role=='Walk':
            rotate('wrist',(1,0,0),3+3*math.sin(phase));rotate('palm',(0,1,0),2*math.sin(phase))
            rig.pose.bones['wrist'].scale=(1+.045*math.cos(phase*2),1+.05*math.cos(phase*2),1-.04*math.cos(phase*2))
            fingers(3+2*math.sin(phase+.6),.8)
        elif role=='Hammer':
            recoil=curve(t,[(0,0),(.09,-4),(.1875,8),(.36,3),(.92,2),(1.35,0),(1.5,0)])
            rotate('wrist',(1,0,0),-recoil);rotate('palm',(1,0,0),recoil*.4);fingers(2,.8)
        elif role in ('Slam','GrandSlam'):
            grand=role=='GrandSlam';hit=10/19 if grand else .25
            tilt=curve(t,[(0,0),(hit*.46,-18 if grand else -5),(hit,81 if grand else 66),(1.14 if grand else 1.15,81 if grand else 66),(1.68,8),(1.9,0),(2,0)])
            curl=curve(t,[(0,0),(hit*.5,9),(hit,22 if grand else 70),(1.13,22 if grand else 70),(1.74,4),(1.95,0),(2,0)])
            rotate('wrist',(1,0,0),tilt);rotate('palm',(1,0,0),curve(t,[(0,0),(hit,8),(1.15,8),(1.9,0),(2,0)]))
            fingers(curl,curve(t,[(0,1),(hit,6),(1.15,6),(1.85,1),(2,1)]) if grand else 1)
        elif role=='Hit':
            strength=curve(t,[(0,0),(.12,1),(.3,.6),(.48,.28),(.7,0)])
            rotate('wrist',(1,.25,0),-14*strength);fingers(10*strength,1)
        elif role=='Dizzy':
            rotate('wrist',(math.cos(phase),math.sin(phase),0),7)
            rotate('palm',(1,0,0),3*math.sin(phase+.8));fingers(8+5*math.sin(phase+1),2)
        else:
            fall=curve(t,[(0,0),(.2,.13),(.62,1),(.76,.93),(1.05,1),(1.8,1)])
            rotate('wrist',(.45,1,0),87*fall);rotate('palm',(1,0,0),16*fall);fingers(49*fall,1)
        ground()
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name);p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('scale',frame=frame,group=p.name)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag=strip.channelbag(slot)
                if bag:
                    for channel in bag.fcurves:
                        if channel.data_path=='pose.bones["root"].location':
                            for key in channel.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    path=OUT/('A_FleshHand_'+role+'.fbx');export(path,True)
    clips[role]={'file':str(path),'duration_seconds':frames/60,'frames':frames,'loop':role in ('Idle','Walk','Dizzy')}
    print('FLESHHAND_CLIP '+role,flush=True)

# Palm-emitted fist: a baked lower-detail hand with a closed wrist sleeve.
# It is a single static draw, extended only during the original hammer window.
rig.animation_data.action=None;reset();fingers(92,0);bpy.context.view_layer.update()
low=next(o for o in scene.objects if o.type=='MESH' and 'LOD2' in o.name)
evaluated=low.evaluated_get(bpy.context.evaluated_depsgraph_get())
data=bpy.data.meshes.new_from_object(evaluated);fist=bpy.data.objects.new('SM_FleshHand_PalmFist',data);scene.collection.objects.link(fist)
# A short forearm grows from the palm: overlap the closed source wrist, with matching UV/material.
verts=[];faces=[];rings=[(-.5,.068),(-.25,.085),(.04,.102),(.12,.105)];segments=16
for z,r in rings:
    for j in range(segments):
        a=2*math.pi*j/segments;verts.append((.025+math.cos(a)*r,math.sin(a)*r*.82,z))
for i in range(len(rings)-1):
    for j in range(segments):a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
faces.append(tuple(reversed(range(segments))))
tube_data=bpy.data.meshes.new('PalmForearm');tube_data.from_pydata(verts,[],faces);tube_data.update()
tube=bpy.data.objects.new('PalmForearm',tube_data);scene.collection.objects.link(tube);tube.data.materials.append(mesh.data.materials[0])
uv=tube.data.uv_layers.new(name='UVMap')
for poly in tube.data.polygons:
    for li in poly.loop_indices:
        vi=tube.data.loops[li].vertex_index;uv.data[li].uv=(.43+(vi%segments)/segments*.12,.43+(vi//segments)/(len(rings)-1)*.12)
bpy.ops.object.select_all(action='DESELECT');fist.select_set(True);tube.select_set(True);bpy.context.view_layer.objects.active=fist;bpy.ops.object.join()
# Put the sleeve origin at its hidden base and rotate the fist to palm +Y forward.
rotation=Matrix.Rotation(-math.pi/2,4,'X')
for v in fist.data.vertices:v.co=rotation@(v.co-Vector((.025,0,-.5)))
for poly in fist.data.polygons:poly.use_smooth=True
export(OUT/'SM_FleshHand_PalmFist.fbx')
reset();rig.animation_data.action=None
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FleshHand_Animated.blend'))
receipt={'clips':clips,'fps':60,'palm_fist':str(OUT/'SM_FleshHand_PalmFist.fbx'),
 'palm_outward_axis':[0,1,0],'choreography_revision':'PalmForward20260927',
 'grounding_revision':'RootLocalSupport20260927V1',
 'legacy_choreography':'upright walk; emitted fist; folded slam; spread grand slam',
 'new_choreography':['Hit','Dizzy','Death'],'rendered':False,'tested':False}
(OUT/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FLESHHAND_ANIMATION_AUTHORING_COMPLETE',flush=True)
