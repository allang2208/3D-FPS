from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT.parent/'DungeonWorkshopTools20260921'
m=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OLD/'Authored/DungeonRooms_WithWorkshopTools.blend'))
names=['SM_WSTools_'+k for k in ('BenchFrame','BenchTop','BenchDetail','HandTools','TaskLamp','CeilingFixtures','Rag','ToolMarkings','BenchWear','ToolWear','TaskCable')]
for name in names:
    ob=bpy.data.objects.get(name)
    if ob:ob.hide_render=True;ob.hide_set(True)
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonWorkshopComponents.blend'),link=False) as (src,dst):dst.objects=[e['name'] for e in m['objects']]
for ob in dst.objects:bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
path=ROOT/'Authored/DungeonRooms_WithRefinedWorkshop.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path));print('REFINED_WORKSHOP_ASSEMBLY_SAVED',str(path),'NO_RENDER')
