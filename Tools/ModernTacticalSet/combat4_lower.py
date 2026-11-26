"""R4 lower construction finishing and exact degenerate glove face removal."""
import sys,copy,hashlib,os,uuid
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write as _write,subset,smooth_transport
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';B=S/'CombatShirtR3';R=S/'CombatShirtR4';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4'
def write(path,data):
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');_write(temp,data);os.replace(temp,path)
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def islands(f,n):
    e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);_,labels=connected_components(coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(n,n)),directed=False)
    return [np.unique(f[labels[f[:,0]]==i]) for i in np.unique(labels[f[:,0]])]

def cloth_ids(d):
    f=np.array(d['triangles']);return np.unique(f[[not d['material_slots'][i].startswith('NATIVE:') for i in d['triangle_materials']]])

def pants(d):
    old=np.array(d['positions']);new=old.copy();f=np.array(d['triangles']);m=np.array(d['triangle_materials']);ids=cloth_ids(d);bones={b['name']:np.array(b['position']) for b in d['bones']}
    panels=[]
    for group in islands(f[m==d['material_slots'].index('TS01_CharcoalStretch')],len(old)):
        q=old[group];lo=q.min(0);hi=q.max(0)
        if len(group)<300 or hi[2]>65 or lo[2]<25 or hi[1]>-3:continue
        center=(lo+hi)*.5;half=(hi-lo)*.5;panels.append((center,half))
    q=old[ids];delta=np.zeros_like(q)
    for center,half in panels:
        x=(q[:,0]-center[0])/half[0];z=(q[:,2]-center[2])/half[2]
        support=np.exp(-((q[:,1]-center[1])/2.5)**4)*(1-smooth((abs(x)-1.05)/.5))*(1-smooth((abs(z)-1.05)/.55))
        # Round top/bottom corners in the whole local cloth stack, including binding.
        delta[:,2]-=(q[:,2]-center[2])*.25*np.minimum(abs(x),1)**4*support
        # Three unequal flex creases arc around the bent posterior knee, tapered at ends.
        for offset,amp,width,tilt in [(-3.2,.21,.62,.28),(.15,.31,.85,-.18),(3.65,.17,.72,.36)]:
            curve=center[2]+offset+tilt*(q[:,0]-center[0])+.055*(q[:,0]-center[0])**2
            v=(q[:,2]-curve)/width;crease=amp*(np.exp(-v*v/2)-.34*np.exp(-v*v/6))
            delta[:,1]-=crease*support*np.exp(-(x/.95)**4)
    # Directional load folds on the free lower calf; matching inner shell and thread move together.
    for side,sign in [('l',1),('r',-1)]:
        knee=bones['calf_'+side];foot=bones['foot_'+side];t=np.clip((q[:,2]-foot[2])/(knee[2]-foot[2]),0,1);center=foot[None,:]*(1-t[:,None])+knee[None,:]*t[:,None];rad=q-center;rad[:,2]=0;rr=np.linalg.norm(rad,axis=1);direction=rad/np.maximum(rr[:,None],1e-6);angle=np.arctan2(rad[:,1],rad[:,0]*sign)
        support=(q[:,0]*sign>0)*smooth((q[:,2]-29)/6)*(1-smooth((q[:,2]-65)/7))
        fold=np.zeros(len(q))
        for level,amp,width,tilt in [(36.4,.22,.8,1.8),(40.9,.30,1.15,-2.1),(55.6,.24,1.2,2.5)]:
            center_z=level+tilt*np.cos(angle+.4*sign);v=(q[:,2]-center_z)/width;fold+=amp*(np.exp(-v*v/2)-.32*np.exp(-v*v/7))*(.7+.3*np.cos(angle-.7))
        delta+=direction*(fold*support)[:,None]
    cut=float(d.get('cloth_production',{}).get('boot_tuck_preserved_below_cm',17.))
    delta*=smooth((q[:,2]-cut)/6)[:,None]
    new[ids]+=delta;d['positions']=new.tolist();smooth_transport(d,old)
    d['r4_tailoring']=dict(rounded_rear_knee_panels=len(panels),common_field_all_layers=True,preserved_native_waist=True,preserved_existing_boot_tucks=True,crease_style='asymmetric curved compression; retained offline physical cloth')
    return d

