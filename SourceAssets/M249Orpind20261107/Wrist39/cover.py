"""Refit only the two M249 box-reload lid lifts to the saved V7 grip layers."""
from pathlib import Path
import gzip
import json
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'Wrist36'))
import rig as G

LMG = HERE.parents[1] / 'LMGStabilityGrip20261111'
FAMILIES = ['base', 'vertical', 'angled', 'canted', 'prism', 'handguard']
CL, U, E, H, ARM, _ = G.indices('l')
OWNED = [CL, *ARM, H]
COVER = G.ix['PKM_Cover']
# Calibrated from the M249's owner captures. Positive view depth is -Y.
EYE = np.array([0., 24., 5.])
REGION = (.30, 1.28)

def shoulder_margin():
    triangles=G.faces[G.sections==G.g['slots'].index('Skin_UpperArm')]
    upper=np.unique(triangles)
    _,vertex=np.unique(np.round(G.vertices[upper],3),axis=0,return_inverse=True)
    welded=vertex[np.searchsorted(upper,triangles)]
    edges=np.sort(np.vstack([welded[:,(0,1)],welded[:,(1,2)],welded[:,(2,0)]]),axis=1)
    edges,count=np.unique(edges,axis=0,return_counts=True)
    boundary=np.isin(vertex,np.unique(edges[count==1]))
    axis=G.B[E,:3,3]-G.B[U,:3,3]
    station=(G.vertices[upper]-G.B[U,:3,3])@axis/(axis@axis)
    ids=upper[boundary&(station<.40)&np.array([G.names[b].endswith('_l') for b in G.dominant[upper]])]
    groups={}
    for j,i in enumerate(ids):
        for bone,weight in G.g['weights'][i]:
            which,points=groups.setdefault(bone,([],[]))
            which.append(j);points.append(np.r_[G.vertices[i],1.]*weight)
    skin=[(bone,np.array(which),np.array(points)@G.invB[bone].T) for bone,(which,points) in groups.items()]
    tan=np.tan(np.radians(107.512/2))*1.07
    def margin(w):
        pts=np.zeros((len(ids),3))
        for bone,which,coords in skin:pts[which]+=coords@w[bone,:3].T
        x,y,z=(pts-EYE).T;depth=-y
        return np.maximum.reduce([abs(x)-depth*tan,abs(z)-depth*tan*9/16,-depth]).min()
    return margin

cap_margin=shoulder_margin()

def profile_input(family):
    return LMG / 'M249_profile.json.gz' if family == 'handguard' else HERE.parent / 'Wrist38' / (family+'.json.gz')


def surface_distance(sections):
    # Rasterize cross-sections of the real mesh, then interpolate the signed
    # distance to its envelope. This also follows the top and underside of the lip.
    from scipy.ndimage import distance_transform_edt
    from scipy.interpolate import RegularGridInterpolator
    cell=.16
    xs=np.arange(-17.,17.,cell)
    ys=np.arange(-38.,7.,cell)
    zs=np.arange(-8.,17.,cell)
    surface = np.full((len(ys), len(zs)), np.inf)
    back=-surface.copy()
    for tri in G.vertices[G.faces[np.isin(G.sections,sections)]]:
        v = tri[:,1:]
        iy = np.flatnonzero((ys >= v[:,0].min()) & (ys <= v[:,0].max()))
        iz = np.flatnonzero((zs >= v[:,1].min()) & (zs <= v[:,1].max()))
        if not len(iy) or not len(iz): continue
        a,b = v[1]-v[0], v[2]-v[0]
        det = a[0]*b[1]-a[1]*b[0]
        if abs(det)<1e-12: continue
        dy,dz = ys[iy,None]-v[0,0],zs[None,iz]-v[0,1]
        u,w = (dy*b[1]-dz*b[0])/det, (a[0]*dz-a[1]*dy)/det
        x = tri[0,0]+u*(tri[1,0]-tri[0,0])+w*(tri[2,0]-tri[0,0])
        idx = np.ix_(iy,iz)
        within=(u>=0)&(w>=0)&(u+w<=1)
        surface[idx]=np.minimum(surface[idx],np.where(within,x,np.inf))
        back[idx]=np.maximum(back[idx],np.where(within,x,-np.inf))
    solid=(xs[:,None,None]>=surface-cell/2)&(xs[:,None,None]<=back+cell/2)
    field=(distance_transform_edt(~solid)-distance_transform_edt(solid))*cell
    return RegularGridInterpolator((xs,ys,zs),field,bounds_error=False,fill_value=20.)


