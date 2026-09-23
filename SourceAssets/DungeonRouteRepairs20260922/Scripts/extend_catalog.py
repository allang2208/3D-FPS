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
    return catalog
