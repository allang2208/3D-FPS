"""Read imported production geometry to fit cart collision, without rendering."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
result={}
for key,folder,name in [('cart','MedicalCart20260929','SM_Hospital_MedicalCart'),('iv','IVDripCrutch20260929','SM_Hospital_IVDrip_Crutch')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(PROJECT/'SourceAssets'/folder/'Exports'/(name+'.fbx')))
    meshes=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        slots=[]
        for index,material in enumerate(obj.data.materials):
            ids={i for face in obj.data.polygons if face.material_index==index for i in face.vertices}
            if ids:slots.append(dict(name=material.name,min=[min(points[i][k] for i in ids) for k in range(3)],max=[max(points[i][k] for i in ids) for k in range(3)]))
        slices=[]
        for z0,z1 in [(0,.2),(.2,.9),(.9,1.1),(1.1,1.25),(1.25,1.37)]:
            p=[v for v in points if z0<=v.z<=z1]
            if p:slices.append(dict(z=[z0,z1],min=[min(v[k] for v in p) for k in range(3)],max=[max(v[k] for v in p) for k in range(3)]))
        meshes.append(dict(name=obj.name,min=[min(v[k] for v in points) for k in range(3)],max=[max(v[k] for v in points) for k in range(3)],slots=slots,slices=slices))
    result[key]=meshes
(ROOT/'shape-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
