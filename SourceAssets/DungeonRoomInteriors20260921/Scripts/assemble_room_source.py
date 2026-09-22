"""Assemble the two approved room revisions into an editable source, no render."""
import bpy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
manifest=json.loads((ROOT/'Authored/room-manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OLD/'Authored/DungeonAtmosphereV2_Dressed.blend'))
for label in manifest['hidden_existing']+['DGN_AV2_LightFixtures']:
    short=label.removeprefix('DGN_AV2_');obj=bpy.data.objects.get('SM_V2_'+short) or bpy.data.objects.get(short)
    if obj:obj.hide_render=True;obj.hide_set(True)
with bpy.data.libraries.load(str(ROOT/'Authored/DungeonRooms_Authored.blend'),link=False) as (src,dst):dst.objects=[e['name'] for e in manifest['objects']]
for obj in dst.objects:bpy.context.scene.collection.objects.link(obj)
for p in manifest['prop_moves']:
    obj=bpy.data.objects.get(p['label'].removeprefix('DGN_AV2_'))
    if not obj:raise RuntimeError('Source prop missing '+p['label'])
    obj.location=[v/100 for v in p['cm']];obj.rotation_euler=(0,0,math.radians(-p['yaw']));obj.scale=p['scale']
masters={}
for p in manifest['new_generated']:
    ident=p['id']
    if ident not in masters:
        with bpy.data.libraries.load(str(ROOT/'Generated'/ident/'Game'/(ident+'_Editable.blend')),link=False) as (src,dst):dst.objects=['SM_Room_'+ident]
        masters[ident]=dst.objects[0]
    obj=masters[ident].copy();bpy.context.scene.collection.objects.link(obj);obj.name=p['label']
    obj.hide_render=False;obj.hide_set(False);obj.location=[v/100 for v in p['cm']];obj.rotation_euler=(0,0,math.radians(-p['yaw']));obj.scale=p['scale']
marker=bpy.data.objects.get('Existing Goddess UE asset - anchor')
if marker:marker.location=[v/100 for v in manifest['statue_anchor_blender_cm']]
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonRooms_Dressed.blend'))
print('EDITABLE_ROOM_ASSEMBLY_SAVED_NO_RENDER')
