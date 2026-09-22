"""Carry the completed workshop revision into a copy of the editable dungeon source."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
base=ROOT.parent/'DungeonRuinEarthwork20260921/Authored/DungeonRooms_WithFabEarthwork.blend'
bpy.ops.wm.open_mainfile(filepath=str(base))
for e in manifest['objects']:
    if not e['replace']:continue
    obj=bpy.data.objects.get(e['actor'].replace('DGN_Room_','SM_Room_'))
    if obj:obj.hide_render=True;obj.hide_set(True)
for label in manifest['remove_actors']:
    obj=bpy.data.objects.get(label.removeprefix('DGN_AV2_'))
    if obj:obj.hide_render=True;obj.hide_set(True)
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonWorkshopDetail.blend'),link=False) as (src,dst):
    dst.objects=[e['name'] for e in manifest['objects']]
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath and Path(bpy.path.abspath(image.filepath)).exists():image.pack()
output=ROOT/'Authored/DungeonRooms_WithWorkshopDetails.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
print('EDITABLE_WORKSHOP_ASSEMBLY_SAVED',str(output),'NO_RENDER')
