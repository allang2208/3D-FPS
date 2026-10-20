"""Preserve selected source topology/UV/normals; bind rigid parts to the current rig."""
import bpy,bmesh,json,gzip,math,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O/'Download/Extracted/Original/Native/KVInhibitor';R8=O.parent/'SVCHRefinement20261018/R8Surface'
sys.path.insert(0,str(O));from contact_geometry import fit_surface
bpy.context.preferences.filepaths.save_version=0
reg=json.loads((O/'registration.json').read_text());SN=np.array(reg['source_to_previous_native'])
hold=json.loads((O.parent/'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
def component(n):
 n=np.asarray(n);g=np.stack((n[...,0]-18.7444,n[...,2]-1.5268,n[...,1]),axis=-1);return g@HR.T+HT
def bpos(n):return component(n)*np.array([.01,-.01,.01])
def src_native(p):return np.asarray(p)@SN[:3,:3].T+SN[:3,3]
T=np.eye(4);T[:3,3]=bpos(SN[:3,3]);T[:3,:3]=np.column_stack([bpos(SN[:3,3]+SN[:3,i])-T[:3,3] for i in range(3)])
bpy.ops.wm.open_mainfile(filepath=str(R8/'SVCH_R8Surface.blend'),load_ui=False)
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';rig.animation_data_clear()
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
arms=bpy.data.objects['SVCH_BareArmsV9'];arms.animation_data_clear()
for ob in list(bpy.data.objects):
 if ob not in (rig,arms):bpy.data.objects.remove(ob,do_unlink=True)
selected=['other\\KVInhibitor.smd','other\\barrel.smd','other\\mag.smd','other\\stock.smd','other\\bullets.smd']
with bpy.data.libraries.load(str(S/'KV Inhibitor.blend'),link=False) as (a,b):b.objects=list(selected)
source_objects=list(b.objects);bone_map={'j_trigger':'WPN_Trigger','j_charging_handle':'WPN_bolt','mag':'WPN_SOCKET_Magazine','j_follower':'WPN_SOCKET_Magazine','bulletA':'WPN_SOCKET_Magazine','bulletB':'WPN_SOCKET_Magazine','bulletC':'WPN_SOCKET_Magazine'}
report={'source_model':'b3bb922bdf1a481a96b9e2940b2d26fc','preserved':['source topology','source UV','source normals','source colors and normal maps','approved skeleton','V9 arms'], 'selected_parts':selected,'omitted':['alternate long barrel','extended magazine','duplicate cartridges','source scope'],'parts':{},'materials':{},'runtime_tested':False}
source_matrices={r['name']:Matrix(r['matrix']) for r in json.loads((O/'source_inventory.json').read_text())['objects']}
for ob in source_objects:
 bpy.context.scene.collection.objects.link(ob)
 source_world=source_matrices[ob.name];dom=[ob.vertex_groups[max(v.groups,key=lambda x:x.weight).group].name for v in ob.data.vertices]
 ob.data=ob.data.copy();ob.data.transform(source_world)
 sv=np.array([list(v.co) for v in ob.data.vertices]);part=ob.name.split('\\')[-1];nv=fit_surface(sv,dom,part)
 # Apply the local shape Jacobian to original custom corner normals.
 normals=np.array([list(n.vector) for n in ob.data.corner_normals]);ids=np.array([l.vertex_index for l in ob.data.loops])
 jac=np.empty((len(sv),3,3));eps=1e-4
 for axis in range(3):
  delta=np.eye(3)[axis]*eps;jac[:,:,axis]=(fit_surface(sv+delta,dom,part)-fit_surface(sv-delta,dom,part))/(2*eps)
 adjusted=np.einsum('nij,nj->ni',np.linalg.inv(jac[ids]).transpose(0,2,1),normals);adjusted/=np.maximum(np.linalg.norm(adjusted,axis=1,keepdims=True),1e-10)
 for v,p in zip(ob.data.vertices,nv):v.co=p
 ob.data.normals_split_custom_set(adjusted.tolist());ob.data.transform(Matrix(T));ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 ob.vertex_groups.clear()
 for dst in sorted({bone_map.get(n,'WPN_root') for n in dom}):
  ids=[i for i,n in enumerate(dom) if bone_map.get(n,'WPN_root')==dst];ob.vertex_groups.new(name=dst).add(ids,1.,'REPLACE')
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 ob.modifiers.new('ApprovedRigBinding','ARMATURE').object=rig;ob.parent=rig
 ob.name='SVCH_New_'+ob.name.split('\\')[-1].replace('.smd','')
 ob.data.calc_loop_triangles()
 report['parts'][ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'bones':[v.name for v in ob.vertex_groups]}
 for m in ob.data.materials:
  if m.name in report['materials']:continue
  n=m.name.removesuffix('.001');color=S/(n+'.png');normal=S/(n+'_n.png')
  m.use_nodes=True;nodes=m.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
  tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(color),check_existing=True);tex.image.colorspace_settings.name='sRGB';m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
  norm=nodes.new('ShaderNodeTexImage');norm.image=bpy.data.images.load(str(normal),check_existing=True);norm.image.colorspace_settings.name='Non-Color'
  # Source-engine normal maps are DirectX; Blender requires +Y tangent maps.
  sep=nodes.new('ShaderNodeSeparateXYZ');inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.;comb=nodes.new('ShaderNodeCombineXYZ');nm=nodes.new('ShaderNodeNormalMap')
  lk=m.node_tree.links;lk.new(norm.outputs['Color'],sep.inputs[0]);lk.new(sep.outputs['X'],comb.inputs['X']);lk.new(sep.outputs['Y'],inv.inputs[1]);lk.new(inv.outputs[0],comb.inputs['Y']);lk.new(sep.outputs['Z'],comb.inputs['Z']);lk.new(comb.outputs[0],nm.inputs['Color']);lk.new(nm.outputs[0],bs.inputs['Normal'])
  rough=.42 if 'PartA' in n or 'barrel' in n else .52 if 'PartB' in n or 'stock' in n else .45
  metal=.85 if 'bullet' in n else .25 if 'barrel' in n else .12 if 'PartA' in n else 0.
  bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
  report['materials'][m.name]={'color':str(color),'normal':str(normal),'roughness':rough,'metallic':metal,'alpha_used':False,'source_maps':'color + DirectX normal; roughness/metallic authored here'}

# Model-specific rail-mounted irons. Machined edges, true open aperture, rounded
# protective ears and pins; independent material section for attachment hiding.
mat=bpy.data.materials.new('SVCH_New_FactorySights');mat.diffuse_color=(.028,.032,.035,1);mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bs.outputs[0],out.inputs[0]);bs.inputs['Base Color'].default_value=(.028,.032,.035,1);bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.34
parts=[]
def finish(ob,name):
 ob.name=name;ob.data.materials.clear();ob.data.materials.append(mat)
 for p in ob.data.polygons:p.use_smooth=True
 bpy.context.view_layer.objects.active=ob
 bevel=ob.modifiers.new('MachinedEdge','BEVEL');bevel.width=.025;bevel.segments=3
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 weighted=ob.modifiers.new('CornerNormals','WEIGHTED_NORMAL');weighted.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=weighted.name)
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);parts.append(ob);return ob
def box(name,center,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(ob,name)
def cyl(name,center,radius,depth,axis='Y'):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=center,rotation=(math.pi/2,0,0) if axis=='Y' else (0,math.pi/2,0) if axis=='X' else (0,0,0));return finish(bpy.context.object,name)
rail=src_native([0,0,2.3927176])[2];rear=src_native([2.55,0,2.3927176])[0];front=src_native([-3.1,0,2.3927176])[0];height=rail+3.8
for name,x in [('Rear',rear),('Front',front)]:
 box(name+'Clamp',(x,0,rail+.15),(3.1,2.25,.5));box(name+'Hinge',(x,0,rail+.65),(1.5,1.7,.7));cyl(name+'HingePin',(x,0,rail+.7),.31,2.1)
 box(name+'Tower',(x,0,rail+1.7),(.58,.75,1.9))
 for y in (-.83,.83):
  box(name+'ProtectiveEar',(x,y,rail+2.85),(.72,.25,2.0));cyl(name+'EarRound',(x,y,rail+3.84),.36,.25,'Y')
 cyl(name+'ClampScrew',(x+.9,-1.18,rail+.18),.21,.17,'Y')
