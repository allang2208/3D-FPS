"""Scoped wall-interface fixes for hospital descriptors; no room shell changes."""
import copy
import math

BASE='/Game/Dungeons/HospitalPolish20261003/Meshes/'
OLD_PUMP='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PumpSkid'
OLD_SPARES='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_ServiceSpares'
OLD_SINK='/Game/Dungeons/IncineratorHall20260929/MorgueB1V1/Meshes/SM_Incinerator_WashSink_MorgueB1'
PUMP=BASE+'SM_Hospital_WallPump_V2'
SINK=BASE+'SM_Hospital_ScrubSink_V2'


def old_reserve(p,size):
    a=math.radians(p.get('yaw',0));x,y,z=size
    ex=(abs(math.cos(a))*x+abs(math.sin(a))*y)/2+18
    ey=(abs(math.sin(a))*x+abs(math.cos(a))*y)/2+18
    at=p['position'];return dict(min=[at[0]-ex,at[1]-ey,at[2]-5],max=[at[0]+ex,at[1]+ey,at[2]+z+15])


def pump_part(part):
    result=copy.deepcopy(part)
    side=abs(part.get('yaw',0))==90
    result.update(mesh=PUMP,position=[937.8158998759463,-820,.3] if side else [525,-84,.3],
        yaw=-90 if side else 0,scale=[1,1,1],materials=[],collision=True,cast_shadow=True,
        hospital_fixture_id='Pump.EastWall' if side else 'Pump.NorthWall')
    return result


def pump_reserve(p):
    a=math.radians(p['yaw']);at=p['position'];points=[]
    for x in (-129,129):
        for y in (-70,69):points.append([at[0]+x*math.cos(a)-y*math.sin(a),at[1]+x*math.sin(a)+y*math.cos(a)])
    return dict(min=[min(v[0] for v in points),min(v[1] for v in points),-.2],
                max=[max(v[0] for v in points),max(v[1] for v in points),165])


def collection(owner):
    removed=[];reserves=[];parts=[]
    for p in owner.get('parts',[]):
        path=p.get('mesh','').split('.')[0]
        if path==OLD_SPARES:
            removed.append(old_reserve(p,(80,50,30)));continue
        if path in (OLD_PUMP,PUMP):
            removed.append(old_reserve(p,(220,95,130)) if path==OLD_PUMP else pump_reserve(p))
            p=pump_part(p);reserves.append(pump_reserve(p))
        parts.append(p)
    owner['parts']=parts
    if 'scene_keep_clear' in owner:
        owner['scene_keep_clear']=[r for r in owner['scene_keep_clear'] if r not in removed]+reserves


def extend_module(module):
    result=copy.deepcopy(module);identity=result['id']
    if identity=='Drainage':
        collection(result)
        for recipe in result.get('scene_recipes',[]):
            collection(recipe)
            for state in recipe.get('states',[]):collection(state)
        result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+[PUMP]))
        result['hospital_fixture_revision']=2
    elif identity=='AbandonedAnatomyTheatre':
        for part in result.get('parts',[]):
            if part.get('mesh','').split('.')[0] in (OLD_SINK,SINK):
                part.update(mesh=SINK,position=[-600,1147,.3],yaw=0,scale=[1,1,1],materials=[],collision=True,
                    hospital_fixture_id='ScrubSink.SouthWall')
        result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+[SINK]))
        result['hospital_fixture_revision']=2
    return result


def extend(catalog):
    result=copy.deepcopy(catalog);result['modules']=[extend_module(m) for m in result['modules']]
    result['hospital_fixture_revision']=2
    return result
