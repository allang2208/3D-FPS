"""Join the fitted apartment side entry to the new Meshy-supported lie-down."""
import copy,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyApartmentBed20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
helper={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],helper)
fk,ix,smooth,blend,solve,bind,rot=[helper[n] for n in ('fk','ix','smooth','blend','solve','bind','rot')]
old=read(OUT.parent/'BedHandDriveV10/authored.json');source=read(OUT.parent/'MeshyBedSupportedHands20261024/authored.json')
main=read(ROOT/'Content/ColdSteelData/furniture_rest.json');apartment=read(ROOT/'Content/ColdSteelData/apartment_furniture_rest.json')
geometry=read(OUT/'Geometry/index.json');mesh=next(p for p in apartment['furniture'] if 'RefinementV3' in p['mesh'] and p['slots'][0]['kind']=='ApartmentBed')
g=read(OUT/'Geometry'/geometry[mesh['mesh']]);tri=np.asarray(g['positions'])[np.asarray(g['triangles'],int)]*np.asarray(mesh['scale'])
origin=tri[:,0,:2];a=tri[:,1,:2]-origin;b=tri[:,2,:2]-origin;den=a[:,0]*b[:,1]-a[:,1]*b[:,0];valid=abs(den)>1e-8
def surface(x,y):
    q=np.array([x,y])-origin;u=np.divide(q[:,0]*b[:,1]-q[:,1]*b[:,0],den,out=np.zeros_like(den),where=valid);v=np.divide(a[:,0]*q[:,1]-a[:,1]*q[:,0],den,out=np.zeros_like(den),where=valid)
    mask=valid&(u>=0)&(v>=0)&(u+v<=1);z=tri[:,0,2]+u*(tri[:,1,2]-tri[:,0,2])+v*(tri[:,2,2]-tri[:,0,2]);return float(z[mask].max()) if mask.any() else 0.
prefix=[]
for j,f in enumerate(np.asarray(old['clips']['Rest.ApartmentBed.Enter']['frames'])[:136]):
    f=f.copy();f[ix['pelvis'],0]-=39.*float(1-smooth((j/30)/1.15));prefix.append(f)
core=[]
for f in np.asarray(source['clips']['Rest.Bed.Enter']['frames'])[96:]:
    f=f.copy();f[ix['pelvis'],:3]+=[-8.,-38.,0.];core.append(f)
join=[blend(prefix[-1],core[0],float(smooth(i/24))) for i in range(1,25)]
enter=prefix+join+core[1:]
for j,f in enumerate(enter):
    if j<136:continue
    amount=float(smooth((j-135)/12))
    for side in ('l','r'):
        w=fk(f);foot=ix['foot_'+side];goal=w[foot,:3,3].copy();top=surface(*goal[:2]);goal[2]+=max(0.,top+11.-goal[2])*amount
        solve(f,side,('thigh','calf','foot'),goal,w[foot,:3,:3])
idle=[]
for f in np.asarray(source['clips']['Rest.Bed.Idle']['frames']):
    f=f.copy();f[ix['pelvis'],:3]+=[-8.,-38.,0.]
    for side in ('l','r'):
        w=fk(f);foot=ix['foot_'+side];goal=w[foot,:3,3].copy();goal[2]=max(goal[2],surface(*goal[:2])+11.)
        solve(f,side,('thigh','calf','foot'),goal,w[foot,:3,:3])
    idle.append(f)
def settle(f,time):
    contact=float(smooth((time-1.1)/.5));f[ix['pelvis'],2]+=.45*contact+.35*float(smooth((time-1.5)/.2)*(1-smooth((time-2.2)/.3)))
    for side in ('l','r'):
        w=fk(f);hand=ix['hand_'+side]
        solve(f,side,('upperarm','lowerarm','hand'),w[hand,:3,3]+[0.,0.,1.6*contact],w[hand,:3,:3])
    angle=8.*float(smooth((time-9.3)/1.3));w=fk(f)
    for name,factor in [('neck_01',1.),('neck_02',1.),('head',.5)]:
        rot(f,ix[name],R.from_euler('x',angle*factor,degrees=True).as_matrix()@w[ix[name],:3,:3])
for j,f in enumerate(enter):settle(f,j/30)
for f in idle:settle(f,11.)
exit_frames=[f.copy() for f in enter[::-1]]+[enter[0].copy() for _ in range(9)]
data={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};data['clips']={};metadata={}
for phase,frames in [('Enter',enter),('Idle',idle),('Exit',exit_frames)]:
    role='Rest.ApartmentBed.'+phase;duration=(len(frames)-1)/30;camera=[]
    for f in frames:
        w=fk(f)[ix['head']];eye=w[:3,3]+w[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
    data['clips'][role]={'duration':duration,'rate':30,'frames':np.asarray(frames).tolist()};metadata[role]={'duration':duration,'camera':camera}
candidate=copy.deepcopy(apartment);candidate['clips'].update(metadata);candidate['types']['ApartmentBed'].update({'entry_offset':[-200.,0.,0.],'entry_yaw':90.})
for row in candidate['furniture']:
    for slot in row['slots']:
        if slot['kind']=='ApartmentBed':slot['seat']=[0.,10. if 'RefinementV14' in row['mesh'] else 0.,67.]
review=copy.deepcopy(main);review['types'].update(candidate['types']);review['clips'].update(candidate['clips']);review['furniture'].extend(reversed(candidate['furniture']))
body=read(ROOT/'Content/ColdSteelData/player_body.json');roles=list(data['clips']);snapshot=OUT/'baseline_routes.json'
if not snapshot.exists():snapshot.write_text(json.dumps({'default':{r:body['clips'][r] for r in roles},'variants':{n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body['body_variants'].items() if v.get('ready')}},indent=2))
for name,value in [('authored.json',data),('clip_metadata.json',metadata),('review_config.json',review),('apartment_candidate.json',candidate)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('APARTMENT_MESHY_AUTHORED',[(k,v['duration']) for k,v in data['clips'].items()],flush=True)
