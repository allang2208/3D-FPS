"""Read anatomical authoring inputs for the requested local quadruped binding."""
import bpy,json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/InfectedDogMeshy20260924/LocalRig'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/ZombieDogV1/Source/Wolf_Source.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
bpy.context.view_layer.update()
world=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()
source={'rig':rig.name,'world_matrix':[list(r) for r in world], 'bones':[
    {'name':b.name,'parent':b.parent.name if b.parent else None,
     'head':list(world@b.head_local),'tail':list(world@b.tail_local),
     'deform':b.use_deform,'roll_matrix':[list(r) for r in b.matrix_local]}
    for b in rig.data.bones]}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'SourceAssets/InfectedDogMeshy20260924/Meshy/candidate01_quad50k/downloads/model.glb'))
meshes=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    points=[o.matrix_world@Vector(p) for p in o.bound_box]
    meshes.append({'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),
        'min':[min(p[i] for p in points) for i in range(3)],
        'max':[max(p[i] for p in points) for i in range(3)],
        'matrix':[list(r) for r in o.matrix_world],
        'materials':[m.name for m in o.data.materials]})
(OUT/'binding_inputs.json').write_text(json.dumps({'source':source,'target_meshes':meshes},indent=2),encoding='utf-8')
print('Binding context saved to',OUT/'binding_inputs.json')
