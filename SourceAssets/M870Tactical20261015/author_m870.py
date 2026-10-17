"""Bind the supplied M870 to V7 arms and author its pump/feed actions."""
import bpy,bmesh,json,math,bisect
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;P=O.parents[1];X=O/'Exports';X.mkdir(exist_ok=True);(X/'Animations').mkdir(exist_ok=True)
D=json.loads((O/'Donor/animation_inputs.json').read_text())
A=json.loads((P/'SourceAssets/Super90QuickMelee20261008/LeftArmR5/author_space.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/Super90LocomotionIdleGrip20261010/Super90_Locomotion_IdleGrip_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['SK_Super90'];s.render.fps=60
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};I=Matrix.Identity(4)
Ci=Matrix(A['conversion']['C']).inverted();E=Matrix(A['conversion']['E']);Ki={n:Matrix(m).inverted() for n,m in A['conversion']['K'].items()}
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:]))
def decode(row):
 w={}
 for n in D['names']:w[n]=w.get(D['parents'][n],I)@matrix(row[n])
 return {n:E@Ci@w[n]@Ki[n] for n in rest}
clips={k:[decode(v) for v in c['rows']] for k,c in D['clips'].items()}
idle=clips['idle'][0];gun_rest=rest['WPN_root'];gun_inverse=idle['WPN_root'].inverted()
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
def mix(a,b,w):
 pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
 return Matrix.LocRotScale(pa.lerp(pb,w),qa.slerp(qb,w),sa.lerp(sb,w))
def ease(v):v=max(0.,min(1.,v));return v*v*(3-2*v)
def pulse(t,a,b,c,d):return ease((t-a)/(b-a))*(1-ease((t-c)/(d-c)))
def relocate_hand(row,side,target):
 """Move the complete hand using a two-bone arm and the donor elbow plane."""
 old={n:m.copy() for n,m in row.items()};un='upperarm_'+side;ln='lowerarm_'+side;hn='hand_'+side
 shoulder=old[un].translation;elbow=old[ln].translation;wrist=old[hn].translation;goal=target.translation
 l1=(elbow-shoulder).length;l2=(wrist-elbow).length;axis=goal-shoulder;distance=axis.length
 if distance>l1+l2-.006:
  shift=axis.normalized()*(distance-(l1+l2-.006));shoulder+=shift
  row['clavicle_'+side].translation+=shift;axis=goal-shoulder;distance=axis.length
 axis.normalize();plane=elbow-shoulder;plane-=axis*plane.dot(axis)
 if plane.length<1e-6:plane=Vector((-1 if side=='l' else 1,0,-1)).cross(axis)
 plane.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*max(distance,1e-6));height=math.sqrt(max(0,l1*l1-along*along));new_elbow=shoulder+axis*along+plane*height
 qu=(elbow-old[un].translation).rotation_difference(new_elbow-shoulder);qf=(wrist-elbow).rotation_difference(goal-new_elbow)
 upper_delta=Matrix.Translation(shoulder)@qu.to_matrix().to_4x4()@Matrix.Translation(-old[un].translation)
 fore_delta=Matrix.Translation(new_elbow)@qf.to_matrix().to_4x4()@Matrix.Translation(-elbow)
 hand_delta=target@old[hn].inverted()
 for n in row:
  if under(n,hn):row[n]=hand_delta@old[n]
  elif under(n,ln):row[n]=fore_delta@old[n]
  elif under(n,un):row[n]=upper_delta@old[n]

