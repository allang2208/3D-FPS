import bpy, json
from pathlib import Path
from mathutils import Vector
source=Path('D:/FPS3D/VaultCache/FabLibrary/Plastic_Water_Bottle-543bb27e/fbx/water_bottle_extracted/Files/Water Bottle.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
report=[]
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    pts=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    report.append(dict(name=obj.name,vertices=len(obj.data.vertices),faces=len(obj.data.polygons),bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]],materials=[m.name if m else None for m in obj.data.materials],modifiers=[dict(name=m.name,type=m.type) for m in obj.modifiers],rotation=list(obj.rotation_euler),scale=list(obj.scale),location=list(obj.location)))
Path(__file__).with_name('source_geometry.json').write_text(json.dumps(report,indent=2))
print('SOURCE_GEOMETRY '+json.dumps(report))
