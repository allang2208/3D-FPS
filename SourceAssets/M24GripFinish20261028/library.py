"""Use the saved current UE profile; never move the rifle or shoulder anchors."""
import json,math,bisect,ast
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent
OLD=OUT.parent/'M24BoltRematch20261027'
saved_file=__file__;__file__=str(OLD/'surface_contact.py')
exec(compile((OLD/'surface_contact.py').read_text().split("if __name__=='__main__':")[0],'surface_library','exec'))
__file__=saved_file
ue=json.loads((OUT/'ue_before.json').read_text());K=Matrix.Diagonal((1,-1,1,1))
def unpack(v):return Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10])
def sample(t,time):
 ts=t['times'];i=max(0,min(len(ts)-2,bisect.bisect_right(ts,time)-1));v=t['values'];a=unpack(v[10*i:10*i+10])
 if len(ts)==1:return a
 b=unpack(v[10*i+10:10*i+20]);w=max(0,min(1,(time-ts[i])/(ts[i+1]-ts[i])))
 return a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
clips={}
for role,data in ue['clips'].items():
 family='mag10' if role.endswith('_mag10') else 'base'
 layer=next(c for c in ue['profiles'][family] if c['base']==data['path']);tracks={t['bone']:t for t in layer['tracks']};rows=[]
 for f,raw_pose in data['poses'].items():
  comp={}
  for n,v in zip(names,raw_pose):
   p,q,sc=unpack(v)
   if n in tracks:
    dp,dq,ds=sample(tracks[n],int(f)/data['fps']);p+=dp;q=dq@q;sc+=ds
   loc=Matrix.LocRotScale(p,q,sc);comp[n]=comp[parents[n]]@loc if parents[n] else loc
  rows.append({n:K@m@K for n,m in comp.items()})
 clips[role]=rows
# The previous author helper could move the shoulder when reaching the limit.
# This refinement fixes the shoulder and retains the existing clavicle frame.
tree=ast.parse((OUT.parent/'M24ArmRebuild20261027/author.py').read_text())
func=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve_frames'))
func='\n'.join(line for line in func.splitlines() if 'S += axis.normalized()' not in line and 'if axis.length >' not in line)
exec(compile(func,'fixed_shoulder_ik','exec'))
original_apply=apply_arm
def fixed_arm(row,side,phi):
 c=row['clavicle_'+side].copy();shoulder=row['upperarm_'+side].translation.copy()
 original_apply(row,side,phi);row['clavicle_'+side]=c
 if (row['upperarm_'+side].translation-shoulder).length>1e-6:raise RuntimeError('Shoulder moved')
def serial(rows):return [{n:[list(v) for v in m] for n,m in row.items()} for row in rows]
