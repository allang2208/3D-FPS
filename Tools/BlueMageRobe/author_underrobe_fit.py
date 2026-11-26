"""Bake robe-only inner trousers against the native body's actual sections.

All work is offline. Preserve native topology, UVs, binding and complete legs;
the outer trousers remain the normal equipment asset when the robe is removed.
"""
import json, hashlib
from pathlib import Path
import numpy as np

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/BlueMageRobe20261018'
OUT=ROOT/'UnderRobeFit20261020';OUT.mkdir(parents=True,exist_ok=True)
AUTH=OUT/'Authored';AUTH.mkdir(exist_ok=True)
REV='20261020-native-body-inner-pants-v1'
ANGLES=128

def smooth(t):
    t=np.clip(t,0.,1.);return t*t*(3-2*t)

def asset_file(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')

class NativeFit:
    def __init__(self,skin,waist):
        self.bones=skin['bones'];self.scale=np.mean([np.linalg.norm(np.array(self.bones['calf_'+s]['position'])-self.bones['foot_'+s]['position']) for s in ('l','r')])/40.
        self.z=np.arange(min(self.bones['foot_'+s]['position'][2] for s in ('l','r'))-.5*self.scale,waist+3*self.scale,.65*self.scale)
        self.theta=np.arange(ANGLES)*2*np.pi/ANGLES
        self.direction=np.c_[np.cos(self.theta),np.sin(self.theta)]
        p=np.asarray(skin['positions']);f=np.asarray(skin['triangles'],dtype=int)
        byid={b['index']:n for n,b in self.bones.items()}
        def is_arm(n):
            while n in self.bones:
                if n in ('upperarm_l','upperarm_r'):return True
                if self.bones[n]['parent']<0:return False
                n=byid[self.bones[n]['parent']]
            return False
        arms={n for n in self.bones if is_arm(n)}
        arm_mass=np.array([sum(w for n,w in weights.items() if n in arms) for weights in skin['weights']])
        proxy={i for i,n in enumerate(skin['material_slots']) if 'Proxy' in n}
        use=(arm_mass[f].max(axis=1)<.05)&~np.isin(skin['triangle_materials'],list(proxy))
        self.body=self.sections(p,f[use],False)

    def axis(self,z,side):
        knots=np.asarray([self.bones[n+'_'+side]['position'] for n in ('foot','calf','thigh')])
        return np.stack([np.interp(z,knots[:,2],knots[:,i]) for i in (0,1)],axis=-1)

    def sections(self,p,f,outer):
        tri=p[f];lo=tri[:,:,2].min(axis=1);hi=tri[:,:,2].max(axis=1)
        result=np.full((2,len(self.z),ANGLES),np.nan)
        for zi,z in enumerate(self.z):
            t=tri[(lo<=z)&(hi>z)]
            if not len(t):continue
            b=np.roll(t,-1,axis=1);cross=((t[:,:,2]<=z)&(b[:,:,2]>z))|((b[:,:,2]<=z)&(t[:,:,2]>z))
            valid=cross.sum(axis=1)==2;t=t[valid];b=b[valid];cross=cross[valid]
            if not len(t):continue
            a=t[cross];b=b[cross];hits=a[:,:2]+(b[:,:2]-a[:,:2])*((z-a[:,2])/(b[:,2]-a[:,2]))[:,None]
            segments=hits.reshape(-1,2,2);edge=segments[:,1]-segments[:,0]
            den=self.direction[:,None,0]*edge[None,:,1]-self.direction[:,None,1]*edge[None,:,0]
            safe=np.where(np.abs(den)>1e-9,den,1.)
            for si,side in enumerate(('l','r')):
                rel=segments[:,0]-self.axis(z,side)
                distance=(rel[None,:,0]*edge[None,:,1]-rel[None,:,1]*edge[None,:,0])/safe
                u=(rel[None,:,0]*self.direction[:,None,1]-rel[None,:,1]*self.direction[:,None,0])/safe
                distance=np.where((np.abs(den)>1e-9)&(distance>1e-4)&(u>=0)&(u<=1),distance,np.inf)
                nearest=distance.min(axis=1)
                if outer:
                    # Keep the connected lining/mail layers around the FIRST
                    # leg exit; do not reach across the gap into the other leg.
                    near_shell=np.isfinite(distance)&(distance<=nearest[:,None]+1.5*self.scale)
                    nearest=np.where(near_shell,distance,-np.inf).max(axis=1)
                result[si,zi]=np.where(np.isfinite(nearest),nearest,np.nan)
        # Open hems/waistbands need their closest available section at the
        # boundary. Interpolate small holes between captured sections as well.
        for si in range(2):
            for angle in range(ANGLES):
                good=np.isfinite(result[si,:,angle])
                if not good.any():raise RuntimeError('No native fitting section for direction '+str(angle))
                result[si,:,angle]=np.interp(self.z,self.z[good],result[si,good,angle])
        return result

    def sample(self,field,p,si):
        origin=self.axis(p[:,2],('l','r')[si]);delta=p[:,:2]-origin
        angle=np.mod(np.arctan2(delta[:,1],delta[:,0]),2*np.pi)*ANGLES/(2*np.pi)
        a=np.floor(angle).astype(int)%ANGLES;b=(a+1)%ANGLES;u=angle-np.floor(angle)
        z=np.clip((p[:,2]-self.z[0])/(self.z[1]-self.z[0]),0,len(self.z)-1)
        lo=np.minimum(np.floor(z).astype(int),len(self.z)-2);hi=lo+1;v=z-lo
        radius=(field[si,lo,a]*(1-u)+field[si,lo,b]*u)*(1-v)+(field[si,hi,a]*(1-u)+field[si,hi,b]*u)*v
        return origin,delta,radius

    def fit(self,d):
        p=np.asarray(d['positions']);f=np.asarray(d['triangles'],dtype=int)
        shell=self.sections(p,f,True);out=p.copy();mid=self.bones['pelvis']['position'][0]
        for si,side in enumerate(('l','r')):
            selected=np.flatnonzero(p[:,0]>=mid if si==0 else p[:,0]<mid)
            q=p[selected];origin,delta,body=self.sample(self.body,q,si);_,_,outer=self.sample(shell,q,si)
            distance=np.linalg.norm(delta,axis=1);target=body+.35*self.scale
            # Scale the whole local shell together to retain lining thickness,
            # then bound isolated protruding details to the same inner fit.
            ratio=np.minimum(1.,target/np.maximum(outer,1e-4))
            ratio=np.minimum(ratio,target/np.maximum(distance,1e-4))
            cuff=float(q[:,2].min());blend=smooth((q[:,2]-cuff-1.5*self.scale)/(6*self.scale))
            ratio=1-(1-ratio)*blend
            out[selected,:2]=origin+delta*ratio[:,None]
        displacement=np.linalg.norm(out-p,axis=1)
        return out,dict(changed_vertices=int((displacement>1e-4).sum()),maximum_contraction_cm=float(displacement.max()),body_clearance_cm=.35*self.scale,cuff_fixed_height_cm=1.5*self.scale,cuff_transition_cm=6*self.scale)

def main():
    previous=json.loads((ROOT/'TurnLegContinuity20261020/inputs.json').read_text())
    cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    mapping=cfg['items']['ue_blue_mage_robe']['underlayer_meshes']
    sources={r['source']:r for r in previous['rows']};wanted={}
    # Enumerate current base and every boot-specific pant route once.
    for item in cfg['items'].values():
        if item.get('slot')!=15:continue
        for profile,path in item.get('rig_meshes',{}).items():
            if profile in ('Body','Jason') and path:wanted[path]=profile
        for fit in item.get('shoe_fit_meshes',{}).values():
            for profile,path in fit.items():
                if profile in ('Body','Jason') and path:wanted[path]=profile
    fitters={};body_sources={};rows=[]
    for path,profile in wanted.items():
        if path not in sources or path not in mapping:raise RuntimeError('Capture new native trouser source before fitting: '+path)
        row=sources[path]
        if hashlib.sha256(asset_file(path).read_bytes()).hexdigest()!=row['asset_sha256']:raise RuntimeError('Native trouser source changed; recapture '+path)
        if profile not in fitters:
            native=next(r for r in previous['rows'] if r['kind']=='skin' and r['profile']==profile)
            if hashlib.sha256(asset_file(native['source']).read_bytes()).hexdigest()!=native['asset_sha256']:raise RuntimeError('Native body changed; recapture '+profile)
            skin=json.loads(Path(native['file']).read_text());dims=json.loads((ROOT/'Authored/Body'/(profile+'.json')).read_text())['cloth_dimensions']
            fitters[profile]=NativeFit(skin,dims['waist_cm']);body_sources[profile]=native
        d=json.loads(Path(row['file']).read_text());positions,production=fitters[profile].fit(d)
        destination=AUTH/(row['key']+'.json')
        destination.write_text(json.dumps(dict(positions=positions.tolist(),source=row['source'],source_asset_sha256=row['asset_sha256'],revision=REV,production=production),separators=(',',':')),encoding='utf-8')
        rows.append(dict(**row,authored=str(destination),previous_underlayer=mapping[path],production=production))
        print('ROBE_INNER_PANTS_AUTHORED',row['key'],production['changed_vertices'],flush=True)
    (OUT/'authored.json').write_text(json.dumps(dict(revision=REV,rows=rows,body_sources=body_sources,underlayer_meshes=mapping,runtime_tested=False),indent=2),encoding='utf-8')

if __name__=='__main__':main()
