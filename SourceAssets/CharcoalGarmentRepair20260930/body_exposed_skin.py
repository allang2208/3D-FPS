"""Charcoal-specific exposed skin; hidden body regions cannot tear through cloth.

Hands and glove ownership remain on the existing base. The outfit contributes
only uncovered arms and neck/lower torso; all skin positions/weights stay native.
"""
import sys,copy
from pathlib import Path
import bmesh,numpy as np,math
from mathutils import Vector
R=Path(__file__).resolve().parent;P=R.parent.parent
sys.path.insert(0,str(R));from author import read,write
def build():
 d=read(R/'Authored/Body.json');out=copy.deepcopy(d)
 skin=read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_skin.json')
 current=read(R/'Before/Body/skin.json');names=sorted({n for w in current['weights'] for n in w})
 points=np.array(d['positions']);center=np.array([0.,-1.5]);q=points[:,:2]-center
 neck_candidates=(np.linalg.norm(q,axis=1)<13)&(points[:,2]>149)
 theta=np.mod(np.arctan2(q[:,1],q[:,0]),2*math.pi);bins=64;heights=np.full(bins,np.nan)
 for i in np.flatnonzero(neck_candidates):
  j=min(int(theta[i]/(2*math.pi)*bins),bins-1)
  heights[j]=max(heights[j],points[i,2]) if np.isfinite(heights[j]) else points[i,2]
 known=np.flatnonzero(np.isfinite(heights));heights=np.interp(np.arange(bins),np.r_[known-bins,known,known+bins],np.tile(heights[known],3))
 heights=(np.roll(heights,1)+2*heights+np.roll(heights,-1))/4
 def collar_height(p):
  angle=math.atan2(p.y-center[1],p.x-center[0])%(2*math.pi);t=angle/(2*math.pi)*bins-.5
  return float(np.interp(t,np.arange(-1,bins+1),np.r_[heights[-1],heights,heights[0]]))
 counts={}
 def part(name,material,select,plane,normal,clear_outer):
  bm=bmesh.new();uv=bm.loops.layers.uv.verify();deform=bm.verts.layers.deform.verify();ns=bm.verts.layers.float_vector.new('NativeNormal')
  faces=[i for i,(f,m) in enumerate(zip(skin['triangles'],skin['materials'])) if m==material and select(f)]
  used=sorted({v for i in faces for v in skin['triangles'][i]});vs={i:bm.verts.new(current['positions'][i]) for i in used}
  for i,v in vs.items():
   v[ns]=skin['normals'][i]
   for n,w in current['weights'][i].items():v[deform][names.index(n)]=w
  for fi in faces:
   f=skin['triangles'][fi];face=bm.faces.new([vs[i] for i in f])
   for l,i in zip(face.loops,f):l[uv].uv=skin['uv'][i]
  original=bm.verts.layers.float_vector.new('NativePosition')
  for v in bm.verts:
   v[original]=v.co
   if name.startswith('neck'):v.co.z-=collar_height(v.co)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector((0,0,-.35)) if name.startswith('neck') else plane,plane_no=normal,dist=.000001,clear_outer=clear_outer,clear_inner=not clear_outer)
  for v in bm.verts:v.co=v[original]
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update();offset=len(out['positions'])
  out['positions'].extend([list(v.co) for v in bm.verts]);out['weights'].extend([{names[i]:w for i,w in v[deform].items()} for v in bm.verts])
  for face in bm.faces:
   out['triangles'].append([offset+v.index for v in face.verts]);out['uv'].append([list(l[uv].uv) for l in face.loops]);out['normals'].append([list(v[ns].normalized()) for v in face.verts]);out['triangle_materials'].append(3 if material==1 else 4)
  counts[name]=len(bm.faces);bm.free()
 for side in ['l','r']:
  a=Vector(d['bones']['upperarm_'+side]['position']);b=Vector(d['bones']['lowerarm_'+side]['position']);axis=(b-a).normalized();cut=(b-a).length*.55-.5;sign=1 if a.x>0 else -1
  part('arm_'+side,1,lambda f,sign=sign:all(current['positions'][i][0]*sign>0 for i in f),a+axis*cut,axis,False)
  part('arm_rest_'+side,4,lambda f,sign=sign:all(current['positions'][i][0]*sign>18 and current['positions'][i][2]>100 for i in f),a+axis*cut,axis,False)
 part('neck',3,lambda f:True,Vector((0,0,146.5)),Vector((0,0,1)),False)
 part('lower_torso',3,lambda f:True,Vector((0,0,94)),Vector((0,0,1)),True)
 part('neck_rest',4,lambda f:True,Vector((0,0,146.5)),Vector((0,0,1)),False)
 part('lower_body_rest',4,lambda f:True,Vector((0,0,100)),Vector((0,0,1)),True)
 out['contract']+='; integrated native exposed arms/neck/head/lower-body sections; base Body materials 1,3,4 hidden only while this shirt is equipped; hands stay on base'
 out['extra_materials']=[current['slots'][i]['material'] for i in [1,3]]
 write(R/'Authored/BodyEquipped.json',out);write(R/'body-coverage.json',dict(world_covers=[1,3,4],exposed_skin_triangles=counts,unchanged_skin_positions_and_weights=True,hand_region_owned_by_base=True))
 print('CHARCOAL_EXPOSED_SKIN',counts,flush=True)
if __name__=='__main__':build()
