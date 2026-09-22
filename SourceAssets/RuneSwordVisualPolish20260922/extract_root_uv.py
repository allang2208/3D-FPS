"""Read the two actual modules on either side of the blade/guard split."""
from pathlib import Path
import json
import bpy
import numpy as np

P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
arrays={}
for part in ['Blade','Guard']:
    source=P.parent/'RuneSwordModules20260919/Export'/('SM_RuneSword_'+part+'_factory.fbx')
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(source))
    obj=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    obj.data.calc_loop_triangles()
    tris=np.array([list(t.loops) for t in obj.data.loop_triangles])
    uv=np.array([list(p.uv) for p in obj.data.uv_layers[0].data],dtype=np.float32)
    pos=np.array([list(obj.matrix_world@obj.data.vertices[l.vertex_index].co) for l in obj.data.loops],dtype=np.float32)
    arrays[part.lower()+'_uv']=uv[tris];arrays[part.lower()+'_position']=pos[tris]
np.savez_compressed(P/'blade_guard_uv.npz',**arrays)
print('BLADE_GUARD_UV_EXTRACTED')
