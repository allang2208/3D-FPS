"""Extract authored donor geometry/UV/tangent frames, without rendering."""
from pathlib import Path
import bpy
import numpy as np
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
source=P.parent/'FrostSwordModules20260915/Export/SM_FrostSword_Blade_factory.fbx'
bpy.ops.import_scene.fbx(filepath=str(source))
obj=next(o for o in bpy.data.objects if o.type=='MESH')
mesh=obj.data
mesh.calc_loop_triangles()
mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
tri=np.array([list(t.loops) for t in mesh.loop_triangles])
pos=np.array([list(obj.matrix_world@mesh.vertices[l.vertex_index].co) for l in mesh.loops])
uv=np.array([list(p.uv) for p in mesh.uv_layers[0].data])
rot=obj.matrix_world.to_3x3()
norm=np.array([list((rot@n.vector).normalized()) for n in mesh.corner_normals])
tan=np.array([list((rot@l.tangent).normalized()) for l in mesh.loops])
sign=np.array([l.bitangent_sign for l in mesh.loops])
np.savez_compressed(P/'donor.npz',position=pos[tri],uv=uv[tri],normal=norm[tri],tangent=tan[tri],sign=sign[tri])
print('FROST_GEOMETRY_EXTRACTED',pos.min(axis=0).tolist(),pos.max(axis=0).tolist())
