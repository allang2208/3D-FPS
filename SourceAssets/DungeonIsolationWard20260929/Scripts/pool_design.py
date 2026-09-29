"""Approved ward: axial hall entrances, retained accessible decon room, no portal."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def apply(cfg):
    cfg['pool_mode']=True
    cfg['revision']='isolation_ward_axial_combat_pool_v9_20260929'
    cfg['floor_rectangles_m']=cfg['floor_rectangles_m'][:4]+[[-33,-2.3,-30,2.3],[30,-2.3,33,2.3]]
    cfg['ports']=[dict(id=name,position=[x,0,0],normal=[sign,0,0],width=3.,height=2.8)
                  for name,x,sign in [('MainHallWest',-33,-1),('MainHallEast',33,1)]]
    cfg['cells_m']=[dict(min=[x0-.18,y0-.18,-.3],max=[x1+.18,y1+.18,6.1 if i==0 else 3.8 if i>=4 else 4.9])
                    for i,(x0,y0,x1,y1) in enumerate(cfg['floor_rectangles_m'])]
    cfg['blood_scatter']['floor_size_scale']=2.5
    for lamp in cfg['lights']:
        if lamp['id']=='Entry':lamp['position']=[-31.5,0,3.06]
        elif lamp['id']=='Exit':lamp['position']=[31.5,0,3.06]
    cfg['pool']=dict(selection=dict(chance_per_run=.3,max_per_run=1,route='Approach'),
        spawn_count=[6,8],sealed_encounter=True,
        spawn_anchors_m=[[x,y,.05] for x in (-23,-14,-5,5,14,23) for y in (-1.8,1.8)],
        walk_polyline_m=[[-33,0,.05],[0,0,.05],[33,0,.05]],
        external_entry='sealed',decon_room='accessible from main hall',portal_included=False)
    cfg['future_pool']=dict(status='approved_for_integration',policy=cfg['pool'])
    return cfg

if __name__=='__main__':
    path=ROOT/'Config/room.json'
    cfg=apply(json.loads(path.read_text(encoding='utf-8')))
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WARD_POOL_DESIGN_SAVED')
