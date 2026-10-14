"""Leave the production random dungeon without any old monster recipes."""
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parent
REVISION='dungeon_old_spawning_removed_20261009'

def extend(catalog,contract_hash):
    out=copy.deepcopy(catalog)
    for module in out['modules']:
        spawn=module.pop('spawn',{})
        boss=module.pop('boss_encounter',None)
        retired={p.get('class') for p in spawn.get('pool',[])}
        if boss:
            retired.add(boss.get('class'))
            module['terminal_fixtures']={k:copy.deepcopy(boss[k]) for k in ('door','door_size','gate_material')}
        # Keep the authored shutter as a raised static part. No clear-room poll,
        # fake room completion, kill reward or automatic replacement wave.
        gate=module.pop('progression_gate',None)
        if gate:
            yaw=gate.get('yaw',0);a=math.radians(yaw);sx,sy,sz=gate.get('scale',[1,1,1])
            x,y,z=gate['position'];dx,dy,dz=gate['travel'];dx*=sx;dy*=sy;dz*=sz
            module['parts'].append(dict(mesh=gate['mesh'],position=[x+math.cos(a)*dx-math.sin(a)*dy,y+math.sin(a)*dx+math.cos(a)*dy,z+dz],
                scale=[sx,sy,sz],yaw=yaw,collision=False,cast_shadow=True,materials=[],retired_combat_gate=REVISION))
        module['runtime_actors']=[a for a in module.get('runtime_actors',[]) if a.get('type') not in ('spawn_entry','monster_spawner','spawn_director')]
        module['runtime_assets']=[p for p in module.get('runtime_assets',[]) if p not in retired]
    out['monster_spawning_revision']=REVISION
    bank=out.get('facility_flow',{}).get('layout_bank')
    if bank:bank['contract_sha1']=contract_hash(out)
    return out

def reapply_if_installed(catalog,contract_hash):
    receipt=ROOT/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='map_saved':return extend(catalog,contract_hash)
    return catalog
