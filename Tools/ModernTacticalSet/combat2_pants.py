"""Continuous female trouser deformation from paired body surfaces, not bone regions."""
import sys,copy,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter,map_coordinates
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,smooth_transport
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR2';W=P/'SourceAssets/KaitlinPlayer20261023';D=S/'Integration/Delivery'
captured=read(W/'FitInputs/captured.json');cfg=read(W/'FitInputs/modular_outfits.json');body=read(W/'FitInputs/player_body.json');source=read(W/'FitInputs'/captured[cfg['profiles'][body['body_mesh']]['native_bare_skin']]['file']);target=read(W/'NativeGeometry/MHC_Kaitlin_Body.json')
sp=np.array(source['positions']);tp=np.empty_like(sp);tp[np.array(read(W/'body_correspondence.json')['target_to_source_vertices'],int)]=np.array(target['positions']);delta=tp-sp
low=sp[:,2]<112;sp=sp[low];delta=delta[low];tree=cKDTree(sp)
step=1.5;origin=np.array([-32.,-27.,10.]);shape=(45,39,67);coords=np.indices(shape).reshape(3,-1).T*step+origin
dist,near=tree.query(coords,k=48,workers=4);weights=np.exp(-((dist-dist[:,:1])/3.5)**2);weights/=weights.sum(1,keepdims=True)
field=(delta[near]*weights[:,:,None]).sum(1).reshape(*shape,3)
for axis in range(3):field[:,:,:,axis]=gaussian_filter(field[:,:,:,axis],.9,mode='nearest')
np.savez_compressed(R/'Authored/female-trouser-field.npz',field=field,origin=origin,step=step)
for kind in ['pants','pants_boot','pants_short','pants_high']:
    male=read(D/f'{kind}_Jason_Wear.json');old=read(D/f'{kind}_Kaitlin_Wear.json');p=np.array(male['positions']);original=p.copy();bones={b['name']:np.array(b['position']) for b in male['bones']};faces=np.array(male['triangles']);cloth=np.unique(faces[[not male['material_slots'][i].startswith('NATIVE:') for i in male['triangle_materials']]])
    def ease(x):x=np.clip(x,0,1);return x*x*(3-2*x)
    for i in cloth:
        q=p[i];z=q[2]
        if not 32<z<91:continue
        side='l' if q[0]>0 else 'r';foot,knee,hip=[bones[k+'_'+side] for k in ['foot','calf','thigh']];a,b=(foot,knee) if z<knee[2] else (knee,hip);center=a+(b-a)*((z-a[2])/(b[2]-a[2]));v=q-center;v[2]=0;r=np.linalg.norm(v)
        if r<.1:continue
        theta=np.arctan2(v[1],v[0]);loading=np.exp(-((z-knee[2])/6.5)**2);volume=.72+.48*np.exp(-((z-69)/11)**2)
        volume+=(.32*np.sin((z-knee[2])*1.18+.55*np.cos(theta))+.09*np.sin((z-knee[2])*.63-theta*2))*loading
        volume*=ease((z-32)/6)*(1-ease((z-82)/9));volume*=1-(1-ease(abs(q[0])/8))*ease((z-65)/12)
        p[i]+=v/r*volume
    male['positions']=p.tolist();smooth_transport(male,original);result=copy.deepcopy(old)
    c=((p-origin)/step).T;moved=p+np.column_stack([map_coordinates(field[:,:,:,axis],c,order=3,mode='nearest') for axis in range(3)])
    # Retain the actual native waistband and its published tuck contract.
    keep=np.clip((p[:,2]-96.0)/3.0,0,1);keep=keep*keep*(3-2*keep);moved=moved*(1-keep[:,None])+np.array(old['positions'])*keep[:,None]
    f=np.array(old['triangles']);skin=np.unique(f[[old['material_slots'][i].startswith('NATIVE:') for i in old['triangle_materials']]])
    moved[skin]=np.array(old['positions'])[skin];result['positions']=moved.tolist();result['normals']=copy.deepcopy(male['normals']);smooth_transport(result,p)
    result['contract']='Continuous smooth paired-body displacement field for cloth, seams and pockets; actual native female waistband and skin patch retained; no discrete nearest-bone geometry regions'
    for rig,d in [('Jason',male),('Kaitlin',result)]:
        d['materials']=[s[7:] if s.startswith('NATIVE:') else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+s.removeprefix('TS01_') for s in d['material_slots']];write(R/'Authored'/f'{kind}_{rig}.json',d)
    print('TS01_R2_TROUSERS',kind,flush=True)
