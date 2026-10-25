"""Use the selected native entry backwards at its original rate for bed exit."""
import copy,json,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentReverseExit20261024'
BASE=OUT.parent/'ApartmentFastRest20261024R2'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source=read(BASE/'ReviewSaved/saved_poses.json');body=read(ROOT/'Content/ColdSteelData/player_body.json')
apartment=read(ROOT/'Content/ColdSteelData/apartment_furniture_rest.json');main=read(ROOT/'Content/ColdSteelData/furniture_rest.json')
enter='Rest.ApartmentBed.Enter';leave='Rest.ApartmentBed.Exit'
native=read(BASE/'native_saved_samples.json')
for variant,spec in native.items():
    live=body if variant=='default' else body['body_variants'][variant]
    if live['clips'][enter]!=spec['clips'][enter]['asset']:raise RuntimeError('Selected entry changed; capture the current native entry first: '+variant)
data=copy.deepcopy(source);entry=data['clips'][enter];rate=entry['rate']
frames=copy.deepcopy(entry['frames'][::-1])+[copy.deepcopy(entry['frames'][0]) for _ in range(3)]
duration=(len(frames)-1)/rate
data['clips'][leave]={'duration':duration,'rate':rate,'frames':frames};data['changed_roles']=[leave]
times=[(len(entry['frames'])-1-j)/rate for j in range(len(entry['frames']))]+[0.]*3
data['native_retime']={'source_revision':BASE.name,'source_assets':{v:s['clips'][enter]['asset'] for v,s in native.items()},'samples':{leave:times},'reverse_at_source_rate':True,'standing_hold_seconds':3/rate}
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,ix,bind=[ns[k] for k in ('fk','ix','bind')];camera=[]
for f in frames:
    h=fk(np.asarray(f))[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
metadata={leave:{'duration':duration,'camera':camera}};candidate=copy.deepcopy(apartment);candidate['clips'].update(metadata)
review=copy.deepcopy(main);review['types'].update(candidate['types']);review['clips'].update(candidate['clips']);review['furniture'].extend(reversed(candidate['furniture']))
baseline={'default':{leave:body['clips'][leave]},'variants':{v:{'mesh':body['body_variants'][v]['body_mesh'],'clips':{leave:body['body_variants'][v]['clips'][leave]}} for v in native if v!='default'}}
for name,value in [('baseline.json',{'apartment':apartment}),('baseline_routes.json',baseline)]:
    if not (OUT/name).exists():(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
for name,value in [('authored.json',data),('clip_metadata.json',metadata),('apartment_candidate.json',candidate),('review_config.json',review)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
shutil.copytree(BASE/'Geometry',OUT/'Geometry',dirs_exist_ok=True);(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):shutil.copy2(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
print('NATIVE_REVERSE_EXIT_AUTHORED',len(entry['frames']),'reversed frames;',duration,'seconds')
