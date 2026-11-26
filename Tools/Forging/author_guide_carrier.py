"""Update the original ring FBX to the common UV carrier, without rebaking arms."""
import bpy
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ForgeContrast20261024'
EXPORT = OUT / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
name = 'SM_ForgeRing'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
mesh = bpy.data.meshes.new(name)
mesh.from_pydata([(-.0185,-.0185,0),(.0185,-.0185,0),(.0185,.0185,0),(-.0185,.0185,0)], [], [(0,1,2,3)])
mesh.update()
uv = mesh.uv_layers.new(name='UVMap')
for loop, value in zip(uv.data, [(0,0),(1,0),(1,1),(0,1)]): loop.uv = value
obj = bpy.data.objects.new(name, mesh)
bpy.context.collection.objects.link(obj)
mesh.materials.append(bpy.data.materials.new('Guide'))
obj.select_set(True); bpy.context.view_layer.objects.active = obj
tri = obj.modifiers.new('Export triangles', 'TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=tri.name)
target = EXPORT / (name + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Y', axis_up='Z',
    use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Guide_Carrier_Editable.blend'))
original = ROOT / 'SourceAssets/ForgeInteraction20260927' / (name + '.fbx')
backup = OUT / 'BeforeSources' / (name + '.fbx')
backup.parent.mkdir(parents=True, exist_ok=True)
if original.exists() and not backup.exists(): shutil.copy2(original, backup)
shutil.copy2(target, original)
print('FORGE_GUIDE_SOURCE_SAVED ' + str(original), flush=True)
