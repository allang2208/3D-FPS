"""Repair palm topology in place, retaining each file's rig, actions and modifiers."""
import bpy,json,sys,shutil
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent;P=R.parents[1];sys.path.insert(0,str(R))
from plan_repair import make_plan,triangulate_for_patch
bpy.context.preferences.filepaths.save_version=0
files=list((P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable').glob('*.blend'))
files+=list((P/'SourceAssets/SteelWarhammer20261014').rglob('*.blend'))
report=[]
for file in files:
 if '/Original/' in file.as_posix():continue
 bpy.ops.wm.open_mainfile(filepath=str(file));changes=[]
 for obj in list(bpy.context.scene.objects):
  if obj.type!='MESH' or not any(g.name=='hand_r' or g.name=='hand_l' for g in obj.vertex_groups):continue
  mesh=obj.data
  if mesh.shape_keys:raise RuntimeError('Preserve shape keys: '+str(file))
  mesh.calc_loop_triangles();names={g.index:g.name for g in obj.vertex_groups}
  weights=[{names[g.group]:g.weight for g in v.groups} for v in mesh.vertices]
  tris=list(mesh.loop_triangles);normals=[tuple(n.vector) for n in mesh.corner_normals]
  if any(len(p.vertices)!=3 for p in mesh.polygons):raise RuntimeError('Unexpected non-triangular palm source')
  layers={l.name:[[tuple(l.data[li].uv) for li in t.loops] for t in tris] for l in mesh.uv_layers}
  base_uv=next(iter(layers.values()))
  d=dict(path=str(file),positions=[list(v.co*100) for v in mesh.vertices],triangles=[list(t.vertices) for t in tris],
   normals=[[normals[li] for li in t.loops] for t in tris],uv=[[[x,1-y] for x,y in uv] for uv in base_uv],
   triangle_materials=[t.material_index for t in tris],weights=weights,
   materials=[dict(slot=m.name,path='Bare') for m in mesh.materials])
  plans,before=make_plan(d)
  if not plans:continue
  removed={i for p in plans for i in p['remove']};keep=[i for i in range(len(tris)) if i not in removed]
  vertices=[tuple(v.co) for v in mesh.vertices];faces=[list(tris[i].vertices) for i in keep]
  outnorm=[d['normals'][i] for i in keep];outmat=[d['triangle_materials'][i] for i in keep]
  outuv={k:[rows[i] for i in keep] for k,rows in layers.items()}
  colors={}
  for ca in mesh.color_attributes:
   if ca.domain=='CORNER':colors[ca.name]=dict(type=ca.data_type,rows=[[tuple(ca.data[li].color) for li in t.loops] for t in tris])
  outcolors={k:[v['rows'][i] for i in keep] for k,v in colors.items()}
  for patch in plans:
   for triangle in triangulate_for_patch(d,patch):
    corners=[patch['corners'][i] for i in triangle]
    faces.append([d['triangles'][c['triangle']][c['a']] for c in corners])
    outnorm.append([d['normals'][c['triangle']][c['a']] for c in corners]);outmat.append(patch['material'])
    for k,rows in layers.items():outuv[k].append([rows[c['triangle']][c['a']] for c in corners])
    for k,v in colors.items():outcolors[k].append([v['rows'][c['triangle']][c['a']] for c in corners])
  rebuilt=bpy.data.meshes.new(mesh.name+'_PalmClosed20261014');rebuilt.from_pydata(vertices,[],faces);rebuilt.update()
  for mat in mesh.materials:rebuilt.materials.append(mat)
  for poly,mat in zip(rebuilt.polygons,outmat):poly.material_index=mat;poly.use_smooth=True
  for k,rows in outuv.items():
   layer=rebuilt.uv_layers.new(name=k)
   for poly,row in zip(rebuilt.polygons,rows):
    for li,uv in zip(poly.loop_indices,row):layer.data[li].uv=uv
  for k,rows in outcolors.items():
   layer=rebuilt.color_attributes.new(name=k,type=colors[k]['type'],domain='CORNER')
   for poly,row in zip(rebuilt.polygons,rows):
    for li,color in zip(poly.loop_indices,row):layer.data[li].color=color
  rebuilt.normals_split_custom_set([n for row in outnorm for n in row]);obj.data=rebuilt
  for name in names.values():
   if name not in obj.vertex_groups:obj.vertex_groups.new(name=name)
  for vi,ws in enumerate(weights):
   for name,w in ws.items():obj.vertex_groups[name].add([vi],w,'REPLACE')
  changes.append(dict(object=obj.name,patches=len(plans),removed=len(removed),added=len(faces)-len(keep),method='concave perimeter triangulation'))
 if changes:
  backup=R/'Before'/file.relative_to(P);backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(file,backup)
  bpy.ops.wm.save_as_mainfile(filepath=str(file))
  report.append(dict(path=str(file),changes=changes))
  (R/'blends_repaired.json').write_text(json.dumps(report,indent=2))
  print('PALM_BLEND_REPAIRED',str(file),changes,flush=True)
print('PALM_BLEND_REPAIR_COMPLETE',len(report),flush=True)
