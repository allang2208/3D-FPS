"""Save and render only the standalone requested opening preview."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
data=json.loads((P/'candidate.json').read_text());events=data['events']
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'GripPhotoV3/Spellbook_PhotoGripV3.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Spellbook_PhotoGripV3_V7_LeftArm']
rig.animation_data_clear();rig.animation_data_create()
arm_action=bpy.data.actions.new('Preview_Only_PalmUpOpening');rig.animation_data.action=arm_action
old=bpy.data.objects['Alchemy_BluePurple_PhotoSpineGrip'];old.hide_render=True;old.hide_set(True)
with bpy.data.libraries.load(str(P.parents[1]/'Spellbook_Alchemy.blend'),link=False) as (available,loaded):
    loaded.objects=['SpellbookRig','SK_Spellbook_Alchemy']
for obj in loaded.objects:
    bpy.context.collection.objects.link(obj);obj.hide_set(False);obj.hide_viewport=False;obj.hide_render=False
book=next(o for o in loaded.objects if o.type=='ARMATURE')
book.animation_data_clear();book.animation_data_create()
book_action=bpy.data.actions.new('Preview_Only_ClosedThenOpen');book.animation_data.action=book_action
# Attach the rendered book to the original grip bone, so even interpolation
# between authoring frames uses the exact final hand transform.
book.matrix_world=Matrix.Diagonal((.01,.01,.01,1))
for kind in ('COPY_LOCATION','COPY_ROTATION'):
    constraint=book.constraints.new(kind);constraint.target=rig;constraint.subtarget='book_spine_grip_l'
S=Matrix.Diagonal((1,-1,1));scene=bpy.context.scene;scene.render.fps=60
def convert(m):
    m=Matrix(m);r=(S@m.to_3x3()@S).to_4x4();r.translation=S@m.translation*.01;return r
def ease(a,b,t):
    u=max(0,min(1,(t-a)/(b-a)));return u*u*u*(u*(6*u-15)+10)
previous={};previous_book=None
for f,age in enumerate(data['times']):
    scene.frame_set(f)
    for n in data['arm_order']:
        bone=rig.pose.bones[n];ref=rig.data.bones[n]
        native=ref.parent.matrix_local.inverted()@ref.matrix_local if ref.parent else ref.matrix_local
        local=convert(data['poses'][f]['local'][n])
        if n=='clavicle_l':
            lower=Vector((0,0,-.05));local.translation+=bone.parent.matrix.to_3x3().inverted()@lower
        bone.rotation_mode='QUATERNION';bone.matrix_basis=native.inverted()@local
        if n in previous and bone.rotation_quaternion.dot(previous[n])<0:bone.rotation_quaternion.negate()
        previous[n]=bone.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=f)
    # No independent location/rotation keys: the hand attachment owns the book.
    for bone in book.pose.bones:
        bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
    book.pose.bones['Cover_Front'].rotation_euler.y=math.radians(-165)*ease(events['open_start'],events['open_end'],age)
    for p in range(3):book.pose.bones[f'Page_{p+1}_00'].location.z=.05+.021*(2-p)
    for bone in book.pose.bones:
        bone.keyframe_insert('rotation_euler',frame=f);bone.keyframe_insert('location',frame=f)
for obj,action in ((rig,arm_action),(book,book_action)):
    if len(action.slots):obj.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_start=0;scene.frame_end=len(data['times'])-1
scene.timeline_markers.clear()
for label,t in [('SideGrip',0),('RigidTurnComplete',events['turn_end'])]:
    scene.timeline_markers.new(label,frame=round(t*60))
camera=bpy.data.cameras.new('PreviewCamera');camera.sensor_fit='VERTICAL';camera.sensor_height=24
camera.lens=24/(2*math.tan(math.radians(75/2)));camera.clip_start=.01
cam=bpy.data.objects.new('PreviewCamera',camera);scene.collection.objects.link(cam)
cam.rotation_euler=Matrix(((0,0,-1),(-1,0,0),(0,1,0))).to_euler();cam.location.z=-.12;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.device='GPU'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type!='CPU'
    if not any(d.use for d in prefs.devices):scene.cycles.device='CPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.065,.075,.09,1);bg.inputs['Strength'].default_value=.5
scene.view_settings.view_transform='AgX'
target=Vector((.40,.15,-.12))
for name,location,power,size in [('Key',(-.15,-.25,.40),35,.65),('Fill',(.1,.65,.2),18,.55),('Rim',(.75,.05,.38),45,.5)]:
    lightdata=bpy.data.lights.new('Preview'+name,'AREA');lightdata.energy=power;lightdata.shape='DISK';lightdata.size=size
    light=bpy.data.objects.new('Preview'+name,lightdata);scene.collection.objects.link(light)
    light.location=location;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
scene.frame_set(0);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Spellbook_PalmUp_Preview.blend'))
stills='--stills' in sys.argv
times=[0,.15,.30,.45,.60,.75,.90,1.20] if stills else [i/24 for i in range(math.ceil(events['duration']*24)+1)]
folder=P/('stills' if stills else 'frames');folder.mkdir(exist_ok=True)
for i,t in enumerate(times):
    frame=t*60;scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
    scene.render.filepath=str(folder/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
    print(f'PREVIEW_FRAME {i+1}/{len(times)}',flush=True)
(P/('stills.json' if stills else 'render.json')).write_text(json.dumps({'times':times,'fps':24,'count':len(times),'game_capture':False,'camera':'75 degree vertical FOV; detail camera 12 cm below gameplay','candidate_only':True},indent=2))
