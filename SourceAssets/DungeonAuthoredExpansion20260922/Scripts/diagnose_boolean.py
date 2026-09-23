import bpy,json,bmesh
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
base=ROOT.parents[1]/'SourceAssets/DungeonAtmosphereV2_20260921/Authored/DungeonAtmosphereV2_Structure.blend'
with bpy.data.libraries.load(str(base),link=False) as (src,dst):dst.objects=['SM_V2_ServiceDoor']
obj=dst.objects[0];bpy.context.scene.collection.objects.link(obj)
def bounds(o):
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    return [[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]]
print('ORIGINAL',bounds(obj))
bm=bmesh.new();bm.from_mesh(obj.data)
print('SIGNED_VOLUME_BEFORE',bm.calc_volume(signed=True))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
print('SIGNED_VOLUME_AFTER',bm.calc_volume(signed=True))
bm.to_mesh(obj.data);bm.free();obj.data.update()
bpy.ops.mesh.primitive_cube_add(size=1,location=(24,13.86,2.15))
c=bpy.context.object;c.dimensions=(1.322,.13,2.282)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.context.view_layer.update()
print('CUTTER',bounds(c),c.matrix_world)
bm=bmesh.new();bm.from_mesh(c.data);print('CUTTER_VOLUME',bm.calc_volume(signed=True));bm.free()
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
mod=obj.modifiers.new('cut','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='FLOAT';mod.object=c
print('MODIFIERS',[(m.name,m.type) for m in obj.modifiers],mod.operation,mod.solver);bpy.ops.object.modifier_apply(modifier=mod.name)
print('RESULT',bounds(obj),len(obj.data.vertices))
