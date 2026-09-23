from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];MAN=json.loads((ROOT/'Authored/manifest.json').read_text());CFG=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'DungeonWorkshopBenchPolish20260921/Authored/DungeonRooms_WithBenchPolish.blend'))
for name in [e.get('source_object') for e in MAN['components']]+['SM_WSBench_TaskCable']:
    ob=bpy.data.objects.get(name) if name else None
    if ob:ob.hide_render=True;ob.hide_set(True)
with bpy.data.libraries.load(MAN['source_blend'],link=False) as (src,dst):dst.objects=[e['name'] for e in MAN['components']]
parent=bpy.data.objects.new('WorkbenchKit_InUse',None);bpy.context.scene.collection.objects.link(parent);r=CFG['root']['world_location'];parent.location=(r[0]/100,-r[1]/100,r[2]/100)
for ob in dst.objects:
    bpy.context.scene.collection.objects.link(ob);ob.parent=parent;ob.hide_render=False;ob.hide_set(False)
surrounding_sources=ROOT/'Config/surrounding-sources.json'
if surrounding_sources.exists():
    for entry in json.loads(surrounding_sources.read_text())['overrides']:
        for old_name in entry['replacements']:
            ob=bpy.data.objects.get(old_name)
            if ob:ob.hide_render=True;ob.hide_set(True)
        with bpy.data.libraries.load(entry['source_blend'],link=False) as (src,dst):dst.objects=list(entry['replacements'].values())
        for ob in dst.objects:
            bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
maintenance=ROOT.parent/'DungeonMaintenance20260922'
if (maintenance/'Authored/manifest.json').exists():
    import runpy
    runpy.run_path(str(maintenance/'Scripts/append_to_blend.py'),run_name='__main__')
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonRooms_WithWorkbenchKit.blend'))
print('WORKBENCH_EDITABLE_ROOM_SAVED_NO_RENDER')
