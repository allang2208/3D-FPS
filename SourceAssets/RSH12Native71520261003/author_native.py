"""Restore native 715 arms, grasp and all action tracks on RSH-12.

Original animations remain shared. Private sparse profiles transport the
mechanical pivots and contact paths; no gameplay or acceptance runs.
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
B=O.parent/'RSH12Integration20261003'
SIDE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
OUT=O/('Single' if SIDE=='single' else 'Dual/'+SIDE);OUT.mkdir(parents=True,exist_ok=True)
D=json.loads((O.parent/'RSH12Grip20261003'/('native_'+SIDE+'.json')).read_text())
raw=json.loads((B/'canonical_parts.json').read_text())
FIT=json.loads((O.parent/'RSH12Fit20261003/fit_contract.json').read_text())
SHELLS=json.loads((O.parent/'RSH12Fit20261003/part_shells.json').read_text())
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=str(B/'RSH12_Original.blend'))
source=bpy.data.objects['10_l'];axes=Matrix(((0,0,1,0),(1,0,0,0),(0,1,0,0),(0,0,0,1)))
cm=Matrix.Diagonal((.001,.001,.001,1))@axes
cartridge=dict(name='Cartridge',verts=[list(cm@v.co) for v in source.data.vertices],
 faces=[list(p.vertices) for p in source.data.polygons],uv=[list(v.uv) for v in source.data.uv_layers.active.data],
 normals=[list((cm.to_3x3()@n.vector).normalized()) for n in source.data.corner_normals])
adj=[set() for _ in cartridge['verts']]
for face in cartridge['faces']:
 for i in face:adj[i].update(face)
seen=set();shells=[]
for i in range(len(adj)):
 if i in seen:continue
 stack=[i];seen.add(i);ids=[]
 while stack:
  k=stack.pop();ids.append(k)
  for j in adj[k]:
   if j not in seen:seen.add(j);stack.append(j)
 shells.append(ids)
tip=set(shells[0]);vv=[Vector(v) for v in cartridge['verts']]
tipmean=sum(vv[i].y for i in tip)/len(tip)
othermean=sum(v.y for i,v in enumerate(vv) if i not in tip)/(len(vv)-len(tip))
if tipmean>othermean:
 cm=Matrix.Rotation(math.pi,4,'Z')
 cartridge['verts']=[list(cm@v) for v in vv]
 cartridge['normals']=[list(cm.to_3x3()@Vector(n)) for n in cartridge['normals']]
vv=[Vector(v) for v in cartridge['verts']]
shift=Vector((-(min(v.x for v in vv)+max(v.x for v in vv))*.5,
 FIT['rear_plane_m']+1e-5-FIT['cartridge_rim_y_m'],-(min(v.z for v in vv)+max(v.z for v in vv))*.5))
cartridge['verts']=[list(v+shift) for v in vv]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(B/'Donor'/SIDE/'SK_DW715_Donor.fbx'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE');r.animation_data_clear()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};root=rest['WPN_root'];ri=root.inverted()
parent=D['parents'];names=list(D['rest'])
hands=[]
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 wg={g.index for g in ob.vertex_groups if g.name.startswith('WPN_')}
 remove={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in wg)>.5}
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in remove],context='VERTS');bm.to_mesh(ob.data);bm.free()
 if not len(ob.data.vertices):bpy.data.objects.remove(ob,do_unlink=True);continue
 ob.name='RSH12_NativeBareArms_'+ob.name;hands.append(ob)
 # Keep the original Manny slot contract used by world and inventory filters.
 for mat in ob.data.materials:
  if mat and 'Manny' not in mat.name:mat.name='Manny_'+mat.name
occupied=bpy.data.objects.get('SK_DW715_Manny')
if occupied and occupied!=r:occupied.name='RSH12_DonorRootContainer'
r.name='SK_DW715_Manny'
trigger=Vector((0,.086,.011))
alignment=Matrix.Translation((ri@rest['WPN_Trigger']).translation-trigger)
grip_source=O.parent/'RSH12Grip20261003';sys.path.insert(0,str(grip_source))
# Native 715 hand, wrist and arm transforms are preserved verbatim.
contact=json.loads((O/'grip_registration.json').read_text())
original_alignment=alignment.copy();alignment=alignment@Matrix(contact['registration'])
cx,cz,radius=FIT['cylinder_axis_xz_radius']
center=Vector((cx,FIT['cylinder_middle_m'],cz))
points={'WPN_Trigger':trigger,'WPN_Crane':Vector((.006,.010,.035)),
 'WPN_Cylinder':center,'WPN_Extractor':Vector((cx,FIT['rear_plane_m'],cz)),
 'WPN_Hammer':Vector((0,.119,.040)),'WPN_SOCKET_Muzzle':Vector((-.00045,-.16369,.03569)),
 'WPN_FrontSight':Vector((0,-.142,.084)),'WPN_RearSight':Vector((0,.096,.084)),
 'WPN_SOCKET_Eject':Vector((cx,FIT['rear_plane_m'],cz)), 'WPN_SOCKET_Magazine':center}
chambers=[]
for i in range(5):
 x,z,_=FIT['chambers'][i]['center_xz_radius']
 p=Vector((x,center.y,z))
 chambers.append(p);points['WPN_Case_'+str(i)]=p;points['WPN_Round_'+str(i)]=p
newrest={n:m.copy() for n,m in rest.items()}
orientation_correction=root.to_quaternion()@Matrix(contact['registration']).to_quaternion()@root.to_quaternion().inverted()
for n,p in points.items():
 newrest[n]=Matrix.LocRotScale(root@(alignment@p),orientation_correction@rest[n].to_quaternion(),rest[n].to_scale())
mat=bpy.data.materials.new('M_RSH12_SourcePBR');mat.use_nodes=True
mapping={'4_l':'WPN_Crane','6_l':'WPN_Cylinder','12_l':'WPN_root','13_l':'WPN_Extractor','8_l':'WPN_Hammer','17_l':'WPN_Trigger'}
gun=[]
def make(part,bone,offset=Vector(),ids=None,rotation=None):
 rotation=rotation or Matrix.Identity(4)
 verts=[rotation@Vector(v)+offset for v in part['verts']]
 if ids is None:ids=set(range(len(verts)))
 ordered=sorted(ids);remap={j:i for i,j in enumerate(ordered)};faces=[];uv=[];norm=[];cursor=0
 for face in part['faces']:
  if all(j in ids for j in face):
   faces.append([remap[j] for j in face]);uv.extend(part['uv'][cursor:cursor+len(face)]);norm.extend(part['normals'][cursor:cursor+len(face)])
  cursor+=len(face)
 # Transport geometry inversely; the sparse pose applies the matching new pivot.
 bind=rest[bone]@newrest[bone].inverted()@root@alignment
 mesh=bpy.data.meshes.new(part['name']+'_'+bone);mesh.from_pydata([bind@verts[j] for j in ordered],[],faces);mesh.update()
 ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
 mesh.materials.append(mat);layer=mesh.uv_layers.new(name='UVMap')
 for a,b in zip(layer.data,uv):a.uv=b
 for poly in mesh.polygons:poly.use_smooth=True
 mesh.normals_split_custom_set([(bind.to_3x3().inverted().transposed()@rotation.to_3x3()@Vector(n)).normalized() for n in norm])
 group=ob.vertex_groups.new(name=bone);group.add(list(range(len(ordered))),1.,'REPLACE')
 mod=ob.modifiers.new('Native715Binding','ARMATURE');mod.object=r;ob.parent=r
 gun.append(ob);return ob
for part in raw:
 if part['name']=='10_l':continue
 if part['name']=='4_l':
  for shell in SHELLS['4_l']:
   # The front coaxial rod retracts with the rear extractor plate; the yoke stays on the crane.
   bone='WPN_Extractor' if shell['min'][1]<-.018 else 'WPN_Crane'
   make(part,bone,ids=set(shell['ids']))
  continue
 make(part,mapping.get(part['name'],'WPN_root'))
for i,c in enumerate(chambers):
 offset=Vector((c.x,0,c.z))
 # Match the source's twelve-sided cases to each bore's independently rotated facets.
 angle=FIT['cartridge_facet_phase']-FIT['chambers'][i]['facet_phase']
 rotation=Matrix.Rotation(angle,4,'Y')
 make(cartridge,'WPN_Round_'+str(i),offset,tip,rotation)
 make(cartridge,'WPN_Case_'+str(i),offset,set(range(len(vv)))-tip,rotation)

def matrix(v):
 return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def pack(m):
 p,q,s=m.decompose();return [*p,q.x,q.y,q.z,q.w,*s]
oldworld={n:matrix(v) for n,v in D['rest'].items()};desired={n:m.copy() for n,m in oldworld.items()}
S=Matrix.Diagonal((1,-1,1,1))
for n in points:
 # The native FBX uses meters; UE component transforms use centimeters.
 desired[n]=Matrix.LocRotScale((S@r.matrix_world@newrest[n]).translation*100,
  (S@r.matrix_world@newrest[n]@S).to_quaternion(),desired[n].to_scale())
oldlocal={n:oldworld[parent[n]].inverted()@m if parent[n] in oldworld else m for n,m in oldworld.items()}
newlocal={n:desired[parent[n]].inverted()@m if parent[n] in desired else m for n,m in desired.items()}
canonical_to_world=S@r.matrix_world@root@alignment
original_canonical_cm=Matrix.Diagonal((100,100,100,1))@S@r.matrix_world@root@original_alignment
bore_axis=(desired['WPN_Cylinder'].inverted().to_3x3()@canonical_to_world.to_3x3()@Vector((0,1,0))).normalized()
changed=set(points);previous_angle={};records=[];idle_contacts={}
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
for kind,clip in D['clips'].items():
 tracks={n:[] for n in changed};times=[];prevangle=None
 for row in clip['samples']:
  t=row['time'];times.append(t);base={n:matrix(v) for n,v in row['local'].items()};local={n:m.copy() for n,m in base.items()}
  for n in changed:
   local[n].translation+=newlocal[n].translation-oldlocal[n].translation
   local[n]=Matrix.LocRotScale(local[n].translation,
    newlocal[n].to_quaternion()@oldlocal[n].to_quaternion().inverted()@base[n].to_quaternion(),local[n].to_scale())
   if n.startswith('WPN_Case_'):
    displacement=base[n].translation-oldlocal[n].translation
    # Keep the longer clearing stroke on the actual bore axis, with an exact seated endpoint.
    local[n]=Matrix.LocRotScale(newlocal[n].translation+bore_axis*displacement.dot(bore_axis)*1.3,
      newlocal[n].to_quaternion(),local[n].to_scale())
  n='WPN_Cylinder';q0=oldlocal[n].to_quaternion();dq=q0.inverted()@base[n].to_quaternion()
  if dq.w<0:dq.negate()
  axis,angle=dq.to_axis_angle();signed=angle*(1 if axis.z>=0 else -1)
  if prevangle is not None:
   while signed-prevangle>math.pi:signed-=math.tau
   while signed-prevangle<-math.pi:signed+=math.tau
  prevangle=signed
  local[n]=Matrix.LocRotScale(local[n].translation,newlocal[n].to_quaternion()@Quaternion(bore_axis,signed*1.2),local[n].to_scale())
  # Build the changed hierarchy using the donor's exact animation world clock.
  old={n:matrix(v) for n,v in row['world'].items()};world={n:m.copy() for n,m in old.items()}
  for n in names:
   if n not in changed:continue
   p=parent[n];pm=world[p] if p in world else oldworld[p]
   world[n]=pm@local[n]
  # A cartridge in the left hand follows the original 715 pickup path.
  # Bring only its mechanical seating offset in during the final push;
  # never synthesize shoulder, wrist or finger tracks to chase a new bore.
  if kind.startswith('single_'):
   start,count=map(int,kind.split('_')[1:]);begin=1.5 if start==0 else .6
   for i in range(start,min(5,start+count)):
    phase=(t-begin-1.1*(i-start))/1.1
    if 0.0<=phase<.64/1.1:
     w=smooth((phase-.26)/(.64/1.1-.26))
     n='WPN_Case_'+str(i)
     local[n]=Matrix.LocRotScale(base[n].translation.lerp(local[n].translation,w),
       base[n].to_quaternion().slerp(local[n].to_quaternion(),w),local[n].to_scale())
  for n in list(tracks):
   if n not in local:tracks[n].append([0,0,0,0,0,0,1,0,0,0]);continue
   bt,bq,bs=base[n].decompose();nt,nq,ns=local[n].decompose();q=nq@bq.inverted()
   if q.w<0:q.negate()
   tracks[n].append([*(nt-bt),q.x,q.y,q.z,q.w,*(ns-bs)])
  # Contact tracks first appearing partway through the action need identity keys.
  for n,values in tracks.items():
   if len(values)<len(times):values[:0]=[[0,0,0,0,0,0,1,0,0,0]]*(len(times)-len(values))
 sparse=[]
 for n,values in tracks.items():
  if max(max(abs(x) for x in v[:6]+v[7:]) for v in values)<1e-6:continue
  constant=all(max(abs(a-b) for a,b in zip(values[0],v))<1e-6 for v in values[1:])
  sparse.append(dict(bone=n,times=[0.] if constant else times,values=values[0] if constant else [x for v in values for x in v]))
 records.append(dict(base=clip['asset'],duration=clip['duration'],kind=kind,tracks=sparse))
 print('RSH12_SHARED_PROFILE_AUTHORED',SIDE,kind,len(sparse),flush=True)
(OUT/'profile.json').write_text(json.dumps(dict(family='base',clips=records),separators=(',',':')),encoding='utf8')
r.data.pose_position='REST';bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
for ob in hands+gun:ob.hide_set(False);ob.select_set(True)
# One export skin emits a complete bind pose. Weighted shells retain their
# independent WPN groups and UVs inside the joined production mesh.
r.select_set(False);bpy.context.view_layer.objects.active=gun[0]
bpy.ops.object.join();combined=bpy.context.view_layer.objects.active;combined.name='RSH12_NativeAssembly'
r.select_set(True)
bpy.context.view_layer.objects.active=r
name='SK_RSH12_Manny' if SIDE=='single' else 'SK_Dual_RSH12_'+SIDE
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('RSH12_'+SIDE+'_Editable.blend')))
(OUT/'authoring.json').write_text(json.dumps(dict(mesh=name+'.fbx',skeleton=D['skeleton'],source='Medji Rsh-12.fbx',capacity=5,
 cartridge_source='10_l',source_length_m=.34132,cylinder_step_degrees=72,alignment=[list(v) for v in alignment],
 markers={n:list(v) for n,v in points.items()},mechanical_part_mapping=mapping,
 mechanical_shell_overrides={'4_l_front_rod':'WPN_Extractor'},
 chamber_fit_source='RSH12Fit20261003/fit_contract.json',cartridge_rim_seat_m=FIT['rear_plane_m']+1e-5,native_arms='Installed DW715 V7',
 grip_contact_source='RSH12Native71520261003/grip_registration.json',native_hand_animation=True,grip_registration=contact['registration'],
 mechanical_bind_matrices={n:[list(row) for row in newrest[n]] for n in points},
 cylinder_bore_axis_ue_local=list(bore_axis),cylinder_bore_axis_local=list(S.to_3x3()@bore_axis),
 shared_clips=len(records),acceptance_tested=False),indent=2),encoding='utf8')
if SIDE=='single':
 # Package cartridge as a standalone production resource, preserving original UVs.
 bpy.ops.object.select_all(action='DESELECT')
 mesh=bpy.data.meshes.new('RSH12_Cartridge');mesh.from_pydata(cartridge['verts'],[],cartridge['faces']);mesh.materials.append(mat);mesh.update()
 uv=mesh.uv_layers.new(name='UVMap')
 for a,b in zip(uv.data,cartridge['uv']):a.uv=b
 ob=bpy.data.objects.new('SM_RSH12_Cartridge',mesh);bpy.context.collection.objects.link(ob);ob.select_set(True)
 bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.fbx(filepath=str(O/'SM_RSH12_Cartridge.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
 # Icon input is the assembled factory gun, before inverse-bind transport.
 (O/'icon_geometry.json').write_text(json.dumps([p for p in raw if p['name']!='10_l'],separators=(',',':')),encoding='utf8')
print('RSH12_NATIVE_GEOMETRY_SAVED',SIDE,flush=True)
