"""Build the complete field-sweater FP family from each native V7 arm surface.
No donor sleeve deformation, nearest-surface weight transfer, or shoulder caps.
"""
import copy,json,sys,math
from pathlib import Path
import bmesh,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,digest

def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
def unit(v):return v/max(float(np.linalg.norm(v)),1e-12)
def surface_normals(p,f):
 n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
 for k in range(3):np.add.at(n,f[:,k],cross)
 return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
def side_of(w):
 return max(('l','r'),key=lambda s:sum(v for n,v in w.items() if n.endswith('_'+s)))
def normal_weights(w):
 pairs=sorted(((n,float(v)) for n,v in w.items() if v>1e-8),key=lambda pair:-pair[1])[:8]
 total=sum(v for _,v in pairs)
 return {n:v/total for n,v in pairs}
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)

def build(profile):
 path=R/'Before'/profile/'skin.json';skin=read(path);names=sorted(skin['rest'])
 p0=np.array(skin['positions']);source_side=[side_of(w) for w in skin['weights']]
 d=dict(profile=profile,binding_source=skin['source'],positions=[],weights=[],triangles=[],uv=[],triangle_materials=[],normals=[],contract='Native V7 arm topology per binding; paired shell weights; side selected by bone influences; open planar shoulders with thickness rims; continuous elbow UVs; identical protected FP LOD topology')
 report=dict(native_source=skin['source'],native_snapshot_sha256=digest(path),arms={},thickness_cm=.20,shoulder_trim_cm=1.0,lod_triangle_ratios=[1.,1.,1.])
 for side in ['l','r']:
  faces=[face for face,mat in zip(skin['triangles'],skin['materials']) if mat in (0,1,3) and all(source_side[i]==side for i in face)]
  if not faces:continue
  used=sorted({i for face in faces for i in face});bm=bmesh.new();deform=bm.verts.layers.deform.verify()
  vertices={i:bm.verts.new(p0[i]) for i in used}
  for i,v in vertices.items():
   for n,w in skin['weights'][i].items():v[deform][names.index(n)]=w
  for f in faces:bm.faces.new([vertices[i] for i in f])
  # Join only this arm's coincident native material boundaries. Every duplicated
  # cloth layer and seam is emitted from the resulting single surface field.
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
  a=np.array(skin['rest']['upperarm_'+side]['p']);e=np.array(skin['rest']['lowerarm_'+side]['p']);w=np.array(skin['rest']['hand_'+side]['p'])
  upper=unit(e-a);lower=unit(w-e);upper_length=float(np.linalg.norm(e-a));lower_length=float(np.linalg.norm(w-e))
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=Vector(a+upper),plane_no=Vector(upper),clear_inner=True,clear_outer=False)
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
  p=np.array([list(v.co) for v in bm.verts]);f=np.array([[v.index for v in face.verts] for face in bm.faces])
  ws=[normal_weights({names[i]:value for i,value in v[deform].items()}) for v in bm.verts]
  boundary=[(edge.link_loops[0].vert.index,edge.link_loops[0].link_loop_next.vert.index) for edge in bm.edges if edge.is_boundary]
  bm.free();count=len(p);start=len(d['positions']);n=surface_normals(p,f)
  distance_to_wrist=-(p-w)@lower
  clearance=.24+.31*smooth(distance_to_wrist/6.)
  # One correspondence for every inner/outer vertex, including plane-cut edges.
  d['positions'].extend((p+n*clearance[:,None]).tolist())
  d['positions'].extend((p+n*(clearance-.20)[:,None]).tolist())
  d['weights'].extend(ws+copy.deepcopy(ws))
  # A common bend-plane radial basis and smoothly varying longitudinal axis
  # avoid the previous abrupt upperarm/forearm UV-frame switch at the elbow.
  seed=unit(np.cross(upper,lower))
  if np.linalg.norm(seed)<.5:
   seed=np.array([0.,1.,0.]);seed=unit(seed-upper*(seed@upper))
  longitudinal=(p-e)@lower;blend=smooth((longitudinal+4.)/8.)
  axis=(1-blend[:,None])*upper+blend[:,None]*lower
  axis/=np.linalg.norm(axis,axis=1)[:,None]
  cross=np.cross(axis,seed);q=p-e
  angle=np.arctan2(np.einsum('ij,ij->i',q,cross),q@seed)/(2*math.pi)
  along=upper_length+np.einsum('ij,ij->i',q,axis)
  uv=np.column_stack([angle,along/25.])
  for face in f.tolist():
   coords=uv[face].copy()
   if np.ptp(coords[:,0])>.5:coords[coords[:,0]<0,0]+=1
   coords[:,0]*=1.5
   cuff=float(distance_to_wrist[face].mean())<7.
   d['triangles'].append([i+start for i in face]);d['uv'].append(coords.tolist());d['triangle_materials'].append(1 if cuff else 0)
   d['triangles'].append([i+start+count for i in face[::-1]]);d['uv'].append(coords[::-1].tolist());d['triangle_materials'].append(2)
  # Annulus only: no polygon spans the shoulder or wrist opening.
  for i,j in boundary:
   ids=[j+start,i+start,i+start+count,j+start+count]
   length=float(np.linalg.norm(p[i]-p[j]));coords=[[0,0],[length/25,0],[length/25,.20/25],[0,.20/25]]
   for ix in ((0,1,2),(0,2,3)):
    d['triangles'].append([ids[k] for k in ix]);d['uv'].append([coords[k] for k in ix]);d['triangle_materials'].append(1)
  report['arms'][side]=dict(native_faces=len(faces),surface_vertices=count,surface_faces=len(f),thickness_boundary_edges=len(boundary),upper_length_cm=upper_length,lower_length_cm=lower_length)
 p=np.array(d['positions']);f=np.array(d['triangles']);d['normals']=surface_normals(p,f)[f].tolist()
 write(R/'Authored'/(profile+'.json'),d)
 report.update(vertices=len(p),triangles=len(f),paired_weights=True)
 print('NATIVE_SLEEVE_AUTHORED',profile,len(p),len(f),list(report['arms']),flush=True)
 return report

if __name__=='__main__':
 profiles=[p for p in read(R/'before.json')['recipe']['rig_meshes'] if p!='Body']
 reports={profile:build(profile) for profile in profiles}
 write(R/'authoring.json',reports)