def anchor(frame, clear, optical):
    # Fit the existing curled fingertips against the exposed side of the lid,
    # away from the rear corner and from the top-mounted optic.
    inv=G.B[COVER]@np.linalg.inv(frame[COVER])
    skin=G.skin(frame)@inv[:3,:3].T+inv[:3,3]
    fingertips=[np.flatnonzero(G.dominant==G.ix[n+'_03_l'])[::2] for n in ('index','middle','ring','pinky','thumb')]
    palm=np.flatnonzero(np.isin(G.dominant,[G.ix[n] for n in G.names if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))]))[::4]
    tip_slices=[];offset=len(palm)
    for ids in fingertips:
        tip_slices.append(slice(offset,offset+len(ids)));offset+=len(ids)
    points=skin[np.concatenate([palm,*fingertips])]
    wrist=(inv@frame[H])[:3,3]
    def transform(x):
        return R.from_euler('zyx',x[3:],degrees=True).as_matrix(), x[:3]
    def residual(x):
        turn,shift=transform(x)
        positioned=(points-wrist)@turn.T+wrist+shift
        clearance=clear(positioned);avoid=optical(positioned)
        contact=[np.min(clearance[s]) for s in tip_slices]
        return np.r_[np.minimum(0,clearance-.05),np.minimum(0,avoid-.13),
                     min(0,clearance.min()-.05)*18,min(0,avoid.min()-.13)*18,
                     (np.array(contact)-.12)*1.5,.18*(x[1]+19.),.013*x[3:]]
    seeds=[[-9.,-19.,1.,0.,0.,0.],[-9.,-20.,2.,12.,-8.,10.],[-8.,-18.,2.,-15.,15.,-12.]]
    limits=([-15.,-23.,-4.,-45.,-40.,-40.],[-1.,-14.,8.,45.,40.,40.])
    fit=min((least_squares(residual,seed,bounds=limits,max_nfev=70,ftol=1e-6) for seed in seeds),key=lambda f:f.cost)
    turn,shift=transform(fit.x)
    hand=inv@frame[H]
    hand[:3,:3]=turn@hand[:3,:3];hand[:3,3]+=shift
    return hand,fit.x


