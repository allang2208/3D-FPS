"""Shared editor/offline wall grounding; no third-party dependency inside Unreal."""
import json,math
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsVillage'
CATALOG=json.loads((SOURCE/'wall-support.json').read_text(encoding='utf-8'))

def fit_instance(instance):
    name=instance['mesh'].split('.')[-1].rsplit('/',1)[-1]
    letter=name.split('Piece')[-1][0]
    old_roll=instance['rot'][2]
    roll=180 if letter in 'AD' and abs(old_roll)>90 else 0
    profile=CATALOG['profiles'][name+':'+str(roll)]
    scale=instance['scale'][2]
    # Each piece has broad ground support; a neighbouring piece is never a hidden dependency.
    # Minor deterministic burial keeps the tops irregular without floating low vertices.
    x,y=instance['pos'][:2]
    extra=((round(x)*31+round(y)*17)%41)/10.
    datum=max(profile['ground_cm']*scale,
              profile['stone_max_cm']*scale-CATALOG['max_wall_height_cm'])+extra
    instance['pos'][2]=-datum
    instance['rot']=[0.,instance['rot'][1],float(roll)]
    instance['support_version']=CATALOG['version']
    return profile['stone_max_cm']*scale-datum

def remove_blacksmith_front_walls(plan):
    area=plan.get('blacksmith',{}).get('front_wall_clearance_local_m')
    if not area:return []
    house=next(h for h in plan['houses'] if h[0]==plan['blacksmith']['house'])
    yard=plan['blacksmith'].get('smelting_yard')
    a=math.radians(house[5]);c,s=math.cos(a),math.sin(a);removed=[]
    for wall in plan['yard_walls']:
        pieces=[];instances=[]
        for piece,instance in zip(wall['pieces'],wall['native_instances']):
            points=[((x-house[3])*c+(y-house[4])*s,-(x-house[3])*s+(y-house[4])*c) for x,y in ((piece[1],piece[2]),(piece[3],piece[4]))]
            in_front=(max(p[0] for p in points)>area[0] and min(p[0] for p in points)<area[1]
                      and max(p[1] for p in points)>area[2] and min(p[1] for p in points)<area[3])
            cx,cy=instance['pos'][0]*.01,instance['pos'][1]*.01
            bounds=yard['bounds_m'] if yard else None
            if in_front or (bounds and bounds[0]<cx<bounds[2] and bounds[1]<cy<bounds[3]):
                removed.append({'group':wall['name'],'piece':piece,'instance':instance})
            else:pieces.append(piece);instances.append(instance)
        wall['pieces']=pieces;wall['native_instances']=instances
    return removed

def fit_plan(plan):
    remove_blacksmith_front_walls(plan)
    for wall in plan['yard_walls']:
        for piece,instance in zip(wall['pieces'],wall['native_instances']):
            piece[5]=round(fit_instance(instance)/100.,4)
    plan['wall_support_version']=CATALOG['version']
    plan['wall_support_rule']='rotated stone profile, broad embedded base; no inverted B/C; upright courses on flat pad'
    return plan
