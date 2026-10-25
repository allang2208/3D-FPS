"""Fit only the rear interface, keeping installation height and outside cargo detail."""
import json,os,hashlib,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt,gaussian_filter,map_coordinates,maximum_filter
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from preserve_sections import repair
from fit_geometry import contact_field
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');records=read(R/'captured.json');frames=read(R/'Surfaces/frames.json')
out=R/'Authored';out.mkdir(exist_ok=True);dest='/Game/Characters/BackpackFit20261024/'+R.name
def norm(rig,v):
    d=frames[rig];return (v-np.asarray(d['translation']))@np.asarray(d['matrix']).T
def native(rig,v):
    d=frames[rig];return v@np.asarray(d['matrix'])+d['translation']
def load(path):
    return np.fromfile(Path(records[path]['folder'])/'positions.bin',dtype='<f4').reshape(-1,3).astype(float)
def sampler(xs,zs,values,sigma=0):
    valid=np.isfinite(values)
    if not valid.any():raise RuntimeError('Empty surface field')
    nearest=distance_transform_edt(~valid,return_distances=False,return_indices=True)
    grid=values[tuple(nearest)]
    if sigma:grid=gaussian_filter(grid,sigma)
    def sample(points):
        return map_coordinates(grid,np.vstack([(points[:,0]-xs[0])/(xs[1]-xs[0]),(points[:,2]-zs[0])/(zs[1]-zs[0])]),order=1,mode='nearest')
    return sample
def contact_warp(shell,surface):
    back=sampler(shell['xs'],shell['zs'],shell['rear'],.6)
    front=sampler(shell['xs'],shell['zs'],shell['front'],.6)
    body=sampler(surface['xs'],surface['zs'],surface['guarded_rear'],1.2)
    samples=shell['rear_points'];core=samples[(np.abs(samples[:,0])<10)&(samples[:,2]>106)&(samples[:,2]<141)]
    clearance=body(core)-core[:,1]
    shift=float(np.clip(np.quantile(clearance,.45)-1.7,-5.,12.))
    # A central ventilation channel remains open; shoulder/lumbar bands support
    # the load. The rear cage varies smoothly in height and across the back.
    correction=np.zeros_like(shell['rear'])
    def correction_at(q):
        return map_coordinates(correction,np.vstack([(q[:,0]-shell['xs'][0])/.5,(q[:,2]-shell['zs'][0])/.5]),order=1,mode='nearest')
    def warp(q):
        b,f=back(q),front(q);depth=np.maximum(b-f,.2)
        margin=.85+1.1*np.exp(-(q[:,0]/3.2)**2)
        wanted=body(q)-margin-(b+shift)-correction_at(q)
        band=np.maximum(depth-.9,.2)
        thin=np.clip((4.-depth)/2.,0,1)
        change=np.clip(wanted,-.55*band,8.)*(1-thin)+np.minimum(wanted,8.)*thin
        # Rear-only positive-derivative remap keeps outside pockets and face UVs.
        band=np.minimum(band,np.maximum(depth*.55,np.abs(change)*1.85))
        t=np.clip((q[:,1]-(b-band))/band,0,1);blend=t*t*(3-2*t)
        # Thin exposed rear fittings translate intact instead of being flattened.
        blend=blend*(1-thin)+thin
        delta=np.zeros_like(q);delta[:,1]=shift+change*blend
        return delta
    # Authoring collision solve samples triangle interiors as well as vertices.
    # Coarse back panels otherwise bridge over a curved spine despite fitted corners.
    cargo=shell['positions'];faces=shell['triangles'];tri=cargo[faces]
    vertex_ids=np.unique(faces)
    probes=np.vstack([cargo[vertex_ids],tri.mean(1),(tri[:,0]+tri[:,1])*.5,(tri[:,1]+tri[:,2])*.5,(tri[:,2]+tri[:,0])*.5])
    body_valid=sampler(surface['xs'],surface['zs'],np.isfinite(surface['guarded_rear']).astype(float))
    valid=(np.abs(probes[:,0])<23)&(probes[:,2]>90)&(probes[:,2]<157)&(body_valid(probes)>.9)
    for _ in range(4):
        changed=cargo+warp(cargo);t=changed[faces]
        moved=np.vstack([changed[vertex_ids],t.mean(1),(t[:,0]+t[:,1])*.5,(t[:,1]+t[:,2])*.5,(t[:,2]+t[:,0])*.5])
        needed=np.where(valid,np.maximum(0,moved[:,1]-body(probes)+.55),0.)
        if needed.max(initial=0)<.05:break
        per_vertex=np.zeros(len(cargo));np.maximum.at(per_vertex,vertex_ids,needed[:len(vertex_ids)])
        per_face=needed[len(vertex_ids):].reshape(4,-1).max(0)
        for corner in range(3):np.maximum.at(per_vertex,faces[:,corner],per_face)
        grid=np.zeros_like(correction)
        xi=np.clip(np.rint((cargo[:,0]-shell['xs'][0])/.5).astype(int),0,len(shell['xs'])-1)
        zi=np.clip(np.rint((cargo[:,2]-shell['zs'][0])/.5).astype(int),0,len(shell['zs'])-1)
        np.maximum.at(grid,(xi,zi),per_vertex)
        correction+=gaussian_filter(maximum_filter(grid,size=3),.6)
    return warp,shift
