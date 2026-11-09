"""Current layered poses and native, weighted hand geometry for contact fitting."""
from pathlib import Path
import pickle,json,numpy as np
r=Path(__file__).resolve().parent
h=r.parent/'Repair20/author.py';s={'__file__':str(h)}
exec(compile(h.read_text().split("outdir=r/'Motion'")[0],str(h),'exec'),s)
d=pickle.load(open(r/'current.pkl','rb'));s['d']=d
idle=next(p for p in d['clips'] if p.endswith('_idle'))
poses={}
for family in d['profiles']:
    for path,c in d['clips'].items():
        if path!=idle and '/SideMagazine' not in path:continue
        times=np.array(c.get('times',np.arange(len(c['frames']))/c['fps']))
        w=s['world'](s['layer'](np.array(c['frames']),path,family,times))
        poses[(family,path)]=dict(world=w,times=times)
with (r/'poses.pkl').open('wb') as f:pickle.dump(poses,f)
geometry=pickle.load(open(r.parent/'Repair19/geometry.pkl','rb'))
parts={}
for family in d['profiles']:
    folder=r.parent/'ReturnReview24/saved'/f'45_normal_{family}_left'
    j=json.loads((folder/'review.json').read_text());meta=json.loads((folder/'geometry.json').read_text());row=j['frames'][-1];stem=folder/Path(row['file']).stem
    raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7)
    frame=raw[np.argmin(abs(raw[:,0]-row['runtime'])),4:].reshape(-1,7)
    root=s['matrix'](np.r_[frame[meta['bones'].index('WPN_root')],1,1,1]);inv=np.linalg.inv(root)
    def local(points):return points@inv[:3,:3].T+inv[:3,3]
    v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
    f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
    m=np.fromfile(stem.with_suffix('.materials'),np.uint32)
    pp={}
    for slot in ['M249_Factory_Receiver','M249_Factory_Handguard','M249_Factory_Foregrip']:
        mi=meta['slots'].index(slot)
        if mi not in row['visible_materials']:continue
        faces=f[m==mi];ids,remap=np.unique(faces,return_inverse=True)
        pp[slot]=dict(vertices=local(v[ids]),faces=remap.reshape(-1,3))
    for file in folder.glob(stem.name+'_*.vertices'):
        if not any(x in file.name for x in ['side_mag_45','SidePort','_'+family+'.vertices']):continue
        pp[file.stem.removeprefix(stem.name+'_')]=dict(vertices=local(np.fromfile(file,np.float32).reshape(-1,3)),faces=np.fromfile(file.with_suffix('.indices'),np.uint32).reshape(-1,3))
    # Both side-magazine sizes are part of the swept contact constraint.
    folder30=r.parent/'ReturnReview24/saved'/f'30_normal_{family}_left'
    jj=json.loads((folder30/'review.json').read_text());st=folder30/Path(jj['frames'][-1]['file']).stem
    raw30=np.fromfile(folder30/'poses.f32',np.float32).reshape(-1,4+jj['bone_count']*7);fr30=raw30[-1,4:].reshape(-1,7)
    inv30=np.linalg.inv(s['matrix'](np.r_[fr30[meta['bones'].index('WPN_root')],1,1,1]))
    p=Path(str(st)+'_SM_m249_side_mag_30.vertices');pv=np.fromfile(p,np.float32).reshape(-1,3)
    pp['SM_m249_side_mag_30']=dict(vertices=pv@inv30[:3,:3].T+inv30[:3,3],faces=np.fromfile(p.with_suffix('.indices'),np.uint32).reshape(-1,3))
    parts[family]=pp
with (r/'geometry.pkl').open('wb') as f:pickle.dump(dict(native=geometry,parts=parts),f)
print('M249_CONTACT25_PREPARED',len(poses),'layered clips',flush=True)
