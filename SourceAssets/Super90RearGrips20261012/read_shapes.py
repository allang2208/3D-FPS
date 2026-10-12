import bpy,json
from pathlib import Path
from mathutils import Matrix
from collections import Counter
O=Path(__file__).parent;I=O/'Inputs';out={}
for key in ['super90','phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(I/(key+'.fbx')),use_anim=False)
 row={'meshes':[],'bones':{}};out[key]=row
 for ob in list(bpy.context.scene.objects):
  if ob.type=='ARMATURE':
   for b in ob.data.bones:
    if b.name in ['WPN_root','hand_r','index_01_r','pinky_01_r','WPN_Trigger','WPN_RearSight','WPN_FrontSight']:row['bones'][b.name]=[list(v) for v in ob.matrix_world@b.matrix_local]
  if ob.type!='MESH':continue
  xyz=[ob.matrix_world@v.co for v in ob.data.vertices];parent=list(range(len(xyz)))
  def root(a):
   while a!=parent[a]:parent[a]=parent[parent[a]];a=parent[a]
   return a
  # Weld import seams only for identifying connected manufacturing parts.
  cells={}
  for i,p in enumerate(xyz):
   k=tuple(round(x,6) for x in p)
   if k in cells:parent[root(i)]=root(cells[k])
   else:cells[k]=i
  for f in ob.data.polygons:
   for v in f.vertices[1:]:parent[root(v)]=root(f.vertices[0])
  islands={}
  for f in ob.data.polygons:islands.setdefault(root(f.vertices[0]),[]).append(f)
  groups=[]
  for fs in islands.values():
   if len(fs)<12:continue
   ids={i for f in fs for i in f.vertices};pos=[xyz[i] for i in ids]
   mats=Counter(ob.data.materials[f.material_index].name for f in fs)
   if any('Skin' in k for k in mats):continue
   groups.append({'faces':len(fs),'materials':dict(mats),'bounds':[[min(p[j] for p in pos) for j in range(3)],[max(p[j] for p in pos) for j in range(3)]],'faces_first':fs[0].index})
  row['meshes'].append({'name':ob.name,'slots':[m.name for m in ob.data.materials],'bounds':[[min(p[j] for p in xyz) for j in range(3)],[max(p[j] for p in xyz) for j in range(3)]],'islands':sorted(groups,key=lambda g:-g['faces'])})
(O/'source_shapes.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('REARGRIP_SOURCES_READ')
