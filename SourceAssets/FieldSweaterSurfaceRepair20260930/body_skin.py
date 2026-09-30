"""Restore only native skin exposed beyond the actual collar, hem and cuffs."""
import copy,sys,math
from pathlib import Path
import bmesh,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write

def build():
 d=read(R/'Authored/Body.json');out=copy.deepcopy(d)
 skin=read(P/'SourceAssets/ModularOutfit20260924/NativeSkin/Body_skin.json');current=read(R/'Before/Body/skin.json')
 if np.max(np.abs(np.array(skin['vertices'])-np.array(current['positions'])))>.001:raise RuntimeError('Native skin UV source no longer matches')
 names=sorted({n for w in current['weights'] for n in w});points=np.array(d['positions']);bins=64;center=np.array([0.,-1.5])
 def outline(mode):
  q=points[:,:2]-center;angles=np.mod(np.arctan2(q[:,1],q[:,0]),2*math.pi)
  selected=(np.linalg.norm(q,axis=1)<13)&(points[:,2]>149) if mode=='neck' else (np.abs(points[:,0])<24)&(points[:,2]<112)
  heights=np.full(bins,np.nan)
  for i in np.flatnonzero(selected):
   j=min(int(angles[i]/(2*math.pi)*bins),bins-1);h=points[i,2]
   heights[j]=(max if mode=='neck' else min)(heights[j],h) if np.isfinite(heights[j]) else h
  known=np.flatnonzero(np.isfinite(heights))
  if len(known)<bins//2:raise RuntimeError('Incomplete garment opening')
  heights=np.interp(np.arange(bins),np.r_[known-bins,known,known+bins],np.tile(heights[known],3))
  heights=(np.roll(heights,1)+2*heights+np.roll(heights,-1))/4
  def height(p):
   t=(math.atan2(p.y-center[1],p.x-center[0])%(2*math.pi))/(2*math.pi)*bins-.5
   return float(np.interp(t,np.arange(-1,bins+1),np.r_[heights[-1],heights,heights[0]]))
  return height,heights.tolist()
 collar,collar_heights=outline('neck');hem,hem_heights=outline('hem');counts={}
 def part(name,material,select,plane,normal,clear_outer):
  bm=bmesh.new();uv=bm.loops.layers.uv.verify();deform=bm.verts.layers.deform.verify();ns=bm.verts.layers.float_vector.new('NativeNormal');pos=bm.verts.layers.float_vector.new('NativePosition')
  faces=[i for i,(f,m) in enumerate(zip(skin['triangles'],skin['materials'])) if m==material and select(f)]
  used=sorted({v for fi in faces for v in skin['triangles'][fi]});vs={i:bm.verts.new(current['positions'][i]) for i in used}
  for i,v in vs.items():
   v[ns]=skin['normals'][i];v[pos]=v.co
   for n,w in current['weights'][i].items():v[deform][names.index(n)]=w
  for fi in faces:
   ids=skin['triangles'][fi];face=bm.faces.new([vs[i] for i in ids])
   for loop,i in zip(face.loops,ids):loop[uv].uv=skin['uv'][i]
  curve=collar if name.startswith('neck') else hem if name.startswith('lower') else None
  if curve:
   for v in bm.verts:v.co.z-=curve(v.co)
   plane=Vector((0,0,-.4 if name.startswith('neck') else .4))
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=plane,plane_no=normal,dist=.000001,clear_outer=clear_outer,clear_inner=not clear_outer)
  for v in bm.verts:v.co=v[pos]
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update();offset=len(out['positions'])
  out['positions'].extend([list(v.co) for v in bm.verts]);out['weights'].extend([{names[i]:w for i,w in v[deform].items()} for v in bm.verts])
  for face in bm.faces:
   out['triangles'].append([offset+v.index for v in face.verts]);out['uv'].append([list(l[uv].uv) for l in face.loops]);out['normals'].append([list(v[ns].normalized()) for v in face.verts]);out['triangle_materials'].append(3 if material in [0,1] else 4)
  counts[name]=len(bm.faces);bm.free()
 for side in ['l','r']:
  wrist=Vector(d['bones']['hand_'+side]['position']);elbow=Vector(d['bones']['lowerarm_'+side]['position']);axis=(wrist-elbow).normalized();sign=1 if wrist.x>0 else -1
  q=points-np.array(wrist);t=q@np.array(axis);radial=q-t[:,None]*np.array(axis);ids=(points[:,0]*sign>30)&(np.linalg.norm(radial,axis=1)<9)&(t>-12)
  cut=float(t[ids].max())-.5;plane=wrist+axis*cut
  for material in [0,1]:part('wrist_'+side+'_'+str(material),material,lambda f,sign=sign:all(current['positions'][i][0]*sign>0 for i in f),plane,axis,False)
  part('wrist_rest_'+side,4,lambda f,sign=sign:all(current['positions'][i][0]*sign>20 for i in f),plane,axis,False)
 for material in [3,4]:
  part('neck_'+str(material),material,lambda f:True,Vector(),Vector((0,0,1)),False)
  part('lower_'+str(material),material,lambda f:True,Vector(),Vector((0,0,1)),True)
 out['extra_materials']=[current['slots'][i]['material'] for i in [1,3]]
 out['contract']+='; native exposed neck/head/lower-body/wrist skin follows actual garment outlines; Body base regions 0,1,3,4 hidden while equipped; hand region 2 remains independently glove-owned'
 write(R/'Authored/BodyEquipped.json',out)
 write(R/'body-coverage.json',dict(world_covers=[0,1,3,4],skin_parts=counts,collar_heights_cm=collar_heights,hem_heights_cm=hem_heights))
 print('FIELD_BODY_SKIN_COVERAGE',counts,flush=True)

if __name__=='__main__':build()
