"""Publish only completed furniture or jacket-fit fields against current shared data."""
import hashlib,json,runpy,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
sha=lambda path:hashlib.sha256((P/'Content'/(path[6:].split('.')[0]+'.uasset')).read_bytes()).hexdigest()
part=sys.argv[1];path=P/'Content/ColdSteelData/player_body.json';before=path.read_bytes();body=json.loads(before.decode('utf-8-sig'));owned=[]
if part=='furniture':
    folder=W/'Furniture';catalog=read(folder/'source_catalog.json');saved=read(folder/'saved_assets.json');camera=read(folder/'camera_tracks.json')
    if set(saved)!=set(catalog['stale_roles']):raise RuntimeError('Incomplete furniture saves')
    female=body['body_variants']['kaitlin']
    for role,source in catalog['clips'].items():
        if body['clips'][role]!=source or sha(source)!=catalog['source_sha256'][role]:raise RuntimeError('Furniture source changed: '+role)
        target=saved[role]['asset'] if role in saved else catalog['female_before'][role]
        if female['clips'][role] not in (catalog['female_before'][role],target):raise RuntimeError('Female route changed: '+role)
        if camera[role]['animation']!=target:raise RuntimeError('Camera belongs to another clip: '+role)
        sha(target)
        if role in saved:female['clips'][role]=target;owned.append(('body_variants','kaitlin','clips',role))
    female['furniture_camera_tracks']=camera;owned.append(('body_variants','kaitlin','furniture_camera_tracks'))
elif part=='packs':
    folder=W/'Packs';rows=read(folder/'manifest.json');saved=read(folder/'saved_assets.json');inputs=read(folder/'inputs.json');baseline=read(W/'body_before.json')
    if len(rows)!=len(saved):raise RuntimeError('Incomplete pack saves')
    for source,record in inputs.items():
        if sha(source)!=record['sha256']:raise RuntimeError('Fitting source changed: '+source)
    for row in rows:
        prefix=() if row['rig']=='Jason' else ('body_variants','kaitlin')
        node=body;old=baseline
        for key in prefix:node=node[key];old=old[key]
        item=row['item'];recipe=node['outfits'][item];base=old['outfits'][item]
        if recipe['world_mesh']!=row['source']:raise RuntimeError('Pack route changed: '+item)
        for field in ('mesh','location','rotation_quat'):
            if recipe.get('rigid_pack',{}).get(field)!=base.get('rigid_pack',{}).get(field):raise RuntimeError('Rigid pack mount changed: '+item)
        if recipe.get('hanging_pack')!=base.get('hanging_pack'):raise RuntimeError('Sling support changed: '+item)
        key=row['rig']+'/'+item;target=saved[key]
        if target!=row['asset']+'.'+row['asset'].rsplit('/',1)[-1]:raise RuntimeError('Latest pack revision not saved: '+key)
        sha(target)
        fit=recipe.setdefault('world_mesh_by_shirt',{})
        if fit.get('ue_work_jacket') not in (None,target):raise RuntimeError('Another jacket fit exists: '+key)
        fit['ue_work_jacket']=target;owned.append(prefix+('outfits',item,'world_mesh_by_shirt','ue_work_jacket'))
        if 'rigid_location' in row:
            recipe['rigid_pack'].setdefault('location_by_shirt',{})['ue_work_jacket']=row['rigid_location']
            owned.append(prefix+('outfits',item,'rigid_pack','location_by_shirt','ue_work_jacket'))
        if 'hanging_pack' in row:
            recipe.setdefault('hanging_pack_by_shirt',{})['ue_work_jacket']=row['hanging_pack']
            owned.append(prefix+('outfits',item,'hanging_pack_by_shirt','ue_work_jacket'))
        for name,fn in [('bounds_min',min),('bounds_max',max)]:
            recipe['backpack_motion'][name]=[fn(a,b) for a,b in zip(recipe['backpack_motion'][name],row[name])]
            owned.append(prefix+('outfits',item,'backpack_motion',name))
else:raise RuntimeError('Expected furniture or packs')
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit']
receipt=commit(path,before,body,owned_paths=owned,producer=__file__)
(W/(part+'_publication.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('KAITLIN_COMPLETION_PUBLISHED',part,len(owned),'owned fields')
