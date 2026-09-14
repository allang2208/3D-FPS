import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector

def open_source(path):
 try:bpy.ops.wm.open_mainfile(filepath=str(path))
 except RuntimeError:
  if Path(bpy.data.filepath)!=Path(path):raise
 bpy.context.preferences.filepaths.save_version=0

def level_frame(rig):
 rear=rig.matrix_world@rig.data.bones['WPN_RearSight'].matrix_local
 front=rig.matrix_world@rig.data.bones['WPN_FrontSight'].matrix_local
 up=rear.to_3x3().col[2].normalized()
 forward=front.translation-rear.translation;forward-=up*forward.dot(up);forward.normalize()
 x=-forward;y=up.cross(x).normalized();z=x.cross(y).normalized()
 return Matrix(((*x,0),(*y,0),(*z,0),(0,0,0,1)))

def components(me):
 adjacent=[[] for v in me.vertices]
 for edge in me.edges:
  a,b=edge.vertices;adjacent[a].append(b);adjacent[b].append(a)
 unseen=set(range(len(adjacent)));groups=[]
 while unseen:
  seed=unseen.pop();g={seed};stack=[seed]
  while stack:
   for v in adjacent[stack.pop()]:
    if v in unseen:unseen.remove(v);g.add(v);stack.append(v)
  groups.append(g)
 return sorted(groups,key=lambda g:(-len(g),min(g)))

def filter_mesh(me,selector):
 if not selector:return
 if 'material' in selector:
  names=selector['material'];ids={i for i,m in enumerate(me.materials) if m and any(s in m.name for s in names)}
  keep={v for p in me.polygons if p.material_index in ids for v in p.vertices}
 elif 'ids_file' in selector:
  records=json.loads(Path(selector['ids_file']).read_text());keep=set().union(*(set(records[i]['ids']) for i in selector['components']))
 elif 'components' in selector:
  groups=components(me);keep=set().union(*(groups[i] for i in selector['components']))
 else:raise ValueError(selector)
 bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS');bm.to_mesh(me);bm.free();me.update()
