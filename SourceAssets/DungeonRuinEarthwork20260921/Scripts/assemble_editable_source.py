"""Save the room source with the fitted earthwork overlay, without rendering."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROOM=ROOT.parent/'DungeonRoomInteriors20260921'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOM/'Authored/DungeonRooms_Dressed.blend'))
for label in manifest['hidden_previous']:
    obj=bpy.data.objects.get(label) or bpy.data.objects.get(label.replace('DGN_Room_','SM_Room_'))
    if obj:obj.hide_render=True;obj.hide_set(True)
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonRuinEarthwork.blend'),link=False) as (src,dst):
    dst.objects=[e['name'] for e in manifest['objects']]
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath and Path(bpy.path.abspath(image.filepath)).exists():image.pack()
target=ROOT/'Authored/DungeonRooms_WithFabEarthwork.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
print('EDITABLE_FAB_EARTHWORK_ASSEMBLY_SAVED',str(target),'NO_RENDER')
