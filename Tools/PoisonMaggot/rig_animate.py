import bpy,json,math
from mathutils import Vector,Matrix,Quaternion
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911');out=root/'delivery'
bpy.ops.wm.open_mainfile(filepath=str(out/'PoisonMaggot_Retopology.blend'))
s=bpy.context.scene;s.render.fps=30;s.frame_start=1
low=bpy.data.objects['PoisonMaggot_Retopo'];bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
if low.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
arm=bpy.data.armatures.new('PoisonMaggot_Skeleton');rig=bpy.data.objects.new('SK_PoisonMaggot',arm);s.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;low.select_set(False);rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
def bone(n,h,t,parent=None):
 b=arm.edit_bones.new(n);b.head=h;b.tail=t
 if parent:b.parent=arm.edit_bones[parent]
 return b
bone('root',(0,0,0),(0,0,.15));bone('death_pivot',(0,0,.36),(.15,0,.36),'root')
xs=[-.98,-.75,-.48,-.21,.06,.33,.60,.79];zs=[.29,.39,.43,.45,.45,.45,.44,.43]
for i,x in enumerate(xs):bone(f'body_{i:02}',(x,0,zs[i]),(xs[i+1] if i<7 else .96,0,zs[i+1] if i<7 else .39),'death_pivot' if i==0 else f'body_{i-1:02}')
bone('head',(.96,0,.38),(1.12,0,.34),'body_07');bone('jaw',(.98,0,.26),(1.10,0,.26),'head');bone('mouth_socket',(1.085,0,.31),(1.16,0,.31),'jaw')
legxs=[-.52,-.17,.18,.48,.73,.90]
for side,sign in [('L',-1),('R',1)]:
 for i,x in enumerate(legxs):
  j=min(range(8),key=lambda j:abs(xs[j]-x));y=sign*(.46 if i<4 else .34)
  bone(f'leg_{side}_{i:02}',(x,y*.68,.22),(x+.025,y,.065),f'body_{j:02}');bone(f'foot_{side}_{i:02}',(x+.025,y,.065),(x+.105,y*1.15,.025),f'leg_{side}_{i:02}')
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;arm.display_type='BBONE'
for b in arm.bones:low.vertex_groups.new(name=b.name)
# Segment interpolation plus independent short-leg groups; at most four influences.
axes=xs+[.98];names=[f'body_{i:02}' for i in range(8)]+['head'];counts={}
for v in low.data.vertices:
 x,y,z=v.co;j=max(0,min(7,next((k-1 for k,a in enumerate(axes) if x<a),7)));t=max(0,min(1,(x-axes[j])/(axes[j+1]-axes[j])));weights={names[j]:1-t,names[j+1]:t}
 if z<.25 and abs(y)>.19 and x>-.72:
  i=min(range(6),key=lambda i:abs(legxs[i]-x));side='L' if y<0 else 'R';w=max(0,min(1,(.25-z)/.11))*max(0,min(1,(abs(y)-.19)/.10));weights={n:a*(1-w) for n,a in weights.items()};toe=max(0,min(1,(.10-z)/.06));weights[f'leg_{side}_{i:02}']=w*(1-toe);weights[f'foot_{side}_{i:02}']=w*toe
 if x>.99 and z<.35 and abs(y)<.20:
  w=max(0,min(1,(x-.99)/.07))*max(0,min(1,(.35-z)/.07));weights={n:a*(1-w) for n,a in weights.items()};weights['jaw']=w
 weights=dict(sorted(((n,w) for n,w in weights.items() if w>.0001),key=lambda x:-x[1])[:4]);total=sum(weights.values())
 for n,w in weights.items():low.vertex_groups[n].add([v.index],w/total,'REPLACE');counts[n]=counts.get(n,0)+1
