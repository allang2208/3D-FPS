"""Retime the fitted native apartment motion with a smooth sub-four-second clock."""
import copy,json,shutil
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator,CubicHermiteSpline

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentFastRest20261024R2'
BASE=OUT.parent/'ApartmentLegTransfer20261024R2'
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source=read(BASE/'ReviewSaved/saved_poses.json')
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,ix,bind,blend=[ns[k] for k in ('fk','ix','bind','blend')]
# Extra time stays with seating and leg clearance. The quiet preparation and
# recline shorten more, with zero clock velocity at the standing/resting ends.
new_times=np.array([0.,.22,.75,1.1,1.9,2.12,2.28,3.,3.3])
old_times=np.array([0.,.25,1.2,1.75,3.,3.6,4.3,6.2,6.7])
slopes=PchipInterpolator(new_times,old_times).derivative()(new_times);slopes[[0,-1]]=0.
clock=CubicHermiteSpline(new_times,old_times,slopes)
entry_samples=np.clip(clock(np.arange(100)/30),0.,6.7).tolist()
# The runtime already spends 0.6 seconds aligning before Enter. Exit has no
# extra approach phase, so its reverse traversal keeps a little more time.
exit_samples=np.clip(clock(np.linspace(3.3,0.,115)),0.,6.7).tolist()+[0.]*3
native_routes=read(BASE/'assets_saved.json')
body=read(ROOT/'Content/ColdSteelData/player_body.json')
apartment=read(ROOT/'Content/ColdSteelData/apartment_furniture_rest.json')
main=read(ROOT/'Content/ColdSteelData/furniture_rest.json')
roles=['Rest.ApartmentBed.Enter','Rest.ApartmentBed.Exit']
baseline={'default':{r:body['clips'][r] for r in roles},'variants':{n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body['body_variants'].items() if v.get('ready')}}
for variant,routes in [('default',native_routes['default']),*native_routes['variants'].items()]:
    current=baseline['default'] if variant=='default' else baseline['variants'][variant]['clips']
    if any(current[r]!=routes[r] for r in roles):raise RuntimeError('The selected apartment motion changed: '+variant)
data={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};data['clips']={};data['changed_roles']=roles
data['native_retime']={'source_revision':BASE.name,'source_assets':{'default':native_routes['default']['Rest.ApartmentBed.Enter'],**{n:v['Rest.ApartmentBed.Enter'] for n,v in native_routes['variants'].items()}},'samples':dict(zip(roles,[entry_samples,exit_samples])),'clock':{'new_seconds':new_times.tolist(),'source_seconds':old_times.tolist(),'slopes':slopes.tolist()}}
old=np.asarray(source['clips']['Rest.ApartmentBed.Enter']['frames']);metadata={}
for role,times in data['native_retime']['samples'].items():
    frames=[];camera=[]
    for t in times:
        v=np.clip(t*30,0,len(old)-1);j=min(int(v),len(old)-2);f=blend(old[j],old[j+1],v-j);frames.append(f.tolist())
        h=fk(f)[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
    duration=(len(frames)-1)/30;data['clips'][role]={'duration':duration,'rate':30,'frames':frames};metadata[role]={'duration':duration,'camera':camera}
data['clips']['Rest.ApartmentBed.Idle']=copy.deepcopy(source['clips']['Rest.ApartmentBed.Idle'])
candidate=copy.deepcopy(apartment);candidate['clips'].update(metadata)
review=copy.deepcopy(main);review['types'].update(candidate['types']);review['clips'].update(candidate['clips']);review['furniture'].extend(reversed(candidate['furniture']))
for name,value in [('baseline.json',{'apartment':apartment}),('baseline_routes.json',baseline)]:
    if not (OUT/name).exists():(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
for name,value in [('authored.json',data),('clip_metadata.json',metadata),('apartment_candidate.json',candidate),('review_config.json',review)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
shutil.copytree(BASE/'Geometry',OUT/'Geometry',dirs_exist_ok=True);(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):shutil.copy2(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
print('FAST_REST_AUTHORED',[(r,data['clips'][r]['duration']) for r in roles])
