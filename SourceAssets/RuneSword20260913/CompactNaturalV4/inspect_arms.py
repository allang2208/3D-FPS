"""User-requested, scoped arm deformation inspection in the editable source."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'WristRiftV3'
source=P.parent/version/'AzureRunesword_Manny_Editable.blend'
out=P/('Review_'+version);out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_RuneSword_Rig']
# Linked source rig libraries repopulate their own large meshes on reload.
# Isolate only the actual exported geometry in a new scene for inspection.
s=bpy.data.scenes.new('RuneArmInspection')
for name in ['SK_RuneSword_Rig','SK_Manny_Arms_Export','RuneSword_Blade']:s.collection.objects.link(bpy.data.objects[name])
bpy.context.window.scene=s;s.render.fps=240
rest={b.name:b.matrix_local.copy() for b in r.data.bones};report={}
tracked=['hand_l','hand_r','lowerarm_l','lowerarm_r','lowerarm_twist_01_l','lowerarm_twist_01_r','upperarm_l','upperarm_r']
for clip in ['Slash1','Slash2']:
    action=bpy.data.actions['A_RuneSword_'+clip];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    prev={};first={};row={'max_wrist_bend':{},'max_relative_step_degrees':{},'end_difference_degrees':{}}
    for f in range(201):
        s.frame_set(f);wp=r.pose.bones['WPN_root'].matrix.inverted()
        for side in ['l','r']:
            fn,hn='lowerarm_'+side,'hand_'+side
            H=r.pose.bones[hn].matrix;F=r.pose.bones[fn].matrix
            fd=(H.translation-F.translation).normalized();old=(rest[hn].translation-rest[fn].translation).normalized()
            hd=H.to_quaternion()@rest[hn].to_quaternion().inverted()@old
            bend=math.degrees(fd.angle(hd))
            if bend>row['max_wrist_bend'].get(side,{}).get('degrees',-1):row['max_wrist_bend'][side]={'degrees':bend,'frame':f}
        for n in tracked:
            q=(wp@r.pose.bones[n].matrix).to_quaternion()
            if f==0:first[n]=q.copy()
            if n in prev:
                angle=math.degrees(2*math.acos(min(1,abs(prev[n].dot(q)))))
                if angle>row['max_relative_step_degrees'].get(n,{}).get('degrees',-1):row['max_relative_step_degrees'][n]={'degrees':angle,'frame':f}
            prev[n]=q.copy()
            if f==200:row['end_difference_degrees'][n]=math.degrees(2*math.acos(min(1,abs(first[n].dot(q)))))
    report[clip]=row
(out/'arm_metrics.json').write_text(json.dumps(report,indent=2))
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type!='CPU'
    s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100
s.render.use_compositing=False;s.render.use_sequencer=False;s.view_settings.exposure=0;s.view_settings.gamma=1
# Use a neutral diagnostic surface on the arms to expose geometry folds even
# when archived source material images are unavailable; UE inspection uses the
# installed game materials separately.
clay=bpy.data.materials.new('ArmInspectionClay');clay.use_nodes=True
bs=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.24,.29,.36,1);bs.inputs['Roughness'].default_value=.5
arms=bpy.data.objects['SK_Manny_Arms_Export'];arms.data.materials.clear();arms.data.materials.append(clay)
for poly in arms.data.polygons:poly.material_index=0
s.render.image_settings.file_format='PNG';s.render.film_transparent=False;s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('ArmReviewWorld');s.world.use_nodes=True
bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs[0].default_value=(.11,.14,.19,1);bg.inputs[1].default_value=.65
for name,loc,power,size in [('Key',(-1,-.5,1.6),100,2),('Fill',(1,0,.4),65,1.5),('Rim',(0,1.4,.8),110,1.2)]:
    ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);s.collection.objects.link(lo);lo.location=loc
    lo.rotation_euler=(Vector((0,.35,-.2))-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size
cd=bpy.data.cameras.new('ArmReviewCamera');cam=bpy.data.objects.new('ArmReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam
cd.clip_start=.005;cd.clip_end=50;cd.sensor_fit='HORIZONTAL';cd.angle=2*math.atan(math.tan(math.radians(75)*.5)*16/9)
cam.location=(0,0,0);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
shots=[('Idle',0),('Slash1',17),('Slash1',55),('Slash1',69),('Slash1',111),('Slash1',143),('Slash2',18),('Slash2',69),('Slash2',111),('Slash2',146)]
for clip,f in shots:
    action=bpy.data.actions['A_RuneSword_'+clip];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];s.frame_set(f)
    s.render.filepath=str(out/(clip+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
for clip,f in [('Slash1',69),('Slash2',69)]:
    action=bpy.data.actions['A_RuneSword_'+clip];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];s.frame_set(f)
    cam.location=(.75,-.15,.40);target=Vector((0,.35,-.17));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.angle=math.radians(60)
    s.render.filepath=str(out/(clip+'_detail.png'));bpy.ops.render.render(write_still=True)
print('ARM_REVIEW_WRITTEN',str(out),flush=True)
