"""Add the optional treasury pool and side-wall variants to an existing route catalogue."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
def extend(catalog):
    config=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
    mapping=json.loads((ROOT/'Receipts/import.json').read_text())['meshes']
    sockets=json.loads((ROOT/'Config/sockets.json').read_text())
    rules=json.loads((ROOT.parent/'DungeonRoutes20260922/Config/rules.json').read_text())
    catalog['treasure_chance_per_room']=rules.get('treasure_chance_per_room',.1)
    catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ('Treasure','TreasureLink')]
    def parts(rid):
        return [dict(mesh=mapping[o['name']],position=[0,0,0],scale=[1,1,1],yaw=0,collision=o['collision'],fluid=False,materials=[])
                for o in manifest['objects'] if o['room']==rid]
    for module in catalog['modules']:
        if module['id'] not in sockets:continue
        module['side_sockets']=[]
        for s in sockets[module['id']]:
            module['side_sockets'].append(dict(s,replace_suffixes=['_Shell','_Tiles','_Frames'],parts=parts(s['variant'])))
    room=config['rooms'][0]
    m=dict(id='Treasure',min=[-555,-1067,-80],max=[555,43,370],
        cells=[dict(min=[-555,-1067,-80],max=[555,43,370])],
        ports=[dict(position=[0,0,0],normal=[0,1,0],width=300,height=280,id='entry')],
        parts=parts('Treasure'),lights=[],anchors=[])
    for lamp in room['lights']:
        x,y,z=lamp['at'];m['lights'].append(dict(position=[100*x,-100*y,100*(z-.085)],intensity=lamp['lumens'],radius=lamp['radius_cm'],color=[1,.64,.36] if lamp['warm'] else [.73,.84,1]))
    for anchor in room['anchors']:
        x,y,z=anchor['at'];m['anchors'].append(dict(position=[100*x,-100*y,100*z],role=anchor['role']))
    chest=json.loads((PROJECT/'Content/ColdSteelData/treasure_chest_assets.json').read_text(encoding='utf-8-sig'))
    m['props']=[dict(skeletal_mesh=chest['mesh'],closed_animation=chest['close'],material_overrides=chest['materials'],
                     collision_extent=chest['collision_extent'],collision_center=chest['collision_center'],
                     position=[0,-512,.8],yaw=90,scale=[1,1,1],role='treasure_chest',identity=chest['identity'])]
    if chest.get('opening'):m['props'][0]['opening_animation']=chest['opening']
    catalog['modules'].append(m)
    catalog['modules'].append(dict(id='TreasureLink',min=[-176,-200,-22],max=[176,0,298],
       cells=[dict(min=[-176,-200,-22],max=[176,0,298])],
       ports=[dict(position=[0,0,0],normal=[0,1,0],width=300,height=280),dict(position=[0,-200,0],normal=[0,-1,0],width=300,height=280)],
       parts=parts('TreasureLink'),lights=[],anchors=[]))
    return catalog
def asset_paths(catalog):
    for module in catalog['modules']:
        if module.get('boss_encounter'):
            yield module['boss_encounter']['class'];yield module['boss_encounter']['gate_material']
        for side in module.get('side_sockets',[]):
            for p in side['parts']:
                yield p['mesh']
                yield from p['materials']
        for p in module.get('props',[]):
            yield p['skeletal_mesh'];yield p['closed_animation']
            if p.get('opening_animation'):yield p['opening_animation']
            yield from p['material_overrides'].values()
