"""Capture unchanged R4 UV/tangent data and actual factory steel source triangles."""
from pathlib import Path
import bpy,json,shutil
import numpy as np

P=Path(__file__).resolve().parent
R4=P.parent
HATCHET=R4.parents[1]
for folder in ['Before','Textures','Icons']:(P/folder).mkdir(parents=True,exist_ok=True)
for name in ['SwiftCrescent_Editable.blend','SwiftCrescent.json','author.py','import_assets.py','register.py','README.md','delivery.json']:
    dst=P/'Before'/name
    if not dst.exists():shutil.copy2(R4/name,dst)
for folder in ['Textures','Icons']:
    (P/'Before'/folder).mkdir(exist_ok=True)
    for path in (R4/folder).glob('*.png'):
        if not (P/'Before'/folder/path.name).exists():shutil.copy2(path,P/'Before'/folder/path.name)
bpy.ops.wm.open_mainfile(filepath=str(P/'Before/SwiftCrescent_Editable.blend'))
entry=json.loads((P/'Before/SwiftCrescent.json').read_text('utf-8'))
target=bpy.data.objects[entry['object']]
mesh=target.data;mesh.calc_loop_triangles();mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
triangles=list(mesh.loop_triangles)
np.savez_compressed(P/'target_surface.npz',
    points=np.array([[mesh.vertices[v].co[:] for v in tri.vertices] for tri in triangles]),
    uv=np.array([[mesh.uv_layers[0].data[li].uv[:] for li in tri.loops] for tri in triangles]),
    normals=np.array([[mesh.corner_normals[li].vector[:] for li in tri.loops] for tri in triangles]),
    tangents=np.array([[mesh.loops[li].tangent[:] for li in tri.loops] for tri in triangles]),
    signs=np.array([[mesh.loops[li].bitangent_sign for li in tri.loops] for tri in triangles]))
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory'];mesh=factory.data;mesh.calc_loop_triangles()
uv=[];points=[];normals=[]
for tri in mesh.loop_triangles:
    corners=np.array([mesh.vertices[v].co[:] for v in tri.vertices]);center=corners.mean(axis=0)
    if center[2]>.18 and center[0]>.025 and abs(tri.normal.y)>.65:
        uv.append([mesh.uv_layers[0].data[li].uv[:] for li in tri.loops]);points.append(corners);normals.append(tri.normal[:])
np.savez_compressed(P/'factory_steel.npz',uv=np.array(uv),points=np.array(points),normals=np.array(normals))
sources={key:str(HATCHET/'Textures'/('source_image_%02d.png'%index)) for key,index in [('BaseColor',1),('ORM',2),('Normal',0)]}
(P/'surface_source.json').write_text(json.dumps({'target':entry['mesh'],'source_mesh':factory.name,
    'factory_material':'/Game/Weapons/TacticalHatchet20261101/Materials/M_TacticalHatchet',
    'textures':sources,'source_blend':str(HATCHET/'ModulesV1/TacticalHatchet_Modules_Editable.blend'),
    'geometry_modified':False,'uv_modified':False,'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
print('FACTORY_SURFACE_CAPTURED source_triangles='+str(len(uv))+' target_triangles='+str(len(triangles)),flush=True)
