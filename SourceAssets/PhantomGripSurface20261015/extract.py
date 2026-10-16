import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;X=O/'Working';X.mkdir(exist_ok=True)
D=json.loads((O/'capture.json').read_text())
def data(ob):
 me=ob.data;me.calc_loop_triangles();nm=ob.matrix_world.to_3x3().inverted().transposed()
 d={'positions':np.asarray([tuple(ob.matrix_world@v.co) for v in me.vertices]),'triangles':np.asarray([list(f.vertices) for f in me.polygons],dtype=np.int32),'mids':np.asarray([f.material_index for f in me.polygons],dtype=np.int32),'normals':np.asarray([tuple((nm@n.vector).normalized()) for n in me.corner_normals]).reshape(-1,3,3),'sharp':np.asarray([e.use_edge_sharp for e in me.edges])}
 for i,uv in enumerate(me.uv_layers):d['uv'+str(i)]=np.asarray([tuple(v.uv) for v in uv.data]).reshape(-1,3,2)
 return d
for key,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['export']);ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');np.savez_compressed(X/(key+'.npz'),**data(ob));print('EXTRACT',key,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_HighNormalProbe.blend'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.polygons)>400000)
np.savez_compressed(X/'M4_high.npz',**data(ob))
entry=O/'diagnose.py';exec(compile(entry.read_text(encoding='utf-8').split("for key in ['M4'")[0],str(entry),'exec'))
cur,scene=setup('M4');cur.hide_render=True
path=O.parent/'RearGripFinish20260913/M4/phantom/Editable.blend'
with bpy.data.libraries.load(str(path),link=False) as (a,b):
 print('SOURCE_OBJECTS',a.objects,flush=True);b.objects=['SM_PhantomRearGrip']
ob=b.objects[0];bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
np.savez_compressed(X/'M4_original.npz',**data(ob))
for i in range(len(ob.data.materials)):ob.data.materials[i]=cur.data.materials[0]
scene.cycles.samples=24;scene.render.filepath=str(O/'Preview/M4_original_low.png');bpy.ops.render.render(write_still=True)
print('SOURCE_LOW_COMPLETE',len(ob.data.polygons),flush=True)