# Keep the installed skin and its repaired palm topology. Transport the FBX
# import's bone axes to the retained author bind instead of copying rotations.
for ob in list(s.objects):
 if ob!=r:bpy.data.objects.remove(ob,do_unlink=True)
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(O/'Donor/installed_super90.fbx'),use_anim=False)
imported=[o for o in bpy.data.objects if o not in before];dr=next(o for o in imported if o.type=='ARMATURE')
dre={b.name:dr.matrix_world@b.matrix_local for b in dr.data.bones};arms=[];shells=[]
for ob in imported:
 if ob.type!='MESH':continue
 names={g.index:g.name for g in ob.vertex_groups}
 for role in ('skin','shell'):
  keep=[]
  for p in ob.data.polygons:
   mat=ob.data.materials[p.material_index];n=mat.name if mat else ''
   is_skin=any(x in n.lower() for x in ('skin','manny','barearm'))
   is_shell=(n.split('.')[0]=='12gauge' or n.split('.')[0].endswith('_12gauge')) and all(any(names[g.group]=='WPN_Shell' and g.weight>.5 for g in ob.data.vertices[vi].groups) for vi in p.vertices)
   if (role=='skin' and is_skin) or (role=='shell' and is_shell):keep.append(p.index)
  if not keep:continue
  out=ob.copy();out.data=ob.data.copy();s.collection.objects.link(out);out.name='M870_V7' if role=='skin' else 'M870_ReloadShell'
  bm=bmesh.new();bm.from_mesh(out.data);bm.faces.ensure_lookup_table();wanted=set(keep);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in wanted],context='FACES');bm.to_mesh(out.data);bm.free()
  for v in out.data.vertices:
   source=ob.matrix_world@v.co;influences=[(g.weight,names[g.group]) for g in v.groups if names[g.group] in rest and names[g.group] in dre];total=sum(w for w,n in influences)
   if total:v.co=sum((rest[n]@dre[n].inverted()@source*w for w,n in influences),Vector())/total
  out.parent=r;out.matrix_parent_inverse=I;out.matrix_basis=I;out.modifiers.clear();out.modifiers.new('M870 V7 native skin','ARMATURE').object=r
  (arms if role=='skin' else shells).append(out)
for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
if not arms:raise RuntimeError('Installed V7 arm surfaces were not exported')

# Use the FBX's own UVs and complete connected shells. Source units are 10x
# metres: 9.943 units becomes 0.9943 m, with the trigger as the assembly anchor.
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Original/Source/source/M870_Tactical.fbx'))
source=next(o for o in bpy.data.objects if o not in before and o.type=='MESH')
scale=.1;offset=Vector((0,.01068,-.7970));source_to_author=Matrix.Translation(offset)@Matrix.Scale(scale,4)
geometry=json.loads((O/'source_geometry.json').read_text())[0]
roles={};groups={};part_indices={};bolt_islands={8,46,111,200,240,241,242,243,244};trigger_islands={17,73,74}
for idx,island in enumerate(geometry['islands']):
 lo,hi=island['lo'],island['hi'];pump=(lo[1]>=1.209 and hi[1]<=3.088 and hi[2]<=.604) or (lo[1]>=.175 and hi[1]<=1.627 and lo[2]>=.445 and hi[2]<=.548)
 role='pump' if pump else 'bolt' if idx in bolt_islands else 'trigger' if idx in trigger_islands else 'loading_gate' if idx in {9,14,51,79,80} else 'body'
 groups.setdefault(role,set()).update(island['ids']);part_indices.setdefault(role,[]).append(idx)
for v in source.data.vertices:v.co=source_to_author@(source.matrix_world@v.co)
source.matrix_world=I
source.data.materials[0].name='M870_OriginalSurface';mat=source.data.materials[0];mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for key,stem in [('Base Color','Albedo'),('Metallic','Metalic'),('Roughness','Roughness'),('Normal','Normal')]:
 tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'Original/Source/textures'/('M870_Tactical_'+stem+'.png')),check_existing=True);tex.image.colorspace_settings.name='sRGB' if key=='Base Color' else 'Non-Color'
 if key=='Normal':
  normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
 else:mat.node_tree.links.new(tex.outputs['Color'],bs.inputs[key])
parts=[]
for role,ids in groups.items():
 ob=source.copy();ob.data=source.data.copy();s.collection.objects.link(ob);ob.name='M870_'+role
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(ob.data);bm.free()
 bone={'pump':'WPN_bolt','bolt':'WPN_bolt','trigger':'WPN_Trigger','loading_gate':'WPN_Load','body':'WPN_root'}[role]
 ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE');ob.parent=r;ob.matrix_parent_inverse=I;ob.matrix_basis=I;ob.modifiers.clear();ob.modifiers.new('M870 mechanism','ARMATURE').object=r;parts.append(ob)
 roles[role]=dict(bone=bone,vertices=len(ob.data.vertices),islands=part_indices[role])
