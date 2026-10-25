"""Publish all fitted bed roles and native camera tracks without touching apartment beds."""
import json,runpy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','BedFamilyReuse20261024')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
native=read(OUT/'native_saved_samples.json');rig=read(OUT/'authored.json');inventory=read(OUT/'inventory.json')
config=read(ROOT/'Content/ColdSteelData/furniture_rest.json');body=read(ROOT/'Content/ColdSteelData/player_body.json');saved=read(OUT/'assets_saved.json')
for kind,profiles in inventory['models'].items():
    current={p['mesh'] for p in config['furniture'] if any(s['kind']==kind for s in p['slots'])}
    if current!={p['mesh'] for p in profiles}:raise RuntimeError('Bed model coverage changed: '+kind)
bind=[]
for i,p in enumerate(rig['parents']):
    v=rig['reference'][i];m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.asarray(v[7:])[None,:];m[:3,3]=v[:3];bind.append(bind[p]@m if p>=0 else m)
offsets={'default':bind[rig['names'].index('head')][:3,:3].T@np.array([0.,7.,6.])}
geometry=ROOT/'SourceAssets/KaitlinPlayer20261023/NativeGeometry';bones=read(geometry/'MHC_Kaitlin_Body.json')['bones'];face=read(geometry/'SKM_MHC_Kaitlin_FaceMesh.json')
head=next(b for b in bones if b['name']=='head');eyes=np.asarray([b['position'] for b in face['bones'] if b['name'] in ('FACIAL_L_Eye','FACIAL_R_Eye')]);offsets['kaitlin']=np.asarray(head['axes'])@(eyes.mean(axis=0)-np.asarray(head['position']))
tracks={}
for variant,spec in native.items():
    node=body if variant=='default' else body['body_variants'][variant]
    if spec['mesh']!=node['body_mesh']:raise RuntimeError('Native body changed: '+variant)
    routes=saved['default'] if variant=='default' else saved['variants'][variant];head=spec['names'].index('head');tracks[variant]={}
    for role,take in spec['clips'].items():
        if take['asset']!=routes[role]:raise RuntimeError('Camera source changed: '+role)
        points=[]
        for frame in take['world']:
            p=np.asarray(frame[head]);points.append((p[:3]+R.from_quat(p[3:7]).as_matrix()@(offsets[variant]*p[7:])).tolist())
        tracks[variant][role]={'duration':take['duration'],'eyes':points,'animation':take['asset']}
runpy.run_path(str(Path(__file__).with_name('publish_chair_reuse.py')),init_globals={'FURNITURE_REVISION':OUT.name,'NATIVE_CAMERA_UPDATES':tracks})
(OUT/'native_camera_tracks.json').write_text(json.dumps(tracks,separators=(',',':')))
print('BED_FAMILY_PUBLISHED',len(inventory['types']),'types',sum(map(len,inventory['models'].values())),'models')
