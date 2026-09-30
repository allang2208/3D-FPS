"""Fit the accepted drum shell using the host factory feed neck; preserve UVs."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());G=json.loads((O/'geometry_inputs.json').read_text());bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Current201.fbx'),use_anim=False)
rig=next(a for a in bpy.data.objects if a.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;mag=rig.matrix_world@rig.data.bones['WPN_SOCKET_Magazine'].matrix_local;root_to_mag=mag.inverted()@root
body=next(a for a in bpy.data.objects if a.type=='MESH' and len(a.data.materials)==len(S['rigs']['201']['slots']))
indices=[i for i,s in enumerate(S['rigs']['201']['slots']) if s['name'] in ['M_LMG201_Magazine','M_LMG201_MagazineInside']]
inside=next(i for i,s in enumerate(S['rigs']['201']['slots']) if s['name']=='M_LMG201_MagazineInside')
neck=body.copy();neck.data=body.data.copy();bpy.context.collection.objects.link(neck);neck.name='D46_FactoryFeedNeck'
neck.parent=None;neck.modifiers.clear();neck.data.transform(root.inverted()@body.matrix_world);neck.matrix_world=Matrix.Identity(4)
bm=bmesh.new();bm.from_mesh(neck.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in indices],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,-.064),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.064)<1e-5 for v in e.verts)]
if rim:bmesh.ops.holes_fill(bm,edges=rim,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free()
face_indices=[1 if f.material_index==inside else 0 for f in neck.data.polygons]
factory_mat=bpy.data.materials.new('D46_FactoryNeck');neck.data.materials.clear();neck.data.materials.append(factory_mat);neck.data.materials.append(bpy.data.materials.new('D46_FactoryInside'))
for f,mi in zip(neck.data.polygons,face_indices):f.material_index=mi
for a in list(bpy.data.objects):
 if a!=neck:bpy.data.objects.remove(a,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/DonorDrum.fbx'),use_anim=False);drum=next(a for a in bpy.context.selected_objects if a.type=='MESH');drum.name='D46_AcceptedDrumShell'
bpy.context.view_layer.objects.active=drum;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
frames=json.loads((O.parents[1]/'LargeDrumUpgrade20260920/Reference/author_frames.json').read_text());canonical=Matrix(frames['AKM']['canonical_to_source']);bm=bmesh.new();bm.from_mesh(drum.data)
# Remove the old donor feed neck while retaining every shell, latch and cover.
inv=canonical.inverted()
seen=set();remove=[]
for seed in bm.verts:
 if seed in seen:continue
 stack=[seed];seen.add(seed);component=[]
 while stack:
  v=stack.pop();component.append(v)
  for e in v.link_edges:
   w=e.other_vert(v)
   if w not in seen:seen.add(w);stack.append(w)
 # The retained donor neck is the only component extending above the saddle.
 if max((inv@v.co).z for v in component)>.025:remove.extend(component)
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(drum.data);bm.free();drum.data.update()
factory=np.load(O/'Inputs/factory_mag_root.npy');top=factory[factory[:,2]>-.052];cx=float((top[:,0].min()+top[:,0].max())*.5)
old_center=(mag.inverted()@root).inverted()@canonical.translation
dx=cx-old_center.x;shift=Vector((dx,0,0))
for v in drum.data.vertices:v.co+=root_to_mag.to_3x3()@shift
for i,m in enumerate(drum.data.materials):m.name=['D46_DrumPolymer','D46_DrumFasteners','D46_DrumIndex'][i]
# A closed, softly edged transition overlaps the retained neck and drum saddle.
bpy.ops.mesh.primitive_cube_add(size=1,location=(cx,-.0625,-.0675));collar=bpy.context.object;collar.name='D46_NeckTransition';collar.dimensions=(.040,.085,.019);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bev=collar.modifiers.new('Moulded transition radius','BEVEL');bev.width=.003;bev.segments=4;bpy.ops.object.modifier_apply(modifier=bev.name)
norm=collar.modifiers.new('Continuous face normals','WEIGHTED_NORMAL');norm.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=norm.name)
collar.data.materials.append(bpy.data.materials.new('D46_TransitionPolymer'))
for a in [neck,collar]:a.data.transform(root_to_mag@a.matrix_world);a.matrix_world=Matrix.Identity(4)
parts=[drum,neck,collar]
# Export is authored in the exact magazine-bone frame. UE uses identity + 0.01.
for a in parts:
 a['author_frame']='201 WPN_SOCKET_Magazine, metres; UE FBX centimetres with 0.01 runtime compensation'
 if a.data.uv_layers:a.data.uv_layers[0].name='UV0'
 for m in a.data.materials:
  m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  metal='Fasteners' in m.name or 'FactoryNeck' in m.name
  n.inputs['Base Color'].default_value=(.021,.027,.032,1) if metal else (.020,.023,.026,1);n.inputs['Metallic'].default_value=.75 if metal else 0;n.inputs['Roughness'].default_value=.4 if metal else .46
bpy.ops.object.select_all(action='DESELECT')
for a in parts:a.select_set(True)
bpy.context.view_layer.objects.active=drum;bpy.ops.object.join();drum=bpy.context.object;drum.name='SM_LMG201_LargeDrum'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Drum46.blend'))
export=O/'SM_LMG201_LargeDrum.fbx';bpy.ops.export_scene.fbx(filepath=str(export),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
drum.data.calc_loop_triangles();report={'mesh':str(export),'triangles':len(drum.data.loop_triangles),'frame':'201 magazine bone frame','relative_scale':.01,'donor_shell_offset_root_blender_m':list(shift),'slots':[m.name for m in drum.data.materials],'factory_neck_cut_root_z_m':-.064,'source_drum':S['meshes']['drum']['asset'],'source_body':S['rigs']['201']['asset'],'runtime_tested':False}
(O/'model.json').write_text(json.dumps(report,indent=2));print('DRUM46_MODEL_SAVED',report['triangles'],flush=True)
