import os,runpy,json,random
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
cfg=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
# Standard room library produces the exact accepted walls, tiled fractures, pipes and trim.
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
source=LIB.read_text(encoding='utf-8')
source=source.replace("for index,room in enumerate(CFG['rooms']):", "for index,room in enumerate([r for r in CFG['rooms'] if r.get('source_id') not in ('VentilationLoop','FreightTransfer')]):")
exec(compile(source,str(LIB),'exec'),{'__file__':str(LIB),'__name__':'__main__'})
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
# The new rooms have custom architecture in Shell; preserve it when opening their side wall.
vf=ROOT.parent/'DungeonVentFreight20260922/Scripts/author.py'
scope={'__file__':str(vf),'__name__':'variant_author'}
exec(compile(vf.read_text(encoding='utf-8').split("for index,room in enumerate(H['CFG']['rooms']):",1)[0],str(vf),'exec'),scope)
H=scope['H'];H['ROOT']=ROOT;H['OUT']=ROOT/'Authored';H['RECORDS']=[]
for index,room in enumerate(r for r in cfg['rooms'] if r.get('source_id') in ('VentilationLoop','FreightTransfer')):
    H['ROOM']=room;H['GROUPS']={};H['R']=random.Random(cfg['seed']+index)
    scope['ventilation' if room['source_id']=='VentilationLoop' else 'freight']()
    for edge,(a,b) in enumerate(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1])):
        H['wall'](a,b,room['height_m'],[o for o in room['openings'] if o['edge']==edge])
    for x,y in room['columns']:H['box']('Shell',(x,y,room['height_m']/2),(.32,.32,room['height_m']))
    for a,b in room['beams']:H['bar']('Shell',a,b,.32,.32)
    H['export']()
manifest['objects']+=H['RECORDS']
(ROOT/'Authored/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/NewRoomSideWalls.blend'))
# Reuse the sealed start transition with only its output aperture adjusted to the repaired connectors.
src=ROOT.parent/'DungeonDoorTransitions20260922/Scripts/author_transition.py'
text=src.read_text(encoding='utf-8').replace("ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]",f"ROOT=Path({str(ROOT)!r});PROJECT=ROOT.parents[1]")
text=text.replace("config=json.loads((ROUTES/'Config/rooms.json').read_text(encoding='utf-8'))","config=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))")
text=text.replace("(ROUTES/'Config/start_connection.json').write_text(json.dumps(recipe,indent=2))", "")
text=text.replace("/Game/Dungeons/DoorTransitions20260922", "/Game/Dungeons/RouteRepairs20260922")
exec(compile(text,str(src),'exec'),{'__file__':str(src),'__name__':'__main__'})
transition=json.loads((ROOT/'Authored/manifest.json').read_text())['objects'][0]
transition.update(room='StartTransition',collision=True)
manifest['objects'].append(transition)
(ROOT/'Authored/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('ROUTE_REPAIR_GEOMETRY_AUTHORED',len(manifest['objects']))
