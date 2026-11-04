from pathlib import Path
import json,numpy as np
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
class Skin:
    def __init__(self,c,variant='Standard'):
        self.c=c;f=P/'NativeBefore'/variant;d=json.loads((f/'surface.json').read_text(encoding='utf-8-sig'))
        self.names=d['bone_names'];n=d['influences'];self.v=np.fromfile(f/'arms.bind',dtype=np.float32).reshape(-1,3)*[.01,-.01,.01]
        idx=np.fromfile(f/'arms.bones',dtype=np.uint16).reshape(-1,n);w=np.fromfile(f/'arms.weights',dtype=np.float32).reshape(-1,n)
        main=np.fromfile(f/'arms.mainbone',dtype=np.uint16);self.labels=np.array(self.names)[main];self.sides={s:np.flatnonzero(np.array([x.endswith('_'+s) and any(x.startswith(k) for k in ['hand','thumb','index','middle','ring','pinky']) for x in self.labels])) for s in ['l','r']}
        self.weights={};self.restinv={}
        for b in np.unique(idx):
            name=self.names[b]
            if name not in c.rest:continue
            total=np.sum(np.where(idx==b,w,0),axis=1);ids=np.flatnonzero(total>0)
            self.weights[name]=(ids,total[ids]);self.restinv[name]=np.array(c.rest[name].inverted())
        self.parts=[]
        for part in d['parts']:
            v=np.fromfile(f/(part['id']+'.vertices'),dtype=np.float32).reshape(-1,3)*[.01,-.01,.01]
            faces=np.fromfile(f/(part['id']+'.indices'),dtype=np.uint32).reshape(-1,3)[:,::-1]
            self.parts.append((part['id'],BVHTree.FromPolygons(v.tolist(),faces.tolist(),all_triangles=True),v.min(0),v.max(0)))
    def points(self,pose,side=None):
        out=np.zeros_like(self.v)
        for name,(ids,w) in self.weights.items():
            M=np.array(pose[name])@self.restinv[name];out[ids]+=(self.v[ids]@M[:3,:3].T+M[:3,3])*w[:,None]
        return out if side is None else out[self.sides[side]]
    def contact_points(self,pose,side):
        pts=self.points(pose,side);M=np.array(pose['WPN_root'].inverted());return pts@M[:3,:3].T+M[:3,3]
