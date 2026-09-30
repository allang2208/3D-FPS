"""Fit the R29 visual candidate to the installed 201 animation/attachment frame.

Coordinates are game-art fitting data, not physical weapon specifications.
Native arms, magazine, and operating controls are retained by the UE assembly.
"""
import bpy,bmesh,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.geometry import delaunay_2d_cdt
O=Path(__file__).parent;R=O.parent/'Refine29';(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'LMG201_R29_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
# Only the native reference armature is loaded; its animation is never exported.
with bpy.data.libraries.load(str(O.parent/'Video26/LMG201_Video26_Editable.blend'),link=False) as (src,dst):
 dst.objects=['SK_M4_Infima']
rig=dst.objects[0];bpy.context.scene.collection.objects.link(rig)
rig.animation_data_clear();rig.data.pose_position='REST'
root=rig.data.bones['WPN_root'].matrix_local.copy()
parts={p['name']:bpy.data.objects[p['name']] for p in json.loads((R/'delivery.json').read_text())['parts']}
for ob in parts.values():
 ns=[ob.matrix_world.to_3x3().inverted().transposed()@n.vector for n in ob.data.corner_normals]
 ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 ob.data.normals_split_custom_set(ns)
 ob.hide_render=False;ob.hide_set(False)

# Reuse the exact face/corner-preserving cut implementation from R29.
tree=ast.parse((R/'author_parts.py').read_text(encoding='utf8'))
for fn in tree.body:
 if isinstance(fn,ast.FunctionDef) and fn.name in ['cut_plane','planar_caps']:
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(R/'author_parts.py'),'exec'))

def split_front(ob):
 me=ob.data;me.calc_loop_triangles();uv=me.uv_layers[0].data
 t=[];ids=[]
 for p in me.loop_triangles:
  t.append([list(me.vertices[me.loops[i].vertex_index].co)+list(me.corner_normals[i].vector)+list(uv[i].uv) for i in p.loops]);ids.append(p.material_index)
 lo,li,hi,ii=cut_plane(np.array(t),np.array(ids),(0,0,1),.1416,1)
 result=[]
 for name,data,mids in [('FrontSightBase',lo,li),('FrontSight',hi,ii)]:
  coords,iv=np.unique(np.round(data[:,:,:3].reshape(-1,3),8),axis=0,return_inverse=True);faces=iv.reshape(-1,3)
  good=(faces[:,0]!=faces[:,1])&(faces[:,1]!=faces[:,2])&(faces[:,0]!=faces[:,2])
  good &= np.linalg.norm(np.cross(coords[faces[:,1]]-coords[faces[:,0]],coords[faces[:,2]]-coords[faces[:,0]]),axis=1)>1e-13
  faces=faces[good];data=data[good];mids=mids[good]
  m=bpy.data.meshes.new(name);m.from_pydata(coords.tolist(),[],faces.tolist());m.update()
  for mat in me.materials:m.materials.append(mat)
  u=m.uv_layers.new(name='UV0');u.data.foreach_set('uv',data[:,:,6:8].astype(np.float32).ravel())
  for p,mid in zip(m.polygons,mids):p.material_index=int(mid);p.use_smooth=True
  m.normals_split_custom_set(data[:,:,3:6].reshape(-1,3).tolist())
  item=bpy.data.objects.new(name+'_Fitted',m);bpy.context.scene.collection.objects.link(item);result.append(item)
 bpy.data.objects.remove(ob,do_unlink=True)
 return result
parts['FrontSightBase'],parts['FrontSight']=split_front(parts['FrontSight'])

# Shared longitudinal stations prevent seams drifting between adjacent parts.
XP=np.array([-.950634,-.875,-.626,-.454,-.138,-.126,-.09,.204,.214,.318,.361,.478164,.528,.949722])
YP=np.array([-.76637,-.68770,-.54212,-.45166,-.2375,-.232,-.22251,-.097,-.093,-.01490,.006,.06578,.07209,.33586])
ZP=np.array([-.23,-.13276,-.07727,-.027,-.01,0,.071,.104,.13579,.1416,.15,.16,.174,.181616,.236625])
ZQ=np.array([-.124,-.07391,-.047,-.036,-.00644,.00165,.030,.04866,.0605,.0648,.07240,.0758,.082,.086,.12562])

