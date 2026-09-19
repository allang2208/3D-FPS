import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Euler
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4AnimationAudit20260910/M4_Hand_MAT_Editable.blend');r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
names=[b.name for b in r.pose.bones];rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones};parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
def sample(name,f):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
p=sample('M4_MAT_reload',95);ref=sample('M4_idle',0);mag=p['WPN_SOCKET_Magazine']
for n in names:
 if n.endswith('_l') and n.startswith(('index','middle','ring','pinky')):ref[n]=ref['hand_l']@rest['hand_l'].inverted()@rest[n]
ref_original={n:m.copy() for n,m in ref.items()}
for digit in ['index','middle','ring','pinky']:
 for j,angle in enumerate([-20,65,55],1):
  n=f'{digit}_{j:02}_l';par=parent[n];localrest=rest[par].inverted()@rest[n];local=localrest.inverted()@ref_original[par].inverted()@ref_original[n];e=local.to_euler();e.z=math.radians(angle);ref[n]=ref[par]@localrest@Matrix.LocRotScale(local.translation,e.to_quaternion(),local.to_scale())

u=(ref['index_01_l'].translation-ref['pinky_01_l'].translation).normalized();v=(ref['middle_01_l'].translation-ref['hand_l'].translation);v=(v-u*v.dot(u)).normalized();w=u.cross(v).normalized();basis=Matrix((u,v,w)).transposed();target=Matrix((Vector((0,0,1)),Vector((0,-1,0)),Vector((1,0,0)))).transposed();q=(target@basis.inverted()).to_quaternion();rot=q.to_matrix().to_4x4();rot.translation=Vector((.030,-.043,.010))-q@ref['middle_01_l'].translation
for n in names:
 if n.endswith('_l'):p[n]=mag@rot@ref[n]
a=bpy.data.actions.new('M4_WRAP_fit');r.animation_data.action=a
for n in names:
 local=(rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n]).inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location,b.rotation_quaternion,b.scale=local.decompose()
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
s.frame_set(0);bpy.context.view_layer.update();print('WRIST',(mag.inverted()@p['hand_l']).translation[:]);print('BONES',{n:tuple(mag.inverted()@p[n].translation) for n in ['index_01_l','index_03_l','middle_01_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']})
bpy.ops.wm.save_as_mainfile(filepath=str(O/'grip_candidate.blend'))
# Shared review lighting/cameras, fixed contact pose.
for o in s.objects:o.hide_render=o.type!='MESH' or o.parent!=r
s.world.color=(.1,.1,.1)
for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=95;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,.2,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('ReviewCam');cam=bpy.data.objects.new('ReviewCam',d);s.collection.objects.link(cam);s.camera=cam;d.clip_start=.005;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=16;s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100
focus=r.pose.bones['hand_l'].head.copy()+Vector((0,0,.025))
for i,off in enumerate([(-.35,-.3,.25),(.35,-.3,.25),(0,.4,.2)]):
 d.type='ORTHO';d.ortho_scale=.34;cam.location=focus+Vector(off);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'grip_candidate_{i}.png');bpy.ops.render.render(write_still=True)
