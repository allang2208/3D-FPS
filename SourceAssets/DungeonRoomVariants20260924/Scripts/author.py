"""Build precise room meshes in background Blender from the shared libraries."""
import os,json,random
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
text=LIB.read_text(encoding='utf-8')
text=text.replace("for index,room in enumerate(CFG['rooms']):", "for index,room in enumerate(r for r in CFG['rooms'] if r['family_id']=='Drainage'):")
exec(compile(text,str(LIB),'exec'),{'__file__':str(LIB),'__name__':'__main__'})
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
vf=ROOT.parent/'DungeonVentFreight20260922/Scripts/author.py'
scope={'__file__':str(vf),'__name__':'variant_author'}
source=vf.read_text(encoding='utf-8').split("for index,room in enumerate(H['CFG']['rooms']):",1)[0]
source=source.replace("ROOT=Path(__file__).resolve().parents[1]",f"ROOT=Path({str(ROOT)!r})")
exec(compile(source,str(vf),'exec'),scope)
H=scope['H'];cfg=H['CFG']
for index,room in enumerate(r for r in cfg['rooms'] if r['family_id']=='VentilationLoop'):
    H['ROOM']=room;H['GROUPS']={};H['R']=random.Random(cfg['seed']+index)
    scope['ventilation']()
    for edge,(a,b) in enumerate(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1])):
        H['wall'](a,b,room['height_m'],[o for o in room['openings'] if o['edge']==edge])
    for x,y in room['columns']:H['box']('Shell',(x,y,room['height_m']/2),(.32,.32,room['height_m']))
    for a,b in room['beams']:H['bar']('Shell',a,b,.32,.32)
    for p in room['pipes']:H['smooth_pipe'](p['points'],p['radius'])
    for l in room['lights']:
        H['lamp'](l);x,y,z=l['at'];top=H['detail'].ceiling_at(Vector((x,y,z)))
        for dx in (-.34,.34):H['tube']('Fixtures',[(x+dx,y,z+.035),(x+dx,y,top)],.008,'BareSteel',12)
    H['export']()
    print('VARIANT_AUTHORED',room['id'],flush=True)
manifest['objects']+=H['RECORDS']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/VentilationVariants.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('VARIANT_GEOMETRY_SAVED',len(manifest['objects']),flush=True)
