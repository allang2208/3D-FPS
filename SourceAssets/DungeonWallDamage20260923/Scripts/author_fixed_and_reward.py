"""Refresh the fixed start's wall skins and the final reward room, keeping world transforms."""
import ast,json,os
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
LIB=BASE/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
H={'__file__':str(LIB),'__name__':'fixed_wall_author'}
exec(compile(LIB.read_text(encoding='utf-8').split("for index,room in enumerate(CFG['rooms']):",1)[0],str(LIB),'exec'),H)
tree=ast.parse((BASE/'DungeonWallRelief20260922/Scripts/author_walls.py').read_text())
spans=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SPANS' for t in n.targets))
manifest=json.loads((ROOT/'Authored/manifest.json').read_text());surfaces=H['SURFACES']
for rid,rows in spans.items():
    H['ROOM']=dict(id='Start_'+rid+'_Damage0',surface_seed_id='Start_'+rid,surface_variant=0,origin_m=[0,0,0],export_kinds=['Tiles'])
    H['GROUPS']={}
    for axis,a,b,fixed,inside in rows:
        start=Vector((a,fixed) if axis=='x' else (fixed,a));direction=Vector((1,0) if axis=='x' else (0,1))
        normal=Vector((0,inside) if axis=='x' else (inside,0))
        first=len(H['group']('Tiles')['f'])
        surfaces.wall(H,start,direction,normal,b-a,(),None,.24)
        # The shared wall emitter expects its normal to be left of the direction.
        if (axis=='x' and inside<0) or (axis=='y' and inside>0):
            g=H['group']('Tiles')
            for i in range(first,len(g['f'])):g['f'][i]=tuple(reversed(g['f'][i]));g['uv'][i]=list(reversed(g['uv'][i]))
    H['export']();record=H['RECORDS'][-1]
    record.update(source_mesh='/Game/Dungeons/AtmosphereV2/TileFracture/Meshes/SM_TileFracture_'+rid,variant=0,fixed_start=True)
    manifest['objects'].append(record)
for variant in range(3):
    H['ROOM']=dict(id='FinalRewardRoom_Damage'+str(variant),surface_seed_id='FinalRewardRoom',surface_variant=variant,origin_m=[0,0,0],export_kinds=['Tiles'])
    H['GROUPS']={};outline=[[-2.3,26],[9.7,26],[9.7,36.5],[-2.3,36.5]]
    # Only these three sides are tiled in the source. The machinery gate owns the front wall.
    for a,b in zip(outline[1:],outline[2:]+outline[:1]):H['wall'](a,b,4.2)
    H['export']();record=H['RECORDS'][-1]
    record.update(source_mesh='/Game/Dungeons/FinalReward20260923/Meshes/SM_RS_FinalRewardRoom_Tiles',variant=variant)
    manifest['objects'].append(record)
manifest['skipped']=[x for x in manifest['skipped'] if 'FinalRewardRoom_Tiles' not in x['mesh']]
(ROOT/'Authored/manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'Authored/fixed-distribution.json').write_text(json.dumps(surfaces.placements,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonFixedWallDamage.blend'))
print('FIXED_AND_REWARD_WALLS_AUTHORED',len(H['RECORDS']),flush=True)
