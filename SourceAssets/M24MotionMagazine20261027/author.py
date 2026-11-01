"""M24 native V9 motion and extended magazine production; no preview/test run."""
import bpy, json, math, ast, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).resolve().parent; X=O/'Exports'; (X/'Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
s=bpy.context.scene; r=bpy.data.objects['M24_V9_Rig']; skin=bpy.data.objects['M24_V9_BareArms']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}; parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
for file,names in [('M24CustomScope20261026/author_gameplay.py',('under','twists')),('M24Hold20261027/author_hold.py',('bake',))]:
 tree=ast.parse((O.parent/file).read_text())
 for name in names:exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
report={'clips':{},'fps':30,'source':'M24ActionLayout20261027/M24_ActionLayout_Editable.blend',
 'shared':['idle','aim'],'magazine_extension_m':.045,'runtime_tested':False,
 'events_frames':{'mag_out':21,'mag_insert':38,'mag_seat':40,'charge_start':54,'charge_pull':77,'charge_release':94}}
def clone(row):return {n:m.copy() for n,m in row.items()}
def ease(t):
 t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def blend(a,b,t):return {n:a[n].lerp(b[n],t) for n in a}
def sample(role):
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rows=[]
 for f in range(round(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return rows
roles=('equip','fire','reload','reload_empty','cycle','inspect','quick_melee')
clips={role:sample(role) for role in roles}; idle=sample('aim')[0]

def arm(row,side,D):
 old=clone(row);u,l,h='upperarm_'+side,'lowerarm_'+side,'hand_'+side
 shoulder=old[u].translation.copy();elbow=old[l].translation;wrist=old[h].translation;goal=(D@old[h]).translation
 a=(elbow-shoulder).length;b=(wrist-elbow).length;axis=goal-shoulder
 if axis.length>.985*(a+b):shoulder+=axis.normalized()*(axis.length-.985*(a+b))
 axis=goal-shoulder;d=max(axis.length,abs(a-b)+1.e-6);axis.normalize()
 pole=elbow-shoulder;pole-=axis*pole.dot(axis);pole.normalize()
 along=(a*a-b*b+d*d)/(2*d);ep=shoulder+axis*along+pole*math.sqrt(max(0,a*a-along*along))
 uq=(elbow-old[u].translation).rotation_difference(ep-shoulder)@old[u].to_quaternion()
 lq=(wrist-elbow).rotation_difference(goal-ep)@old[l].to_quaternion()
 um=Matrix.LocRotScale(shoulder,uq,Vector((1,1,1)));lm=Matrix.LocRotScale(ep,lq,Vector((1,1,1)))
 for n in row:
  if under(n,h):row[n]=D@old[n]
  elif under(n,l):row[n]=lm@old[l].inverted()@old[n]
  elif under(n,u):row[n]=um@old[u].inverted()@old[n]
 row['clavicle_'+side].translation+=shoulder-old[u].translation
def held(row,D):
 for side in ('l','r'):arm(row,side,D)
 for n in row:
  if n.startswith('WPN_'):row[n]=D@row[n]
 return row

# Smooth the original approach and settle intervals, with exact original event frames.
# Do not alter the bolt-contact portion or any mechanical bone timing.
for role in ('fire','reload','reload_empty','cycle'):
 rows=clips[role];start=len(rows)-7;pose=clone(rows[start])
 for f in range(start,len(rows)):rows[f]=blend(pose,idle,ease((f-start)/6))
 if role!='fire':
  pose=clone(rows[6])
  for f in range(7):rows[f]=blend(idle,pose,ease(f/6))
# Ease the full equip path from its retained low-right entry without moving the hold.
original=clips['equip'];clips['equip']=[]
for f in range(len(original)):
 t=ease(f/(len(original)-1))*(len(original)-1);i=min(int(t),len(original)-2)
 clips['equip'].append(blend(original[i],original[i+1],t-i))
# Keep inspection low: the previous lift brought the scope toward the center.
for f,row in enumerate(clips['inspect']):
 w=math.sin(math.pi*f/(len(clips['inspect'])-1))**2
 held(row,Matrix.Translation((.015*w,.012*w,-.018*w)))
# Longer eased melee recovery; preserve windup and the frame-5 hit contract.
rows=clips['quick_melee'];a=clone(rows[10])
for f in range(10,len(rows)):rows[f]=blend(a,idle,ease((f-10)/(len(rows)-11)))

# The donor uses a bottom-cup grasp. Extend only below the original neck;
# move the whole support hand to the new floorplate during the contact interval.
extension=.045
for role in ('reload','reload_empty'):
 rows=[clone(p) for p in clips[role]]
 for f,row in enumerate(rows):
  w=ease((f-8)/7)*(1-ease((f-42)/8))
  delta=(row['WPN_Magazine']@rest['WPN_Magazine'].inverted()).to_3x3()@Vector((0,0,-extension*w))
  if w:arm(row,'l',Matrix.Translation(delta))
 clips[role+'_mag10']=rows

# Camera-space authoring from the saved accepted hip calibration. X forward,
# Y right, Z up. Raise the muzzle outside the central view with a fixed right grip.
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
pivot=C@idle['hand_r'].translation
def sprint(t,phase=0,loop=False):
 row=clone(idle);w=ease(t)
 rot=Matrix.Rotation(math.radians(-54)*w,4,'Y')@Matrix.Rotation(math.radians(8)*w,4,'Z')
 bob=Vector((.35*math.sin(phase),.30*math.sin(phase),.45*math.cos(2*phase))) if loop else Vector((0,0,0))
 dc=Matrix.Translation(Vector((1,7,-3))*w+bob)@Matrix.Translation(pivot)@rot@Matrix.Translation(-pivot)
 D=C.inverted()@dc@C
 arm(row,'r',D)
 for n in row:
  if n.startswith('WPN_'):row[n]=D@row[n]
 # Release before the muzzle rises, return after it lowers. Pump below the view.
 release=ease(t/.7)
 goal=Vector((-.17,.07,-.18))
 if loop:goal+=Vector((.008*math.sin(phase),.055*math.sin(phase),.025*math.cos(phase)))
 target=idle['hand_l'].translation.lerp(goal,release)
 ld=Matrix.Translation(target)@Matrix.Rotation(-.22*release,4,'Y')@Matrix.Rotation(.30*release,4,'X')@Matrix.Translation(-idle['hand_l'].translation)
 arm(row,'l',ld)
 # Loosen the supporting fingers after release, using native local axes.
 old=clone(row)
 for b in r.data.bones:
  n=b.name
  if n!='hand_l' and under(n,'hand_l'):
   local=old[parents[n]].inverted()@old[n]
   row[n]=row[parents[n]]@local.lerp(local_rest[n],.35*release)
 return row
clips['sprint_enter']=[sprint(f/15) for f in range(16)]
clips['sprint_loop']=[sprint(1,2*math.pi*f/30,True) for f in range(31)]
clips['sprint_exit']=[sprint(1-f/12) for f in range(13)]

def export(path,obs,anim=False):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=r if r in obs else obs[0];bpy.context.view_layer.update()
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',
  add_leaf_bones=False,bake_anim=anim,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
  mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
for role,rows in clips.items():
 old=bpy.data.actions.get('A_M24_'+role);r.animation_data.action=None
 if old:bpy.data.actions.remove(old)
 bake(role,rows);path=X/'Animations'/('A_M24_'+role+'.fbx');export(path,[r],True);report['clips'][role]['file']=str(path)

r.animation_data.action=None
for pb in r.pose.bones:pb.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
mag=bpy.data.objects['M24_clip'];mat=mag.data.materials[0].copy();mat.name='M24_Magazine5'
mag.data.materials.clear();mag.data.materials.append(mat)
# Split the source walls at a flat section and insert a real continuous band.
# Keep the entire floorplate/detail assembly rigid. Interpolate original corner
# attributes at the cut; original UVs are never stretched across the new band.
cut=.042;verts=[];faces=[];uvs=[];normals=[];indices=[]
def face(points,material=0):
 if len(points)<3:return
 faces.append(tuple(range(len(verts),len(verts)+len(points))))
 for p,uv,n in points:verts.append(tuple(p));uvs.append(tuple(uv));normals.append(tuple(n))
 indices.append(material)
def clip(poly,upper):
 result=[];intersections=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ina=(a[0].z>=cut) if upper else (a[0].z<=cut)
  inb=(b[0].z>=cut) if upper else (b[0].z<=cut)
  if ina:result.append(a)
  if ina!=inb:
   t=(cut-a[0].z)/(b[0].z-a[0].z)
   point=(a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized())
   result.append(point);intersections.append(point)
 return result,intersections
for p in mag.data.polygons:
 poly=[(mag.data.vertices[mag.data.loops[i].vertex_index].co.copy(),mag.data.uv_layers.active.data[i].uv.copy(),mag.data.corner_normals[i].vector.copy()) for i in p.loop_indices]
 upper,hits=clip(poly,True);lower,_=clip(poly,False)
 face(upper);face([(v-Vector((0,0,extension)),uv,n) for v,uv,n in lower])
 if len(hits)==2:
  a,b=hits;pa,pb=a[0],b[0];down=Vector((0,0,extension))
  positions=[pa,pb,pb-down,pa-down]
  if (pb-pa).cross(-down).dot(p.normal)<0:positions.reverse()
  n=(positions[1]-positions[0]).cross(positions[2]-positions[0]).normalized()
  width=(pb-pa).length/.02;height=extension/.02
  face([(v,Vector(uv),n) for v,uv in zip(positions,((0,0),(width,0),(width,height),(0,height)))],1)
data=bpy.data.meshes.new('M24_Magazine10_ContinuousShell');data.from_pydata(verts,[],faces);data.update()
layer=data.uv_layers.new(name='UVMap')
for i,uv in enumerate(uvs):layer.data[i].uv=uv
data.materials.append(mat)
band=bpy.data.materials.new('M24_ExtensionSteel');band.use_nodes=True
bsdf=next(n for n in band.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=(.034,.036,.039,1);bsdf.inputs['Metallic'].default_value=1;bsdf.inputs['Roughness'].default_value=.39
data.materials.append(band)
for p,m in zip(data.polygons,indices):p.material_index=m;p.use_smooth=True
data.normals_split_custom_set(normals)
ext=bpy.data.objects.new('M24_Magazine10',data);s.collection.objects.link(ext)
mod=json.loads((O.parent/'M24Modular20261027/authoring.json').read_text())
removed={n for row in mod['models'].values() for n in row['objects']}
obs=[ob for ob in s.objects if ob.type=='MESH' and ob.name not in removed and ob!=ext]
mesh=X/'SK_M24_MotionV9.fbx';export(mesh,[r,*obs]);report['mesh']=str(mesh)
path=X/'SM_M24_m24_extended_mag_10.fbx';export(path,[ext]);report['magazine_mesh']=str(path)
report['magazine']={'factory_height_m':max(v.co.z for v in mag.data.vertices)-min(v.co.z for v in mag.data.vertices),
 'extended_height_m':max(v.co.z for v in ext.data.vertices)-min(v.co.z for v in ext.data.vertices),
 'protected_above_z_m':cut,'floorplate_translation_m':-extension,'material_slot':'M24_Magazine5',
 'extension_surface':'continuous cut-and-bridge wall; independent UV band; original loop normals and UVs retained',
 'attachment_bone':'WPN_Magazine','hand_contact':'floorplate cup; extended reload sparse left-arm correction',
 'static_space':'full native rifle reference, FBX -Y/Z; same registration as existing M24 parts'}
ext.hide_render=True;ext.hide_set(True)
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_MotionMagazine_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_MOTION_MAGAZINE_EXPORTED',len(report['clips']),flush=True)
