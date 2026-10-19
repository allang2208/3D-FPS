"""User-requested mage-set delivery and source topology audit."""
import json,hashlib,sys
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageSetAudit20261019';R.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
items=read(P/'Content/ColdSteelData/items.json');cfg=read(P/'Content/ColdSteelData/modular_outfits.json');body=read(P/'Content/ColdSteelData/player_body.json')
profiles=sorted({v['rig_profile'] for v in cfg['profiles'].values()});report=dict(items={},geometry={},profiles=profiles,failures=[])
def paths(value):
    if isinstance(value,dict):
        for k,v in value.items():yield from paths(k);yield from paths(v)
    elif isinstance(value,list):
        for v in value:yield from paths(v)
    elif isinstance(value,str) and value.startswith('/Game/'):yield value
for label,family in [('robe','BlueMageRobe20261018'),('hat','BlueMageHat20261019'),('gloves','BlueMageGloves20261019'),('pants','BlueMagePants20261019'),('boots','BlueMageBoots20261019')]:
    key='ue_blue_mage_'+label;item=items[key];recipe=cfg['items'].get(key,body.get('head_equipment',{}).get(key,{}));canonical=P/'Content/ColdSteelData/Icons'/(key+'.png');family_png=P/'Content/ColdSteelData'/item['ue_icon'];im=Image.open(canonical);a=np.asarray(im)
    missing=[v for v in sorted(set(paths(item))|set(paths(recipe))) if not (P/'Content'/(v[6:].split('.')[0]+'.uasset')).exists()]
    row=dict(missing_packages=missing,canonical_icon=str(canonical),icon_size=im.size,alpha_channel=im.mode=='RGBA',alpha_nonzero=int((a[:,:,-1]>0).sum()),same_family_png=canonical.read_bytes()==family_png.read_bytes(),missing_profiles=sorted(set(profiles)-set(recipe.get('rig_meshes',{}))) if label in ('robe','gloves') else [],appearance_family=family)
    report['items'][key]=row
    if missing or row['missing_profiles'] or not row['same_family_png']:report['failures'].append(key+' missing routes/assets/icon')
robe=cfg['items']['ue_blue_mage_robe'];main=read(P/'SourceAssets/BlueMageRobe20261018/saved_assets.json')
report['robe_republish_loss']=dict(underlayer_paths=sorted(set(robe['underlayer_meshes'])-set(main.get('underlayers',{}))),recipe_fields=sorted(set(robe)-{'slot','part','material','appearance_family','cloth_simulation','rig_meshes','owner_body_meshes','covers','rig_world_covers','underlayer_meshes','leg_fit_revision'}))
sources=[P/'SourceAssets/BlueMagePants20261019/Authored/Jason_BlueMagePants_Garment.json',P/'SourceAssets/BlueMageBoots20261019/Authored/Jason_BlueMageBoots_Garment.json',P/'SourceAssets/BlueMageHat20261019/Authored/hat.json']
sources.extend(P/'SourceAssets/BlueMageRobe20261018/Authored/Body'/(name+'.json') for name in ('Body','Jason'))
sources.extend(P/'SourceAssets/BlueMageRobe20261018/Authored/FP'/(name+'.json') for name in profiles if name not in ('Body','Jason'))
sources.extend(Path(row['authored']) for row in read(P/'SourceAssets/BlueMageGloves20261019/manifest.json')['rows'])
for path in sources:
    d=read(path);p=np.asarray(d['positions']);f=np.asarray(d['triangles'],int);n=np.asarray(d['normals']);uv=np.asarray(d['uv']);area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)*.5
    _,labels=np.unique(np.round(p,6),axis=0,return_inverse=True);faces=np.sort(labels[f],axis=1);_,counts=np.unique(faces,axis=0,return_counts=True);duplicate_faces=int(np.sum(counts-1));edges=np.sort(np.concatenate([labels[f[:,[0,1]]],labels[f[:,[1,2]]],labels[f[:,[2,0]]]]),axis=1);_,ec=np.unique(edges,axis=0,return_counts=True)
    ws=d.get('weights',[]);sums=np.asarray([sum(w.values()) if isinstance(w,dict) else sum(x[1] for x in w) for w in ws]);badweights=int(np.sum(abs(sums-1)>1.e-4))
    row=dict(vertices=len(p),triangles=len(f),finite=bool(np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all()),degenerate=int(np.sum(area<1.e-8)),duplicate_position_faces=duplicate_faces,position_nonmanifold_edges=int(np.sum(ec>2)),position_boundary_edges=int(np.sum(ec==1)),weight_sum_errors=badweights,max_influences=max(map(len,ws),default=0),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report['geometry'][str(path.relative_to(P))]=row
    if not row['finite'] or row['degenerate'] or row['duplicate_position_faces'] or badweights:report['failures'].append(str(path.relative_to(P)))
(R/('source-audit-'+(sys.argv[1] if len(sys.argv)>1 else 'before')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(failures=report['failures'],geometry=report['geometry']),ensure_ascii=False,indent=2))
