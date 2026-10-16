import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());row=D['assets']['LMG201'];X=O/'Working'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.import_scene.fbx(filepath=row['export']);ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data
# The source constructor stores its shoulder mask as (z - cut) / neck height.
s=np.load(X/'LMG201_source_uv4.npz');q=s['positions'][s['triangles']];truth=np.clip((q[:,:,2]+.030)/.036,0,1);delta=abs(truth-s['uv4'][:,:,0]);assert delta.max()<2e-6,delta.max()
p=np.asarray([tuple(ob.matrix_world@v.co) for v in me.vertices]);li=np.asarray([l.vertex_index for l in me.loops]);mask=np.column_stack((np.clip((p[li,2]+.030)/.036,0,1),np.zeros(len(li))));me.uv_layers[4].data.foreach_set('uv',mask.astype(np.float32).ravel())
ns=np.asarray([tuple(n.vector) for n in me.corner_normals]);bad=np.linalg.norm(ns,axis=1)<.9
for f in me.polygons:
 for l in f.loop_indices:
  if bad[l]:ns[l]=f.normal
me.normals_split_custom_set(ns)
for i,m in enumerate(me.materials):m.name=row['slots'][i]['name']
ob.name=row['path'].rsplit('/',1)[1];bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
fbx=O/'Exports/LMG201.fbx';blend=fbx.with_suffix('.blend');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True);bpy.ops.wm.save_as_mainfile(filepath=str(blend))
R=json.loads((O/'production.json').read_text());R['assets']['LMG201']={'fbx':str(fbx),'blend':str(blend),'body_slot':1,'triangles':len(me.polygons),'preserved_interface_triangles':'all geometry unchanged','geometry_unchanged':True,'restored_mask_corners':int((mask[:,0]>.00001).sum()),'repaired_zero_normals':int(bad.sum()),'source_mask_formula_max_error':float(delta.max()),'materials':[m.name for m in me.materials]};R['complete']=len(R['assets'])==9;(O/'production.json').write_text(json.dumps(R,indent=2));print('PHANTOM_LMG_MASK_RESTORED',flush=True)