def lift(world,t,hand,clear,optical):
    envelope=G.ease((t-REGION[0])/.36)*G.ease((REGION[1]-t)/.30)
    ids=np.flatnonzero((t>=REGION[0])&(t<=REGION[1]))
    shifts={};turns={};parameters=[];last=np.zeros(10)
    pivots={};coordinates={};cover_inv={}
    fingers=['index','middle','ring','pinky','thumb']
    distal=[np.flatnonzero(G.dominant==G.ix[n+'_03_l'])[::2] for n in fingers]
    palm=np.flatnonzero(np.isin(G.dominant,G.indices('l')[5]))[::4]
    source_ids=np.concatenate([palm,*distal])
    slices=[];offset=len(palm)
    for digit in distal:slices.append(slice(offset,offset+len(digit)));offset+=len(digit)
    for k in ids:
        w=world[k];weight=envelope[k]
        target=w[COVER]@np.linalg.inv(G.B[COVER])@hand
        shifts[k]=(target[:3,3]-w[H,:3,3])*weight
        # Unhook laterally before leaving the rim. Sliding along the original
        # straight return clips through the optic mount as the lid rotates.
        enter=G.ease((t[k]-.34)/.12)*G.ease((.66-t[k])/.14)
        leave=G.ease((t[k]-.91)/.13)*G.ease((REGION[1]-t[k])/.12)
        clearance=np.array([-2.4*enter-6.*leave,0.,.8*enter+2.8*leave])
        shifts[k]+=(G.rot(w[COVER])@G.rot(G.B[COVER]).T)@clearance
        turns[k]=R.from_rotvec(R.from_matrix(G.rot(target)@G.rot(w[H]).T).as_rotvec()*weight).as_matrix()
        coordinates[k]=G.skin(w)[source_ids]-w[H,:3,3]
        pivots[k]=np.mean([coordinates[k][s].mean(0) for s in slices],axis=0)
        cover_inv[k]=G.B[COVER]@np.linalg.inv(w[COVER])
    def pose(k,x,contacts=False):
        w=world[k];weight=envelope[k]
        # The fingertips support the lift. Let the palm roll about that
        # support while the shoulder stays clear of the camera.
        lid_axes=G.rot(w[COVER])@G.rot(G.B[COVER]).T
        wrist_turn=R.from_rotvec(lid_axes@(weight*x[4:7])).as_matrix()
        turn=wrist_turn@turns[k]
        shift=shifts[k]+(turns[k]-turn)@pivots[k]+lid_axes@(weight*x[7:])
        # Transport the donor elbow plane between the original and new
        # shoulder-to-wrist directions. Projecting its old elbow onto the new
        # axis can flip at the instant the two pass through each other.
        c=w[CL,:3,3];a=c+R.from_rotvec(x[:3]).apply(w[U,:3,3]-c)
        axis=G.unit(w[H,:3,3]+shift-a)
        def proj(v):return G.unit(v-axis*(axis@v))
        source=proj(w[E,:3,3]-a)
        old_axis=G.unit(w[H,:3,3]-w[U,:3,3])
        old_dir=w[E,:3,3]-w[U,:3,3]
        old_pole=G.unit(old_dir-old_axis*(old_dir@old_axis))
        transport=R.from_quat(np.r_[np.cross(old_axis,axis),1.+old_axis@axis])
        pole=R.from_rotvec(axis*x[3]).apply(transport.apply(old_pole))
        control=np.r_[x[:3],np.arctan2(axis@np.cross(source,pole),source@pole)]
        posed=G.solve(w,control,shift=shift,hand_rotation=turn,station_weight=1.)
        if not contacts:return posed
        inv=cover_inv[k]
        pts=(coordinates[k]@turn.T+w[H,:3,3]+shift)@inv[:3,:3].T+inv[:3,3]
        lid=clear(pts);optic=optical(pts)
        held=G.ease((t[k]-.61)/.07)*G.ease((.97-t[k])/.06)
        gaps=np.array([lid[s].min() for s in slices])
        contact=np.r_[np.sort(gaps[:4])[:2]-.09,gaps[4]-.17]*held
        return posed,np.r_[max(0,.035-lid.min())*20,max(0,.09-optic.min())*21,contact*10]
    keys=np.unique(np.r_[ids[::3],ids[-1]])
    for k in keys:
        weight=envelope[k];w=world[k]
        if weight<.001:
            last=np.zeros(10)
        else:
            length=np.linalg.norm(w[U,:3,3]-w[E,:3,3])+np.linalg.norm(w[E,:3,3]-w[H,:3,3])
            def residual(x):
                q,contact=pose(k,x,True)
                el=q[E,:3,3];shoulder=q[U,:3,3];wrist=q[H,:3,3]
                stretch=np.linalg.norm(wrist-shoulder)-.975*length
                # The elbow leads below/left of the hand. Keep the middle of
                # the forearm clear of the camera even when the wrist clears it.
                mid=(el+wrist)*.5
                return np.r_[max(0,G.bend(q)-12)*1.5, max(0,stretch)*20,
                             max(0,el[2]-wrist[2]+2)*weight,
                             max(0,19-np.linalg.norm(mid-EYE))*3*weight,
                             max(0,1.5-cap_margin(q))*17*min(1.,weight/.12),
                             contact,x[:4]*5,x[4:7]*6,x[7:]*.75,(x[:7]-last[:7])*5,(x[7:]-last[7:])*.9]
            bounds=np.array([.95,.95,.95,1.55,.85,.85,.85,2.8,2.8,2.8])
            fit=least_squares(residual,last,bounds=(-bounds,bounds),max_nfev=55)
            last=fit.x
        parameters.append(last.copy())
    curva=PchipInterpolator(t[keys],parameters)(t[ids])
    result=world.copy()
    for k,x in zip(ids,curva):
        if envelope[k]>0:
            result[k]=pose(k,x*min(1.,envelope[k]/.12))
            # Carry the original wrist's residual roll. The wrist-side skin
            # station follows the hand during the entire approach and release.
            neutral=G.solve(world[k],np.zeros(4),station_weight=1.)
            for name in ('lowerarm_twist_01_l','lowerarm_twist_02_l'):
                b=G.ix[name]
                result[k,b,:3,:3]=G.rot(result[k,b])@G.rot(neutral[b]).T@world[k,b,:3,:3]
    return result


