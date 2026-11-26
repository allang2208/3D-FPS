"""Assemble native cloth/carrier and waist-specific world/owner variants."""
import sys,copy,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,merge,subset,smooth_transport
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';BASE=S/'CombatShirtR1';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3'
plan=read(BASE/'plan.json');snapshot=read(BASE/'Inputs/modular_outfits.json');owners=set();rows=[]
def scan(v):
    if not isinstance(v,dict):return
    for key,value in v.items():
        if key=='owner_body_meshes':owners.update(value.values())
        elif isinstance(value,dict):scan(value)
for cfg in [snapshot,snapshot['body_variants']['kaitlin']]:scan(cfg['items']['ue_st6_sleeves'])
def recolour(d):
    for i,slot in enumerate(d['material_slots']):
        name=slot.removeprefix('TS01_')
        if name=='RangerRipstop':d['materials'][i]=DEST+'/Materials/M_CombatRipstop'
        elif name in ['RangerNylon','OliveWebbing']:d['materials'][i]=DEST+'/Materials/M_CombatCarrier'
        elif name=='StitchThread':d['materials'][i]=DEST+'/Materials/M_CombatThread'
        elif name=='CharcoalStretch':d['materials'][i]=DEST+'/Materials/M_CombatStretch'
    return d
for rig,config in [('Jason',snapshot),('Kaitlin',snapshot['body_variants']['kaitlin'])]:
    cloth=read(R/'Authored'/f'shirt_detail_{rig}.json');rawcloth=read(R/'Authored'/f'shirt_cloth_{rig}.json');count=len(rawcloth['positions'])//2;f=np.array(rawcloth['triangles']);base_tree=BVHTree.FromPolygons(rawcloth['positions'],f[(f<count).all(1)].tolist(),all_triangles=True)
    native=read(R/'Inputs'/f'Body_{rig}.json');bones={b['name']:np.array(b['position']) for b in native['bones']};origin=bones['pelvis'].copy()
    vest=read(S/'Integration/Delivery'/f'vest_{rig}_Wear.json');vest['materials']=[m[7:] if m.startswith('NATIVE:') else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+m.removeprefix('TS01_') for m in vest['material_slots']];recolour(vest)
    neck=read(R/'Authored'/f'neck_skin_{rig}.json');base_paths={config['items']['ue_st6_sleeves']['rig_meshes'][rig],config['items']['ue_st6_sleeves']['owner_body_meshes'][rig]}
    for row in plan['rows']:
        if row['rig']!=rig or row.get('role')=='body':continue
        d=copy.deepcopy(cloth);old=np.array(d['positions']);new=old.copy();guide=read(BASE/'Inputs'/row['file'])
        if row['source'] not in base_paths:
            gp=np.array(guide['positions']);gf=np.array(guide['triangles']);centers=gp[gf].mean(1);mask=(centers[:,2]<114)&(abs(centers[:,0])<24);ids=np.unique(gf[mask]);tree=BVHTree.FromPolygons(gp.tolist(),gf[mask].tolist(),all_triangles=True);zlo,zhi=np.quantile(gp[ids,2],[.03,.97]);zs=np.linspace(92,112,41);angles=np.arange(96)*2*np.pi/96;field=np.zeros((41,96))
            for iz,z in enumerate(zs):
                center=np.array([origin[0],origin[1],z]);gz=float(np.clip(z,zlo+.08,zhi-.08));gc=center.copy();gc[2]=gz
                for it,theta in enumerate(angles):
                    direction=np.array([np.cos(theta),np.sin(theta),0.]);a=tree.ray_cast(Vector(gc+direction*30),Vector(-direction),30)[0];bc=center.copy();bc[2]=max(z,94.7 if rig=='Jason' else 93.7);b=base_tree.ray_cast(Vector(bc+direction*30),Vector(-direction),30)[0]
                    if a is not None and b is not None:field[iz,it]=float(np.clip(np.dot(np.array(a)-gc,direction)-.12-np.dot(np.array(b)-bc,direction),-2.2,0))
            for _ in range(2):field=(field*4+np.roll(field,1,1)+np.roll(field,-1,1)+np.vstack([field[:1],field[:-1]])+np.vstack([field[1:],field[-1:]]))/8
            for i,q in enumerate(old):
                if not 91.5<q[2]<111 or abs(q[0])>23:continue
                c=np.array([origin[0],origin[1],q[2]]);v=q-c;radius=np.linalg.norm(v)
                if radius<.1:continue
                theta=np.arctan2(v[1],v[0])%(2*np.pi);tf=theta*96/(2*np.pi);it=int(tf)%96;ft=tf-int(tf);zf=np.clip((q[2]-92)*2,0,40);iz=min(39,int(zf));fz=zf-iz
                delta=(field[iz,it]*(1-ft)+field[iz,(it+1)%96]*ft)*(1-fz)+(field[iz+1,it]*(1-ft)+field[iz+1,(it+1)%96]*ft)*fz
                fade=np.clip((110-q[2])/max(3.,110-zhi),0,1);fade=fade*fade*(3-2*fade);new[i]+=v/radius*delta*fade
            d['positions']=new.tolist();smooth_transport(d,old)
        if row['source'] in owners:
            p=np.array(d['positions']);faces=np.array(d['triangles']);d=subset(d,np.abs(p[faces][:,:,0]).max(1)<20.0)
        merge(d,neck);merge(d,vest);d['contract']='Native complete combat shirt and original carrier; actual saved ST6 waist trim used only as the measured tuck envelope; neck skin retained to unchanged head seam; no duplicate visible torso'
        file=R/'Authored'/('wear_'+rig+'_'+Path(row['file']).stem+'.json');write(file,d);asset=DEST+'/Wear/'+rig+'/SK_TS01_Combat_'+rig+'_'+Path(row['file']).stem;rows.append(dict(source=row['source'],rig=rig,file=str(file),asset=asset,owner=row['source'] in owners));print('TS01_R2_ASSEMBLED',rig,len(rows),flush=True)
world_only='--world-only' in sys.argv or '--upper-only' in sys.argv
fp=dict(completed=True,rows=[]) if world_only else read(R/'fp-authored.json')
if not fp['completed']:raise RuntimeError('Finish native sleeve production')
for entry in fp['rows']:
    source=next(row['source'] for row in plan['rows'] if row['rig']==entry['rig']);rows.append(dict(source=source,rig=entry['rig'],file=entry['file'],asset=DEST+'/Wear/'+entry['rig']+'/SK_TS01_Combat_'+entry['rig']))
for rig in ([] if '--upper-only' in sys.argv else ['Jason','Kaitlin']):
    for kind in ['pants','pants_boot','pants_short','pants_high','pants_tactical']:
        d=recolour(read(R/'Authored'/f'{kind}_{rig}.json'));file=R/'Authored'/f'wear_{kind}_{rig}.json';write(file,d);rows.append(dict(source=None,kind=kind,rig=rig,file=str(file),asset=DEST+'/Wear/'+rig+'/SK_TS01_'+kind+'_'+rig))
write(R/('authored-world.json' if world_only else 'authored.json'),dict(completed=True,rows=rows))
