import bpy,bmesh,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ThorSeatsPrecisionV4.blend'))
src=bpy.data.objects['SM_ThunderGodHammer_head_mount_factory'].data
def count(m):
 m.calc_tangents(uvmap=m.uv_layers[0].name)
 bad=[f.index for f in m.polygons if any(m.loops[i].tangent.length<1e-4 or m.loops[i].bitangent.length<1e-4 for i in f.loop_indices)]
 return bad
original=count(src)
for mode in ['planar_caps']:
 m=src.copy()
 if mode=='planar_caps':
  ns=[tuple(n.vector) for n in m.corner_normals];uv=m.uv_layers[0]
  cap_count=0
  for f in m.polygons:
   coords=[m.vertices[i].co for i in f.vertices];axis=None
   if all(abs(v.z-.842)<2e-7 for v in coords):axis=2;n=(0,0,-1)
   elif all(abs(v.x-(-.0004452141001820564-.065))<2e-7 for v in coords):axis=0;n=(-1,0,0)
   elif all(abs(v.x-(-.0004452141001820564+.065))<2e-7 for v in coords):axis=0;n=(1,0,0)
   if axis is None:continue
   cap_count+=1
   for li in f.loop_indices:
    ns[li]=n;v=m.vertices[m.loops[li].vertex_index].co
    uv.data[li].uv=(.5+v.x*4,.5+v.y*4) if axis==2 else (.5+v.y*4,.5+(v.z-.91)*4)
  m.normals_split_custom_set(ns)
  print('CAP_COUNT',cap_count,flush=True)
 elif mode=='split_bad_edges':
  for iteration in range(8):
   bad=count(m)
   if not bad:break
   bm=bmesh.new();bm.from_mesh(m);bm.faces.ensure_lookup_table()
   edges=list({max(bm.faces[fi].edges,key=lambda e:e.calc_length()) for fi in bad})
   res=bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
   bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3],quad_method='BEAUTY',ngon_method='BEAUTY')
   bm.to_mesh(m);bm.free();m.update()
   print('SPLIT',iteration,len(bad),flush=True)
 elif mode=='flat_normals':
  ns=[tuple(n.vector) for n in m.corner_normals]
  for fi in original:
   for li in m.polygons[fi].loop_indices:ns[li]=(0,0,-1)
  m.normals_split_custom_set(ns)
 elif mode in ['beautify','dissolve_cap']:
  bm=bmesh.new();bm.from_mesh(m)
  cap=[f for f in bm.faces if all(abs(v.co.z-.842)<2e-7 for v in f.verts)]
  edges=list({e for f in cap for e in f.edges if len(e.link_faces)==2 and all(g in cap for g in e.link_faces)})
  if mode=='beautify':bmesh.ops.beautify_fill(bm,faces=cap,edges=edges,use_restrict_tag=False,method='AREA')
  else:
   result=bmesh.ops.dissolve_faces(bm,faces=cap,use_verts=False)
   bmesh.ops.triangulate(bm,faces=result['region'],quad_method='BEAUTY',ngon_method='BEAUTY')
  bm.to_mesh(m);bm.free()
 m.update();bad=count(m)
 print('CAP_MODE',mode,'bad',len(bad),'faces',len(m.polygons),flush=True)
 if mode=='original':
  print('BAD_CORNERS',json.dumps([dict(face=i,corners=[dict(normal=list(m.corner_normals[li].vector),tangent=list(m.loops[li].tangent),bitangent=list(m.loops[li].bitangent),sign=m.loops[li].bitangent_sign) for li in m.polygons[i].loop_indices]) for i in bad]),flush=True)
