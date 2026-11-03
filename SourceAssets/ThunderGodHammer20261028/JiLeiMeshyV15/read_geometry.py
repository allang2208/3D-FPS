import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
def metadata(o):
    o.data.calc_loop_triangles()
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    return dict(name=o.name,vertices=len(vs),triangles=len(o.data.loop_triangles),bounds=[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],materials=[s.material.name if s.material else None for s in o.material_slots],matrix=[list(r) for r in o.matrix_world])
bpy.ops.import_scene.gltf(filepath=str(P/'Original/Meshy_AI_Nordic_Aegis_Shield_1101101638_texture.glb'))
meshy=[metadata(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='Cube']
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'JiLeiInlaidLightningV14/JiLei_V14_Editable.blend'))
names=['20_NativeLeftHeadInterface','21_NativeRightHeadInterface','22_NativeNeckInterface','01_HeadInterfaceLoadWeb','01_HeadInterfaceLoadWeb.001','SM_ThunderGodHammer_hammer_heads_factory','SM_ThunderGodHammer_neck_factory']
native=[metadata(bpy.data.objects[n]) for n in names if n in bpy.data.objects]
r=dict(meshy=meshy,native=native)
(P/'Original/geometry_source.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r,indent=2))
