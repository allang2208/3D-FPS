"""Tailor paired native sleeves, physical UVs and a shared cuff inertia mask."""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import finish, smooth, unit, write

P=Path('D:/FPS3D/FPSGAME')
BASE=P/'SourceAssets/BlueMageRobe20261018'
OUT=BASE/'FPSoftSleeves20261020'
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
routes={k:v for k,v in cfg['items']['ue_blue_mage_robe']['rig_meshes'].items() if k not in ('Body','Jason')}
records=[]
for profile,path in routes.items():
    source=BASE/'Authored/FP'/(profile+'.json')
    data=json.loads(source.read_text())
    positions=np.array(data['positions']);colors=np.zeros((len(positions),4));colors[:,3]=1.
    sides=np.array([max(('l','r'),key=lambda s:sum(w for n,w in row.items() if n.endswith('_'+s))) for row in data['weights']])
    for channel,side in enumerate(('l','r')):
        ids=np.flatnonzero(sides==side)
        if not len(ids):continue
        half=len(ids)//2
        outer,inner=ids[:half],ids[half:]
        if len(outer)!=len(inner):raise RuntimeError('Unpaired sleeve source '+profile)
        middle=(positions[outer]+positions[inner])*.5
        radial=positions[outer]-positions[inner]
        radial/=np.maximum(np.linalg.norm(radial,axis=1)[:,None],1.e-8)
        a,e,w=[np.array(data['bones'][name+'_'+side]['position']) for name in ('upperarm','lowerarm','hand')]
        upper,lower=unit(e-a),unit(w-e)
        prox=-(middle-w)@lower
        upper_length=np.linalg.norm(e-a)
        blend=smooth(((middle-e)@lower+4.)/8.)
        axis=(1-blend[:,None])*upper+blend[:,None]*lower
        axis/=np.linalg.norm(axis,axis=1)[:,None]
        seed=unit(np.cross(upper,lower))
        if np.linalg.norm(seed)<.5:seed=unit(np.cross(upper,[0,1,0]))
        theta=np.arctan2(np.einsum('ij,ij->i',radial,np.cross(axis,seed)),radial@seed)
        along=upper_length+np.einsum('ij,ij->i',middle-e,axis)
        cuff=1-smooth((prox-3.5)/3.5)
        shoulder=smooth((((middle-a)@upper)-1.)/6.)
        elbow=1-.30*np.exp(-np.sum((middle-e)**2,axis=1)/25.)
        allowance=(.65*cuff+1.1*(1-cuff))*shoulder*elbow
        folds=(.13*np.sin(theta*3+along*.18)+.09*np.sin(theta*5-along*.13))
        folds*=shoulder*(1-.72*cuff)
        thickness=.18+.04*cuff
        center=middle+radial*(allowance+folds)[:,None]
        positions[outer]=center+radial*(thickness*.5)[:,None]
        positions[inner]=center-radial*(thickness*.5)[:,None]
        motion=1-smooth((prox-2.)/9.)
        colors[outer,channel]=motion;colors[inner,channel]=motion
        # Estimate each station circumference from the native arm axis. Both
        # surfaces get identical coordinates and motion masks at paired points.
        q=middle-e
        across=q-axis*np.einsum('ij,ij->i',q,axis)[:,None]
        radius=np.maximum(np.linalg.norm(across,axis=1)+allowance,1.)
        for fi,face in enumerate(data['triangles']):
            if sides[face[0]]!=side or data['triangle_materials'][fi] not in (1,3):continue
            # Retain narrow rim UVs; map both sleeve surfaces in centimetres.
            ids_face=np.asarray(face)
            pair_ids=np.searchsorted(ids,ids_face)
            if np.any(pair_ids<half) and np.any(pair_ids>=half):
                data['uv'][fi]=(np.asarray(data['uv'][fi])*25/8).tolist()
                continue
            local=pair_ids%half
            angles=(theta[local]/math.tau)%1
            if np.ptp(angles)>.5:angles=np.where(angles<.5,angles+1,angles)
            data['uv'][fi]=np.column_stack((angles*math.tau*radius[local]/8.,along[local]/8.)).tolist()
    data['positions']=positions.tolist();data['colors']=colors.tolist()
    data['contract']='Robe FP relaxed paired sleeves; native weights; physical 8 cm twill UV; shared cuff inertia max 0.28 cm'
    finish(data)
    file=OUT/'Authored'/f'{profile}.json';write(file,data)
    records.append(dict(profile=profile,source_mesh=path,source_file=str(source),file=str(file),
        triangles=len(data['triangles']),vertices=len(data['positions'])))
    print('SOFT_ROBE_SLEEVE_AUTHORED',profile,flush=True)
write(OUT/'manifest.json',dict(completed=True,revision='soft-sleeves-20261020',
    routes=routes,records=records,fabric_tile_cm=8.,max_cuff_offset_cm=.28,
    spring_frequency_hz=4.5,damping_ratio=.9,runtime_tested=False))