def pw(value,a,b):
 i=int(np.clip(np.searchsorted(a,value,side='right')-1,0,len(a)-2));s=(b[i+1]-b[i])/(a[i+1]-a[i]);return b[i]+(value-a[i])*s,s

def fit(name,p):
 x,y,z=p;yy,sy=pw(x,XP,YP);zz,sz=pw(z,ZP,ZQ);sx=.55
 xx=.0008-(y-.0055)*sx
 if name=='PistolGrip':
  yy=-.01490043+(x-.318)*(.080683357/.160163987);sy=.080683357/.160163987
  zz=-.116617113+(z+.220199004)*(.110180477/.210199004);sz=.110180477/.210199004
  sx=.043552468/.060424998;xx=-.022097172+(.035475999-y)*sx
 if name=='Handguard':
  # Conserve the accepted palm contact silhouette at the lower fore-end.
  zz=.00164749+(z+.026629)*(.07075720/.176754802);sz=.07075720/.176754802
 if name=='FrontSight' or name=='FrontSightBase':
  # Keep both pieces centered on the fixed folding mount.
  yy=-.54212+(x+.626)*.57;sy=.57
 if name=='RearSight':
  yy=.04252+(x-.27628)*.57;sy=.57
  zz=.0855+(z-.174)*(.03612/.043112);sz=.03612/.043112
 if name=='TopRail':
  # Preserve rail height; extend the back to the retained rear-sight foot.
  yy=-.082+(x-.213)*(.14/.242420405);sy=.14/.242420405
 return Vector((xx,yy,zz)),Matrix(((0,-sx,0),(sy,0,0),(0,0,sz)))

material_roles={}
def role_material(ob,name):
 if name=='FlashHider':prefix='M_LMG201_FactoryMuzzle_R30'
 elif name=='Stock':prefix='M_LMG201_FactoryStock_R30'
 elif name=='PistolGrip':prefix='M_LMG201_FactoryRearGrip_R30'
 elif name=='AmmoBag':prefix='M_LMG201_Feed__R30_AmmoBag'
 elif name=='AmmoBelt':prefix='M_LMG201_Feed__R30_AmmoBelt'
 else:prefix='M_LMG201_R30'
 for i,mat in enumerate(list(ob.data.materials)):
  kind='Cloth' if 'Woven' in mat.name else 'Interior' if 'CutInterior' in mat.name else 'Steel' if 'RebuiltSteel' in mat.name else 'Surface'
  key=prefix+'_'+kind
  dest=bpy.data.materials.get(key)
  if not dest:dest=mat.copy();dest.name=key
  ob.data.materials[i]=dest;material_roles[key]=kind

for name,ob in parts.items():
 if name=='TriggerGuardAssembly':continue
 me=ob.data;old=[v.co.copy() for v in me.vertices];normals=[n.vector.copy() for n in me.corner_normals]
 transforms=[]
 for v,p in zip(me.vertices,old):v.co,J=fit(name,p);transforms.append(J.inverted().transposed())
 normals=[(transforms[l.vertex_index]@n).normalized() for l,n in zip(me.loops,normals)]
 me.normals_split_custom_set(normals);role_material(ob,name)
 ob['Native201ContactFit']='Install30: stationary rig, factory-magazine and gunsmith attachment interfaces'
 if name=='AmmoBag':
  atlas=me.uv_layers.get('ClothAtlas')
  if atlas:
   data=np.empty(len(me.loops)*2,np.float32);atlas.data.foreach_get('uv',data)
   me.uv_layers[0].data.foreach_set('uv',data);me.uv_layers.active_index=0;me.uv_layers[0].active_render=True

# A clean guard frame surrounds the retained native animated trigger. The
# generated fused trigger is excluded, so two triggers can never overlap.
bpy.data.objects.remove(parts.pop('TriggerGuardAssembly'),do_unlink=True)
outer=[(-.095,-.001),(-.014,-.001),(-.014,-.034),(-.024,-.043),(-.080,-.043),(-.095,-.031)]
inner=[(-.088,-.005),(-.021,-.005),(-.021,-.030),(-.029,-.035),(-.076,-.035),(-.088,-.027)]
vs=[(x,y,z) for x in [-.005,.0066] for profile in [outer,inner] for y,z in profile];fs=[];n=6
for i in range(n):
 j=(i+1)%n
 fs.extend([(i,j,6+j,6+i),(12+i,18+i,18+j,12+j),(i,12+i,12+j,j),(6+i,6+j,18+j,18+i)])
