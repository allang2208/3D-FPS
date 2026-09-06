import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ore-spider-joints-v06-20260906/ore-spider-joints.blend'))
scene=bpy.context.scene;arm=bpy.data.objects['OreRig'];scene.render.fps=90
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def curve(t,keys):
 for (a,x),(b,y) in zip(keys,keys[1:]):
  if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
 return keys[-1][1]
defs={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in arm.data.bones}
rest={b.name:b.matrix_local.copy() for b in arm.data.bones}
def orient(n,h,t):
 a,b=defs[n];rot=(b-a).rotation_difference(t-h)@rest[n].to_quaternion()
 m=rot.to_matrix().to_4x4();m.translation=h;arm.pose.bones[n].matrix=m;bpy.context.view_layer.update()
old=bpy.data.actions['Throw'];old.name='Throw_old'
for tr in list(arm.animation_data.nla_tracks):
 if any(s.action==old for s in tr.strips):arm.animation_data.nla_tracks.remove(tr)
# Sample inherited body/support poses first; replace only the independent throwing arm.
arm.animation_data.action=old
samples=[]
for frame in range(136):
 scene.frame_set(frame);samples.append({p.name:p.matrix_basis.copy() for p in arm.pose.bones})
new=bpy.data.actions.new('Throw');new.use_fake_user=True;arm.animation_data.action=new
previous={}
for frame,poses in enumerate(samples):
 t=frame/90;scene.frame_set(frame)
 for name,m in poses.items():arm.pose.bones[name].matrix_basis=m
 bpy.context.view_layer.update()
 body=arm.pose.bones['body'].matrix@rest['body'].inverted()
 base=body@defs['arm_hand'][0]+Vector((.23,-.20,.19))
 # Outside the crystal silhouette: gather low, draw back beside the right flank,
 # accelerate forward at the existing 1.125s release, then absorb and return.
 grab=curve(t,[(0,0),(.20,0),(.375,1),(.60,1),(.78,0),(1.5,0)])
 draw=curve(t,[(0,0),(.38,0),(.87,1),(1.02,1),(1.16,0),(1.5,0)])
 release=curve(t,[(0,0),(1.02,0),(1.15,1),(1.26,.88),(1.5,0)])
 wrist=base+Vector((.05,-.10,-.08))*grab+Vector((.29,.12,.43))*draw+Vector((-.16,-.55,.24))*release
 shoulder=body@defs['arm_upper'][0]
 elbow=(body@defs['arm_lower'][0])+Vector((.055+.19*draw,-.055-.20*release,.015+.14*draw))
 orient('arm_upper',shoulder,elbow);orient('arm_lower',elbow,wrist)
 direction=Vector((.05,-.12,-.19)).lerp(Vector((-.12,-.30,.08)),release)
 orient('arm_hand',wrist,wrist+direction)
 for pb in arm.pose.bones:
  if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
  previous[pb.name]=pb.rotation_quaternion.copy()
  for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=frame,group=pb.name)
bpy.data.actions.remove(old)
arm.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ore-spider-impact.blend'))
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
for ob in scene.objects:
 if ob.type=='MESH':ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P.parents[2]/'assets/models/ore_spider/ore_spider_v07_preview.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True)
(P/'build-report.json').write_text(json.dumps({'throw_seconds':1.5,'release_seconds':1.125,'slam_seconds':2.0,'slam_hit':10/18*2,'death_seconds':1.2,'bones':len(arm.data.bones)},indent=2))
print('IMPACT_BUILD_PASS',flush=True)
