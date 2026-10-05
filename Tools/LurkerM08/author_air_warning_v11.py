"""Author M08's readable, bore-fitted air-cannon wind-up; no preview/test run."""
import bpy, json, math, random, wave, array
from pathlib import Path

PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'AirWarningV11_20261005';OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
SOURCE=BASE/'MotionV09_20261005/M08_Attacks_MotionV09.blend'
FPS=120;RELEASE=1.50;OLD_RELEASE=.92;FRAMES=round((1.85+RELEASE-OLD_RELEASE)*FPS)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.render.fps=FPS;scene.render.fps_base=1
rig=bpy.data.objects['Armature'];skin=bpy.data.objects['SK_LurkerM08']
modifier=next(m for m in skin.modifiers if m.type=='ARMATURE');modifier.show_viewport=False
old=bpy.data.actions['A_M08_AttackAirCannon_MotionV09']
rig.animation_data.action=old
# Preserve V09's oral clearance and support poses. Stretch the pressure build
# after the initial crouch, leaving recoil/recovery at their authored speed.
samples=[]
for i in range(FRAMES+1):
    t=i/FPS
    source_t=t if t<=.34 else (.34+(t-.34)*(OLD_RELEASE-.34)/(RELEASE-.34) if t<RELEASE else min(1.85,OLD_RELEASE+t-RELEASE))
    frame=source_t*FPS+1
    scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
    samples.append({pb.name:(pb.location.copy(),pb.rotation_quaternion.copy(),pb.scale.copy()) for pb in rig.pose.bones})
action=bpy.data.actions.new('A_M08_AttackAirCannon_AirWarningV11');action.use_fake_user=True
rig.animation_data.action=action;scene.frame_start=1;scene.frame_end=FRAMES+1
previous={}
for i,pose in enumerate(samples):
    for pb in rig.pose.bones:
        loc,q,scale=pose[pb.name]
        if pb.name in previous and previous[pb.name].dot(q)<0:q.negate()
        previous[pb.name]=q.copy();pb.rotation_mode='QUATERNION'
        pb.location=loc;pb.rotation_quaternion=q;pb.scale=scale
        for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=i+1,group=pb.name)
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
clip=ANIM/(action.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(clip),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
modifier.show_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_AirWarning_Animated_V11.blend'))

# One mesh/material: two readable bore rings, three inward wind ribbons, core.
# Normal +Z; the existing runtime skinned-rim frame scales the 34 cm bore.
verts=[];faces=[];uvs=[];layers=[]
def vertex(co,uv,layer):
    verts.append(co);uvs.append(uv);layers.append(layer);return len(verts)-1
def torus(radius,tube,z):
    start=len(verts);segments=64;sides=8
    for i in range(segments+1):
        a=i/segments*math.tau
        for j in range(sides+1):
            b=j/sides*math.tau;r=radius+tube*math.cos(b)
            vertex((r*math.cos(a),r*math.sin(a),z+tube*math.sin(b)),(i/segments,j/sides),0.)
    for i in range(segments):
        for j in range(sides):
            a=start+i*(sides+1)+j;b=a+sides+1;faces.append((a,b,b+1,a+1))
torus(.415,.024,.018);torus(.315,.018,.06)
for branch in range(3):
    start=len(verts);steps=48
    for i in range(steps+1):
        t=i/steps;r=.40-.31*t;a=branch*math.tau/3+math.tau*.65*t
        width=.014+.018*math.sin(math.pi*t)
        for side in (-1,1):
            rr=r+side*width
            vertex((rr*math.cos(a),rr*math.sin(a),.03+.11*t),(t,(side+1)/2),.5)
    for i in range(steps):
        a=start+2*i;faces.append((a,a+2,a+3,a+1))
start=len(verts);segments=32;rings=16
for j in range(rings+1):
    p=math.pi*j/rings
    for i in range(segments+1):
        a=math.tau*i/segments
        vertex((.12*math.sin(p)*math.cos(a),.12*math.sin(p)*math.sin(a),.10+.085*math.cos(p)),(i/segments,j/rings),1.)
for j in range(rings):
    for i in range(segments):
        a=start+j*(segments+1)+i;b=a+segments+1;faces.append((a,b,b+1,a+1))
data=bpy.data.meshes.new('M08_AirWarning_Geometry');data.from_pydata(verts,[],faces);data.update()
uv=data.uv_layers.new(name='UVMap');color=data.color_attributes.new(name='WarningLayer',type='FLOAT_COLOR',domain='CORNER')
for polygon in data.polygons:
    polygon.use_smooth=True
    for li in polygon.loop_indices:
        vi=data.loops[li].vertex_index;uv.data[li].uv=uvs[vi];color.data[li].color=(layers[vi],0.,0.,1.)
data.color_attributes.active_color=color
warning=bpy.data.objects.new('SM_M08_AirWarning_V11',data);scene.collection.objects.link(warning)
warning.data.materials.append(bpy.data.materials.new('M08_AirWarning_SingleSlot'))
bpy.ops.object.select_all(action='DESELECT');warning.select_set(True);bpy.context.view_layer.objects.active=warning
mesh_file=OUT/'SM_M08_AirWarning_V11.fbx'
bpy.ops.export_scene.fbx(filepath=str(mesh_file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',colors_type='LINEAR',bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_AirWarning_Animated_V11.blend'))

# Audible intake starts immediately; pitch rises into a short final lock accent.
rng=random.Random(80811);rate=44100;pcm=array.array('h');low=0.;phase=0.;accent=0.
for i in range(round(RELEASE*rate)):
    t=i/rate;p=t/RELEASE;noise=rng.uniform(-1,1);low+=.13*(noise-low)
    env=min(1.,t/.025)*min(1.,(RELEASE-t)/.025)
    phase+=math.tau*(105+240*p*p)/rate
    v=(.11+.18*p)*low+(.04+.025*p)*math.sin(phase)+(.025+.045*p)*noise
    if t>=1.2:
        accent+=math.tau*(650-150*(t-1.2)) /rate
        v+=.085*math.sin(accent)*min(1.,(t-1.2)/.008)*math.exp(-(t-1.2)*14)
    pcm.append(round(max(-.95,min(.95,env*v))*32767))
audio=OUT/'S_M08_AirWarning_Charge_V11.wav'
with wave.open(str(audio),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(pcm.tobytes())
report={'revision':'M08_AirWarningV11_20261005','source':str(SOURCE),
    'mesh_asset':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03',
    'clips':{'AttackAirCannon':{'file':str(clip),'seconds':FRAMES/FPS,'frames':FRAMES+1,'contact':[RELEASE,RELEASE]}},
    'warning_mesh':str(mesh_file),'charge_audio':str(audio),'warning_triangles':sum(len(f)-2 for f in faces),
    'windup_seconds':RELEASE,'aim_lock_before_release':.30,'runtime_tested':False,'rendered':False,
    'vertex_colors':'Linear red: rings=0, inward ribbons=0.5, core=1; UV.x is path/angle, UV.y is width/cross-section.',
    'provenance':'Original local geometry, synthesized mono audio and retiming of retained V09 animation; user-provided skin unchanged.'}
(OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_AIR_WARNING_V11_AUTHORED',flush=True)