mod=low.modifiers.new('DedicatedMaggotRig','ARMATURE');mod.object=rig;low.parent=rig
rest={b.name:b.matrix_local.copy() for b in arm.bones};identity=Matrix.Identity(4)
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def envelope(t):return smooth((t-.28)/.9)*(1-smooth((t-2.36)/.64))
def targets(action,t,duration):
 result={};phase=2*math.pi*t/duration
 for b in arm.bones:
  n=b.name;p=rest[n].translation.copy();x=p.x;front=smooth((x+.12)/1.1);offset=Vector((0,0,0));rot=Quaternion();sc=Vector((1,1,1))
  if n in ('root','death_pivot'):result[n]=rest[n].copy();continue
  if action=='Idle':
   if n.startswith('body') or n in ('head','jaw','mouth_socket'):
    breath=math.sin(phase);offset.z=.006*breath*(.5+.5*front);sc=Vector((1,1+.012*breath,1+.009*breath));rot=Quaternion((0,1,0),.01*math.sin(phase+.3*x)*front)
  elif action=='Move':
   wave=math.sin(phase*2-x*3);offset.x=.034*wave;offset.z=.013*(.5+.5*wave);sc=Vector((1-.035*math.cos(phase*2-x*3),1+.02*math.cos(phase*2-x*3),1))
   if n.startswith(('leg_','foot_')):
    a=n.split('_');i=int(a[2]);q=phase*2-i*.82+(math.pi if a[1]=='R' else 0);offset.x=.073*math.cos(q);offset.z=.036*max(0,math.sin(q));sc=Vector((1,1,1));rot=Quaternion((0,1,0),.14*math.cos(q))
  elif action=='Spit':
   e=envelope(t);c=math.sin(math.pi*min(1,t/.85)) if t<.85 else 0
   offset.x=(-.045*c+.075*e)*front;offset.z=(.19*e-.018*c)*front;rot=Quaternion((0,1,0),-.22*e*front);sc=Vector((1+.025*e,1+.025*c-.012*e,1+.02*c))
   if n.startswith(('leg_','foot_')):offset*=.25;rot=Quaternion((0,1,0),-.08*e*front);sc=Vector((1,1,1))
   if n=='jaw':offset.z-=.023*e;rot=Quaternion((0,1,0),.12*e)
   if n=='mouth_socket':offset.z-=.023*e
   if 14/33*3<=t<27/33*3:offset.z+=.004*math.sin(t*math.pi*40)*front
  elif action=='Hit':
   e=smooth(t/.1)*(1-smooth((t-.1)/.5));offset.x=-.085*e*front;offset.z=-.032*e*front;rot=Quaternion((0,1,0),.11*e*front)
  elif action=='Death':
   e=smooth(t/1.4);curl=smooth(t/.75)*front;offset.x=-.08*e*front;offset.z=-.10*curl;rot=Quaternion((0,1,0),.24*curl)
   if n.startswith(('leg_','foot_')):offset.z+=.08*e;rot=Quaternion((1,0,0),(-1 if '_L_' in n else 1)*.4*e)
  matrix=Matrix.Translation(p+offset)@rot.to_matrix().to_4x4()@Matrix.Diagonal((*sc,1))@rest[n].to_3x3().to_4x4()
  if action=='Death':
   e=smooth((t-.35)/1.05);pivot=Vector((0,0,.36));r=Quaternion((1,0,0),.96*e);matrix=Matrix.Translation(pivot+Vector((0,0,-.035*e)))@r.to_matrix().to_4x4()@Matrix.Translation(-pivot)@matrix
  result[n]=matrix
 return result
contracts={'Idle':3,'Move':2.5,'Spit':3,'Death':1.8,'Hit':.6};report={'bones':len(arm.bones),'weighted_vertices_per_bone':counts,'actions':{},'max_influences':max(len(v.groups) for v in low.data.vertices)}
rig.animation_data_create()
for action,duration in contracts.items():
 a=bpy.data.actions.new(action);a.use_fake_user=True;rig.animation_data.action=a;end=round(duration*30)+1
 for f in range(1,end+1):
  s.frame_set(f);ts=targets(action,(f-1)/30,duration)
  for b in arm.bones:
   pb=rig.pose.bones[b.name];parent=b.parent
   basis=rest[b.name].inverted()@rest[parent.name]@ts[parent.name].inverted()@ts[b.name] if parent else rest[b.name].inverted()@ts[b.name]
   pb.matrix_basis=basis;pb.rotation_mode='QUATERNION';pb.keyframe_insert('location',frame=f);pb.keyframe_insert('rotation_quaternion',frame=f);pb.keyframe_insert('scale',frame=f)
  if not rig.animation_data.action_slot and a.slots:rig.animation_data.action_slot=a.slots[0]
 report['actions'][action]={'seconds':duration,'frames_inclusive':end,'loop':action in ('Idle','Move')}
 print('ANIM_DONE',action,flush=True)
# Preserve the side-collapse identity while keeping the body above its support plane.
report['ground_correction_max_m']={}
for name,duration in contracts.items():
 a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];lifts=[]
 for f in range(1,round(duration*30)+2):
  s.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();ev=low.evaluated_get(dg);em=ev.to_mesh();bottom=min((ev.matrix_world@v.co).z for v in em.vertices);ev.to_mesh_clear()
  lift=max(0,.005-bottom)
  if lift:
   pb=rig.pose.bones['death_pivot'];pb.location+=rest['death_pivot'].to_3x3().inverted()@Vector((0,0,lift));pb.keyframe_insert('location',frame=f)
  lifts.append(lift)
 report['ground_correction_max_m'][name]=max(lifts)
# Source file contains packed PBR textures and editable per-bone action keys.
rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];s.frame_start=1;s.frame_end=91;s.frame_set(1)
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'PoisonMaggot_Animated.blend'))
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
kw=dict(use_selection=True,path_mode='COPY',embed_textures=False,add_leaf_bones=False,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.fbx(filepath=str(out/'SK_PoisonMaggot.fbx'),bake_anim=False,**kw)
for n,d in contracts.items():
 a=bpy.data.actions[n];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];s.frame_end=round(d*30)+1;s.frame_set(1)
 bpy.ops.export_scene.fbx(filepath=str(out/f'A_PoisonMaggot_{n}.fbx'),bake_anim=True,**kw)
(out/'rig_animation.json').write_text(json.dumps(report,indent=2));print('MAGGOT_RIG_EXPORT_COMPLETE',flush=True)
