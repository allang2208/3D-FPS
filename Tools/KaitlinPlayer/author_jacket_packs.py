"""Fit existing native harnesses around the saved jacket, retaining rigid shells/UVs."""
import copy,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024/Packs'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
index=read(W/'inputs.json');rigs=read(W/'rigs.json')
load=lambda path:read(W/index[path]['file'])

def visible_torso(data):
    bones=data['bones']; torso={b['index'] for b in bones if b['name']=='pelvis' or b['name'].startswith(('spine_','clavicle'))}
    slots=[m['slot'].lower() for m in data['materials']]
    valid=np.array([not any(s in x for s in ('inner','lining','proxy','neckseam','exposed')) for x in slots])
    faces=np.asarray(data['triangles'],int)[valid[np.asarray(data['triangle_materials'])]]
    ids=np.unique(faces);v=np.asarray(data['positions'])[ids]
    influence=np.array([sum(w for b,w in data['weights'][i] if b in torso) for i in ids])
    shoulder=np.mean([b['position'][2] for b in bones if b['name'].startswith('clavicle_')])
    return v[influence>np.where(v[:,2]>shoulder-9,.24,.65)]

def cells_for(body,shirts):
    cloud=np.vstack([visible_torso(x) for x in [body]+shirts])
    bones={b['name']:b for b in body['bones']}
    low=bones['pelvis']['position'][2]-8.;high=bones['neck_02']['position'][2]+2.
    cells=[]
    for z in np.arange(low,high,2.):
        pts=cloud[(cloud[:,2]>=z-1)&(cloud[:,2]<=z+3)]
        if len(pts)<5 or np.linalg.matrix_rank(pts-pts.mean(0))<3:continue
        # Pocket tessellation is concentrated on the front. Its vertex median
        # is not the torso centre and would push a chest strap backwards.
        center=(pts.min(0)+pts.max(0))*.5
        cells.append((z-1,z+3,ConvexHull(pts).equations,center))
    if len(cells)<12:raise RuntimeError('Insufficient jacket surface sections')
    return cells,cloud,bones

def rear_shift(points,cells):
    depth=0.
    for lo,hi,planes,center in cells:
        q=points[(points[:,2]>=lo)&(points[:,2]<=hi)]
        if not len(q):continue
        lower=np.full(len(q),-np.inf);upper=np.full(len(q),np.inf);valid=np.ones(len(q),bool)
        for x,y,z,d in planes:
            v=q[:,0]*x+q[:,2]*z+d
            if y<-.02:lower=np.maximum(lower,-v/y)
            elif y>.02:upper=np.minimum(upper,-v/y)
            else:valid&=v<=.2
        valid&=lower<=upper
        if valid.any():depth=max(depth,float(np.max(q[valid,1]-lower[valid]+.4)))
    if depth>15:raise RuntimeError('Jacket would require excessive shell displacement')
    return np.array([0.,-depth,0.])

def garment_field(points,cells,bones):
    # Author a smooth polar deformation cage. Offset depends on angle and height,
    # never on radius, so inner/outer strap faces keep their separation.
    from scipy.ndimage import maximum_filter,gaussian_filter,map_coordinates
    spine=np.asarray(sorted([b['position'] for n,b in bones.items() if n=='pelvis' or n.startswith('spine_')],key=lambda p:p[2]))
    def frame(q):
        center=np.zeros_like(q);center[:,2]=q[:,2]
        for axis in (0,1):center[:,axis]=np.interp(q[:,2],spine[:,2],spine[:,axis])
        d=q-center;d[:,2]=0;d/=np.maximum(np.linalg.norm(d,axis=1,keepdims=True),.001)
        theta=np.mod(np.arctan2(d[:,1],d[:,0]),2*np.pi)
        return d,theta
    direction,angles=frame(points);needed=np.zeros(len(points))
    for lo,hi,planes,c in cells:
        ids=np.flatnonzero((points[:,2]>=lo)&(points[:,2]<=hi))
        if not len(ids):continue
        signed=points[ids]@planes[:,:3].T+planes[:,3]-.4
        rate=direction[ids]@planes[:,:3].T
        sides=np.linalg.norm(planes[:,:2],axis=1)>.2
        distance=np.where((rate>.02)&sides,-signed/np.maximum(rate,.02),np.inf)
        delta=np.where(np.all(signed[:,sides]<0,axis=1),np.maximum(0,np.min(distance,axis=1)),0)
        needed[ids]=np.maximum(needed[ids],delta)
    if np.any(~np.isfinite(needed)) or needed.max(initial=0)>15:
        raise RuntimeError('Unbounded native strap clearance')
    z0=np.floor(points[:,2].min())-4;z1=np.ceil(points[:,2].max())+4
    bins=64;grid=np.zeros((int(z1-z0)+1,bins))
    zi=np.rint(points[:,2]-z0).astype(int);ai=np.rint(angles*bins/(2*np.pi)).astype(int)%bins
    np.maximum.at(grid,(zi,ai),needed)
    grid=maximum_filter(grid,size=(7,5),mode=('nearest','wrap'))
    grid=gaussian_filter(grid,sigma=(.8,.8),mode=('nearest','wrap'))
    grid=np.c_[grid[:,-2:],grid,grid[:,:2]]
    def deform(q):
        d,theta=frame(q);coords=np.vstack([q[:,2]-z0,theta*bins/(2*np.pi)+2])
        amount=map_coordinates(grid,coords,order=1,mode='nearest')
        return d*np.where(amount>.001,amount+.08,0)[:,None]
    return deform

