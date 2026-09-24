"""Build only tile skins for active dungeon modules; preserve structural meshes and portals."""
import copy,json,os,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
LIB=BASE/'DungeonRoomShells20260922/Scripts/author_rooms.py'
catalog=json.loads((BASE/'DungeonRoutes20260922/Config/catalog.json').read_text(encoding='utf-8'))
prior=ROOT/'Config/mesh-variants.json'
reverse={v:k for k,values in json.loads(prior.read_text()).items() for v in values} if prior.exists() else {}
paths=set()
for module in catalog['modules']:
    for owner in [module]+module.get('side_sockets',[]):
        paths.update(reverse.get(p['mesh'],p['mesh']) for p in owner.get('parts',[]) if p['mesh'].rsplit('/',1)[-1].endswith('_Tiles'))
recipes={}
for folder in ['DungeonRoomShells20260922','DungeonRoutes20260922','DungeonTreasure20260922',
               'DungeonVentFreight20260922','DungeonRouteRepairs20260922','DungeonFinalReward20260923']:
    path=BASE/folder/'Config/rooms.json'
    if not path.exists():continue
    cfg=json.loads(path.read_text(encoding='utf-8'))
    for row in cfg.get('rooms',[]):recipes[row['id']]=('room',row)
    for row in cfg.get('links',[]):recipes[row['id']]=('link',row)
style=json.loads((BASE/'DungeonRoomShells20260922/Config/rooms.json').read_text())['style']
config=dict(seed=923847,style=style,rooms=[],links=[])
(ROOT/'Config/rooms.json').write_text(json.dumps(config,indent=2))
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
# Load the shared author functions without its full-room execution loop.
source=LIB.read_text(encoding='utf-8').split("for index,room in enumerate(CFG['rooms']):",1)[0]
H={'__file__':str(LIB),'__name__':'wall_author'};exec(compile(source,str(LIB),'exec'),H)
wall=H['wall'];surfaces=H['SURFACES'];out=[];skipped=[]
for old in sorted(paths):
    rid=old.rsplit('/',1)[-1].removeprefix('SM_RS_').removesuffix('_Tiles')
    if rid not in recipes:
        skipped.append(dict(mesh=old,reason='custom stair/boss geometry; retain original skin'));continue
    kind,row=recipes[rid]
    for variant in range(3):
        room=copy.deepcopy(row)
        room.update(id=rid+'_Damage'+str(variant),surface_seed_id=row.get('surface_seed_id',rid),
                    surface_variant=variant,origin_m=[0,0,0],export_kinds=['Tiles'])
        H['ROOM']=room;H['GROUPS']={}
        if kind=='room':
            outline=room['footprint']
            for edge,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
                wall(a,b,room.get('wall_heights',{}).get(str(edge),room['height_m']),
                     [o for o in room['openings'] if o['edge']==edge],
                     room.get('breach') if room.get('breach',{}).get('edge')==edge else None)
        else:
            from mathutils import Vector
            width=room['width']+2*room.get('portal_recess_m',0);length=room['length'];collar=room.get('portal_collar_m',0)
            depth=style['wall_thickness']
            if rid in ('Transit','Threshold'):width+=.04;depth-=.04
            edges=[((0,-width/2),(length,-width/2)),((length,width/2),(0,width/2))] if room['axis']=='x' else [((-width/2,length),(-width/2,0)),((width/2,0),(width/2,length))]
            for a,b in edges:
                a,b=Vector(a),Vector(b);direction=(b-a).normalized();normal=Vector((-direction.y,direction.x))
                surfaces.wall(H,a+direction*collar,direction,normal,length-2*collar,(),None,depth)
        # Only the tile group is exported. Structural collision stays on the original shell.
        H['export']();item=H['RECORDS'][-1];item.update(source_mesh=old,variant=variant)
        out.append(item)
        print('WALL_VARIANT_AUTHORED',rid,variant,flush=True)
manifest=dict(objects=out,skipped=skipped,variants_per_skin=3,tests_run=False)
(ROOT/'Authored/manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'Authored/distribution.json').write_text(json.dumps(surfaces.placements,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonWallDamage.blend'))
print('WALL_VARIANTS_AUTHORED',len(out),flush=True)
