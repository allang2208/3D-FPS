"""HK416 measured interfaces, accepted common bodies and original UVs."""
import bpy,bmesh,json,math
import importlib.util
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;H=S/'HK416Reworked20260930';D=S/'M16UniversalAttachments20260920'
I=json.loads((H/'authoring.json').read_text());J=json.loads((D/'authoring.json').read_text());sources=json.loads((D/'sources.json').read_text())
R=Matrix(I['root_matrix']);A=Matrix(I['source_to_weapon_root']);RA=R@A
spec=importlib.util.spec_from_file_location('hk416_stock_interfaces',O/'stock_interfaces.py');stock_interfaces=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock_interfaces)
spec=importlib.util.spec_from_file_location('hk416_reargrip_interfaces',O/'reargrip_interfaces.py');reargrip_interfaces=importlib.util.module_from_spec(spec);spec.loader.exec_module(reargrip_interfaces)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
(O/'Meshes').mkdir(exist_ok=True)
report={'parts':{},'runtime_tested':False}
metal=bpy.data.materials.new('HK416_InterfaceSteel')
G=Matrix(J['donors']['vertical']['mount']);G.translation+=Vector((0,.006,-.013))
report['grip_mount']=[list(v) for v in G]
def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
def box(center,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(metal)
 bevel=o.modifiers.new('Machined interface edge','BEVEL');bevel.width=.0004;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
 o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4);return o
def sleeve(center,length,inner,outer):
 n=64;v=[]
 for y in [-length/2,length/2]:
  for radius in [inner,outer]:
   v += [Vector(center)+Vector((radius*math.cos(j*math.tau/n),y,radius*math.sin(j*math.tau/n))) for j in range(n)]
 f=[]
 for j in range(n):
  k=(j+1)%n;f.extend([(j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j),(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k)])
 me=bpy.data.meshes.new('Open bore collar');me.from_pydata(v,[],f);me.materials.append(metal);o=bpy.data.objects.new('HK416 fitted collar',me);bpy.context.collection.objects.link(o);return o
def load(key):
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=sources[key]['fbx'],use_custom_normals=True)
 obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH' and not o.name.startswith(('UCX_','UBX_','UCP_','USP_'))]
 for o in obs:o.data.transform(o.matrix_world);o.parent=None;o.matrix_world=Matrix.Identity(4)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 o=bpy.context.object
 for i,slot in enumerate(sources[key]['slots']):
  m=bpy.data.materials.get(slot['slot']) or bpy.data.materials.new(slot['slot'])
  o.data.materials[i]=m
 return o
