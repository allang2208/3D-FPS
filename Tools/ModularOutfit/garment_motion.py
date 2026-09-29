"""Evaluate saved LOD0/1/2 against native compressed poses collected by UE."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from garment_pipeline import read,write,digest,asset_file,fingerprint

def matrix(t):
    m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m

def prepare(d):
    groups={};p=np.array(d['positions'])
    for i,w in enumerate(d['weights']):
        for n,v in w.items():groups.setdefault(n,[]).append((i,v))
    packed=[]
    for n,rows in groups.items():
        a=np.array(rows);packed.append((n,a[:,0].astype(int),a[:,1,None],np.linalg.inv(matrix(d['rest'][n]))))
    return p,packed

def posed(data,mat):
    p,groups=data;out=np.zeros_like(p)
    for n,ids,w,inv in groups:
        m=mat[n]@inv;out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w
    return out

def evaluate(path):
    path=Path(path);m=read(path);rows=[];errors=[];covered=set()
    for profile,candidate in m['candidates'].items():
        motion=read(path.parent/'motion'/(profile+'.json'))
        if motion['asset_sha256']!=digest(asset_file(candidate['asset'])):raise RuntimeError('Candidate changed '+profile)
        if motion['native_sha256']!=digest(asset_file(motion['native_source'])):raise RuntimeError('Native mesh changed '+profile)
        for clip,sha in motion['clips'].items():
            if digest(asset_file(clip))!=sha:raise RuntimeError('Animation changed '+clip)
        for lod,ref in candidate['snapshots'].items():
            if digest(ref['path'])!=ref['sha256']:raise RuntimeError('Snapshot changed')
            d=read(ref['path']);data=prepare(d);p=data[0];f=np.array(d['triangles']);edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
            rest=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);valid=rest>.1
            for n in {n for w in d['weights'] for n in w}:
                if n not in motion['native_rest'] or not np.allclose(matrix(d['rest'][n]),matrix(motion['native_rest'][n]),atol=.002):errors.append(profile+':bind_mismatch:'+n)
            clips={}
            for pose in motion['poses']:
                points=posed(data,{n:matrix(t) for n,t in pose['bones'].items()});length=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
                row=clips.setdefault((pose['group'],pose['clip']),dict(samples=0,max_edge_cm=0.,max_stretch=0.))
                row['samples']+=1;row['max_edge_cm']=max(row['max_edge_cm'],float(length.max()));row['max_stretch']=max(row['max_stretch'],float((length[valid]/rest[valid]).max(initial=0)))
            for (group,clip),row in clips.items():
                covered.add((profile,group,clip));rows.append(dict(profile=profile,lod=int(lod),group=group,clip=clip,**row))
                if row['max_edge_cm']>m['limits']['max_posed_edge_cm'] or row['max_stretch']>m['limits']['max_edge_stretch']:errors.append(profile+':LOD'+lod+':'+clip)
    output=path.with_suffix('.motion.json');write(output,dict(status='pass' if not errors else 'fail',fingerprint=fingerprint(m),profiles=list(m['candidates']),covered_actions=sorted(covered),errors=errors,rows=rows,method='Saved render LODs; compressed native poses at 20 Hz plus endpoints; no runtime camera/IK or cloth collision acceptance'))
    m['evidence']['motion']=dict(path=str(output),sha256=digest(output));write(path,m);return errors

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('manifest');args=parser.parse_args();errors=evaluate(args.manifest);print('MOTION', 'FAIL' if errors else 'PASS',len(errors));raise SystemExit(bool(errors))