rows=[];statics=[];dedup={}
only=sys.argv[sys.argv.index('--item')+1] if '--item' in sys.argv else None
if only and (R/'authored.json').exists():
    previous=read(R/'authored.json');rows=[r for r in previous['rows'] if r['item']!=only]
    used={r.get('rigid_mesh') for r in rows};statics=[s for s in previous['statics'] if s['asset']+'.'+s['asset'].rsplit('/',1)[-1] in used]
for row in plan['rows']:
    if only and row['item']!=only:continue
    gravity='hanging_pack' in row
    if gravity and not plan.get('include_gravity'):continue
    rig=row['rig'];path=row['mesh'];v=load(path);folder=Path(records[path]['folder'])
    mask=np.fromfile(folder/'mask.bin',dtype='<f4');f=np.fromfile(folder/'triangles.bin',dtype='<i4').reshape(-1,3)
    points=norm(rig,v);key=rig+'_'+row['item']+'_'+(row['shirt'] or 'bare')
    surface=np.load(R/'Surfaces'/(rig+'_'+(row['shirt'] or 'bare')+'.npz'))
    if gravity:
        rotation=Rotation.from_quat(row['rigid_rotation_quat']).as_matrix()
        cargo=norm(rig,load(row['rigid_mesh'])@rotation.T+row['rigid_location'])
        body=sampler(surface['xs'],surface['zs'],surface['guarded_rear'])
        shift=-max(0.,float(np.max(cargo[:,1]-body(cargo)+.45)))
        delta=np.zeros_like(cargo);delta[:,1]=shift
    else:
        shell=np.load(R/'Shells'/(key+'.npz'));warp,shift=contact_warp(shell,surface);cargo=shell['positions'];delta=warp(cargo)
        # Farreach's hard rear edge needs another 4.5 mm beyond the smooth cage.
        if row['item']=='ue_farreach_backpack':delta[:,1]-=.45;shift-=.45
    deform=contact_field(points,mask,surface)
    if row.get('rigid_mesh'):
        # Sewn endpoints receive exactly the same movement as the adjoining shell.
        tree=cKDTree(cargo);_,ids=tree.query(points);end_delta=delta[ids]
    else:end_delta=warp(points)
    blend=mask*mask if gravity else mask
    proposed=points+end_delta*blend[:,None]+deform(points)*(1-blend[:,None])
    result,sections=repair(v,native(rig,proposed),f,mask)
    stem='SK_'+rig+'_'+row['item'].removeprefix('ue_')+'_'+(row['shirt'].removeprefix('ue_') or 'bare')
    file=out/(stem+'.bin');result.astype('<f4').tofile(file)
    data={'rig':rig,'item':row['item'],'shirt':row['shirt'],'source':path,'source_sha256':records[path]['package_sha256'],
          'asset':dest+'/'+rig+'/'+stem,'positions':str(file),'vertices':len(result),'section_reconstruction':sections,
          'pitch_delta_degrees':0.,'lift_cm':0.,'forward_shift_cm':shift}
    changed_shell=native(rig,cargo+delta)
    data.update(bounds_min=np.minimum(changed_shell.min(0),result.min(0)).tolist(),bounds_max=np.maximum(changed_shell.max(0),result.max(0)).tolist())
    translation=native(rig,np.array([0.,shift,0.]))-native(rig,np.zeros(3))
    data['motion_pivot']=(np.asarray(row['outfit']['backpack_motion']['pivot'])+translation).tolist()
    cargo_ids=np.arange(len(changed_shell)) if row.get('rigid_mesh') else np.unique(shell['triangles'])
    data['support']={'pivot':data['motion_pivot'],'bounds_min':changed_shell[cargo_ids].min(0).tolist(),'bounds_max':changed_shell[cargo_ids].max(0).tolist()}
    if row.get('rigid_mesh'):
        source=row['rigid_mesh'];rotation=Rotation.from_quat(row['rigid_rotation_quat']).as_matrix()
        location=np.asarray(row['rigid_location'])+translation
        local=(changed_shell-location)@rotation
        raw=local.astype('<f4').tobytes();digest=hashlib.sha256(raw).hexdigest();identity=(source,digest)
        if gravity:dedup[identity]=source
        if identity not in dedup:
            static_stem='SM_'+key.removeprefix('ue_')+'_Contact';static_file=out/(static_stem+'.bin');static_file.write_bytes(raw)
            static={'source':source,'asset':dest+'/'+rig+'/'+static_stem,'positions':str(static_file),'source_sha256':records[source]['package_sha256'],'vertices':len(local)}
            statics.append(static);dedup[identity]=static['asset']+'.'+static_stem
        data.update(rigid_location=location.tolist(),rigid_rotation_quat=row['rigid_rotation_quat'],rigid_mesh=dedup[identity])
    if gravity:
        from fit_sling import update_hanging
        deform_native=lambda q:deform(norm(rig,q))@np.asarray(frames[rig]['matrix'])
        data['hanging_pack']=update_hanging(row['hanging_pack'],translation,deform_native,surface,records[row['body']]['bones'],lambda q:native(rig,q))
    rows.append(data);print('BACKPACK_CONTACT_AUTHORED',key,'forward',round(shift,2),flush=True)
(R/'authored.json').write_text(json.dumps({'revision':R.name,'rows':rows,'statics':statics,'preserved_sling':not any('hanging_pack' in row for row in rows),'method':'Rear-interface fit; original height, tilt, topology, UVs, native skinning and external cargo retained'},indent=2))