bpy.data.objects.remove(source,do_unlink=True)

markers={'WPN_SOCKET_Muzzle':(0,4.985,.6653),'WPN_SOCKET_Eject':(.15,-.32,.66),'WPN_RearSight':(0,-.927,.960),'WPN_FrontSight':(0,4.386,.9365),'WPN_ChargingHandle':(-.18,2.0,.38),'WPN_BoltCatch':(-.10,-1.05,.26),'WPN_SOCKET_Magazine':(0,-.35,.25)}
bpy.context.view_layer.objects.active=r;r.select_set(True);r.animation_data.action=None;bpy.ops.object.mode_set(mode='EDIT')
for n,p in markers.items():
 bone=r.data.edit_bones[n];m=rest[n].copy();m.translation=source_to_author@Vector(p);bone.matrix=m;bone.length=.01
bpy.ops.object.mode_set(mode='OBJECT');rest={b.name:b.matrix_local.copy() for b in r.data.bones}

# Traditional stock wrist: rotate the whole grip around the index knuckle,
# retaining the trigger finger relationship. The arm solver carries the wrist.
reference={n:gun_rest@gun_inverse@m for n,m in idle.items()};pivot=reference['index_01_r'].translation
right_delta=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-50),4,'X')@Matrix.Translation(-pivot)
left_delta=Matrix.Translation((0,.070,.020));shell_delta=left_delta
def adapt(raw):
 row={n:m.copy() for n,m in raw.items()};gm=row['WPN_root']@gun_rest.inverted();gi=gm.inverted()
 relocate_hand(row,'r',gm@right_delta@gi@row['hand_r'])
 relocate_hand(row,'l',gm@left_delta@gi@row['hand_l'])
 row['WPN_Shell']=gm@shell_delta@gi@row['WPN_Shell']
 for n in markers:row[n]=gm@rest[n]
 for n in ('WPN_bolt','WPN_Load','WPN_Trigger'):row[n]=gm@rest[n]
 return row
adapted_idle=adapt(idle)
def pump(row,amount):
 gm=row['WPN_root']@gun_rest.inverted();delta=gm@Matrix.Translation((0,-.105*amount,0))@gm.inverted()
 row['WPN_bolt']=delta@row['WPN_bolt'];relocate_hand(row,'l',delta@row['hand_l'])
 return row
def hinge(row,bone,source_pivot,angle):
 gm=row['WPN_root']@gun_rest.inverted();pivot=source_to_author@Vector(source_pivot)
 delta=gm@Matrix.Translation(pivot)@Matrix.Rotation(angle,4,'X')@Matrix.Translation(-pivot)@gm.inverted()
 row[bone]=delta@row[bone]
 return row
