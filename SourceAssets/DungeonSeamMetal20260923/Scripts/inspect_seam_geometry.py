"""Bounded geometry diagnosis for the two reported treasure-link interfaces."""
import json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
rows={}
for label,path in [('before',ROOT.parent/'DungeonTreasure20260922/Authored/Dungeon_DistinctRoomShells.blend'),
                   ('after',ROOT/'Authored/Dungeon_DistinctRoomShells.blend')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n.startswith('SM_RS_TreasureLink_')]
    faces=0
    for obj in dst.objects:
        if not obj or obj.type!='MESH':continue
        for face in obj.data.polygons:
            vs=[obj.data.vertices[i].co for i in face.vertices]
            if min(v.y for v in vs)>.1451 and max(v.y for v in vs)<1.8549:continue
            at_x=any(all(abs(v.x-sign*1.5)<.0001 for v in vs) for sign in (-1,1))
            at_z=all(abs(v.z-2.8)<.0001 for v in vs)
            if at_x or at_z:faces+=1
    rows[label]=dict(coplanar_faces_crossing_frame_zone=faces)
rows['scope']='Authored connector planes only; no PIE/render/game test'
(ROOT/'Receipts/seam-geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('TREASURE_CONNECTOR_PLANES',json.dumps(rows),flush=True)