def apply_window(row,locals_before,world_after,t):
    solved=G.encode(world_after,G.parents)
    for bone in OWNED:
        old=next((q for q in row['tracks'] if q['bone']==G.names[bone]),None)
        correction=R.from_quat(solved[:,bone,3:7])*R.from_quat(locals_before[:,bone,3:7]).inv()
        if correction.magnitude().max()<1e-7: continue
        times=np.unique(np.r_[old['times'] if old else [],t[(t>REGION[0])&(t<REGION[1])],REGION])
        # Include endpoints for an added track: UE extends end keys on sampling.
        if not old: times=np.unique(np.r_[0,times,t[-1]])
        inside=(times>REGION[0])&(times<REGION[1])
        values=G.sample(old['values'],old['times'],times) if old else np.tile([0,0,0,0,0,0,1,0,0,0.],(len(times),1))
        # Keep the original raw key values (including quaternion signs) outside
        # the edit. The two boundary keys copy the unmodified evaluated track.
        if old:
            orig=np.array(old['values']).reshape(-1,10);values[np.searchsorted(times,old['times'])]=orig
        dq=np.zeros((len(t),10));dq[:,3:7]=correction.as_quat()
        delta=G.sample(dq.ravel(),t,times[inside])
        values[inside,3:7]=(R.from_quat(delta[:,3:7])*R.from_quat(values[inside,3:7])).as_quat()
        for i in np.flatnonzero(inside):
            if values[i,3:7]@values[i-1,3:7]<0: values[i,3:7]*=-1
        track=dict(bone=G.names[bone],times=times.tolist(),values=values.ravel().tolist())
        if old:old.update(track)
        else:row['tracks'].append(track)


def main():
    clear=surface_distance([26]);optical=surface_distance([14,16,17]);targets={};report={}
    for family in FAMILIES:
        with gzip.open(profile_input(family),'rt') as stream:p=json.load(stream)
        for row in p['clips']:
            path=row['base']
            if not path.endswith(('.A_M249_reload','.A_M249_reload_empty')): continue
            src=G.d['clips'][path];t=np.array(src['times']);base=np.array(src['frames'])
            local=G.layer(base,path,p,G.names,t);world=G.compose(local,G.parents)
            if path not in targets:
                hand,fit=anchor(world[np.argmin(abs(t-.75))],clear,optical)
                targets[path]=hand
                print('anchor',path,fit,flush=True)
            # A common contact uses a separate joint solve on each grip. A
            # shared rotational delta can miss the lid on the prism profile.
            target=lift(world,t,targets[path],clear,optical)
            apply_window(row,local,target,t)
            after=G.layer(base,path,p,G.names,t);w=G.compose(after,G.parents)
            ids=np.flatnonzero((t>=.55)&(t<=1.02))
            distance=lambda poses:float(min(np.linalg.norm(poses[i,H,:3,3]-EYE) for i in ids))
            report[family+'/'+path.rsplit('.',1)[1]]=dict(wrist_eye_before=distance(world),wrist_eye_after=distance(w),
                bend_before=max(G.bend(world[i]) for i in ids),bend_after=max(G.bend(w[i]) for i in ids))
            print(family,path.rsplit('.',1)[1],report[family+'/'+path.rsplit('.',1)[1]],flush=True)
        with gzip.open(HERE/(family+'.json.gz'),'wt') as stream:json.dump(p,stream,separators=(',',':'))
    (HERE/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
