"""Derive robe underlayers and refit the paired shirt to the selected V3 waist.

Background Blender authoring only; does not run pose checks or preview renders.
"""
import gc,hashlib,runpy,shutil,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
from finish_inner_normals import smooth_split_normals
R.mkdir(parents=True,exist_ok=True)
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');catalog=read(P/'Content/ColdSteelData/items.json')
baseline=R/'baseline.json'
if not baseline.exists():write(baseline,dict(items={k:cfg['items'][k] for k in ('ue_leather_pants','ue_field_sweater','ue_blue_mage_robe')},definition=catalog['ue_leather_pants']))
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from author_underrobe_fit import NativeFit
old=read(P/'SourceAssets/BlueMageRobe20261018/UnderRobeFit20261020/authored.json')
skin=read(old['body_sources']['Jason']['file'])
waist=read(P/'SourceAssets/BlueMageRobe20261018/Authored/Body/Jason.json')['cloth_dimensions']['waist_cm']
fitter=NativeFit(skin,waist);del skin;gc.collect()
records=[]
for profile in PROFILES:
    src=SOURCE/'Authored/ue_leather_pants'/(profile+'.json')
    out=R/'Authored/ue_leather_pants'/(profile+'.json');out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out)
    records.append(dict(item='ue_leather_pants',profile=profile,file=str(out),source=str(src),author_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
    d=read(src);p=np.asarray(d['positions']);f=np.asarray(d['triangles'],dtype=int);q,fit=fitter.fit(d)
    # Rotate authored split normals with the local face rotation, retaining
    # intentional hard/soft edge choices on buckles, pockets and stitching.
    a=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    b=np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]])
    a/=np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-12);b/=np.maximum(np.linalg.norm(b,axis=1,keepdims=True),1e-12)
    axis=np.cross(a,b);cos=np.sum(a*b,axis=1);n=np.asarray(d['normals']);v=axis[:,None,:]
    n=n+np.cross(v,n)+np.cross(v,np.cross(v,n))/np.maximum(1+cos[:,None,None],1e-8)
    n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    original_normals=d['normals'];d['normals']=n.tolist();d['positions']=q.tolist();smooth_split_normals({'normals':original_normals},d);del original_normals;d['profile']=profile+'_RobeInner'
    d['material_slots']=['RobeStairHidden_'+str(i) for i in range(6)]
    d['contract']+='; robe-only native-body envelope with original cuff transition; continuous visible legs; existing robe pixel visibility contract'
    out=R/'Authored/ue_leather_pants'/(d['profile']+'.json');write(out,d)
    records.append(dict(item='ue_leather_pants',profile=d['profile'],file=str(out),source=str(src),author_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),robe_fit=fit))
    print('RANGER_INTEGRATION_AUTHORED',profile,flush=True)
    del d,p,f,q,n,a,b,v,axis;gc.collect()
runpy.run_path(str(P/'Tools/RangerCrouchFit/author_tucked.py'),init_globals={'OUTPUT_ROOT':str(R/'ShirtPair'),'PANTS_FILE':str(SOURCE/'Authored/ue_leather_pants/Jason.json')},run_name='__main__')
for row in read(R/'ShirtPair/authored.json')['records']:
    src=Path(row['file']);out=R/'Authored/ue_field_sweater'/src.name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out)
    records.append(dict(item='ue_field_sweater',profile=row['profile'],file=str(out),source=str(src),author_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
write(R/'authored.json',dict(completed=True,revision='RealisticCutV3',records=records,runtime_tested=False,preview_rendered=False))
print('RANGER_V3_INTEGRATION_SOURCES_READY',len(records),flush=True)
