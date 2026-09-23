"""Append the current authored cabinet placements to an already open room source."""
import bpy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
for placement in manifest['config']['placements']:
    existing=bpy.data.objects.get(placement['label'])
    if existing:bpy.data.objects.remove(existing,do_unlink=True)
    with bpy.data.libraries.load(manifest['source_blend'],link=False) as (source,target):target.objects=[manifest['name']]
    ob=target.objects[0];bpy.context.scene.collection.objects.link(ob);ob.name=placement['label']
    x,y,z=placement['location_cm'];ob.location=(x/100,-y/100,z/100);ob.rotation_euler=(0,0,math.radians(-placement['yaw']))
    ob.hide_render=False;ob.hide_set(False)