me=bpy.data.meshes.new('TriggerGuard');me.from_pydata(vs,[],fs);me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
ob=bpy.data.objects.new('TriggerGuard_Fitted',me);bpy.context.scene.collection.objects.link(ob)
mat=bpy.data.materials.get('M_LMG201_R30_Steel')
if not mat:mat=bpy.data.materials.new('M_LMG201_R30_Steel')
me.materials.append(mat);material_roles[mat.name]='Steel'
parts['TriggerGuard']=ob
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
select([ob]);bevel=ob.modifiers.new('Guard edge rounding','BEVEL');bevel.width=.001;bevel.segments=3
bpy.ops.object.modifier_apply(modifier=bevel.name)
for p in me.polygons:p.use_smooth=True
norm=ob.modifiers.new('Guard plane normals','WEIGHTED_NORMAL');norm.keep_sharp=True
bpy.ops.object.modifier_apply(modifier=norm.name)

# Sight base matches the retained rear folding origin, with the sight in its
# own static component. These small solid objects are visual mounting pieces.
for name,c,size in [('RearSightBase',(.0008,.04252,.0804),(.020,.022,.011))]:
 bpy.ops.mesh.primitive_cube_add(size=1,location=c);ob=bpy.context.object;ob.name=name+'_Fitted';ob.scale=size
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 ob.data.materials.append(mat);bevel=ob.modifiers.new('Base fillet','BEVEL');bevel.width=.0007;bevel.segments=3
 bpy.ops.object.modifier_apply(modifier=bevel.name);parts[name]=ob

exports={};counts={}
def fbx(path,obs,skeletal=False):
 select(obs)
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,
  object_types={'MESH','ARMATURE'} if skeletal else {'MESH'},axis_forward='-Y',axis_up='Z',
  add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
body=[]
for name,ob in parts.items():
 counts[name]=sum(len(p.vertices)-2 for p in ob.data.polygons)
 if name in ['FrontSight','RearSight']:
  hinge=Vector((.0008,-.54212,.0648) if name=='FrontSight' else (.0008,.04252,.0855))
  ob.data.transform(Matrix.Translation(-hinge));path=O/'Exports'/('SM_LMG201_'+name+'.fbx');fbx(path,[ob]);exports[name]=str(path)
  ob.matrix_world=root@Matrix.Translation(hinge)
 elif name in ['AmmoBag','AmmoBelt']:
  path=O/'Exports'/('SM_LMG201_R30_'+name+'.fbx');fbx(path,[ob]);exports[name]=str(path)
  ob.matrix_world=root;ob.hide_render=True;ob.hide_set(True)
 else:
  normals=[root.to_3x3()@n.vector for n in ob.data.corner_normals]
  ob.data.transform(root);ob.data.normals_split_custom_set(normals)
  ob.vertex_groups.clear();bone='LMG201_Cover' if name=='TopCover' else 'WPN_root'
  ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1.,'REPLACE')
  ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
  ob.modifiers.new('Native201Rig','ARMATURE').object=rig;body.append(ob)
# Merge only export copies; editable components remain separated.
copies=[]
for ob in body:
 cp=ob.copy();cp.data=ob.data.copy();bpy.context.scene.collection.objects.link(cp);copies.append(cp)
select(copies);bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_R30_WeaponSurface'
path=O/'Exports/SK_LMG201_R30_Weapon.fbx';fbx(path,[joined,rig],True);exports['Weapon']=str(path)
bpy.data.objects.remove(joined,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_R30_NativeFit.blend'))
(O/'fit.json').write_text(json.dumps({'status':'native_frame_authored_and_exported','exports':exports,
 'triangles':counts,'material_roles':material_roles,'source_candidate':str(R/'LMG201_R29_Editable.blend'),
 'retained_native':['arms','magazine','trigger','charging controls','bipod','animations','skeleton','attachments'],
 'hidden_storage_only':['AmmoBag','AmmoBelt'],'rendered':False,'tested':False},indent=2))
print('NATIVE_201_FIT_EXPORTED',json.dumps(counts),flush=True)
