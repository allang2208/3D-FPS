"""Fit the carrier to sewn R4 cloth and bind every existing waist/owner route."""
import sys,copy,math,gc,os,uuid
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write as _write,subset,merge,smooth_transport,unit
from combat3_cloth import smooth
from combat4_pattern import torso_field,sample_field
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';B=S/'CombatShirtR3';R=S/'CombatShirtR4';BASE=S/'CombatShirtR1';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4';MAT='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'
def write(path,data):
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');_write(temp,data);os.replace(temp,path)

def sample_grid(field,x,z,xmin,zmin,step=.5):
    xf=np.clip((x-xmin)/step,0,field.shape[1]-1);zf=np.clip((z-zmin)/step,0,field.shape[0]-1);ix=np.minimum(xf.astype(int),field.shape[1]-2);iz=np.minimum(zf.astype(int),field.shape[0]-2);a=xf-ix;b=zf-iz
    return (field[iz,ix]*(1-a)+field[iz,ix+1]*a)*(1-b)+(field[iz+1,ix]*(1-a)+field[iz+1,ix+1]*a)*b

def fit_carrier(rig,cloth,body):
    d=read(S/'Integration/Delivery'/f'vest_{rig}_Wear.json');old=np.array(d['positions']);new=old.copy();native=BVHTree.FromPolygons(body['positions'],body['triangles'],all_triangles=True);shirt=BVHTree.FromPolygons(cloth['positions'],cloth['triangles'],all_triangles=True)
    bones={b['name']:np.array(b['position']) for b in body['bones']};clav=(bones['clavicle_l'][2]+bones['clavicle_r'][2])*.5;fields=[]
    for sign in [-1,1]:
        field=np.zeros((117,93))
        for iz,z in enumerate(np.arange(94.,152.5,.5)):
            for ix,x in enumerate(np.arange(-23,23.5,.5)):
                origin=Vector((x,sign*45,z));direction=Vector((0,-sign,0));a=shirt.ray_cast(origin,direction,45)[0];b=native.ray_cast(origin,direction,45)[0]
                if a is not None and b is not None:field[iz,ix]=max(0,(a.y-b.y)*sign-.65)
        for _ in range(2):field=(field*4+np.roll(field,1,1)+np.roll(field,-1,1)+np.vstack([field[:1],field[:-1]])+np.vstack([field[1:],field[-1:]]))/8
        ids=np.flatnonzero((old[:,1]-1.5)*sign>=0);q=old[ids];delta=sample_grid(field,q[:,0],q[:,2],-23,94);new[ids,1]+=delta*sign*(1-smooth((q[:,2]-clav+3)/5));fields.append(field)
    # Shoulder straps use a common radial field around the native shoulder axis.
    xs=np.arange(-21,21.5,.5);angles=np.arange(128)*2*np.pi/128;field=np.zeros((len(xs),len(angles)))
    for ix,x in enumerate(xs):
        c=np.array([x,1.5,clav-2.6])
        for it,t in enumerate(angles):
            dr=np.array([0,np.cos(t),np.sin(t)]);a=shirt.ray_cast(Vector(c+dr*35),Vector(-dr),35)[0];b=native.ray_cast(Vector(c+dr*35),Vector(-dr),35)[0]
            if a is not None and b is not None:field[ix,it]=max(0,np.dot(np.array(a)-np.array(b),dr)+.35)
    for _ in range(2):field=(field*4+np.roll(field,1,1)+np.roll(field,-1,1)+np.vstack([field[:1],field[:-1]])+np.vstack([field[1:],field[-1:]]))/8
    for i,q in enumerate(old):
        fade=float(smooth((q[2]-clav+4)/5)*smooth((abs(q[0])-4)/3))
        if fade<=0:continue
        c=np.array([q[0],1.5,clav-2.6]);v=q-c;direction=unit(v);a=np.arctan2(v[2],v[1])%(2*np.pi);tf=a*128/(2*np.pi);it=int(tf)%128;ft=tf-int(tf);xf=np.clip((q[0]+21)*2,0,len(xs)-1);ix=min(int(xf),len(xs)-2);fx=xf-ix
        delta=((1-ft)*field[ix,it]+ft*field[ix,(it+1)%128])*(1-fx)+((1-ft)*field[ix+1,it]+ft*field[ix+1,(it+1)%128])*fx;new[i]+=direction*delta*fade
    faces=np.array(d['triangles']);hardware=np.unique(faces[np.array(d['triangle_materials'])==d['material_slots'].index('TS01_MattePolymer')])
    for sign in [-1,1]:
        ids=hardware[old[hardware,0]*sign>0];a=old[ids];b=new[ids];ac=a.mean(0);bc=b.mean(0);u,_,vt=np.linalg.svd((a-ac).T@(b-bc));rot=u@vt
        if np.linalg.det(rot)<0:u[:,-1]*=-1;rot=u@vt
        new[ids]=(a-ac)@rot+bc
    d['positions']=new.tolist();smooth_transport(d,old)
    mapping={'RangerRipstop':'CombatRipstop','RangerNylon':'CombatCarrier','OliveWebbing':'CombatCarrier','StitchThread':'CombatThread','CharcoalStretch':'CombatStretch'}
    d['materials']=[MAT+mapping[m.removeprefix('TS01_')] if m.removeprefix('TS01_') in mapping else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+m.removeprefix('TS01_') for m in d['material_slots']]
    d['r4_contact']='Front/back clearance and shoulder radial clearance sampled from final sewn shirt; common deformation for inner/outer shell, straps, pockets and stitches; release buckles rigid'
    write(R/'Authored'/f'vest_{rig}.json',d);print('R4_CARRIER_FIT',rig,flush=True);return d

