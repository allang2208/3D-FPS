"""Move one reception service-door assembly to the opposite ground-floor wall."""
import copy

MODULE='FacilityReceptionHall'
FIXTURE=MODULE+'.service.01'
POSITION=[420.,1645.,0.]
YAW=270
OLD_POSITION=[1140.,-1645.0001220703125,0.]
OLD_CLEARANCE=dict(min=[1015.,-1645.0001220703125,-5.],max=[1265.,-1275.0001220703125,320.])
NEW_CLEARANCE=dict(min=[295.,1275.,-5.],max=[545.,1645.,320.])
OFFSETS={'SM_Entry_DoorBody':[0.,0.,0.],
         'SM_Entry_DoorLeaf':[-90.,-150.,0.],
         'SM_Entry_DoorLeafRight':[90.,-150.,0.]}

def near(a,b):
    return len(a)==len(b) and all(abs(x-y)<.01 for x,y in zip(a,b))

def move(catalog):
    out=copy.deepcopy(catalog)
    hall=next(m for m in out['modules'] if m['id']==MODULE)
    parts=[p for p in hall['parts'] if p.get('fixture_id')==FIXTURE]
    if len(parts)!=3:raise RuntimeError('Preserve independently changed service-door assembly')
    body=next(p for p in parts if p['mesh'].endswith('/SM_Entry_DoorBody'))
    if not (near(body['position'],OLD_POSITION) or near(body['position'],POSITION)):
        raise RuntimeError('Service door has independently moved')
    for part in parts:
        offset=OFFSETS[part['mesh'].split('/')[-1]]
        part['position']=[a+b for a,b in zip(POSITION,offset)]
        part['yaw']=YAW
    clearances=[b for b in hall['scene_keep_clear']
        if b.get('owner')=='room_closed_fixtures_20261009'
        and any(all(near(b[k],c[k]) for k in ('min','max')) for c in (OLD_CLEARANCE,NEW_CLEARANCE))]
    if len(clearances)!=1:raise RuntimeError('Cannot identify this doorway clearance')
    clearances[0].update(copy.deepcopy(NEW_CLEARANCE))
    for actor in hall.get('runtime_actors',[]):
        for box in actor.get('keep_clear',[]):
            if all(near(box[k],OLD_CLEARANCE[k]) for k in ('min','max')):
                box.update(copy.deepcopy(NEW_CLEARANCE))
    return out

def move_source(placements):
    out=copy.deepcopy(placements)
    entry=next(e for e in out[MODULE] if e['id']==FIXTURE)
    entry['position']=POSITION.copy();entry['yaw']=YAW
    return out
