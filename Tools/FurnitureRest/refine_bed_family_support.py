"""Small supported-body lift for the remaining mattress contacts; keep palms and ankles fixed."""
import copy,hashlib,json,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'SourceAssets/FurnitureRest20261022/BedFamilyReuse20261024';OUT=BASE.parent/'BedFamilyReuse20261025'
OUT.mkdir(exist_ok=True);read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
data=read(BASE/'authored.json');metadata=read(BASE/'clip_metadata.json');changed=[]
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')};exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,ix,bind,solve,smooth=[ns[n] for n in ('fk','ix','bind','solve','smooth')]
for kind in ('Hospital','Ward','Bunk'):
    role=f'Rest.{kind}.Enter';frames=[]
    for j,original in enumerate(data['clips'][role]['frames']):
        f=np.asarray(original).copy();w=fk(f);t=j/30;lift=.8*float(smooth((t-.40)/.12)*(1-smooth((t-2.85)/.35)))
        if lift>0:
            f[ix['pelvis'],2]+=lift
            for side in ('l','r'):
                for chain in (('thigh','calf','foot'),('upperarm','lowerarm','hand')):
                    end=ix[chain[-1]+'_'+side];solve(f,side,chain,w[end,:3,3],w[end,:3,:3])
        frames.append(f.tolist())
    for phase,poses in [('Enter',frames),('Exit',copy.deepcopy(frames[::-1])+[copy.deepcopy(frames[0]) for _ in range(3)])]:
        role=f'Rest.{kind}.{phase}';data['clips'][role]['frames']=poses;camera=[]
        for f in poses:
            h=fk(np.asarray(f))[ix['head']];eye=h[:3,3]+h[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
        metadata[role]['camera']=camera;changed.append(role)
data['changed_roles']=changed;data['support_refinement']={'source_revision':BASE.name,'lift_cm':.8,'palms_and_ankles_preserved':True}
(OUT/'authored.json').write_text(json.dumps(data,separators=(',',':')))
for name in ('baseline_routes.json','baseline.json','fit_parameters.json','inventory.json','type_updates.json'):
    shutil.copy2(BASE/name,OUT/name)
review=read(BASE/'review_config.json');review['clips'].update(metadata)
for name,value in [('review_config.json',review),('clip_metadata.json',metadata)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True);index=read(BASE/'Geometry/index.json')
(OUT/'Geometry/index.json').write_text(json.dumps({k:str(BASE/'Geometry'/v) for k,v in index.items()},indent=2))
(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):shutil.copy2(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
old=read(BASE/'assets_saved.json');source_hash=hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest()
receipt={'source_sha256':source_hash,'default':{r:p for r,p in old['default'].items() if r not in changed},'variants':{v:{r:p for r,p in routes.items() if r not in changed} for v,routes in old['variants'].items()},'unchanged_roles_reused_from':BASE.name}
if (OUT/'assets_saved.json').exists():raise RuntimeError('Support revision already saved; preserve it.')
(OUT/'assets_saved.json').write_text(json.dumps(receipt,indent=2))
print('BED_SUPPORT_REFINED',len(changed),'roles;',len(receipt['default']),'unchanged native roles retained per body')