# Rear aperture axis is the bore. No opacity mask or opaque disc across the hole.
vs=[];fs=[];N=72
for x in (rear-.17,rear+.17):
 for r in (.285,.49):
  for i in range(N):vs.append((x,r*math.cos(i*2*math.pi/N),height+r*math.sin(i*2*math.pi/N)))
for k in range(N):
 j=(k+1)%N
 fs.extend([(k,j,N+j,N+k),(2*N+k,3*N+k,3*N+j,2*N+j),(N+k,N+j,3*N+j,3*N+k),(k,2*N+k,2*N+j,j)])
me=bpy.data.meshes.new('OpenAperture');me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new('RearOpenAperture',me);bpy.context.collection.objects.link(ob);finish(ob,ob.name)
box('FrontPost',(front,0,height-.6),(.26,.16,1.2));cyl('FrontAdjustment',(front,0,rail+2.1),.32,.45,'Z')
for ob in parts:
 me=ob.data
 # Author in native centimetres, convert once to the accepted Blender bind.
 nm=np.eye(4);nm[:3,3]=bpos([0,0,0]);nm[:3,:3]=np.column_stack([bpos(np.eye(3)[i])-nm[:3,3] for i in range(3)])
 me.transform(Matrix(nm))
 # Coordinate conversion preserves orientation (determinant +1).
 me.update();ob.vertex_groups.new(name='WPN_root').add(list(range(len(me.vertices))),1.,'REPLACE');ob.parent=rig;ob.modifiers.new('ApprovedRigBinding','ARMATURE').object=rig
 bpy.context.view_layer.objects.active=ob;ob.select_set(True)
