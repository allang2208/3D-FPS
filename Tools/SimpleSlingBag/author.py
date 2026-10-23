"""One continuous crossbody strap and one shared, un-decimated Nanite pouch."""
import sys,json,importlib.util,hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline,PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SimpleSlingBag20261022'
sys.path.insert(0,str(P/'Tools/BackpackHarness'))
spec=importlib.util.spec_from_file_location('sling_base',P/'Tools/BackpackHarness/author.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
DEST='/Game/Characters/SimpleSlingBag20261022';REV='SimpleSlingR1_20261022'
angle=np.radians(-20.);rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
quaternion=[0.,float(np.sin(angle/2)),0.,float(np.cos(angle/2))]
pouch=b.read(R/'pouch_prepared.json');vertices=np.load(R/'Authored/pouch_support.npz')['positions']@rotation.T
# Sample the torso-facing surface by small XZ cells, keeping its full front extent.
keys=np.floor(vertices[:,[0,2]]/.25).astype(int)
order=np.lexsort((-vertices[:,1],keys[:,1],keys[:,0]));keys=keys[order]
keep=np.r_[True,np.any(keys[1:]!=keys[:-1],axis=1)];support=vertices[order[keep]]

def build(profile,initial_location=None,extra_clearance=.55,free_lengths=(11.,11.),soft_contact=False):
    shirt,old,margin=b.PROFILES[profile];body=b.read(R/'BodyInputs/body.json')
    garment=b.read(R/'BodyInputs'/(shirt+'.json')) if shirt else None
    equations,_=b.envelope(body,garment)
    location=np.array(initial_location if initial_location is not None else [0.,-20.5,123.],dtype=float)
    facing=support+location;direction=np.tile([0.,-1.,0.],(len(facing),1))
    shift=max(float(b.lift_required(chunk,dirs,equations,margin+extra_clearance).max()) for chunk,dirs in zip(np.array_split(facing,30),np.array_split(direction,30)))
    location[1]-=shift
    top=np.asarray(pouch['anchors_cm']['top'])@rotation.T+location
    bottom=np.asarray(pouch['anchors_cm']['bottom'])@rotation.T+location
    control=np.array([top,[-10,-8,143],[-12,-1,145],[-12,7,140],[-6,13,135],
                      [2,14,128],[10,10,119],[16,3,112],[17,-7,108],bottom])
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(control,axis=0),axis=1))]
    sample=np.linspace(0,arc[-1],int(np.ceil(arc[-1]/.65))+1)
    path=CubicSpline(arc,control,bc_type='natural')(sample)
    widths=PchipInterpolator(arc,[3.,4.5,4.8,4.8,4.4,3.5,3.,3.,3.,3.])(sample)
    thick=PchipInterpolator(arc,[.22,.55,.6,.6,.5,.28,.22,.22,.22,.22])(sample)
    _,across,direction=b.frame(path,equations)
    samples=np.stack([path+across*(widths*f)[:,None]-direction*(thick*.5)[:,None] for f in [-.5,0,.5]],axis=1)
    contact=b.contact_offset(samples.reshape(-1,3),np.repeat(direction,3,axis=0),equations,margin+.15).reshape(-1,3).max(1)
    contact=np.where(np.isfinite(contact),np.clip(contact,-5.,4.),0.)
    contact_lengths=free_lengths if soft_contact else (10.,12.)
    blend=np.minimum(np.minimum(sample/contact_lengths[0],(sample[-1]-sample)/contact_lengths[1]),1.)
    path+=direction*(gaussian_filter1d(contact,4.)*blend)[:,None]
    baseline=path.copy();_,_,direction=b.frame(path,equations);total=np.zeros(len(path))
    for iteration in range(4):
        _,across,normal=b.frame(path,equations);points=[]
        for j,centre in enumerate(path):
            ring=b.rounded_ring(widths[j],thick[j]);dense=np.vstack([ring*(1-f)+np.roll(ring,-1,axis=0)*f for f in (0,.25,.5,.75)])
            points.append(centre+dense[:,:1]*across[j]+dense[:,1:]*normal[j])
        required=b.lift_required(np.vstack(points),np.repeat(direction,48,axis=0),equations,margin+.1).reshape(len(path),48).max(1)
        if max(required[0],required[-1])>.12:raise RuntimeError('Sewn interface needs relocation '+profile)
        total=b.smooth_lift(total+required,pin_ends=True);total[[0,-1]]=0
        path=baseline+direction*total[:,None]
        if required.max()<1e-4:break
    bones=body['bones'];names={row['index']:row['name'] for row in bones};indices={v:k for k,v in names.items()}
    s3=indices['spine_03'];s4=indices['spine_04'];clav=indices['clavicle_r'];arm=indices['upperarm_r']
    distances,nearest=cKDTree(np.asarray(body['positions'])).query(path,k=8);dense=np.zeros((len(path),len(bones)))
    for j,ids in enumerate(nearest):
        factors=1/np.maximum(distances[j],.05)**2;factors/=factors.sum()
        for vi,factor in zip(ids,factors):
            for bi,w in body['weights'][vi]:
                name=names[bi];mapped=None
                if name=='pelvis' or name in ('spine_01','spine_02','spine_03','spine_04','spine_05'):mapped=bi
                elif name.startswith('spine_'):mapped=s4
                elif name.startswith('clavicle'):mapped=clav if path[j,2]>134 and path[j,0]<0 else s4
                elif name.startswith('upperarm'):mapped=arm if path[j,2]>138 and path[j,0]<0 else s4
                if mapped is not None:dense[j,mapped]+=w*factor
        if dense[j].sum()<1e-7:dense[j,s3]=1
        dense[j]/=dense[j].sum();shoulder=float(np.clip((path[j,2]-134)/9,0,1))
        excess=max(dense[j,arm]-.10*shoulder,0);dense[j,arm]-=excess;dense[j,clav]+=excess
        excess=max(dense[j,clav]-.6*shoulder,0);dense[j,clav]-=excess;dense[j,s4]+=excess
    dense=gaussian_filter1d(dense,2.5,axis=0)
    end=np.minimum(np.minimum(sample/free_lengths[0],(sample[-1]-sample)/free_lengths[1]),1.)
    end=end**3*(10-15*end+6*end**2) if soft_contact else end*end*(3-2*end)
    dense*=end[:,None];dense[:,s3]+=1-end
    bindings=[]
    for values in dense:
        ids=np.argsort(-values)[:8];values=values[ids];values/=values.sum()
        bindings.append([[int(i),float(w)] for i,w in zip(ids,values) if w>1e-7])
    mats=[{'slot':'Binding','asset':DEST+'/M_SlingBinding.M_SlingBinding'},
          {'slot':'Hardware','asset':DEST+'/M_SlingHardware.M_SlingHardware'},
          {'slot':'Canvas','asset':DEST+'/M_SlingStrap.M_SlingStrap'}]
    mesh=b.Mesh(bones,mats);part=mesh.ribbon('single_crossbody',path,widths,thick,bindings,equations=equations)
    mask=[1.]*len(mesh.data['positions'])
    for j,row in enumerate(part['rows']):
        for vi in row:mask[vi]=float(1-end[j])
    tangent,across,normal=b.frame(path,equations);front=np.where(path[:,1]>8)[0];j=front[np.argmin(abs(path[front,2]-124))]
    mesh.hardware('single_adjuster',path[j]+normal[j]*.4,across[j],tangent[j],normal[j],3.7,2.4,bindings[j])
    mask.extend([0.]*(len(mesh.data['positions'])-len(mask)));mesh.normals()
    asset=DEST+'/'+old.replace('Backpack','SimpleSling');asset+='.'+asset.rsplit('/',1)[1]
    mesh.data.update(source=asset,revision=REV,geometry_convention='cross_e1_e2',motion_mask=mask)
    source=R/'Authored'/(profile+'.json');b.write(source,mesh.data)
    bounds=vertices+location
    row={'profile':profile,'shirt':shirt,'asset':asset,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'rigid_location':location.tolist(),'bounds_min':bounds.min(0).tolist(),'bounds_max':bounds.max(0).tolist(),
         'top_anchor':top.tolist(),'triangles':len(mesh.data['triangles']),'max_fit_lift_cm':float(total.max())}
    print('SLING_STRAP_AUTHORED',json.dumps(row),flush=True);return row

if __name__=='__main__':
    rows=[build(profile) for profile in b.PROFILES]
    settings={'pivot':rows[0]['top_anchor'],'bounds_min':np.min([r['bounds_min'] for r in rows],axis=0).tolist(),
              'bounds_max':np.max([r['bounds_max'] for r in rows],axis=0).tolist(),'frequency_hz':3.,'damping':.78,
              'max_angle_degrees':3.2,'max_bounce_cm':.5,'response_scale':3.}
    b.write(R/'manifest.json',{'revision':REV,'variants':rows,'rotation_quat':quaternion,'backpack_motion':settings,'runtime_tested':False})
