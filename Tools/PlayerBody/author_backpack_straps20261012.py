"""Retain the native backpack shell; fit two padded straps and two return tapes."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackStraps20261012'
OLD=P/'SourceAssets/JasonEquipmentRepair20261003'
data=json.loads((R/'backpack_input.json').read_text())
source=json.loads((OLD/'backpack.json').read_text())
fitted=json.loads((OLD/'backpack_fitted.json').read_text())
native=np.asarray(source['positions']);vertices=np.asarray(data['positions']);faces=np.asarray(data['triangles'],int)
distance,mapping=cKDTree(np.asarray(fitted['positions'])).query(vertices)
if distance.max()>1e-3:raise RuntimeError('Active backpack differs from its authoring source')
native=native[mapping]
labels=np.load(R/'native_islands.npz')['front_labels'][mapping]
islands=np.load(R/'native_islands.npz')['labels'][mapping]
bones={b['name']:b['index'] for b in data['bones']}
weights=[[[bones['spine_03'],1.]] for _ in vertices]
result=vertices.copy();changed=np.zeros(len(vertices),bool)
spec=importlib.util.spec_from_file_location('backpack_envelope',str(P/'Tools/PlayerBody/refit_jason_backpack_straps.py'))
envelope_io=importlib.util.module_from_spec(spec);spec.loader.exec_module(envelope_io)
target=json.loads((P/'SourceAssets/JasonPlayer20261003/Jason.json').read_text())
envelope,_=envelope_io.make_envelope(target)

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)
def ease(v):
    v=np.clip(v,0.,1.);return v*v*(3.-2.*v)
def interpolate(field,s,grid):
    return np.column_stack([np.interp(s,grid,field[:,i]) for i in range(field.shape[1])])

def path_frame(controls,side,clearance,widths):
    c=np.asarray(controls,float);c[:,0]*=side
    knot=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(c,axis=0),axis=1))];knot/=knot[-1]
    curve=CubicSpline(knot,c,axis=0,bc_type='natural')
    grid=np.linspace(0,1,241);path=curve(grid);tangent=unit(curve(grid,1))
    axis=np.tile([-1.,0.,0.],(len(grid),1));axis=unit(axis-tangent*(axis*tangent).sum(1)[:,None])
    normal=unit(np.cross(tangent,axis))
    width=np.interp(grid,*widths)
    for _ in range(2):
        samples=path[:,None]+axis[:,None]*width[:,None,None]*np.linspace(-.5,.5,7)[None,:,None]
        origins=(samples+normal[:,None]*8.).reshape(-1,3);directions=np.repeat(-normal,7,axis=0)
        hit,ray,_=envelope.ray.intersects_location(origins,directions,multiple_hits=False)
        depth=((origins[ray]-hit)*-directions[ray]).sum(1)
        shift=np.zeros(len(origins));shift[ray]=np.clip(8.+clearance-depth,0,3.)
        lift=shift.reshape(-1,7).max(1);lift=np.maximum(lift,gaussian_filter1d(lift,3.))
        pin=ease(grid/.10)*ease((1-grid)/.10)
        path+=normal*(lift*pin)[:,None]
    tangent=unit(np.gradient(path,grid,axis=0))
    axis=np.tile([-1.,0.,0.],(len(grid),1));axis=unit(axis-tangent*(axis*tangent).sum(1)[:,None])
    normal=unit(np.cross(tangent,axis))
    return grid,path,axis,normal,width

recipes=[]
for side,padded_id,return_id in [(-1,9604,12817),(1,4250,1264)]:
    ids=np.flatnonzero((labels==padded_id)&(native[:,1]<-1.))
    n=native[ids];theta=np.arctan2(4.-n[:,1],n[:,2]+15.);rad=np.hypot(4.-n[:,1],n[:,2]+15.)
    local_grid=np.linspace(theta.min(),theta.max(),181)
    fields=[]
    for x in local_grid:
        near=np.argsort(abs(theta-x))[:70]
        lo,hi=np.quantile(n[near,0],[.035,.965]);rlo,rhi=np.quantile(rad[near],[.12,.88])
        fields.append([(lo+hi)*.5,max((hi-lo)*.5,1.),(rlo+rhi)*.5,max((rhi-rlo)*.5,.16)])
    fields=gaussian_filter1d(np.asarray(fields),4.,axis=0)
    across=np.clip((n[:,0]-np.interp(theta,local_grid,fields[:,0]))/np.interp(theta,local_grid,fields[:,1]),-1.06,1.06)
    depth=np.clip((rad-np.interp(theta,local_grid,fields[:,2]))/np.interp(theta,local_grid,fields[:,3]),-1,1)*.23
    s=(theta-local_grid[0])/(local_grid[-1]-local_grid[0])
    # Padded portion ends on the lower chest. It no longer wraps to the hip.
    controls=[[8.0,-9.8,144.1],[10.6,-6.6,146.0],[12.2,-.8,146.1],
        [12.8,5.1,142.8],[12.3,10.4,137.2],[11.7,12.8,131.1],[12.6,13.3,124.2]]
    grid,path,axis,normal,width=path_frame(controls,side,.55,([0,.12,.55,.85,1],[4.5,4.5,4.0,3.6,2.4]))
    center=interpolate(path,s,grid);wa=unit(interpolate(axis,s,grid));no=unit(interpolate(normal,s,grid))
    new=center+wa*(across*np.interp(s,grid,width)*.5)[:,None]+no*depth[:,None]
    seam=ease((-n[:,1]-1.)/3.)
    rigid=n*np.array([-.9,-.9,.9])+[0.,-10.5,120.]
    result[ids]=rigid*(1-seam)[:,None]+new*seam[:,None];changed[ids]=True
    for j,vi in enumerate(ids):
        clavicle=.12*np.exp(-((s[j]-.24)/.16)**2)*seam[j]
        chest=float(np.interp(s[j],[0,.12,.35,.75,1],[0,.7,.8,.4,.2]))*seam[j]
        weights[vi]=[[bones['spine_03'],1-chest-clavicle],[bones['spine_04'],chest],
                     [bones['clavicle_l' if side>0 else 'clavicle_r'],clavicle]]
        weights[vi]=[[b,w] for b,w in weights[vi] if w>1e-7]
    chest_end=path[-1].copy()
    recipes.append(dict(side=side,part='padded',vertices=len(ids),path=path.tolist(),width_cm=width.tolist()))

    # Reuse the original side tape geometry/UV, with a continuous path from
    # the lower bag seam to the padded strap. No independent hanging wing.
    ids=np.flatnonzero((labels==return_id)&(native[:,1]<-1.));n=native[ids]
    longitudinal=-n[:,1];g=np.linspace(longitudinal.min(),longitudinal.max(),101);f=[]
    for x in g:
        near=np.argsort(abs(longitudinal-x))[:30]
        zl,zh=np.quantile(n[near,2],[.04,.96]);xl,xh=np.quantile(n[near,0],[.10,.90])
        f.append([(zl+zh)*.5,max((zh-zl)*.5,.5),(xl+xh)*.5,max((xh-xl)*.5,.15)])
    f=gaussian_filter1d(np.asarray(f),3,axis=0)
    across=np.clip((n[:,2]-np.interp(longitudinal,g,f[:,0]))/np.interp(longitudinal,g,f[:,1]),-1.05,1.05)
    depth=np.clip((n[:,0]-np.interp(longitudinal,g,f[:,2]))/np.interp(longitudinal,g,f[:,3]),-1,1)*.12
    s=(longitudinal-g[0])/(g[-1]-g[0])
    end=chest_end.copy();end[0]*=side
    controls=[[15.,-10.7,110.5],[17.5,-7.3,112.8],[18.5,-1.0,116.1],
        [17.5,6.2,119.5],[15.1,11.8,122.4],end.tolist()]
    grid,path,axis,normal,width=path_frame(controls,side,.50,([0,.25,.8,1],[2.5,2.25,2.25,2.4]))
    # A return tape's cross direction is vertical at the bag, rotating smoothly
    # into the padded strap's width at the chest connector.
    tangent=unit(np.gradient(path,grid,axis=0));outward=unit(np.column_stack([path[:,0]*.7,path[:,1]-1.,np.zeros(len(path))]))
    tape_axis=unit(np.cross(outward,tangent));tape_normal=unit(np.cross(tangent,tape_axis))
    for i in range(1,len(tape_axis)):
        if tape_axis[i]@tape_axis[i-1]<0:tape_axis[i]*=-1;tape_normal[i]*=-1
    result[ids]=interpolate(path,s,grid)+unit(interpolate(tape_axis,s,grid))*(across*np.interp(s,grid,width)*.5)[:,None]+unit(interpolate(tape_normal,s,grid))*depth[:,None]
    changed[ids]=True
    for j,vi in enumerate(ids):
        chest=.2*float(ease((s[j]-.65)/.35))
        weights[vi]=[[bones['spine_03'],1-chest]]+([[bones['spine_04'],chest]] if chest>1e-7 else [])
    recipes.append(dict(side=side,part='return',vertices=len(ids),path=path.tolist(),width_cm=width.tolist()))

# Remove the old front-facing dangling/waist strips. Keep the sewn top strap
# junction, the bag's pockets, closures, rear compression straps and their UVs.
obsolete=np.isin(labels,[1067,32,15161]) | (islands==0)
keep=~np.any(obsolete[faces],axis=1)
# Side tapes are relocated to lower anchors; discard their old transition
# triangles at the old high anchor instead of stretching those joins.
return_vertex=np.isin(labels,[1264,12817])&(native[:,1]<-1.)
cross_return=np.any(return_vertex[faces],axis=1)&~np.all(return_vertex[faces],axis=1)
keep &= ~cross_return
kept=faces[keep].copy()
uvs=np.asarray(data['uv'])[keep].copy()
# The side tape's native X thickness / Z width parameterization reverses
# handedness. Reverse its winding and matching corner attributes together.
flip=np.all(return_vertex[kept],axis=1)
kept[flip]=kept[flip][:,[0,2,1]]
uvs[flip]=uvs[flip][:,[0,2,1]]
# Keep original shell normals. Only recompute normals on refitted ribbons.
normals=np.asarray(data['normals'])[keep].copy()
normals[flip]=normals[flip][:,[0,2,1]]
area=np.cross(result[kept[:,1]]-result[kept[:,0]],result[kept[:,2]]-result[kept[:,0]])
weld,inverse=np.unique(np.round(result,5),axis=0,return_inverse=True);acc=np.zeros_like(weld)
for corner in range(3):np.add.at(acc,inverse[kept[:,corner]],area)
smooth=unit(acc)[inverse]
for corner in range(3):
    change=changed[kept[:,corner]];normals[change,corner]=smooth[kept[change,corner]]
used=np.unique(kept);index=np.full(len(result),-1,int);index[used]=np.arange(len(used))
data.update(positions=result[used].tolist(),triangles=index[kept].tolist(),weights=[weights[i] for i in used],
    uv=uvs.tolist(),normals=normals.tolist(),
    triangle_materials=np.asarray(data['triangle_materials'])[keep].tolist(),
    revision='TorsoHarness20261012',contract='native bag/UV/material retained; two shoulder pads and lower return tapes; rigid bag; torso/clavicle weights only')
(R/'backpack_repaired.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(R/'authoring.json').write_text(json.dumps(dict(revision=data['revision'],source=data['source'],
    input_triangles=len(faces),output_triangles=len(kept),removed_legacy_triangles=int((~keep).sum()),
    modified_ribbon_vertices=int(changed[used].sum()),binding_bones=[b for b in bones if b in ['spine_03','spine_04','clavicle_l','clavicle_r']],
    straps=recipes,runtime_tested=False),indent=2),encoding='utf-8')
print('BACKPACK_HARNESS_AUTHORED',len(kept),'triangles',int(changed[used].sum()),'ribbon vertices',flush=True)
