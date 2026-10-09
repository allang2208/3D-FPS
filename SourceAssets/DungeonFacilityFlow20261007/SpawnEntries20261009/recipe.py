"""Closed static room fixtures only; monster emergence withdrawn by the user."""
from pathlib import Path
import json,copy,math
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/SpawnEntries20261009'
REVISION='room_closed_fixtures_20261009'
OLD_REVISION='room_spawn_entries_20261009'

def extend(catalog,contract_hash):
    out=copy.deepcopy(catalog)
    placements=json.loads((ROOT/'placements.json').read_text('utf8'))
    floor_changes=json.loads((ROOT/'floor-assets.json').read_text('utf8'))
    originals=json.loads((ROOT/'legacy-spawn-pools.json').read_text('utf8'))
    for m in out['modules']:
        if m['id'] not in placements:continue
        m['runtime_actors']=[a for a in m.get('runtime_actors',[]) if a.get('type')!='spawn_entry']
        m['parts']=[p for p in m['parts'] if p.get('fixture_revision')!=REVISION]
        m['scene_keep_clear']=[a for a in m.get('scene_keep_clear',[]) if a.get('owner') not in (REVISION,OLD_REVISION)]
        # A closed decorative lid needs the original solid floor, not a runtime
        # support component. Restore only our own derived floor references.
        for change in floor_changes.get(m['id'],[]):
            for part in m['parts']:
                if part['mesh'].split('.')[0]==change['mesh']:part['mesh']=change['source']
        for e in placements[m['id']]:
            x,y,z=e['position'];a=math.radians(e['yaw']);c,s=math.cos(a),math.sin(a)
            def part(mesh,offset,collision):
                dx,dy,dz=offset
                m['parts'].append(dict(mesh=mesh,position=[x+c*dx-s*dy,y+s*dx+c*dy,z+dz],yaw=e['yaw'],scale=[1,1,1],materials=[],collision=collision,cast_shadow=True,fixture_revision=REVISION,fixture_id=e['id']))
            solid=e['kind']=='door'
            part(e['body'],e.get('body_offset',[0,0,0]),solid)
            part(e['leaf'],e['hinge'],solid)
            if solid:part(BASE+'/Meshes/SM_Entry_DoorLeafRight',[150,90,0],True)
            xmin,xmax,yspan=(0,370,125) if solid else (-90,290,100) if e['kind']=='hatch' else (-150,150,150)
            pts=[(x+c*dx-s*dy,y+s*dx+c*dy) for dx in (xmin,xmax) for dy in (-yspan,yspan)]
            keep=dict(min=[min(p[0] for p in pts),min(p[1] for p in pts),z-5],max=[max(p[0] for p in pts),max(p[1] for p in pts),z+320],owner=REVISION)
            m['scene_keep_clear'].append(keep)
            for actor in m['runtime_actors']:
                if actor['type']=='beds':
                    box={k:keep[k] for k in ('min','max')}
                    if box not in actor['keep_clear']:actor['keep_clear'].append(box)
        old_members=originals.get(m['id'],{})
        for member in m.get('spawn',{}).get('pool',[]):
            old=old_members.get(member['id'])
            if old=='/Script/FPSGAME.NurseZombie' and member['class']=='/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C':member['class']=old
        m['runtime_assets']=[p for p in m.get('runtime_assets',[]) if not p.startswith(BASE+'/')]
        m.pop('spawn_entry_revision',None);m['closed_fixture_revision']=REVISION
    out.pop('spawn_entry_revision',None);out['closed_fixture_revision']=REVISION
    bank=out.get('facility_flow',{}).get('layout_bank')
    if bank:bank['contract_sha1']=contract_hash(out)
    return out

def reapply_if_installed(catalog,contract_hash):
    r=ROOT/'install-receipt.json'
    return extend(catalog,contract_hash) if r.exists() and json.loads(r.read_text('utf8')).get('stage')=='map_saved' else catalog
