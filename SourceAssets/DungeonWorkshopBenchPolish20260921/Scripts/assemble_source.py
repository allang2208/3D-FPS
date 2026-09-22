from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];PREV=ROOT.parent/'DungeonWorkshopFabTools20260921'
m=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(PREV/'Authored/DungeonRooms_WithFabWorkshopTools.blend'))
for name in ('SM_WSSculpt_BenchTop','SM_WSSculpt_TaskLamp','SM_WSSculpt_BenchWear','SM_WSTools_TaskCable'):
    ob=bpy.data.objects.get(name)
    if ob:ob.hide_render=True;ob.hide_set(True)
motor=bpy.data.objects.get('DGN_Room_WS_RepairMotor')
if motor:bpy.data.objects.remove(motor,do_unlink=True)
with bpy.data.libraries.load(m['source_blend'],link=False) as (src,dst):dst.objects=[e['name'] for e in m['objects']]
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonRooms_WithBenchPolish.blend'))
print('BENCH_POLISH_EDITABLE_ROOM_ASSEMBLY_SAVED_NO_RENDER')
