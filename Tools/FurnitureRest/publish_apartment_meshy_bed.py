"""Publish fitted apartment motion, per-model anchors and native bed eye tracks."""
import copy,hashlib,json,os,runpy,uuid
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','MeshyApartmentBed20261024')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(OUT/'assets_saved.json');complete=read(OUT/'save_complete.json');baseline=read(OUT/'baseline_routes.json');prepared=read(OUT/'apartment_candidate.json')
if not complete['saved'] or hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest()!=complete['authored_sha256']:raise RuntimeError('Apartment save is incomplete or stale.')
helper=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();body=json.loads(before.decode('utf-8-sig'));owned=[]
native_bed=read(OUT.parent/'MeshyBedSupportedHands20261024/native_saved_samples.json');native_apartment=read(OUT/'native_saved_samples.json');rig=read(OUT/'authored.json');tracks={}
changed_cameras_only=globals().get('CHANGED_CAMERAS_ONLY',False)
bind=[]
for i,p in enumerate(rig['parents']):
    v=rig['reference'][i];m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.asarray(v[7:])[None,:];m[:3,3]=v[:3];bind.append(bind[p]@m if p>=0 else m)
male_offset=bind[rig['names'].index('head')][:3,:3].T@np.array([0.,7.,6.])
geometry=ROOT/'SourceAssets/KaitlinPlayer20261023/NativeGeometry';bones=read(geometry/'MHC_Kaitlin_Body.json')['bones'];face=read(geometry/'SKM_MHC_Kaitlin_FaceMesh.json')
joint=next(b for b in bones if b['name']=='head');eyes=np.asarray([b['position'] for b in face['bones'] if b['name'] in ('FACIAL_L_Eye','FACIAL_R_Eye')]);female_offset=np.asarray(joint['axes'])@(eyes.mean(axis=0)-np.asarray(joint['position']))
for variant,routes in [('default',saved['default']),*saved['variants'].items()]:
    node=body if variant=='default' else body['body_variants'][variant];prefix=() if variant=='default' else ('body_variants',variant)
    old=baseline['default'] if variant=='default' else baseline['variants'][variant]['clips']
    for role,asset in routes.items():
        if node['clips'][role] not in (old[role],asset):raise RuntimeError('Apartment route changed: '+variant+'/'+role)
        if not (ROOT/'Content'/(asset.split('.')[0][6:]+'.uasset')).is_file():raise RuntimeError('Missing saved asset: '+asset)
        node['clips'][role]=asset;owned.append(prefix+('clips',role))
    tracks[variant]={}
    for dataset in ((native_apartment,) if changed_cameras_only else (native_bed,native_apartment)):
        spec=dataset[variant];head=spec['names'].index('head');offset=male_offset if variant=='default' else female_offset
        if spec['mesh']!=node['body_mesh']:raise RuntimeError('Body mesh changed during authoring.')
        for role,take in spec['clips'].items():
            if changed_cameras_only and role not in routes:continue
            if node['clips'][role]!=take['asset']:raise RuntimeError('Eye track belongs to another animation: '+role)
            points=[]
            for frame in take['world']:
                pose=np.asarray(frame[head]);points.append((pose[:3]+R.from_quat(pose[3:7]).as_matrix()@(offset*pose[7:])).tolist())
            track={'duration':take['duration'],'eyes':points,'animation':take['asset']}
            node.setdefault('furniture_camera_tracks',{})[role]=track;tracks[variant][role]=track
            owned.append(prefix+('furniture_camera_tracks',role))

ap_path=ROOT/'Content/ColdSteelData/apartment_furniture_rest.json';ap_before=ap_path.read_bytes();ap=json.loads(ap_before.decode('utf-8-sig'));original=copy.deepcopy(ap);initial=read(OUT/'baseline.json')['apartment']
if ap['types']['ApartmentBed'] not in (initial['types']['ApartmentBed'],prepared['types']['ApartmentBed']):raise RuntimeError('Apartment anchor changed concurrently.')
ap['types']['ApartmentBed']=prepared['types']['ApartmentBed']
for role,meta in read(OUT/'clip_metadata.json').items():ap['clips'][role]=meta
expected={p['mesh']:p for p in prepared['furniture'] if any(s['kind']=='ApartmentBed' for s in p['slots'])}
original_profiles={p['mesh']:p for p in initial['furniture']}
current={p['mesh'] for p in ap['furniture'] if any(s['kind']=='ApartmentBed' for s in p['slots'])}
if current!=set(expected):raise RuntimeError('Apartment bed model coverage changed during fitting.')
for profile in ap['furniture']:
    if profile['mesh'] not in expected:continue
    desired=expected[profile['mesh']]
    if profile['slots'] not in (original_profiles[profile['mesh']]['slots'],desired['slots']):raise RuntimeError('Apartment slot changed concurrently.')
    profile['slots']=desired['slots']
edits=list(helper['_changes'](original,ap));text=ap_before.decode('utf-8-sig')
for key,value in edits:
    if key!=('furniture',) and key[:2]!=('types','ApartmentBed') and not (len(key)>1 and key[0]=='clips' and key[1] in saved['default']):raise RuntimeError('Unowned apartment field: '+repr(key))
    text=helper['_set'](text,key,value)
result=(b'\xef\xbb\xbf' if ap_before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
if json.loads(result.decode('utf-8-sig'))!=ap:raise RuntimeError('Apartment serialization differs from candidate.')
with helper['_lock'](ROOT/'Saved/FurnitureRestConfigWrites/writer.lock'):
    if ap_path.read_bytes()!=ap_before:raise RuntimeError('Apartment configuration changed; retry from fresh input.')
    backup=OUT/'apartment_furniture_rest.before.json'
    if not backup.exists():backup.write_bytes(ap_before)
    temporary=ap_path.with_name('.apartment-bed-'+uuid.uuid4().hex+'.tmp');temporary.write_bytes(result)
    os.replace(temporary,ap_path)
receipt=helper['commit'](path,before,body,owned_paths=owned,producer=__file__)
(OUT/'native_camera_tracks.json').write_text(json.dumps(tracks,separators=(',',':')))
(OUT/'publication.json').write_text(json.dumps({'body':receipt,'apartment_changed_paths':[list(k) for k,v in edits],'models':list(expected),'runtime_published':True,'game_tested':False},indent=2))
print('APARTMENT_MESHY_PUBLISHED',len(expected),'models;',len(owned),'body fields')
