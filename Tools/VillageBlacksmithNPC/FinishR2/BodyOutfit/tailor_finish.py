"""Tailor the R2 smith shirt, apron and strap hardware to the existing R4 bound workwear."""
from pathlib import Path
import gzip,json,math
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial import cKDTree
from cloth_surface import Bind,unit,smooth,row_normals,garment_cloud,boundary_loops,grid_tris,rays_at_x,ray_dist

P=Path(__file__).resolve().parents[4]
BASE=P/'SourceAssets/VillageBlacksmithNPC20261118'
TARGET=BASE/'FinishR2/BodyOutfit'
TARGET.mkdir(exist_ok=True,parents=True)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
orig=read(BASE/'BodyOutfit/outfit.json')
oldp=np.asarray(orig['positions']);oldf=np.asarray(orig['triangles'])
slots=orig['material_slots']
d={k:[] for k in ('positions','triangles','uv','normals','triangle_materials','weights')}
d.update(parts={},bones=orig['bones'],material_slots=slots,shirt_finish='R2 continuous fitted cloth and vented leather apron')
def add(name,p,f,uv,slot,weights,norm=None):
    a,j=len(d['positions']),len(d['triangles']);p=np.asarray(p);f=np.asarray(f)
    if norm is None:norm=row_normals(p,f)[f]
    d['positions'].extend(p.round(5).tolist());d['weights'].extend(weights)
    d['triangles'].extend((f+a).tolist());d['normals'].extend(np.round(norm,6).tolist());d['uv'].extend(np.round(uv,6).tolist())
    d['triangle_materials'].extend([slots.index(slot)]*len(f) if isinstance(slot,str) else slot)
    d['parts'][name]=[a,j,len(d['positions']),len(d['triangles'])]
def copy_part(name):
    a,j,b,k=orig['parts'][name]
    add(name,oldp[a:b],oldf[j:k]-a,np.asarray(orig['uv'][j:k]),orig['triangle_materials'][j:k],orig['weights'][a:b],np.asarray(orig['normals'][j:k]))
def data_cloud(name):
    a,j,b,k=orig['parts'][name]
    return oldp[oldf[j:k]]
