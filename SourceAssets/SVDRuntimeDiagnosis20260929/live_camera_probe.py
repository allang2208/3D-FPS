from pathlib import Path
exec(Path('SourceAssets/ChainmailReloadFit20260929/diagnose.py').read_text().split('report=')[0])
R=Path('SourceAssets/SVDRuntimeDiagnosis20260929');pose=read(R/'live-pose.json');mat={n:matrix(t) for n,t in pose['bones'].items()};cam=np.linalg.inv(matrix(pose['camera']))@matrix(pose['source']);out={}
for name,path in [('bare',Path('SourceAssets/SVDOutfitSpike20260929/bare.json')),('chainmail',R/'ue_chainmail_shirt_rig_meshes_LOD0.json')]:
 d=read(path);p=posed(prepare(d),mat);q=p@cam[:3,:3].T+cam[:3,3]
 mask=np.array([sum(v for n,v in w.items() if n.endswith('_r') and n.startswith(('upperarm','clavicle')))>.5 for w in d['weights']]);ids=np.where(mask&(q[:,0]>0)&(q[:,2]>0)&(q[:,2]<q[:,0])&(abs(q[:,1])<q[:,0]))[0]
 out[name]={'upper_viewport_vertices':len(ids),'vertex_ids':ids.tolist(),'camera_positions':q[ids].tolist()};print(name,len(ids))
(R/'live-camera-projection.json').write_text(json.dumps(out,indent=2))
