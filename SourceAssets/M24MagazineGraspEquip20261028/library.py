import bpy,json,math,bisect,ast,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadBoltFix20261028/M24_BoltRoot_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()};parents=source['parents'];names=list(rest)
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
ue=json.loads((O/'ue_before.json').read_text());K=Matrix.Diagonal((1,-1,1,1))
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
 for f,raw in data['poses'].items():
  comp={}
  for n,v in zip(names,raw):
   p,q,sc=unpack(v)
   if n in tracks:
    dp,dq,ds=sample(tracks[n],int(f)/data['fps']);p+=dp;q=dq@q;sc+=ds
   loc=Matrix.LocRotScale(p,q,sc);comp[n]=comp[parents[n]]@loc if parents[n] else loc
  rows.append({n:K@m@K for n,m in comp.items()})
 clips[role]=rows
def under(n,p):
 while n:
  if n==p:return True
  n=parents.get(n)
 return False
def clone(row):return {n:m.copy() for n,m in row.items()}
def ease(t):
 t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
def set_pose(row):
 r.animation_data_clear()
 for n,m in row.items():
  loc=row[parents[n]].inverted()@m if parents[n] else m
  r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
 bpy.context.view_layer.update()
def setup_render():
 code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text()
 exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'),globals())
 s.render.resolution_x=800;s.render.resolution_y=600
def show(row,filename,view='left',extended=False):
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 mag=bpy.data.objects['M24_clip'];ext=bpy.data.objects.get('M24_Magazine10')
 mag.hide_render=extended
 if ext:
  ext.hide_render=not extended
  ext.matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
 target=(row['hand_l'].translation+row['middle_02_l'].translation)*.5
 if view=='left':off=(-.30,-.12,.10)
 elif view=='right':off=(.30,-.10,.08)
 else:off=(-.08,.16,-.30)
 cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.28
 s.render.filepath=str(filename);bpy.ops.render.render(write_still=True)