jr=P/'SourceAssets/JasonStrong20261117'
rig=read(jr/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')
body=np.asarray(read(jr/'R4_PoseRefined/Review/forms.json')['base'])
bf=np.asarray(rig['triangles'])[np.isin(rig['triangle_materials'],[0,1,3,5])]
head=json.loads(gzip.decompress((BASE/'HeadHair/face.json.gz').read_bytes()));hp=np.asarray(head['p']);hf=np.asarray(head['tri'])[np.asarray(head['m'])==1]
ub=np.unique(bf);uh=np.unique(hf)
bind=Bind(np.concatenate([body[ub],hp[uh]]),[rig['weights'][i] for i in ub]+[head['w'][i] for i in uh])
bones={b['name']:np.asarray(b['position']) for b in orig['bones']}
def pair(prefix):return {s:bones[prefix+'_'+('l' if s>0 else 'r')] for s in (-1,1)}
shoulders,elbows,hands=map(pair,('upperarm','lowerarm','hand'))
cloud=np.concatenate([body[bf],hp[hf]])
donor=np.concatenate([data_cloud(name) for name in ('shirt','Rolled work sleeve l','Rolled work sleeve r')])
shirt,f=garment_cloud(cloud,donor,shoulders,elbows,hands)
scloud=shirt[f]
def unroll(angle,rr,vertical):
    # Each triangle has its own UV corners, including the fabric panel seam.
    a=angle.copy()
    wraps=np.ptp(a,axis=1)>math.pi
    a[wraps]=np.where(a[wraps]<0,a[wraps]+math.tau,a[wraps])
    return np.stack([a*rr,vertical],axis=-1)
q=shirt[f]
torso=unroll(np.arctan2(q[:,:,0],q[:,:,1]+.5),14./22,q[:,:,2]/22)
for side in (-1,1):
    axis=unit(elbows[side]-shoulders[side]);other=unit(np.cross(axis,[0,1.,0]));up=unit(np.cross(axis,other))
    use=(q.mean(axis=1)[:,0]*side>16.6)&((q.mean(axis=1)-shoulders[side])@axis>4.0)
    r=q[use]-shoulders[side];torso[use]=unroll(np.arctan2(r@up,r@other),6.4/19,(r@axis)/19)
add('Continuous linen shirt',shirt,f,torso,'Linen',bind(shirt))
angles=np.arange(80)*math.tau/80
loops=boundary_loops(shirt,f)
def interpolate_polar(points,axis,c,first,second,aa):
    ray=points-c
    theta=np.arctan2(ray@second,ray@first)
    idx=np.argsort(theta);order=theta[idx]
    return np.stack([np.interp(aa,order,points[idx,j],period=math.tau) for j in range(3)],axis=-1)
def grid(name,p,slot,weights=None,cycle=False,reverse=False,uvscale=(1.,1.)):
    p=np.asarray(p);m,n=p.shape[:2];v=p.reshape(-1,3);tris=grid_tris(m,n,cycle,reverse)
    # Distances along and across a panel keep weave/tool marks at a physical scale.
    su=np.concatenate([[0],np.cumsum(np.mean(np.linalg.norm(p[:,1:]-p[:,:-1],axis=2),axis=0))]);sv=np.concatenate([[0],np.cumsum(np.mean(np.linalg.norm(p[1:]-p[:-1],axis=2),axis=1))])
    uv=np.stack(np.broadcast_arrays(su[None,:]/uvscale[0],sv[:,None]/uvscale[1]),axis=-1).reshape(-1,2)[tris]
    if cycle:
        border=tris%n;wrap=(border.max(1)-border.min(1))>n//2
        uu=uv[wrap,:,0];uu[border[wrap]==0]=(su[-1]+np.linalg.norm(p[:,0]-p[:,-1],axis=1).mean())/uvscale[0]
        uv[wrap,:,0]=uu
    add(name,v,tris,uv,slot,weights if weights is not None else bind(v))
neck=next(l for l in loops if np.mean(shirt[l,2])>150 and abs(np.mean(shirt[l,0]))<3)
neckpts=interpolate_polar(shirt[neck],np.array([0,0,1]),np.array([0.,-.55,151.]),np.array([0,1.,0]),np.array([1.,0,0]),angles)
# A low stand collar, open at the placket. Ends lie flat and taper beside the throat.
arc=np.linspace(.105,math.tau-.105,91)
qborder=interpolate_polar(shirt[neck],None,np.array([0.,-.55,151.]),np.array([0,1.,0]),np.array([1.,0,0]),arc)
qborder=gaussian_filter1d(qborder,.66,axis=0,mode='nearest')
dr=unit(np.column_stack([qborder[:,0],qborder[:,1]+.55,np.zeros(len(arc))]))
taper=.55+.45*smooth(.10,.50,np.minimum(arc,math.tau-arc))
collar=[]
for height,offset in [(-.24,.06),(.12,.18),(.46,.18),(1.13,.08),(1.63,-.07),(1.72,-.19),(1.62,-.30),(1.29,-.31)]:
    collar.append(qborder+dr*offset+np.column_stack([np.zeros(len(arc)),np.zeros(len(arc)),taper*height]))
grid('Soft collar stand with inner facing',collar,'Linen',uvscale=(20,20))
def ray_y(cloud,x,z,back=False):
    seg=rays_at_x(cloud,x)
    ds=ray_dist(seg,np.array([0,z]),np.array([-1.,0]) if back else np.array([1.,0]))
    return (-1 if back else 1)*ds.max() if len(ds) else np.nan
# Modest half placket with an underlap and a top leaf. Seat both on the same shirt.
for side in (-1,1):
    panel=[]
    for t in np.linspace(0,1,19):
        z=139.4+10.15*t
        cx=side*(.34+.67*t**5)
        r=[]
        for u in np.linspace(-.44,.44,5):
            x=cx+u
            y=ray_y(scloud,x,z)
            if not np.isfinite(y):y=qborder[0,1]
            r.append([x,y+.13+.07*(side==1)+.064*(1-(u/.44)**2),z])
        panel.append(r)
    grid('Overlapping front placket '+str(side),panel,'Linen',uvscale=(20,20))
for side in (-1,1):
    el=elbows[side];axis=unit(hands[side]-el)
    e=unit(np.cross(axis,[0,1.,0]));g=unit(np.cross(axis,e))
    ring=next(l for l in loops if side*np.mean(shirt[l,0])>23 and 111<np.mean(shirt[l,2])<132)
    c=el+axis*6.6
    edge=interpolate_polar(shirt[ring],axis,c,e,g,angles)
    base_radius=np.linalg.norm(edge-c,axis=1);base_radius=gaussian_filter1d(base_radius,.9,mode='wrap')
    rays=np.cos(angles)[:,None]*e+np.sin(angles)[:,None]*g
    panels=[]
    for s,extra in [(-4.1,.10),(-3.95,.36),(-3.58,.52),(-3.19,.58),(-2.75,.44),(-2.41,.27),(-2.28,.42),(-1.85,.60),(-1.22,.64),(-.54,.57),(-.08,.46),(.22,.25),(.29,-.03),(.10,-.22),(-.32,-.24)]:
        ed=.28*np.sin(angles*2.0+.73*side)+.15*np.cos(angles+side)
        # Sample the source sleeve radially at each axial height, avoiding a floating roll when flexed.
        projected=(shirt-c)@axis;valid=(abs(projected-s)<.74)&(shirt[:,0]*side>21)
        rel=shirt[valid]-(c+axis*s);theta=np.arctan2(rel@g,rel@e);rr=np.sqrt((rel@e)**2+(rel@g)**2)
        if len(rr)>12:
            ix=np.argsort(theta);rad=np.interp(angles,theta[ix],rr[ix],period=math.tau)
            rad=gaussian_filter1d(rad,1.,mode='wrap')
        else:rad=base_radius
        panels.append(c+axis*(s+ed[:,None])+rays*(rad+extra)[:,None])
    grid('Twice turned sleeve '+str(side),panels,'Linen',cycle=True,reverse=True,uvscale=(20,20))
# Rebuild the belt after draping the apron, because the apron is its inner layer.
for name in ('trousers','boots'):copy_part(name)
from scipy.ndimage import median_filter,gaussian_filter,distance_transform_edt
from scipy.interpolate import LinearNDInterpolator
from cloth_surface import depth_raster
lo,j,hi,k=orig['parts']['Apron bib and skirt'];old=oldp[lo:hi].reshape(66,47,3)
old_weights=orig['weights'][lo:hi]
zlo,xlo=51.,-23.;pitch=.34
source=np.concatenate([scloud,data_cloud('trousers')]);shift=np.array([xlo,0,zlo])
_,raster=depth_raster((source-shift)/pitch,142,269)
valid=raster>-np.inf
ix=distance_transform_edt(~valid,return_distances=False,return_indices=True)
depth=raster[tuple(ix)]*pitch
surface_depth=RegularGridInterpolator((xlo+pitch*np.arange(142),zlo+pitch*np.arange(269)),depth,bounds_error=False,fill_value=None)
smoothed_depth=gaussian_filter(median_filter(old[:,:,1],size=(3,3)),(.78,.83))
tt=np.linspace(0,1,66);uu=np.linspace(-1,1,47)
grid_inter=RegularGridInterpolator((tt,uu),old)
old_y=RegularGridInterpolator((tt,uu),smoothed_depth)
def apron_at(t,u,sign=0):
    t,u=np.broadcast_arrays(t,u)
    tu=np.stack([t,u],axis=-1)
    base=grid_inter(tu)
    x,y,z=base[...,0],old_y(tu),base[...,2]
    skirt=1-smooth(88.,104.,z)
    wrap=(1.75*skirt+.45)*u**3
    x=x+wrap
    opening=np.maximum((71.8-z)/17.,0)**.89*1.55*(1-abs(u))
    s=np.where(abs(u)<1e-8,sign,np.sign(u))
    x+=opening*s
    z+=skirt*.48*np.sin(2.1*u+.17)
    ripple=(.50*np.sin(8.2*u+1.2*t)+.25*np.sin(16.7*u-1.7*t))*skirt
    strain=.27*np.cos(9*u-.22*z)*np.exp(-((z-104)/9.)**2)
    draped=y-(3.6*skirt+.38)*abs(u)**3+ripple+strain
    limit=surface_depth(np.stack([x,z],axis=-1))+.48
    # Leave soft clearance over the thigh, and close the waistband line around the hips.
    draped=np.maximum(draped, np.where(abs(x)<16.0,limit,limit-.38*smooth(16,20,abs(x))))
    draped+=2.55*skirt*(.63+.37*np.cos(u*1.30))
    return np.stack([x,draped,z],axis=-1)
def cloth_weight(row):
    a,b=np.floor(row).astype(int);return old_weights[int(np.clip(a,0,65))*47+int(np.clip(b,0,46))]
def front_uv(p):
    return np.stack([p[...,0]/23,p[...,2]/23],axis=-1)
apv=[];apw=[];apf=[];ap_uv=[];lookup={}
for s in (-1,1):
    us=np.linspace(-1,0,24) if s==-1 else np.linspace(0,1,24)
    T,U=np.meshgrid(tt,us,indexing='ij');quad=apron_at(T,U,s)
    ids=np.empty((66,24),int)
    for i in range(66):
        for col,u in enumerate(us):
            xyz=quad[i,col];key=tuple(xyz.round(6))
            if key not in lookup:
                lookup[key]=len(apv);apv.append(xyz)
                apw.append(cloth_weight([i,(u+1)*23+.01]))
            ids[i,col]=lookup[key]
    for tri in grid_tris(66,24):
        face=ids.ravel()[tri];apf.append(face);ap_uv.append(front_uv(quad.reshape(-1,3)[tri]))
apv=np.asarray(apv);apf=np.asarray(apf);ap_uv=np.asarray(ap_uv)
an=row_normals(apv,apf)
add('Cut leather bib and vented apron',apv,apf,ap_uv,'Apron',apw)
backv=apv-an*.23
add('Leather reverse',backv,apf[:,::-1],ap_uv[:,::-1,:],'Apron',apw)
edge_list=np.vstack([apf[:,[0,1]],apf[:,[1,2]],apf[:,[2,0]]])
_,ii,ct=np.unique(np.sort(edge_list,axis=1),axis=0,return_index=True,return_counts=True)
boundary=edge_list[ii[ct==1]]
bp=[];bw=[];bt=[];buv=[]
for a,b in boundary:
    first=len(bp);delta=apv[b]-apv[a]
    side=unit(np.cross(an[a]+an[b],delta))
    for off,forward in ((0,0),(.065,-.055),(.075,-.175),(0,-.23)):
        for vi in (a,b):bp.append(apv[vi]+an[vi]*forward+side*off);bw.append(apw[vi])
    for j in range(3):
        faces=np.array([[first+j*2,first+j*2+2,first+j*2+3],[first+j*2,first+j*2+3,first+j*2+1]])
        bt.extend(faces);buv.extend(front_uv(np.array(bp[-8:])[faces-first]))
add('Rounded cut leather edges and vent',np.array(bp),np.array(bt),np.array(buv),'Saddle',bw)
# Cut the leather girdle against both outer-facing sheets as a radius field; shared
# axial rows stop the buckle and waist from sinking through the moving bib.
from scipy.ndimage import maximum_filter1d
belt_cloud=np.concatenate([scloud,apv[apf],data_cloud('trousers')])
belt_cloud=belt_cloud[(np.max(abs(belt_cloud[:,:,0]),axis=1)<23)&(belt_cloud[:,:,2].min(1)<107)&(belt_cloud[:,:,2].max(1)>98)]
ba=np.linspace(0,math.tau,128,endpoint=False)
direction=np.stack([np.sin(ba),np.cos(ba)],axis=1)
waist_origin=np.array([0.,1.5])
def section_radius(z):
    # Project an XY section into the tool's existing YZ intersection routine.
    segments=rays_at_x(belt_cloud[:,:,[2,0,1]],z)
    radii=[]
    for dr in direction:
        hits=ray_dist(segments,waist_origin,dr)
        hits=hits[hits<23.0]
        radii.append(max(hits) if len(hits) else np.nan)
    radii=np.asarray(radii);ok=np.isfinite(radii)
    return np.interp(ba,ba[ok],radii[ok],period=math.tau)
heights=np.array([99.72,99.85,100.03,100.27,101.15,102.55,103.95,104.72,105.,105.13,105.19])
raw=np.stack([section_radius(z) for z in heights])
soft=gaussian_filter(maximum_filter1d(raw,5,axis=1,mode='wrap'),(.72,2.1),mode=('nearest','wrap'))
ease=np.array([.18,.42,.51,.55,.60,.64,.60,.55,.51,.40,.16])
belt=[]
for z,rr,extra in zip(heights,soft,ease):
    pts=waist_origin+direction*(rr+extra)[:,None]
    belt.append(np.column_stack([pts,np.full(len(pts),z)]))
grid('Skived and rounded waist belt',belt,'Saddle',cycle=True,uvscale=(18,18))
curve=RegularGridInterpolator((heights, np.r_[ba,math.tau]),np.column_stack([soft+ease[:,None],soft[:,0]+ease]),bounds_error=False,fill_value=None)
for name in ('Cast buckle frame','Buckle tongue'):
    a,j,b,k=orig['parts'][name];q=oldp[a:b].copy()
    center=np.mean(q,axis=0);origin_y=q[:,1].mean()
    theta=np.arcsin(np.clip(q[:,0]/15.2,-.75,.75))
    rads=curve(np.column_stack([q[:,2],np.mod(theta,math.tau)]))
    q[:,1]=waist_origin[1]+np.sqrt(np.maximum(rads**2-q[:,0]**2,0))+.56+(q[:,1]-origin_y)
    if name=='Buckle tongue':q[:,1]+=.18
    add(name,q,oldf[j:k]-a,np.asarray(orig['uv'][j:k]),'Brass',bind(q))
# Move each repair stitch with its underlying patch as the apron drapes around the legs.
T,U=np.meshgrid(tt,uu,indexing='ij');to_param=LinearNDInterpolator(old[:,:,[0,2]].reshape(-1,2),np.stack([T,U],axis=-1).reshape(-1,2))
for name in orig['parts']:
    if not (name.startswith('Old oblique') or name.startswith('Whip stitch')):continue
    a,j,b,k=orig['parts'][name];pts=oldp[a:b];tu=to_param(pts[:,[0,2]])
    revised=pts+apron_at(tu[:,0],tu[:,1])-grid_inter(tu)
    add(name,revised,oldf[j:k]-a,np.asarray(orig['uv'][j:k]),orig['triangle_materials'][j:k],orig['weights'][a:b])

def tube(name,paths,rad,slot):
    vp=[];tr=[];uv=[];sides=7
    for path in paths:
        path=np.asarray(path);start=len(vp)
        tangent=unit(np.gradient(path,axis=0))
        side=unit(np.cross(tangent,np.tile([0,1.,0],(len(path),1))))
        if np.any(np.linalg.norm(side,axis=1)<.1):side=unit(np.cross(tangent,np.tile([1.,0,0],(len(path),1))))
        normal=unit(np.cross(tangent,side));az=np.arange(sides)*math.tau/sides
        span=np.cumsum(np.r_[0,np.linalg.norm(np.diff(path,axis=0),axis=1)])
        xyz=path[:,None,:]+rad*(side[:,None,:]*np.cos(az)[None,:,None]+normal[:,None,:]*np.sin(az)[None,:,None])
        vp.extend(xyz.reshape(-1,3));idx=grid_tris(len(path),sides,True)
        tr.extend(idx+start);uu=np.broadcast_to(az,(len(path),sides))/(2*math.pi)
        vv=np.broadcast_to(span[:,None],uu.shape)/6
        uv.extend(np.stack([uu,vv],axis=-1).reshape(-1,2)[idx])
    v=np.asarray(vp);add(name,v,np.asarray(tr),np.asarray(uv),slot,bind(v))
strap_shell=np.concatenate([scloud,apv[apf]])
for s in (-1,1):
    arcs=48;total=82;size=7;ribbon=np.empty((total,size,3))
    for k,h in enumerate(np.linspace(-1.31,1.31,size)):
        x=s*8.55+h;seg=rays_at_x(strap_shell,x);origin=np.array([0,131.6])
        angles2=np.linspace(.149,2.55,arcs);radius=[]
        for angle in angles2:
            dr=np.array([math.cos(angle),math.sin(angle)]);hit=ray_dist(seg,origin,dr);hit=hit[hit<36]
            radius.append(hit.max() if len(hit) else np.nan)
        radius=np.asarray(radius);known=np.isfinite(radius);rr=np.interp(angles2,angles2[known],radius[known])
        rr=gaussian_filter1d(rr,.52)+.32
        ribbon[:arcs,k,0]=x;ribbon[:arcs,k,1:]=origin+np.stack([np.cos(angles2),np.sin(angles2)],axis=1)*rr[:,None]
        for j,t in enumerate(np.linspace(0,1,total-arcs+1)[1:],arcs):
            z=ribbon[arcs-1,k,2]*(1-t)+103*t;cx=s*(8.55*(1-t)-12.1*t)+h
            y=ray_y(scloud,cx,z,True)
            ribbon[j,k]=[cx,y-.42-(.42 if s>0 else 0)*math.sin(math.pi*t)**3,z]
        y=ribbon[:,k,1];nan=~np.isfinite(y);y[nan]=np.interp(np.flatnonzero(nan),np.flatnonzero(~nan),y[~nan])
    across=np.gradient(ribbon,axis=1);along=np.gradient(ribbon,axis=0)
    normal=unit(np.cross(along,across))
    if normal[0,3,1]<0:normal*=-1
    ribbon+=normal*(.085*(1-abs(np.linspace(-1,1,size))**1.8))[None,:,None]
    grid('Double bridle cross strap '+str(s),ribbon,'Saddle',uvscale=(14,20))
    # The skived edge turns toward the shirt. Give both margins a round .22 cm leather edge.
    for k in (0,-1):
        edge=ribbon[:,k];n=normal[:,k];along_w=unit(across[:,k])*(1 if k==-1 else -1)
        ed=np.stack([edge,edge+along_w*.055-n*.045,edge+along_w*.060-n*.17,edge-n*.225],axis=1)
        grid('Strap rolled edge '+str(s)+' '+str(k),ed,'Saddle',uvscale=(15,18))
    # A rectangular rolled brass keeper, rounded at four corners, with folded leather underneath.
    idx=int(np.argmin(abs(ribbon[:arcs//2,3,2]-140.3)))
    c=ribbon[idx,3];right=unit(across[idx,3]);up=unit(along[idx,3]);outward=normal[idx,3]
    loop=[]
    for rx,rz,ang in [(1.48,-.68,-90),(1.48,.68,0),(-1.48,.68,90),(-1.48,-.68,180)]:
        for deg in np.linspace(ang,ang+90,7):
            a=math.radians(deg)
            loop.append(c+right*(rx+.31*math.cos(a))+up*(rz+.31*math.sin(a))+outward*.34)
    loop.append(loop[0]);tube('Forged brass bib keeper '+str(s),[loop],.17,'Brass')
    jstart=max(0,idx-5);tab=ribbon[jstart:idx+1].copy()
    tab+=normal[jstart:idx+1]*np.linspace(.13,.25,len(tab))[:,None,None]
    grid('Folded keeper tab '+str(s),tab,'Saddle',uvscale=(14,20))
    rivetc=ribbon[max(0,idx-3),3]+outward*.40
    az=np.arange(18)*math.tau/18
    dome=[]
    for radius,hh in [(.28,0),(.31,.05),(.27,.11),(.16,.155),(.012,.175)]:
        dome.append(rivetc+right*radius*np.cos(az)[:,None]+up*radius*np.sin(az)[:,None]+outward*hh)
    grid('Peened bib rivet '+str(s),dome,'Brass',cycle=True,uvscale=(3,3))
    # Hand-saddled seams near the keeper; leave the shoulder free of bright decorative stitches.
    stitches=[]
    for k in (1,5):
        for j in range(1,idx-2):
            a=ribbon[j,k]+normal[j,k]*.11;b=ribbon[j+1,k]+normal[j+1,k]*.11
            stitches.append([a*.80+b*.20,a*.20+b*.80])
    if stitches:tube('Keeper hand stitches '+str(s),stitches,.040,'Thread')
    # True shoulder seam follows the top of the continuous yoke, with modest textile piping.
    pts=[]
    for x in np.linspace(6.45,20.20,41):
        y=-1.65-(x-6.45)*.115;seg=rays_at_x(scloud,s*x)
        hh=ray_dist(seg,np.array([y,128.]),np.array([0.,1.]))
        if len(hh):pts.append([s*x,y,128+hh.max()+.035])
    if len(pts)>4:tube('Flat-felled shoulder seam '+str(s),[pts],.095,'Linen')
target=TARGET/'outfit.json'
tmp=target.with_suffix('.tmp')
tmp.write_text(json.dumps(d,separators=(',',':')));tmp.replace(target)
(TARGET/'geometry.json').write_text(json.dumps({'vertices':len(d['positions']),'triangles':len(d['triangles']),'shirt_triangles':len(f),'lower_vent_cm':16.8,'turned_apron_mm':2.3,'new_keeper_pairs':2,'source_sha256':__import__('hashlib').sha256((BASE/'BodyOutfit/outfit.json').read_bytes()).hexdigest(),'slots':slots},indent=2))
print('SMITH_R2_PATTERNS',len(d['positions']),len(d['triangles']),flush=True)