def waist_fit(d,guide,body,rig):
    old=np.array(d['positions']);new=old.copy();gp=np.array(guide['positions']);gf=np.array(guide['triangles']);centers=gp[gf].mean(1);mask=(centers[:,2]<114)&(abs(centers[:,0])<24);ids=np.unique(gf[mask]);tree=BVHTree.FromPolygons(gp.tolist(),gf[mask].tolist(),all_triangles=True);zlo,zhi=np.quantile(gp[ids,2],[.03,.97]);bones={b['name']:b for b in body['bones']};zs,bfield,origin=torso_field(body,bones);angles=np.arange(96)*2*np.pi/96;field=np.zeros((41,96))
    for iz,z in enumerate(np.linspace(92,112,41)):
        for it,t in enumerate(angles):
            direction=np.array([np.cos(t),np.sin(t),0]);c=np.array([*origin,z]);gc=c.copy();gc[2]=np.clip(z,zlo+.08,zhi-.08);a=tree.ray_cast(Vector(gc+direction*30),Vector(-direction),30)[0];bodyr=sample_field(c+direction*10,zs,bfield,origin)
            field[iz,it]=max(bodyr+.24,np.dot(np.array(a)-gc,direction)-.12) if a is not None else bodyr+.32
    for i,q in enumerate(old):
        if q[2]>=110 or abs(q[0])>22:continue
        v=q[:2]-origin;radius=np.linalg.norm(v)
        if radius<.1:continue
        theta=np.arctan2(v[1],v[0])%(2*np.pi);tf=theta*96/(2*np.pi);it=int(tf);ft=tf-it;zf=np.clip((q[2]-92)*2,0,40);iz=min(39,int(zf));fz=zf-iz;target=((1-ft)*field[iz,it]+ft*field[iz,(it+1)%96])*(1-fz)+((1-ft)*field[iz+1,it]+ft*field[iz+1,(it+1)%96])*fz
        fade=float(smooth((108-q[2])/max(4,108-zhi)));new[i,:2]+=v/radius*(target-radius)*fade
    d['positions']=new.tolist();smooth_transport(d,old);return d

def main():
    oldrows=read(B/'authored.json')['rows'];plan=read(BASE/'plan.json');snapshot=read(BASE/'Inputs/modular_outfits.json');rows=[]
    for rig in ['Jason','Kaitlin']:
        outer=read(R/'Authored'/f'shirt_outer_{rig}.json');body=read(B/'Inputs'/f'Body_{rig}.json');fit_carrier(rig,outer,body);del outer,body;gc.collect()
    for rig in ['Jason','Kaitlin']:
        cloth=read(R/'Authored'/f'shirt_detail_{rig}.json');body=read(B/'Inputs'/f'Body_{rig}.json');vest=read(R/'Authored'/f'vest_{rig}.json');neck=read(B/'Authored'/f'neck_skin_{rig}.json');config=snapshot if rig=='Jason' else snapshot['body_variants']['kaitlin'];basepaths={config['items']['ue_st6_sleeves']['rig_meshes'][rig],config['items']['ue_st6_sleeves']['owner_body_meshes'][rig]}
        for row in oldrows:
            if row['rig']!=rig or row.get('kind'):continue
            d=copy.deepcopy(cloth)
            if row['source'] not in basepaths:
                guidefile=next(x['file'] for x in plan['rows'] if x['source']==row['source']);waist_fit(d,read(BASE/'Inputs'/guidefile),body,rig)
            if row.get('owner'):
                p=np.array(d['positions']);f=np.array(d['triangles']);d=subset(d,abs(p[f][:,:,0]).max(1)<20.)
            merge(d,neck);merge(d,vest);file=R/'Authored'/Path(row['file']).name;write(file,d);out=copy.deepcopy(row);out.update(file=str(file),old_asset=row['asset'],asset=row['asset'].replace('CombatShirtR3','CombatShirtR4'));rows.append(out);print('R4_WORLD_ASSEMBLED',rig,len(rows),flush=True);del d;gc.collect()
    for row in read(R/'fp-authored.json')['rows']:
        old=next(x for x in oldrows if x['rig']==row['rig'] and not x.get('kind'));out=copy.deepcopy(old);out.update(file=row['file'],old_asset=old['asset'],asset=old['asset'].replace('CombatShirtR3','CombatShirtR4'));rows.append(out)
    rows+=read(R/'lower-authored.json')['rows'];write(R/'authored.json',dict(completed=True,rows=rows));print('R4_ALL_AUTHORED',len(rows),flush=True)
if __name__=='__main__':main()
