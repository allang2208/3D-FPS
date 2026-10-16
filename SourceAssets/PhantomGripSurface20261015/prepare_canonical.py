import bpy,bmesh,math,json,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(O.parent/'PhantomRearGripMultiview_20260913/seed_91627/textured_master_00001_.glb'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.data.transform(high.matrix_world);high.parent=None;high.matrix_world=Matrix.Identity(4);high.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'));high.name='Phantom_SourceHigh'
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='Phantom_ContinuousLow'
bpy.context.view_layer.objects.active=low;bpy.ops.object.select_all(action='DESELECT');low.select_set(True)
if low.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bm=bmesh.new();bm.from_mesh(low.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=5e-6);bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(low.data);bm.free()
for f in low.data.polygons:f.use_smooth=True
dec=low.modifiers.new('Curvature retaining reduction','DECIMATE');dec.ratio=120000/len(low.data.polygons);dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
high.hide_render=True;high.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Phantom_Canonical.blend'))
D=json.loads((O/'capture.json').read_text());meta={}
for k,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['export']);ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data
 meta[k]={'materials':[m.name for m in me.materials],'uv':[u.name for u in me.uv_layers],'colors':[(a.name,a.domain,a.data_type) for a in me.color_attributes]}
 print('CURRENT_METADATA',k,meta[k],flush=True)
with bpy.data.libraries.load(str(O.parent/'LMG201GripSolidJunction20261007/SM_LMG201_phantom_reargrip.blend'),link=False) as (a,b):b.objects=a.objects
ob=next(o for o in b.objects if o and o.type=='MESH');me=ob.data
uv=np.asarray([tuple(a.uv) for a in me.uv_layers[4].data]);print('LMG_SOURCE_UV4',len(me.polygons),uv.min(0),uv.max(0),flush=True)
(O/'current_metadata.json').write_text(json.dumps(meta,indent=2))
