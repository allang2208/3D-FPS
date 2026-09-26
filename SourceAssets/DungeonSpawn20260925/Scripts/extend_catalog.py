"""Inject the frozen per-room spawn sections into the nine combat-room modules."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE='DungeonSpawn20260925'

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def spawn_groups():
    groups=read(ROOT/'Config/spawn-groups.json')['spawn_groups']
    for rid,group in groups.items():
        if group.get('source')!=SOURCE:raise RuntimeError('Spawn group without batch marker: '+rid)
    return groups

def extend(catalog):
    catalog=copy.deepcopy(catalog)
    groups=spawn_groups()
    by_id={m['id']:m for m in catalog['modules']}
    for rid in catalog['room_ids']:
        if rid not in groups:raise RuntimeError('Combat room without a frozen spawn group: '+rid)
        if rid not in by_id:raise RuntimeError('room_ids references a missing module: '+rid)
        # Whole-section replacement is idempotent; the source marker names the owning batch.
        by_id[rid]['spawn']=copy.deepcopy(groups[rid])
    unmatched=sorted(set(groups)-set(catalog['room_ids']))
    if unmatched:raise RuntimeError('Spawn groups absent from room_ids: '+', '.join(unmatched))
    return catalog

def asset_paths(catalog):
    """Yield every pool class path once, in stable catalog module order."""
    seen=set()
    for module in catalog.get('modules',[]):
        spawn=module.get('spawn')
        if not spawn or spawn.get('source')!=SOURCE:continue
        for entry in spawn.get('pool',[]):
            path=entry.get('class')
            if path and path not in seen:
                seen.add(path)
                yield path

if __name__=='__main__':
    # Offline candidate only: never write DungeonRoutes' catalog.json or another batch.
    routes=ROOT.parent/'DungeonRoutes20260922/Config/catalog.json'
    catalog=extend(read(routes))
    (ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
    (ROOT/'Receipts/catalog-extended-candidate.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    injected=sum(1 for m in catalog['modules'] if m.get('spawn',{}).get('source')==SOURCE)
    paths=list(asset_paths(catalog))
    print('DUNGEON_SPAWN_CATALOG_PREPARED','modules=%d'%injected,'assets=%d'%len(paths),'room_ids=%d'%len(catalog['room_ids']),flush=True)
