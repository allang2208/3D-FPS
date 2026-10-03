"""Create actual inventory icon and material recipe; no acceptance render/test."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).parent;P=O.parents[1]
recipe={
 'h-190':{'preset':'CleanAnodized','color':[.021,.023,.026],'roughness':.46,'metallic':1},
 'stell':{'preset':'CleanSatinSteel','color':[.034,.036,.037],'roughness':.42,'metallic':1},
 'copper':{'preset':'CleanPolishedSteel','color':[.47932,.171441,.0331048],'roughness':.30,'metallic':1},
 'brass':{'preset':'CleanPolishedSteel','color':[.445201,.366252,.0528608],'roughness':.30,'metallic':1},
 'polymer':{'preset':'CleanPolymer','color':[.019,.019,.019],'roughness':.55,'metallic':0},
 'Magazine_stell':{'preset':'CleanSatinSteel','color':[.034,.036,.037],'roughness':.42,'metallic':1},
 'Magazine_polymer':{'preset':'CleanPolymer','color':[.019,.019,.019],'roughness':.55,'metallic':0}}
(O/'finish_recipe.json').write_text(json.dumps({'master':'/Game/Weapons/WeaponSurface/Master/M_WeaponSurface','slots':recipe,'source_textures':False,'micro_mapping':'shared pre-skinned centimetre mapping','source_uv0_and_normals':'retained','tests':'not performed'},indent=2),encoding='utf8')
parts=json.loads((O/'icon_parts.json').read_text(encoding='utf8'))
size=768;pixels=np.zeros((size,size,4),dtype=np.uint8);depth=np.full((size,size),-np.inf)
direction=np.array([1.,.24,.12]);direction/=np.linalg.norm(direction)
right=np.array([-.24,1.,0.]);right/=np.linalg.norm(right);up=np.cross(direction,right)
allv=np.concatenate([np.array(p['verts']) for p in parts]);xy=np.stack((allv@right,allv@up),axis=1)
lo=xy.min(0);hi=xy.max(0);scale=(size*.88)/max(hi-lo);center=(hi+lo)*.5
light=np.array([.68,-.30,.67]);light/=np.linalg.norm(light)
for part in parts:
    verts=np.array(part['verts']);uv=np.stack((verts@right,verts@up),axis=1)
    screen=(uv-center)*scale+size*.5;screen[:,1]=size-screen[:,1];z=verts@direction
    spec=recipe.get(part['material']);base=np.array(spec['color'] if spec else [.018,.85,.008]);metal=spec['metallic'] if spec else 0
    for f in part['faces']:
        for j in range(1,len(f)-1):
            ids=[f[0],f[j],f[j+1]];v=verts[ids];q=screen[ids];zz=z[ids]
            normal=np.cross(v[1]-v[0],v[2]-v[0]);length=np.linalg.norm(normal)
            if length<1e-12:continue
            normal/=length
            if np.dot(normal,direction)<0:normal=-normal
            shade=.40+.72*max(0,float(normal@light));half=light+direction;half/=np.linalg.norm(half)
            gloss=max(0,float(normal@half))**(42 if metal else 12)
            color=np.clip(base*shade+gloss*(.17 if metal else .015),0,1)
            color=np.where(color<=.0031308,color*12.92,1.055*color**(1/2.4)-.055)
            xmin,ymin=np.maximum(np.floor(q.min(0)).astype(int),0);xmax,ymax=np.minimum(np.ceil(q.max(0)).astype(int),size-1)
            if xmin>xmax or ymin>ymax:continue
            x,y=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
            a,b,c=q;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-8:continue
            w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
            w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w2=1-w0-w1
            candidate=w0*zz[0]+w1*zz[1]+w2*zz[2];region=depth[ymin:ymax+1,xmin:xmax+1]
            mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(candidate>region)
            region[mask]=candidate[mask];dest=pixels[ymin:ymax+1,xmin:xmax+1];dest[mask,:3]=(color*255).astype(np.uint8);dest[mask,3]=255
image=Image.fromarray(pixels).resize((512,512),Image.Resampling.LANCZOS)
target=P/'Content/ColdSteelData/Icons/ue_pit_viper2011.png';target.parent.mkdir(exist_ok=True,parents=True);image.save(target)
option_folder=P/'Content/ColdSteelData/AttachmentIcons20260913';option_folder.mkdir(exist_ok=True,parents=True)
# Factory and purely numeric options have the same assembled geometry.
for slot in ('optic','muzzle','magazine','reargrip','tactical','trigger'):
    image.save(option_folder/('ue_pit_viper2011_'+slot+'_false.png'))
image.save(option_folder/'ue_pit_viper2011_trigger_pit_viper_lightweight_fast.png')
(O/'icon_receipt.json').write_text(json.dumps({'file':str(target),'purpose':'production inventory icon','source':'actual factory geometry','acceptance_preview':False}),encoding='utf8')
print('PitViper2011 material recipe and catalog icon produced')
