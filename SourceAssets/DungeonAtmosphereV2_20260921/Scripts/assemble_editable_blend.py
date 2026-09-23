"""Save an editable structure-and-props source scene, without rendering it.

The UE map remains authoritative for game materials, lighting and decals.
"""
import bpy
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
placements=json.loads((ROOT/'layout.json').read_text())['props']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/DungeonAtmosphereV2_Structure.blend'))
library=bpy.data.collections.new('Generated prop sources');bpy.context.scene.collection.children.link(library)
instances=bpy.data.collections.new('Dressed corridor');bpy.context.scene.collection.children.link(instances)
sources={}
for prop in json.loads((ROOT/'assets.json').read_text())['props']:
    ident=prop['id'];filename=ROOT/'Generated'/ident/'Game'/(ident+'_Editable.blend')
    with bpy.data.libraries.load(str(filename),link=False) as (src,dst):
        dst.objects=['SM_V2_'+ident]
    model=dst.objects[0];library.objects.link(model)
    model.hide_render=True;model.hide_set(True);sources[ident]=model
for placement in placements:
    ident=placement['id']
    if ident not in sources:continue
    original=sources[ident];obj=original.copy();instances.objects.link(obj)
    obj.name=placement['label'];obj.hide_render=False;obj.hide_set(False)
    x,y,z=placement['cm'];obj.location=(x/100,y/100,z/100)
    obj.rotation_euler=(0,0,math.radians(-placement['yaw']));obj.scale=placement['scale']

# Rejected generated statue and its active-source marker were retired 2026-09-22.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonAtmosphereV2_Dressed.blend'))
print('EDITABLE_DRESSED_BLEND_SAVED_NO_RENDER')