def collision_hulls(cloud,bones):
    edges=np.linspace(bones['pelvis']['position'][2],bones['neck_01']['position'][2]+2,7)
    angles=np.arange(12)*np.pi/6;normals=np.c_[np.cos(angles),np.sin(angles),np.zeros(12)]
    result=[]
    for a,b in zip(edges[:-1],edges[1:]):
        a-=.5;b+=.5;s=cloud[(cloud[:,2]>=a)&(cloud[:,2]<=b)]
        if len(s)<4:raise RuntimeError('Incomplete jacket collision band')
        planes=np.vstack([np.c_[normals,-(s@normals.T).max(0)-.1],[0,0,-1,a],[0,0,1,-b]])
        name=min(('pelvis','spine_01','spine_02','spine_03','spine_04','spine_05'),key=lambda n:abs(bones[n]['position'][2]-(a+b)*.5))
        bone=bones[name];ns=planes[:,:3]@np.asarray(bone['axes']).T;ds=planes[:,3]+planes[:,:3]@bone['position']
        result.append({'bone':name,'side_planes':12,'planes':(np.c_[ns,ds]/np.linalg.norm(ns,axis=1)[:,None]).tolist()})
    return result

only=sys.argv[sys.argv.index('--rig')+1] if '--rig' in sys.argv else None
manifest=[row for row in read(W/'manifest.json') if row['rig']!=only] if only and (W/'manifest.json').exists() else []
for rig,inputs in rigs.items():
    if only and rig!=only:continue
    body=load(inputs['body']);shirts=[load(path) for path in inputs['shirts']]
    cells,cloud,bones=cells_for(body,shirts)
    for item,recipe in inputs['packs'].items():
        source=load(recipe['world_mesh']);v=np.asarray(source['positions']);mask=np.asarray(source['mask'])
        rigid=recipe.get('rigid_pack')
        if rigid:
            shell=np.asarray(load(rigid['mesh'])['positions'])@Rotation.from_quat(rigid['rotation_quat']).as_matrix().T+rigid['location']
        else:shell=v[mask>.999]
        shift=rear_shift(shell,cells)
        fixed=np.flatnonzero(mask<.999)
        fit_field=garment_field(v[fixed],cells,bones)
        field=np.zeros_like(v);field[fixed]=fit_field(v[fixed])
        # The diagonal sling's shoulder turn is still supported by the torso.
        # Keep that turn on the garment cage; reach the rigid move at its sewn end.
        blend=mask*mask if 'hanging_pack' in recipe else mask
        result=v+field*(1-blend[:,None])+shift*blend[:,None]
        stem='SK_'+rig+'_'+item+'_WorkJacketR2'
        asset='/Game/Characters/ModularOutfit20260924/WorkJacketPacks20261024/'+rig+'/'+stem
        geometry=W/(stem+'.json');geometry.write_text(json.dumps({'positions':result.tolist()},separators=(',',':')))
        row={'rig':rig,'item':item,'source':recipe['world_mesh'],'source_sha256':source['sha256'],'body':inputs['body'],
             'asset':asset,'geometry':str(geometry),'shell_shift':shift.tolist(),
             'bounds_min':np.minimum(result.min(0),(shell+shift).min(0)).tolist(),
             'bounds_max':np.maximum(result.max(0),(shell+shift).max(0)).tolist()}
        if rigid:row['rigid_location']=(np.asarray(rigid['location'])+shift).tolist()
        if 'hanging_pack' in recipe:
            hanging=copy.deepcopy(recipe['hanging_pack']);hanging['center']=(np.asarray(hanging['center'])+shift).tolist()
            hanging['probes']=(np.asarray(hanging['probes'])+shift).tolist();hanging['hulls']=collision_hulls(cloud,bones)
            for tether in hanging['tethers']:
                old=np.asarray(tether['point']);before=np.zeros(3);after=np.zeros(3)
                for support in tether['support']:
                    bone=bones[support['bone']];point=np.asarray(support['local'])@bone['axes']+bone['position']
                    moved=point+fit_field(point[None,:])[0]
                    support['local']=((moved-bone['position'])@np.linalg.inv(np.asarray(bone['axes']))).tolist()
                    before+=point*support['weight'];after+=moved*support['weight']
                slack=max(0,tether['length']-np.linalg.norm(old-before));tether['point']=(old+shift).tolist()
                tether['length']=float(np.linalg.norm(old+shift-after)+slack)
            row['hanging_pack']=hanging
        faces=np.asarray(source['triangles'],int)
        def areas(points):
            t=points[faces];return np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
        before,after=areas(v),areas(result);valid=before>1e-8
        row['geometry_receipt']={'original_degenerate_faces':int(sum(~valid)),
            'new_degenerate_faces':int(sum(valid&(after<1e-8))),
            'minimum_retained_face_area_ratio':float((after[valid]/before[valid]).min())}
        if row['geometry_receipt']['new_degenerate_faces'] or row['geometry_receipt']['minimum_retained_face_area_ratio']<.05:
            raise RuntimeError('Harness volume collapsed: '+str(row['geometry_receipt']))
        manifest.append(row)
        (W/'author_progress.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print('WORK_JACKET_PACK_AUTHORED',rig,item,'shell',shift.tolist(),flush=True)
(W/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
