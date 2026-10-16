import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());row=D['assets']['LMG201'];X=O/'Working'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['export']);old=next(o for o in bpy.context.scene.objects if o.type=='MESH')
with bpy.data.libraries.load(str(O.parent/'LMG201GripSolidJunction20261007/SM_LMG201_phantom_reargrip.blend'),link=False) as (a,b):b.objects=a.objects
source=next(o for o in b.objects if o and o.type=='MESH');me=source.data;me.calc_loop_triangles()
p=np.array([tuple(source.matrix_world@v.co) for v in me.vertices]);t=np.array([list(f.vertices) for f in me.loop_triangles]);uv=np.array([tuple(v.uv) for v in me.uv_layers[4].data]);li=np.array([list(f.loops) for f in me.loop_triangles]);np.savez_compressed(X/'LMG201_source_uv4.npz',positions=p,triangles=t,uv4=uv[li])
print('LMG201_SOURCE_EXTRACTED',len(t),flush=True)
