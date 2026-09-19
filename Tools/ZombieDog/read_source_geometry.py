import bpy, json
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogV1')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(R/'Source/SK_Wolf_Source.fbx'), use_anim=False)
rows=[]
for o in bpy.context.scene.objects:
    row={'name':o.name,'type':o.type,'matrix':[list(x) for x in o.matrix_world]}
    if o.type=='ARMATURE':
        row['bones']={b.name:list(o.matrix_world@b.head_local) for b in o.data.bones}
    elif o.type=='MESH':
        points=[o.matrix_world@v.co for v in o.data.vertices]
        row.update(vertices=len(points), faces=len(o.data.polygons), materials=[m.name for m in o.data.materials],
                   bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)])
        row['upper_head_vertices']=[list(p) for p in points if p.x>.025 and p.z>.915]
    rows.append(row)
(R/'Source/geometry_layout.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Source/Wolf_Source.blend'))
print('WOLF_SOURCE_LOADED_FOR_AUTHORING',flush=True)
