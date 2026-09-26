"""Apply repaired interfaces without resetting current material/light overrides."""
import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def extend(catalog):
    manifest=read(ROOT/'Authored/manifest.json');mapping=read(ROOT/'Receipts/import.json')['meshes'];recipe=read(ROOT/'Config/replacements.json')
    def parts(rid):return [dict(mesh=mapping[o['name']],position=[0,0,0],scale=[1,1,1],yaw=0,collision=o['collision'],fluid=False,materials=[]) for o in manifest['objects'] if o['room']==rid]
    for m in catalog['modules']:
        if m['id'] in recipe['walls']:
            m['parts']=[p for p in m['parts'] if not any(p['mesh'].split('.')[0].endswith('_'+kind) for kind in ('Shell','Tiles','Frames'))]+parts(recipe['walls'][m['id']])
            for port in m['ports']:port.update(width=300,height=280)
        if m['id'] in recipe['sockets']:
            m['side_sockets']=[dict(s,replace_suffixes=['_Shell','_Tiles','_Frames'],parts=parts(s['variant'])) for s in recipe['sockets'][m['id']]]
        if m['id'] in ('Transit','Threshold'):
            length=400 if m['id']=='Transit' else 80
            m['parts']=parts(m['id']);m['min']=[-174,-length,-22];m['max']=[174,0,298]
            m['cells']=[dict(min=m['min'],max=m['max'])]
            for port in m['ports']:port.update(width=300,height=280)
            for lamp in m['lights']:lamp['position'][2]=249.5
    catalog['modules']=[m for m in catalog['modules'] if m['id']!='RouteElbow']
    catalog['modules'].append(dict(id='RouteElbow',role='connector',min=[-218,-218,-22],max=[218,218,298],cells=[dict(min=[-218,-218,-22],max=[218,218,298])],
        ports=[dict(position=[0,200,0],normal=[0,1,0],width=300,height=280),dict(position=[200,0,0],normal=[1,0,0],width=300,height=280)],parts=parts('RouteElbow'),lights=[],anchors=[]))
    catalog.update(strict_ports=True,navigation_required=True,treasure_chance_per_room=.1,treasure_eligibility='ordinary_room_with_side_sockets')
    catalog['start_connection']=read(ROOT/'Config/transition.json')
    # Boss authoring is independent. Activate only once its complete import receipt exists.
    terminal=ROOT.parent/'DungeonBossHall20260922'
    receipt=terminal/'Receipts/import.json'
    if receipt.exists() and read(receipt).get('stage')=='meshes_saved':
        data=read(terminal/'Config/terminal-modules.json')
        boss=copy.deepcopy(next(m for m in data['modules'] if m['id']=='BossPumpHall'))
        boss['boss_encounter']=dict(
            **{'class':'/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C'},
            spawn=next(a['position'] for a in boss['anchors'] if a['role']=='boss_spawn'),
            arena_min=[-1470,-2580,-50],arena_max=[1470,50,820],
            door=boss['ports'][0]['position'],door_size=[300,280],
            gate_material='/Game/Dungeons/BossHall20260922/Materials/M_BossStructuralSteel')
        by_id={m['id']:m for m in catalog['modules']}
        confluence=copy.deepcopy(by_id['Junction']);confluence.update(id='BossConfluence',role='terminal_confluence')
        approach=copy.deepcopy(by_id['Transit']);approach.update(id='BossApproach',role='terminal_connector')
        catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ('BossPumpHall','BossConfluence','BossApproach')]+[confluence,approach,boss]
        catalog['boss_terminal_enabled']=True
    else:catalog.setdefault('boss_terminal_enabled',False)
    underground=ROOT.parent/'DungeonUnderground20260923'
    stair_receipt=underground/'Receipts/install.json'
    if stair_receipt.exists() and read(stair_receipt).get('stage')=='map_saved':
        stairs=read(underground/'Config/modules.json')['modules']
        ids={m['id'] for m in stairs}
        catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+copy.deepcopy(stairs)
        catalog.update(compact_underground_boss=True,generator_version=2,branch_links=1,group_links=1)
    reward=ROOT.parent/'DungeonFinalReward20260923'
    reward_receipt=reward/'Receipts/install.json'
    if reward_receipt.exists() and read(reward_receipt).get('stage')=='map_saved':
        import runpy
        catalog=runpy.run_path(str(reward/'Scripts/extend_catalog.py'))['extend'](catalog)
    finish=ROOT.parent/'DungeonSeamMetal20260923'
    finish_receipt=finish/'Receipts/install.json'
    if finish_receipt.exists() and read(finish_receipt).get('stage')=='map_saved':
        import runpy
        catalog=runpy.run_path(str(finish/'Scripts/extend_catalog.py'))['extend'](catalog)
    wall_damage=ROOT.parent/'DungeonWallDamage20260923'
    wall_receipt=wall_damage/'Receipts/install.json'
    if wall_receipt.exists() and read(wall_receipt).get('stage')=='map_saved':
        import runpy
        catalog=runpy.run_path(str(wall_damage/'Scripts/extend_catalog.py'))['extend'](catalog)
    room_variants=ROOT.parent/'DungeonRoomVariants20260924'
    variants_receipt=room_variants/'Receipts/install.json'
    if variants_receipt.exists() and read(variants_receipt).get('stage')=='map_saved':
        import runpy
        catalog=runpy.run_path(str(room_variants/'Scripts/extend_catalog.py'))['extend'](catalog)
    spawn=ROOT.parent/'DungeonSpawn20260925'
    spawn_receipt=spawn/'Receipts/install.json'
    if spawn_receipt.exists() and read(spawn_receipt).get('stage')=='map_saved':
        import runpy
        catalog=runpy.run_path(str(spawn/'Scripts/extend_catalog.py'))['extend'](catalog)
    return catalog
