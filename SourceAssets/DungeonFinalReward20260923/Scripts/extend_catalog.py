"""Append the reward room to the unique Boss reservation, without adding route length."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='/Game/Dungeons/FinalReward20260923/Meshes/'

def extend(catalog):
    data=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
    boss=next(m for m in catalog['modules'] if m['id']=='BossPumpHall')
    # Idempotent overlay; apply to the current module so light/performance edits survive.
    boss['parts']=[p for p in boss['parts'] if not p['mesh'].startswith(BASE)
        and not (p['mesh'].startswith('/Game/Dungeons/BossHall20260922/Meshes/SM_RS_BossPumpHall_')
                 and p['mesh'].rsplit('_',1)[-1] in ('Shell','Tiles','Frames'))]
    for item in data['objects']:
        if item['kind']=='DoorLeaf':continue
        boss['parts'].append(dict(mesh=BASE+item['name'],position=data['door_origin'] if item['kind']=='DoorFrame' else [0,0,0],
            scale=[1,1,1],yaw=0,collision=item['collision'],fluid=False,materials=[]))
    boss['min']=[-1518,-3668,-25]
    boss['cells']=[dict(min=[-1518,-2638,-25],max=[1518,18,865]),
                   dict(min=[-248,-3668,-25],max=[988,-2638,438])]
    # These lights are prepared during loading, on the same floor as the Boss arena.
    boss['lights']=[l for l in boss['lights'] if l.get('source')!='final_reward_room']
    for light in data['lights']:
        x,y,z=light['at']
        boss['lights'].append(dict(position=[x*100,-y*100,(z-.085)*100],intensity=light['lumens'],
            radius=light['radius_cm'],color=[1,.70,.43] if light['warm'] else [.73,.84,1],
            role='key',cast_shadows=True,source='final_reward_room'))
    boss['anchors']=[a for a in boss['anchors'] if a.get('source')!='final_reward_room']
    for role,position in [('final_reward_chest',data['chest_position']),('final_return',data['portal_position']),
                          ('reward_door',[370,-2610,0])]:
        boss['anchors'].append(dict(role=role,position=position,source='final_reward_room'))
    chest=json.loads((ROOT.parents[1]/'Content/ColdSteelData/treasure_chest_assets.json').read_text(encoding='utf-8-sig'))
    boss['props']=[p for p in boss.get('props',[]) if p.get('role')!='final_reward_chest']
    boss['props'].append(dict(skeletal_mesh=chest['mesh'],closed_animation=chest['close'],
        opening_animation=chest['opening'],material_overrides=copy.deepcopy(chest['materials']),
        collision_extent=chest['collision_extent'],collision_center=chest['collision_center'],
        position=data['chest_position'],yaw=90,scale=[1,1,1],role='final_reward_chest',identity=chest['identity']))
    boss['reward_exit']=dict(leaf_mesh=BASE+'SM_RS_FinalRewardGate_DoorLeaf',door_position=data['door_origin'],
        door_travel=data['door_travel'],door_clear_size=[464,70,314],
        return_assets=['/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Frame',
                       '/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Energy'],
        return_portal=dict(position=data['portal_position'],yaw=90,scale=[1,1,1],
                           destination='/Game/GameMaps/DayNight_Lighting'),rewards_configured=False)
    catalog['final_reward_room_enabled']=True
    return catalog

def asset_paths(catalog):
    boss=next(m for m in catalog['modules'] if m['id']=='BossPumpHall')
    for part in boss['parts']:
        yield part['mesh']
        yield from part.get('materials',[])
    for prop in boss.get('props',[]):
        for key in ('skeletal_mesh','closed_animation','opening_animation'):
            if prop.get(key):yield prop[key]
        yield from prop['material_overrides'].values()
    if boss.get('reward_exit'):
        yield boss['reward_exit']['leaf_mesh']
        yield from boss['reward_exit']['return_assets']

if __name__=='__main__':
    routes=ROOT.parent/'DungeonRoutes20260922/Config/catalog.json'
    catalog=extend(json.loads(routes.read_text(encoding='utf-8')))
    (ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
    (ROOT/'Receipts/catalog-candidate.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL_REWARD_CATALOG_PREPARED')
