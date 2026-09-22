"""Update a copy of the editable dungeon assembly, keeping old versions hidden for editing."""
from pathlib import Path
import json,bpy
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT.parent/'DungeonWorkshopDetail20260921'
m=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OLD/'Authored/DungeonRooms_WithWorkshopDetails.blend'))
for e in m['objects']:
    if not e['replace']:continue
    names=[e['actor'].replace('DGN_Room_','SM_Room_')]
    if e['actor']=='DGN_AV2_LightFixtures':names=['SM_Room_FixturesWithoutRuin','SM_V2_LightFixtures']
    for name in names:
        ob=bpy.data.objects.get(name)
        if ob:ob.hide_render=True;ob.hide_set(True)
names=[e['name'] for e in m['objects'] if e['name']!='SM_WSTools_OtherFixtures']
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonWorkshopTools.blend'),link=False) as (src,dst):dst.objects=names
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
path=ROOT/'Authored/DungeonRooms_WithWorkshopTools.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('WORKSHOP_TOOLS_EDITABLE_ASSEMBLY_SAVED',str(path),'NO_RENDER')
