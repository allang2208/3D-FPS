"""Compare saved UE idle frames and render the current M24 at the real hip camera."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;P=O.parents[1];D=json.loads((O/'ue_inputs.json').read_text())
NEW='--candidate' in sys.argv
def mat(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def axes(row,up):
    w={n:mat(v) for n,v in row['world'].items()}
    x=(w['WPN_FrontSight'].translation-w['WPN_RearSight'].translation).normalized()
    raw=w['WPN_root'].to_quaternion()@Vector(up);cross=raw.cross(x)
    if cross.length<.0001:return None,float(cross.length)
    y=cross.normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed(),float(cross.length)
base=Matrix.Rotation(math.pi/2,3,'Z');m4axes,_=axes(D['m4'],(0,0,1))
target=base@m4axes;hand=Vector((0,7,-7))+base@Vector(D['m4']['world']['hand_r'][:3])
def framing(name,up,offset=(10,0,0)):
    source,quality=axes(D[name],up)
    if source is None:return Matrix.Translation((0,7,-7))@base.to_4x4(),quality
    rot=target@source.transposed();out=rot.to_4x4();out.translation=hand+Vector(offset)-rot@Vector(D[name]['world']['hand_r'][:3]);return out,quality
scene_path=O/'M24_Hold_Editable.blend' if NEW else P/'SourceAssets/M24Repair20261027/M24_Repaired_Editable.blend'
if NEW:
    bpy.ops.wm.open_mainfile(filepath=str(scene_path),use_scripts=False)
    r=bpy.data.objects['M24_V9_Rig'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    conversion=Matrix.Diagonal((100,-100,100,1))
    for n,pb in r.pose.bones.items():
        if n not in D['m24']['rest_world']:continue
        u=conversion@pb.matrix@r.data.bones[n].matrix_local.inverted()@conversion.inverted()@mat(D['m24']['rest_world'][n])
        p,q,scale=u.decompose();D['m24']['world'][n]=list(p)+[q.x,q.y,q.z,q.w]+list(scale)
svd,_=framing('svd',(0,0,1));current,quality=framing('m24',(0,0,1));correct,_=framing('m24',(0,-1,0))
svd_rear=svd@Vector(D['svd']['world']['WPN_RearSight'][:3])
m24_rear=correct@Vector(D['m24']['world']['WPN_RearSight'][:3])
delta=svd_rear-m24_rear;offset=Vector((10,0,0))+delta
candidate,_=framing('m24',(0,-1,0),offset)
report={'source':'saved compressed UE idles, zero seconds',
 'current_up_cross_axis_length':quality,'current_frame':[list(v) for v in current],
 'physical_up_frame':[list(v) for v in correct],'candidate_frame':[list(v) for v in candidate],
 'svd_frame':[list(v) for v in svd],'svd_rear_camera_cm':list(svd_rear),
 'm24_correct_axis_rear_camera_cm':list(m24_rear),'candidate_presentation_offset_cm':list(offset)}
bpy.ops.wm.open_mainfile(filepath=str(scene_path),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];s.frame_set(0);bpy.context.view_layer.update()
report['source_pose']={n:[list(v) for v in r.pose.bones[n].matrix] for n in ('WPN_root','hand_l','hand_r','lowerarm_l','lowerarm_r','upperarm_l','upperarm_r','clavicle_l','clavicle_r')}
# Scene is already the exact repaired source for the saved UE idle; retain all V9 data.
for ob in s.objects:
    if ob.type=='MESH':ob.color=(.61,.68,.75,1) if ob.name=='M24_V9_BareArms' else (.16,.19,.22,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('M24 hold review');s.world.color=(.045,.055,.07)
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
s.render.use_compositing=False;s.render.use_sequencer=False
s.view_settings.view_transform='Standard'
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam
cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)));cam.data.clip_start=.01
cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0)
# Engine component -> camera -> Blender display. Reflections cancel as a proper rotation.
convert=Matrix.Diagonal((100,-100,100,1));camera_space=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))
out=O/('Candidate' if NEW else 'Before');out.mkdir(exist_ok=True)
for name,frame in [('current_hip',current),('correct_axis_hip',correct),('svd_matched_hip',candidate)]:
    r.matrix_world=camera_space@frame@convert;bpy.context.view_layer.update()
    s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
r.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
for name,location,targetpoint in [('grip_right',(-.65,-.25,.22),(0,.06,.09)),('grip_left',(.65,.28,.16),(0,.28,.08))]:
    cam.location=location;cam.rotation_euler=(Vector(targetpoint)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=.65
    s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
(O/('framing_candidate.json' if NEW else 'framing_diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_HOLD_DIAGNOSIS',json.dumps({k:v for k,v in report.items() if k not in ('source_pose',)}),flush=True)
