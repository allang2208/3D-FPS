import bpy,math,json
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
source=next(P.glob('enhancement_stone_high_textured_master*.glb'))
bpy.ops.import_scene.gltf(filepath=str(source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];rot=Matrix.Rotation(math.pi/2,4,'Y')
for o in objects:
    matrix=rot@o.matrix_world
    for v in o.data.vertices:v.co=matrix@v.co
    o.matrix_world=Matrix.Identity(4)
points=[v.co for o in objects for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=.14/(hi.z-lo.z)
for o in objects:
    o.name='Enhancement stone / 5080 high detail'
    for v in o.data.vertices:v.co=(v.co-origin)*scale
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'enhancement_stone_display_editable.blend'))
bpy.ops.export_scene.gltf(filepath=str(P/'enhancement_stone_display_candidate.glb'),export_format='GLB')
(P/'enhancement_stone_display_provenance.json').write_text(json.dumps({'source':source.name,'changes':'Rigid rotation 90 degrees about Blender Y; proposed height 14 cm; origin centered at bottom. No geometry regeneration or material replacement.','engine_integration':False},indent=2))