def boots(d):
    old=np.array(d['positions']);new=old.copy();f=np.array(d['triangles']);ids=cloth_ids(d);q=old[ids];bones={b['name']:np.array(b['position']) for b in d['bones']};delta=np.zeros_like(q)
    for side,sign in [('l',1),('r',-1)]:
        foot=bones['foot_'+side];knee=bones['calf_'+side];t=np.clip((q[:,2]-foot[2])/(knee[2]-foot[2]),0,1);center=foot[None,:]*(1-t[:,None])+knee[None,:]*t[:,None];rad=q-center;rad[:,2]=0;rr=np.linalg.norm(rad,axis=1);direction=rad/np.maximum(rr[:,None],1e-6);theta=np.arctan2(rad[:,1],rad[:,0]*sign);z=q[:,2]
        support=(q[:,0]*sign>0)*smooth((z-6.5)/3.5)*(1-smooth((z-24.5)/4.5));fold=np.zeros(len(q))
        for level,amp,width,phase in [(11.5,.23,.62,.5),(14.2,.34,.82,-.3),(18.4,.16,1.0,1.2)]:
            c=level+1.3*np.cos(theta+phase)+.25*np.cos(2*theta+.6);v=(z-c)/width;fold+=amp*(np.exp(-v*v/2)-.3*np.exp(-v*v/7))
        # Quarter flex is concentrated at the ankle; sole, toe last and collar height stay fixed.
        fold*=.65+.35*np.cos(theta-.5)**2;delta+=direction*(fold*support)[:,None]
        delta[:,2]+=.12*np.sin(theta+.6)*np.exp(-((z-19)/5)**2)*support
    new[ids]+=delta
    rigid=[i for i,name in enumerate(d['material_slots']) if name in ['TS01_Gunmetal','TS01_MattePolymer']]
    for group in islands(f[np.isin(d['triangle_materials'],rigid)],len(old)):
        if len(group)<3:continue
        a=old[group];b=new[group];ac=a.mean(0);bc=b.mean(0);u,_,vt=np.linalg.svd((a-ac).T@(b-bc));rot=u@vt
        if np.linalg.det(rot)<0:u[:,-1]*=-1;rot=u@vt
        new[group]=(a-ac)@rot+bc
    d['positions']=new.tolist();smooth_transport(d,old);d['r4_tailoring']=dict(common_field_all_layers=True,rigid_eyelets_preserved=True,sole_toe_last_preserved=True,ankle_quarter_articulated=True)
    return d

def clean_degenerate(d):
    p=np.array(d['positions']);f=np.array(d['triangles']);area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)*.5
    stored=p.astype(np.float32).astype(np.float64);stored_area=np.linalg.norm(np.cross(stored[f[:,1]]-stored[f[:,0]],stored[f[:,2]]-stored[f[:,0]]),axis=1)*.5
    keep=np.isfinite(area)&(area>=1e-10)&(stored_area>=1e-10);removed=int((~keep).sum())
    out=subset(d,keep) if removed else d;out['r4_degenerate_repair']=dict(removed_faces=removed,area_threshold_cm2=1e-10,native_binding_retained=True)
    return out,removed

def main():
    rows=[];counts={}
    for row in read(B/'authored.json')['rows']:
        if '--gloves-only' in sys.argv:continue
        if not row.get('kind','').startswith('pants'):continue
        d=pants(read(row['file']));file=R/'Authored'/Path(row['file']).name;write(file,d);out=copy.deepcopy(row);out.update(old_asset=row['asset'],asset=row['asset'].replace('CombatShirtR3','CombatShirtR4'),file=str(file));rows.append(out);print('R4_PANTS',row['rig'],row['kind'],flush=True)
    for rig in ([] if '--gloves-only' in sys.argv or '--pants-only' in sys.argv else ['Jason','Kaitlin']):
        file=R/'Authored'/f'boots_{rig}.json';d=boots(read(S/'Integration/Delivery'/f'boots_{rig}_Wear.json'))
        d['materials']=[m[7:] if m.startswith('NATIVE:') else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+m.removeprefix('TS01_') for m in d['material_slots']];write(file,d)
        rows.append(dict(source=d['source'],rig=rig,kind='boots',file=str(file),old_asset='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Wear/'+rig+'/SK_TS01_'+rig+'_boots',asset=DEST+'/Wear/'+rig+'/SK_TS01_'+rig+'_boots'));print('R4_BOOTS',rig,flush=True)
    for row in read(B/'CuffRepairR1/gloves-authored.json')['rows']:
        if '--pants-only' in sys.argv:continue
        d,removed=clean_degenerate(read(row['file']));file=R/'Authored'/('gloves_'+row['rig']+'.json');write(file,d);out=copy.deepcopy(row);out.update(old_asset=row['asset'],asset=row['asset'].replace('CombatShirtR3','CombatShirtR4'),file=str(file));rows.append(out);counts[row['rig']]=removed;print('R4_GLOVES',row['rig'],removed,flush=True)
    if '--gloves-only' in sys.argv:rows=[r for r in read(R/'lower-authored.json')['rows'] if r.get('kind')!='gloves']+rows
    if '--pants-only' in sys.argv:
        previous=read(R/'lower-authored.json');rows=[r for r in previous['rows'] if not r.get('kind','').startswith('pants')]+rows;counts=previous['glove_removed_faces']
    write(R/'lower-authored.json',dict(completed=True,rows=rows,glove_removed_faces=counts))
if __name__=='__main__':main()