def export(key,obs,bindings,sockets=None):
 for o in obs:
  coords=[[tuple(d.uv) for d in layer.data] for layer in list(o.data.uv_layers)[:3]]
  for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
  for i in range(4):
   uv=o.data.uv_layers.new(name='HK416_UV'+str(i))
   if i<len(coords):
    for j,p in enumerate(coords[i]):uv.data[j].uv=p
  uv=o.data.uv_layers[3]
  for f in o.data.polygons:
   axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[i for i in range(3) if i!=axis]
   for li in f.loop_indices:
    p=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(p[a]/.04,p[b]/.04)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 o=bpy.context.object;o.name='SM_HK416_'+key;file=O/'Meshes'/(o.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
 bpy.data.libraries.write(str(file.with_suffix('.blend')),{o},fake_user=True)
 report['parts'][key]={'name':o.name,'file':str(file),'bindings':bindings,'sockets':{n:list(p) for n,p in (sockets or {}).items()},'source':sources[key]['source'] if key in sources else 'HK416 factory source'}
 o.hide_set(True)
keys=['tactical_vertical','canted','prism','angled','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','tactical_suppressor','brake','skeleton','qr_performance','core_stock','tactical_telescopic','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip','large_drum']
for key in keys:
 o=load(key);obs=[o];bindings={s['slot']:s['material'] for s in sources[key]['slots']};bindings[metal.name]=None;sockets={}
 if key in ('tactical_vertical','canted','prism','angled'):
  if key=='angled':o.data.transform(Matrix(J['donors']['angled']['mount']).inverted()@Matrix(J['donors']['angled']['rest']['WPN_root']).inverted())
  o.data.transform(G)
  # The common saddle is 4.4 mm below this rail's crown; bridge this gap with
  # a seated cross bolt and two cheeks, without changing the grasping body.
  crown=(A@Vector((0,.0467,.01162788))).z
  center=G.translation.copy();center.z=(center.z+crown)*.5
  obs.append(box(center,(.021,.036,crown-G.translation.z+.001)))
  for x in [-.012,.012]:obs.append(box((x,center.y,crown+.001),(.004,.031,.005)))
  for ob in obs:ob.data.transform(R)
 elif key in ('panoramic_red_dot','prism_scope_2x','lpvo_1_6x'):
  T=Matrix.Rotation(-math.pi/2,4,'Z');T.translation=A@Vector((0,.001,.0297297))
  # Long optic rear bell stays forward of the native rear diopter housing.
  if key=='lpvo_1_6x':T.translation.y-=.028
  o.data.transform(R@T)
  p=Vector((.02125,0,.0325)) if key=='panoramic_red_dot' else Vector((-.0615 if key=='prism_scope_2x' else -.1215,0,.04))
  sockets={'SightRear':R@T@p,'SightFront':R@T@(p+Vector((.1,0,0))),'SightUp':R@T@(p+Vector((0,0,.01)))}
  if key=='lpvo_1_6x':
   sockets['ZoomRing']=R@T@Vector((-.071,0,.04));report['ring_rotation_blender']=[list(v) for v in (R@T).to_3x3()]
 elif key=='lpvo_ring':pass # Pivot stays at its own X-axis for magnification.
 elif key in ('tactical_suppressor','brake'):
  T=Matrix.Rotation(math.pi,4,'Z');T.translation=A@Vector((0,.0828,.0198872))
  tip=max(v.co.y for v in o.data.vertices);o.data.transform(R@T)
  sockets={'Muzzle':R@T@Vector((0,tip,0)),'AimGuide':R@T@Vector((0,tip+.1,0))}
  collar=sleeve(T.translation,.014,.007,.0105);collar.data.transform(R);obs.append(collar)
 elif key in ('skeleton','qr_performance','core_stock','tactical_telescopic'):
  collar,fit=stock_interfaces.fit_stock(key,o,R,A,H/'HK416_Gameplay_Editable.blend',metal);obs.append(collar)
  report.setdefault('stock_interfaces',{})[key]=fit
 elif key.endswith('reargrip'):
  neck,fit=reargrip_interfaces.fit_reargrip(key,o,R,H/'HK416_Gameplay_Editable.blend',metal);obs.append(neck)
  report.setdefault('reargrip_interfaces',{})[key]=fit
 elif key=='large_drum':
  # Keep accepted drum body/contact, replace only its upper feed tower later
  # with the HK factory throat. Both use the same registered AR magazine bone.
  pass
 export(key,obs,bindings,sockets)

# Author real factory sections; material assignments leave UVs and skin intact.
bpy.ops.wm.open_mainfile(filepath=str(H/'HK416_Gameplay_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST';r.animation_data_clear()
sections={};original_materials={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.get('HK416_SourceObject'):continue
 name=o['HK416_SourceObject'];role='FactorySights' if name=='ironsight_low' else 'FactoryRearGrip' if name=='Hand_grip_low' else 'FactoryStock' if name in ('Stock_Stick_low','Stock_ring_low','Shock_Res_low','Stock_body_low','Handle_1_low','Handle_2_low','Stock_cover') else None
 if role:
  old=o.data.materials[0];m=bpy.data.materials.get('M_HK416_'+role) or old.copy();m.name='M_HK416_'+role;o.data.materials[0]=m
  sections[m.name]=old.name
 if name=='Muzzle_low':
  old=o.data.materials[0];m=old.copy();m.name='M_HK416_FactoryMuzzle';o.data.materials.append(m);sections[m.name]=old.name
  # A topology cut produces a distinct hider section, preserving the barrel.
  bm=bmesh.new();bm.from_mesh(o.data);cut=RA@Vector((0,.0828,.0198872));axis=(RA.to_3x3()@Vector((0,1,0))).normalized()
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=cut,plane_no=axis,dist=1e-7)
  for f in bm.faces:
   if (f.calc_center_median()-cut).dot(axis)>1e-7:f.material_index=1
  bm.to_mesh(o.data);bm.free()
activate([r]+[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('HK416_SourceObject') or o.get('inspect_skin_source'))])
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.export_scene.fbx(filepath=str(O/'SK_HK416_Modular.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'HK416_Modular_Editable.blend'))
report['sections']=sections;report['mesh']=str(O/'SK_HK416_Modular.fbx')
(O/'models.json').write_text(json.dumps(report,indent=2));print('HK416_COMMON_GEOMETRY_SAVED',len(report['parts']),flush=True)
