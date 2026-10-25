"""Record effective mesh-to-kind-to-native-clip bindings after publication."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyApartmentBed20261024';BUILD=OUT.parent/'ApartmentIntegration20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
body=read(ROOT/'Content/ColdSteelData/player_body.json');ap=read(ROOT/'Content/ColdSteelData/apartment_furniture_rest.json');saved=read(OUT/'assets_saved.json');native=read(OUT/'native_saved_samples.json');rows=[]
for profile in ap['furniture']:
    for slot in profile['slots']:
        if slot['kind']!='ApartmentBed':continue
        for variant,node in [('default',body),('kaitlin',body['body_variants']['kaitlin'])]:
            routes=saved['default'] if variant=='default' else saved['variants'][variant]
            for phase in ('Enter','Idle','Exit'):
                role='Rest.'+slot['kind']+'.'+phase;asset=node['clips'][role];camera=node['furniture_camera_tracks'][role]
                package=ROOT/'Content'/(asset.split('.')[0][6:]+'.uasset');duration=ap['clips'][role]['duration']
                if asset!=routes[role] or not package.is_file():raise RuntimeError('Runtime route does not use the saved clip: '+role)
                if camera['animation']!=asset or abs(camera['duration']-duration)>.001 or abs(native[variant]['clips'][role]['duration']-duration)>.001:raise RuntimeError('Clock or native eye track mismatch: '+role)
                rows.append({'mesh':profile['mesh'],'kind':slot['kind'],'body':variant,'role':role,'asset':asset,'duration':duration,'native_camera_matches':True})
builds=[read(BUILD/('build-01-'+target+'.json')) for target in ('FPSGAMEEditor','FPSGAME')]
if any(r['exit_code']!=0 for r in builds):raise RuntimeError('Required build failed.')
receipt={'effective_routes':rows,'runtime_published':True,'builds':builds,
    'interaction':'250 cm aimed reach; lying furniture aligns directly to its authored entry with a clear destination; chair approach remains swept',
    'cache_lifetime':'per play world; existing active rest is not hot-swapped',
    'native_assets':saved,'stage_joins':read(OUT/'native_stage_review.json'),
    'geometry':read(OUT/'geometry_audit_saved.json'),'hands_body':read(OUT/'hand_body_contact_saved.json'),
    'geometry_scope':'Jason body/head on all three apartment bed meshes; both native skeletons checked for phase joins, Kaitlin skinned contacts not checked',
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),
    'game_tested':False,'multiplayer_tested':False,'interactive_editor_started':False,
    'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('Source/FPSGAME/Movement/FPSFurnitureRestComponent.cpp','Source/FPSGAME/Characters/FPSPlayerBodyVariants.cpp')},
    'git_commit':None,'git_push':None}
(OUT/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('APARTMENT_INTEGRATION_RECORDED',len(rows),'effective routes')