report['materials'][mat.name]={'base_color':[.028,.032,.035],'roughness':.34,'metallic':.65}
allgun=source_objects+parts
# Hand-fitting data, with the same rigid grouping exported to UE.
geometry={}
for ob in allgun:
 ob.data.calc_loop_triangles();v=np.array([list(x.co) for x in ob.data.vertices])*[100,-100,100]
 dom=[ob.vertex_groups[max(x.groups,key=lambda g:g.weight).group].name for x in ob.data.vertices]
 geometry[ob.name]={'v':v.tolist(),'t':[list(t.vertices) for t in ob.data.loop_triangles],'dom':dom}
with gzip.open(O/'new_geometry.json.gz','wt') as f:json.dump(geometry,f)
landmarks={'RearSight':component([rear,0,height]).tolist(),'FrontSight':component([front,0,height]).tolist(),'MuzzlePoint':component(src_native([-5.8482208,0,1.939539])).tolist(),'EjectPort':component(src_native([.99,.19,1.99])).tolist(),'SightUp':[0,0,1]}
report['landmarks_component_cm']=landmarks;report['rail_top_native_cm']=rail;report['gun_triangles']=sum(len(o.data.loop_triangles) for o in allgun)
report['contact_clearance']={'pistol_grip_lower_lateral_scale':.69,'handguard_lower_lateral_scale':.75,'blend_to_original_interfaces':True,'UV_unchanged':True,'normals':'original custom normals transformed by local deformation Jacobian','hands_unchanged':True}
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig,arms]+allgun:ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_Replacement_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_Replacement.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
print('SVCH_REPLACEMENT_SOURCE_SAVED',report['gun_triangles'])
