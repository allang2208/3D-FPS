"""Split the SVD shoulder stock behind the grip and author closed rod assemblies."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;D=O/'Exports';D.mkdir(exist_ok=True)
data=json.loads((O/'geometry_inputs.json').read_text());report={'meshes':{},'game_tested':False}
bpy.context.preferences.filepaths.save_version=0

def active(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def export(obs,name,rig=False):
 active(obs);bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,
  object_types={'MESH','ARMATURE'} if rig else {'MESH'},axis_forward='-Y',axis_up='Z',
  add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
def matte(name,polymer=False):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.023,.029,.035,1)
 p.inputs['Metallic'].default_value=0 if polymer else .84;p.inputs['Roughness'].default_value=.67 if polymer else .64
 return m
def coat_uv(ob):
 if not ob.data.uv_layers:ob.data.uv_layers.new(name='UVMap')
 while len(ob.data.uv_layers)<3:ob.data.uv_layers.new(name='SVD_CoatingUV' if len(ob.data.uv_layers)==2 else 'UnusedUV')
 for f in ob.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
  for li in f.loop_indices:
   co=ob.data.vertices[ob.data.loops[li].vertex_index].co
   ob.data.uv_layers[2].data[li].uv=(co[axes[0]]/.05,co[axes[1]]/.05)
 ob.data.uv_layers.active_index=0

bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';bpy.context.view_layer.update()
body=bpy.data.objects['SM_SVD_Body'];X=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()@body.matrix_world
normal_source=body.copy();normal_source.data=body.data.copy();normal_source.name='NORMAL_REFERENCE';bpy.context.collection.objects.link(normal_source)
for mod in list(normal_source.modifiers):normal_source.modifiers.remove(mod)
# The plane follows the rear of the retained grip: y + .35*z = .112 m.
# Only the stock/cheekrest shells participate; the receiver and hand skin do not.
selected=set()
shells=[]
for i,row in enumerate(data['islands']):
 if row['min'][1]>.099 or i in [17,19]:selected.update(row['indices']);shells.append(i)
plane_co=X.inverted()@Vector((0,.112,0));plane_no=(X.to_3x3().transposed()@Vector((0,1,.35))).normalized()
poly=matte('SVD_StockCutPolymer',True)
factory=bpy.data.materials['SM_SVD_Body.001'].copy();factory.name='SVD_FactoryStock'

def piece(name,rear):
 ob=body.copy();ob.data=body.data.copy();ob.name=name;bpy.context.collection.objects.link(ob)
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in selected],context='VERTS')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
  plane_co=plane_co,plane_no=plane_no,clear_inner=rear,clear_outer=not rear)
 # Fill each actual cut loop. Existing non-cut edges are not bridged together.
 boundary=[e for e in bm.edges if e.is_boundary and all(abs((v.co-plane_co).dot(plane_no))<1e-6 for v in e.verts)]
 if not boundary:raise RuntimeError('Missing stock split boundary '+name)
 filled=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
 capindex=len(ob.data.materials);ob.data.materials.append(poly)
 for f in filled:
  f.material_index=capindex;f.smooth=False
  expected=-plane_no if rear else plane_no
  if f.normal.dot(expected)<0:f.normal_flip()
 uv=bm.loops.layers.uv.active
 if uv:
  for f in filled:
   for loop in f.loops:
    p=X@loop.vert.co;loop[uv].uv=(p.x/.05+.5,p.z/.05+.5)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
 active([ob]);t=ob.modifiers.new('KeepFactorySurfaceNormals','DATA_TRANSFER');t.object=normal_source
 t.use_loop_data=True;t.data_types_loops={'CUSTOM_NORMAL'};t.loop_mapping='POLYINTERP_NEAREST'
 bpy.ops.object.modifier_apply(modifier=t.name)
 norms=[tuple(n.vector) for n in ob.data.corner_normals]
 for f in ob.data.polygons:
  if f.material_index==capindex:
   for li in f.loop_indices:norms[li]=tuple(f.normal)
 ob.data.normals_split_custom_set(norms)
 if rear:
  ob.data.materials.clear();ob.data.materials.append(factory)
  for f in ob.data.polygons:f.material_index=0
 arm=ob.modifiers.new('Armature','ARMATURE');arm.object=rig
 return ob
front=piece('SM_SVD_RetainedGrip',False);stock=piece('SM_SVD_FactoryStock',True)
# Body topology outside the selected shells and all other parts are preserved.
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in selected],context='VERTS');bm.to_mesh(body.data);bm.free()
active([body]);t=body.modifiers.new('KeepReceiverCornerNormals','DATA_TRANSFER');t.object=normal_source
t.use_loop_data=True;t.data_types_loops={'CUSTOM_NORMAL'};t.loop_mapping='POLYINTERP_NEAREST'
# Apply the normal transfer before its armature so the reference is the rest mesh.
while body.modifiers.find(t.name)>0:bpy.ops.object.modifier_move_up(modifier=t.name)
bpy.ops.object.modifier_apply(modifier=t.name)
bpy.data.objects.remove(normal_source,do_unlink=True)
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]
export(parts+[rig],'SK_SVD_ModularStock',True)
# Separate original-stock source for future replacement and the factory icon.
factory_static=stock.copy();factory_static.data=stock.data.copy();factory_static.name='FactoryStock_StaticSource';bpy.context.collection.objects.link(factory_static)
for m in list(factory_static.modifiers):factory_static.modifiers.remove(m)
factory_static.parent=None;factory_static.data.transform(X);factory_static.matrix_world=Matrix.Identity(4)
export([factory_static],'SM_SVD_factory_stock')
bpy.data.objects.remove(factory_static,do_unlink=True)
report['stock_split']={'source':str(S/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend'),'selected_shells':shells,
 'plane_root_m':'y + 0.35*z = 0.112','factory_slot':'SVD_FactoryStock','new_grip_cap_slot':'SVD_StockCutPolymer',
 'retained_grip_vertices':len(front.data.vertices),'factory_stock_vertices':len(stock.data.vertices)}
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_StockModular_Editable.blend'))

def finish(ob):
 active([ob]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=ob.modifiers.new('MachinedEdgeRadius','BEVEL');mod.width=.00045;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=ob.modifiers.new('MachinedFaceNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);coat_uv(ob)
 # New interface UV0 is its own physical projection, never the donor normal atlas.
 for a,b in zip(ob.data.uv_layers[0].data,ob.data.uv_layers[2].data):a.uv=b.uv
 return ob
def box(name,loc,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.dimensions=size;ob.data.materials.append(mat);return finish(ob)
def cylinder(name,loc,radius,length,mat,axis=(0,1,0),sides=64):
 bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=length,location=loc)
 ob=bpy.context.object;ob.name=name;ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis));ob.data.materials.append(mat);return finish(ob)

for key,entry in data['donors'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);info=entry['source'];bpy.ops.import_scene.fbx(filepath=info['source'][0])
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];bindings={}
 F=Matrix.Translation((.0000364,.139,.041))@Matrix.Rotation(math.pi/2,4,'Z')
 for ob in obs:
  ob.data.transform(F@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
  for i,m in enumerate(ob.data.materials):
   m.name='SVD_Stock_'+key+'_'+str(i);bindings[m.name]={'source':info['materials'][i]['path'],'source_slot':info['materials'][i]['slot']}
  coat_uv(ob)
 steel=matte('SVD_StockAdapterSteel');bindings[steel.name]={'source':'SVD_CURRENT_MATTE_STEEL','source_slot':'adapter'}
 x=.0000364
 obs += [box('SVD_ReceiverEndPlate',(x,.102,.028),(.031,.013,.049),steel),
         box('SVD_UpperTang',(x,.102,.049),(.022,.020,.009),steel),
         box('SVD_RodLowerBrace',(x,.116,.020),(.023,.028,.012),steel),
         cylinder('SVD_StockConnectionRod',(x,.127,.041),.0116,.061,steel),
         cylinder('SVD_ReceiverLockRing',(x,.115,.041),.0149,.007,steel),
         cylinder('SVD_RearCollar',(x,.137,.041),.0141,.004,steel)]
 for side in [-1,1]:
  obs.append(cylinder('SVD_AdapterCrossBolt',(x+side*.0158,.102,.023),.0032,.0026,steel,(1,0,0),12))
 name='SM_SVD_'+key;export(obs,name)
 report['meshes'][key]={'name':name,'materials':bindings,'donor_asset':info['asset'],'source':info['source'][0],
  'frame':'SVD WPN_root rest metres; -Y forward, +Z up','stock_front_m':[x,.139,.041],
  'rod_axis_start_m':[x,.0965,.041],'rod_axis_end_m':[x,.1575,.041],'rod_diameter_m':.0232}
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 print('SVD_STOCK_ASSEMBLY_EXPORTED',key,flush=True)
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('SVD_STOCK_AUTHORING_COMPLETE',flush=True)