def blend_rows(a,b,w):return {n:mix(a[n],b[n],w) for n in a}
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=r
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()};authored={}
def bake(role,rows):
 s.render.fps=60;s.render.fps_base=1.0
 action=bpy.data.actions.new('A_M870_'+role);action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action
 for b in r.pose.bones:
  b.rotation_mode='QUATERNION'
  for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
 curves={(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves};values={n:[] for n in rest};previous={}
 for row in rows:
  for n in rest:
   local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];v,q,sc=(local_rest[n].inverted()@local).decompose()
   if n in previous and q.dot(previous[n])<0:q.negate()
   previous[n]=q.copy();values[n].append((v,q,sc))
 for n in rest:
  for prop,k,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   for axis in range(count):
    curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(rows));curve.keyframe_points.foreach_set('co',[v for i,row in enumerate(values[n]) for v in (i,row[k][axis])])
    for key in curve.keyframe_points:key.interpolation='LINEAR'
    curve.update()
 s.frame_start=0;s.frame_end=len(rows)-1;r.animation_data.action_slot=action.slots[0];s.frame_set(0);select([r]);file=X/'Animations'/('A_M870_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 authored[role]=dict(file=str(file),duration=(len(rows)-1)/60,action=action.name);print('M870_AUTHORED',role,len(rows),flush=True)
for role in ('idle','walk','run','equip','quick_melee'):bake(role,[adapt(row) for row in clips[role]])
fire=[]
for f in range(55):
 t=f/60;row={n:m.copy() for n,m in adapted_idle.items()};w=pulse(t,0,.045,.065,.23)
 pivot=row['hand_r'].translation;delta=Matrix.Translation((0,-.025*w,0))@Matrix.Translation(pivot)@Matrix.Rotation(.035*w,4,'X')@Matrix.Translation(-pivot)
 for n in row:
  if n!='VM_Root':row[n]=delta@row[n]
 hinge(row,'WPN_Trigger',(0,-1.47,.245),-.12*pulse(t,0,.035,.075,.16))
 fire.append(pump(row,pulse(t,.16,.35,.40,.62)))
bake('fire',fire)
for role in ('reload_continuous','reload_full'):
 rows=[adapt(row) for row in clips[role][:361]];empty=role=='reload_full'
 for f,row in enumerate(rows):
  t=f/60;opening=max(pulse(t,44/60+i*50/60-.14,44/60+i*50/60-.035,44/60+i*50/60+.045,44/60+i*50/60+.18) for i in range(7))
  hinge(row,'WPN_Load',(0,-.697,.30),.42*opening)
 start=rows[-1]
 for f in range(361,425 if empty else 400):
  t=f/60;row=blend_rows(start,adapted_idle,ease((t-6)/.30))
  if empty:pump(row,pulse(t,6.30,6.43,6.48,6.62))
  rows.append(row)
 bake(role,rows)
cycle=[]
for f in range(65):cycle.append(pump({n:m.copy() for n,m in adapted_idle.items()},pulse(f/60,.12,.35,.40,.62)))
bake('cycle',cycle)
inspect=[]
for f in range(151):
 t=f/60;w=pulse(t,0,.70,1.55,2.50);p=adapted_idle['hand_r'].translation;delta=Matrix.Translation(p)@Matrix.Rotation(-.38*w,4,'Y')@Matrix.Rotation(.14*w,4,'X')@Matrix.Translation(-p)
 inspect.append({n:delta@m if n!='VM_Root' else m.copy() for n,m in adapted_idle.items()})
bake('inspect',inspect)
for role,count in [('sprint_enter',25),('sprint_loop',61),('sprint_exit',25)]:
 rows=[]
 for f in range(count):
  w=ease(f/(count-1)) if role=='sprint_enter' else 1-ease(f/(count-1)) if role=='sprint_exit' else 1.
  p=adapted_idle['hand_r'].translation;delta=Matrix.Translation((0,-.04*w,-.15*w))@Matrix.Translation(p)@Matrix.Rotation(-.28*w,4,'X')@Matrix.Translation(-p)
  rows.append({n:delta@m if n!='VM_Root' else m.copy() for n,m in adapted_idle.items()})
 bake(role,rows)

# The same skeleton/bind supports the existing fitted Super90 equipment meshes;
# only the held pose and M870 marker bones differ. No outfit sequence copies.
r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=I
s.frame_set(0)
for ob in parts+arms+shells:
 select([ob]);bpy.context.view_layer.objects.active=ob;bpy.ops.object.material_slot_remove_unused()
 tri=ob.modifiers.new('Stable export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
select([r]+parts+arms+shells)
mesh_file=X/'SK_M870_V7.fbx'
bpy.ops.export_scene.fbx(filepath=str(mesh_file),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
select(parts);world_file=X/'SM_M870.fbx'
bpy.ops.export_scene.fbx(filepath=str(world_file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
r.animation_data.action=bpy.data.actions[authored['idle']['action']];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=len(clips['idle'])-1;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_Gameplay_Editable.blend'))
report=dict(mesh=str(mesh_file),world_mesh=str(world_file),parts=roles,clips=authored,source_scale=scale,source_offset=list(offset),markers={n:list(source_to_author@Vector(p)) for n,p in markers.items()},pump_travel_m=.105,fire_clock=dict(pull=.16,eject=.35,forward=.40,closed=.62,end=.9),reload_clock=dict(insert=44/60,step=50/60,tail=6,closed=6.62,end=424/60),runtime_tested=False)
(O/'authoring.json').write_text(json.dumps(report,indent=2))
