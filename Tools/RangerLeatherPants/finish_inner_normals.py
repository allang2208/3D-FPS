"""Preserve the authored smoothing splits when shaping robe-only underlayers."""
import gc,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
def smooth_split_normals(source,d):
    f=np.asarray(d['triangles'],dtype=int);p=np.asarray(d['positions'])
    # Face-wise rotation must not turn every triangle into a new hard edge.
    # Recombine precisely the corners that shared an authored vertex/normal.
    keys=np.c_[f.ravel(),np.round(np.asarray(source['normals']).reshape(-1,3),7)]
    _,inverse=np.unique(keys,axis=0,return_inverse=True)
    area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)
    accum=np.zeros((inverse.max()+1,3));np.add.at(accum,inverse,np.asarray(d['normals']).reshape(-1,3)*np.repeat(area,3)[:,None])
    accum/=np.maximum(np.linalg.norm(accum,axis=1,keepdims=True),1e-12)
    d['normals']=accum[inverse].reshape(-1,3,3).tolist()
def main():
    manifest=read(R/'authored.json')
    for row in manifest['records']:
        if not row['profile'].endswith('_RobeInner'):continue
        source=read(row['source']);d=read(row['file']);smooth_split_normals(source,d)
        file=Path(row['file']);temp=file.with_suffix('.json.tmp');temp.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');temp.replace(file)
        row['author_sha256']=hashlib.sha256(file.read_bytes()).hexdigest();row['normals']='Authored smooth groups retained after local deformation'
        print('RANGER_INNER_SMOOTH_GROUPS_SAVED',row['profile'],flush=True);del source,d;gc.collect()
    write(R/'authored.json',manifest)
if __name__=='__main__':main()
