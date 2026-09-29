"""Author receiver regions and per-room budgets; never author fixed stain positions."""
from copy import deepcopy


def apply_room_blood_design(cfg):
    blood=cfg['blood_scatter']
    # Keep the original surfaces as the shared architectural source. Hall actors
    # no longer compete with bedroom actors for a single random allocation.
    shared=[]
    for surface in blood['surfaces']:
        x,y,_=surface['center_m']
        inside=any(r['x'][0]<x<r['x'][1] and r['y'][0]<y<r['y'][1] for r in cfg['rooms'])
        if not inside:shared.append(deepcopy(surface))
    blood.update(floor_count=36,wall_count=12,scanned_size_range_cm=[35.,85.])
    groups=[dict(id='Shared',floor_count=36,wall_count=12,surfaces=shared)]
    for room in cfg['rooms']:
        x0,x1=room['x'];y0,y1=room['y']
        surfaces=[dict(center_m=[(x0+x1)/2,(y0+y1)/2,.042],normal=[0,0,1],axis_u=[1,0,0],
                       half_size_m=[(x1-x0)/2-.4,(y1-y0)/2-.4],wall=False)]
        # Solid side walls, facing into the room. Leave front glazing untouched.
        for x,normal_x in ((x0+.21,1),(x1-.21,-1)):
            surfaces.append(dict(center_m=[x,(y0+y1)/2,1.4],normal=[normal_x,0,0],axis_u=[0,0,1],
                                 half_size_m=[1.1,(y1-y0)/2-.4],wall=True))
        north=room['id'].startswith('N')
        rear_y=y1-.21 if north else y0+.21
        spans=[(x0+.4,x1-.4)]
        if 'rear_door_x' in room:
            door=room['rear_door_x']
            spans=[(x0+.4,door-2.),(door+2.,x1-.4)]
        for a,b in spans:
            if b-a<.8:continue
            surfaces.append(dict(center_m=[(a+b)/2,rear_y,1.4],normal=[0,-1 if north else 1,0],axis_u=[0,0,1],
                                 half_size_m=[1.1,(b-a)/2],wall=True))
        groups.append(dict(id=room['id'],floor_count=20,wall_count=6,surfaces=surfaces))
    blood['groups']=groups
    blood['total_floor_target']=sum(g['floor_count'] for g in groups)
    blood['total_wall_target']=sum(g['wall_count'] for g in groups)
    return blood
