from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];PREV=ROOT.parent/'DungeonWorkshopSurface20260921'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(PREV/'Authored/DungeonRooms_WithWorkshopSurfaces.blend'))
for name in ('SM_WSFinish_HandTools','SM_WSFinish_BenchDetail','SM_WSFinish_ToolMarkings'):
    ob=bpy.data.objects.get(name)
    if ob:ob.hide_render=True;ob.hide_set(True)
with bpy.data.libraries.load(manifest['source_blend'],link=False) as (src,dst):
    dst.objects=[e['name'] for e in manifest['objects'] if e.get('actor')]
for ob in dst.objects:
    bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
path=ROOT/'Authored/DungeonRooms_WithFabWorkshopTools.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('FAB_WORKSHOP_EDITABLE_ASSEMBLY_SAVED '+str(path)+' NO_RENDER')
