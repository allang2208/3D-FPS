"""Second area increase: current clear floor x 1.5, with two routes around drain columns."""
import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V2=ROOT.parent/'DungeonCombatExpansion20260922';ROOMS=ROOT.parent/'DungeonRoomShells20260922'
sys.path.insert(0,str(V2/'Scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location('first_expansion',V2/'Scripts/layout.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
previous=json.loads((ROOT/'Config/rooms-before.json').read_text(encoding='utf-8'))
def room_at(old,s):
    r=base.enlarge(old,s)
    if r['id']=='Distribution':
        next(o for o in r['openings'] if o['id']=='exit')['width']=2.8
    elif r['id']=='Drainage':
        for op in r['openings']:op['width']=2.8 if op['id']=='entry' else 3.0
        x0,y0,x1,y1=r['trench']['rect']
        for i,p in enumerate(r['columns']):p[0]=x0-3.42 if i%2==0 else x1+3.42
        r['tactical_routes']={'column_to_rail_clear_m':3.42-.18-.026,'front_bypass_depth_m':y0-.12,'bridge_route_width_m':2.0}
        r['anchors']+=[dict(role='west_flank',at=[x0-1.65,(y0+y1)/2,0]),dict(role='east_flank',at=[x1+1.65,(y0+y1)/2,0])]
    else:next(o for o in r['openings'] if o['id']=='entry')['width']=3.0
    return r
if __name__=='__main__':
    cfg=copy.deepcopy(base.OLD);report=[]
    for i,old in enumerate(base.OLD['rooms']):
        before=base.clear_area(previous['rooms'][i]);target=before*1.5;lo,hi=1,2
        for _ in range(32):
            s=(lo+hi)/2
            if base.clear_area(room_at(old,s))<target:lo=s
            else:hi=s
        r=room_at(old,hi);cfg['rooms'][i]=r
        report.append(dict(room=r['id'],previous_clear_m2=before,new_clear_m2=base.clear_area(r),original_clear_m2=base.clear_area(old),factor_from_original=hi))
    d,dr,sb=cfg['rooms'];l=cfg['links'][0];l['width']=2.8;l['origin_m']=base.port(d,'exit');entry=base.port(dr,'entry');off=[entry[j]-dr['origin_m'][j] for j in range(2)];dr['origin_m']=[l['origin_m'][0]-off[0],l['origin_m'][1]+l['length']-off[1],.94]
    l=cfg['links'][1];l['width']=3.0;l['origin_m']=base.port(dr,'exit');sb['origin_m']=[l['origin_m'][0]+l['length'],l['origin_m'][1],.94]
    cfg['version']=3;cfg['area_multiplier_from_original']=2.25
    for p in [ROOT/'Config/rooms.json',ROOMS/'Config/rooms.json']:
        p.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'Config/area-budget.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
