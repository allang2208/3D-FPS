"""Apply the current author furniture transforms to the owned Blender source only."""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Config/room.json').read_text('utf-8'))
source=ROOT/(cfg['current_authored_source'] if cfg.get('container_interaction_revision',0)>=1 else 'IntactTilesV4/Authored/StaffLivingTheme_IntactTilesV4.blend' if cfg.get('layout_revision',0)>=4 else 'RefinementV3/Authored/StaffLivingTheme_RefinementV3.blend' if cfg.get('layout_revision',0)>=3 else 'Authored/StaffLivingTheme_Source.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
for room,offset in zip(cfg['rooms'],cfg['preview_placements_m']):
    for part in room['furniture']:
        name=room['id']+'_'+part['id']
        searchable=cfg.get('container_interaction_revision',0)>=1 and part['prototype'] in ('Locker','LockerOpen','Bookcase','Bookshelf','Bedside')
        obj=bpy.data.objects[name+('_Body' if searchable else '')]
        obj.location=tuple(part['position'][i]+offset[i] for i in range(3))
        obj.rotation_euler.z=math.radians(part['yaw_blender_deg'])
        if searchable and (part['prototype']!='Bookshelf' or cfg.get('container_open_parts_revision',0)>=3):
            hinge=bpy.data.objects[name+'_Hinge']
            pivot=(-.439,-.215,0) if part['prototype']=='Bookcase' else (0,0,0) if part['prototype'] in ('Bedside','Bookshelf') else (-.29,-.284,0)
            hinge.location=obj.location+obj.rotation_euler.to_matrix()@Vector(pivot)
            hinge.rotation_euler=obj.rotation_euler.copy()
bpy.ops.wm.save_as_mainfile(filepath=str(source))
print('STAFF_LIVING_SOURCE_PLACEMENTS_SAVED')
