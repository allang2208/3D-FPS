"""Scope connector recesses and standard room portal reveals to live catalog references."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
catalog=json.loads((BASE/'DungeonRoutes20260922/Config/catalog.json').read_text())
targets={}
def add(path,operation,ports=(),elbow=False):
    path=path.split('.')[0]
    if path in targets:return
    folder=BASE/('Dungeon'+path.split('/')[3]);source=folder/'Authored'/(path.rsplit('/',1)[-1]+'.fbx')
    if not source.exists():raise RuntimeError('Missing editable source '+str(source))
    targets[path]=dict(path=path,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                       operation=operation,ports=list(ports),elbow=elbow)
for module in catalog['modules']:
    rid=module['id']
    if rid in ('Transit','Threshold','BossApproach'):
        for part in module['parts']:
            path=part['mesh'];name=path.rsplit('/',1)[-1]
            if name.endswith(('_Shell','_Frames','_Ceilings','_Tiles')):
                kind=name.rsplit('_',1)[-1]
                for candidate in part.get('surface_mesh_variants',[path]):add(candidate,'connector_'+kind.lower())
        continue
    if rid in ('BossPumpHall','StairDrop1080','TreasureLink'):continue
    for owner in [module]+module.get('side_sockets',[]):
        ports=module['ports']+([owner] if owner is not module else [])
        for part in owner.get('parts',[]):
            path=part['mesh']
            if path.endswith('_Shell'):add(path,'portal_shell',ports,rid=='RouteElbow')
            if path.endswith('_Frames'):add(path,'portal_frames',ports)
            if rid=='RouteElbow' and path.endswith('_Ceilings'):add(path,'connector_ceilings')
(ROOT/'Config/geometry-targets.json').write_text(json.dumps(list(targets.values()),indent=2))
print('GEOMETRY_TARGETS',len(targets))
