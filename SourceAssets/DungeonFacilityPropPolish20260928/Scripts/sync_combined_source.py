"""Replace only cabinet/cargo objects in the existing combined editable Blender source."""
import shutil
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
combined = ROOT.parent / 'DungeonFacilityScenes20260927/Authored/FacilityAssemblies.blend'
backup = ROOT / 'Backup/AuthorChain/FacilityAssemblies.blend'
if not backup.exists():
    shutil.copy2(combined, backup)
bpy.ops.wm.open_mainfile(filepath=str(combined))
names = ['SM_Facility_PowerCabinet', 'SM_Facility_CargoStack']
positions = {name: bpy.data.objects[name].location.copy() for name in names}
for obj in list(bpy.data.objects):
    if obj.name in names or any(obj.name.startswith('UCX_' + name + '_') for name in names):
        bpy.data.objects.remove(obj, do_unlink=True)

with bpy.data.libraries.load(str(ROOT / 'Authored/FacilityProps_Polished.blend'), link=False) as (source, dest):
    dest.objects = [name for name in source.objects
                    if name in names or any(name.startswith('UCX_' + target + '_') for target in names)]
objects = {obj.name: obj for obj in dest.objects if obj}
for obj in objects.values():
    bpy.context.scene.collection.objects.link(obj)
for name in names:
    obj = objects[name]
    delta = positions[name] - obj.location
    obj.location += delta
    for other in objects.values():
        if other.name.startswith('UCX_' + name + '_'):
            other.location += delta
            other.hide_viewport = True
            other.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(combined))
print('FACILITY_COMBINED_SOURCE_UPDATED', len(names), flush=True)
