"""Author one original faceted stone, in metres; FBX import produces ~2 cm width."""
from pathlib import Path
import bpy, random

P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1.0
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.01)
stone=bpy.context.object;stone.name='SM_WarhammerDebris'
r=random.Random(191014)
for v in stone.data.vertices:
    v.co*=r.uniform(.72,1.14)
    v.co.y*=.74
    v.co.z*=.62
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WarhammerDebris.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'SM_WarhammerDebris.fbx'),use_selection=True,
    object_types={'MESH'},apply_unit_scale=True,global_scale=1.,axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False)
