from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];PREV=ROOT.parent/'DungeonWorkshopSculpt20260921'
m=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(PREV/'Authored/DungeonRooms_WithRefinedWorkshop.blend'))
hide=['SM_WSSculpt_Organizer','SM_WSSculpt_ToolMarkings','SM_WSSculpt_HandTools','SM_WSSculpt_BenchDetail','SM_WSTools_Toolboard','SM_Room_WS_UtilityDetail']
for name in hide:
    ob=bpy.data.objects.get(name)
    if ob:ob.hide_render=True;ob.hide_set(True)
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonWorkshopSurfaceDetails.blend'),link=False) as (src,dst):dst.objects=[e['name'] for e in m['objects']]
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
path=ROOT/'Authored/DungeonRooms_WithWorkshopSurfaces.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('WORKSHOP_SURFACE_ASSEMBLY_SAVED',str(path),'NO_RENDER')
