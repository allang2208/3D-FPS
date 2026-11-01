"""Actual triangle surfaces and local winding, separate from broad phase hulls."""
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'fit_clearance.py').read_text().split("report={'metric'")[0],'surface_setup','exec'))
from mathutils.bvhtree import BVHTree
surfaces=[]
for name,bone,_,_ in hulls:
 ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bm.verts.ensure_lookup_table();bm.verts.index_update();v=np.array([list(v.co) for v in bm.verts]);faces=[tuple(x.index for x in f.verts) for f in bm.faces]
 bvh=BVHTree.FromPolygons(v.tolist(),faces,all_triangles=True);tri=v[np.array(faces)];bm.free()
 surfaces.append({'name':name,'bone':bone,'bvh':bvh,'tri':tri,'min':v.min(0),'max':v.max(0)})

def winding(P,T):
 result=[]
 for k in range(0,len(P),64):
  a=T[None,:,0,:]-P[k:k+64,None,:];b=T[None,:,1,:]-P[k:k+64,None,:];c=T[None,:,2,:]-P[k:k+64,None,:]
  la=np.linalg.norm(a,axis=2);lb=np.linalg.norm(b,axis=2);lc=np.linalg.norm(c,axis=2)
  num=np.einsum('pfi,pfi->pf',a,np.cross(b,c))
  den=la*lb*lc+np.einsum('pfi,pfi->pf',a,b)*lc+np.einsum('pfi,pfi->pf',b,c)*la+np.einsum('pfi,pfi->pf',c,a)*lb
  result.extend(np.arctan2(num,den).sum(1)/(2*np.pi))
 return np.abs(result)

def actual(row,P,full_winding=False,subset=None):
 result={}
 for part in surfaces:
  if subset and part['name'] not in subset:continue
  bone=part['bone'];inv=np.array(rest[bone]@row[bone].inverted());Q=P@inv[:3,:3].T+inv[:3,3]
  mask=np.all((Q>part['min']-.008)&(Q<part['max']+.008),axis=1)
  if part['name']=='M24_bolt':mask[:]=True
  ix=np.where(mask)[0];signed=np.full(len(P),.1);nearest=[]
  for i in ix:
   v,n,_,d=part['bvh'].find_nearest(Vector(Q[i]))
   signed[i]=d if (Vector(Q[i])-v).dot(n)>=0 else -d
  if full_winding and len(ix):
   inside=winding(Q[ix],part['tri'])>.5;signed[ix]=np.abs(signed[ix])*np.where(inside,-1,1)
  result[part['name']]=signed
 return result

if __name__=='__main__':
 report={}
 for f in (12,16,19,24,29,34,39,43,48):
  row=clips['fire'][f];P=points(row);result=actual(row,P[::3],True);dom=dominant[::3]
  report[str(f)]={n:{'penetration_mm':float(max(0,-d.min())*1000),'points':int((d<-.001).sum()),'bones':sorted(set(names[x] for x in dom[d<-.003]))} for n,d in result.items() if d.min()<-.0003}
  print('SURFACE',f,report[str(f)],flush=True)
 (O/'surface_before.json').write_text(json.dumps(report,indent=2))
