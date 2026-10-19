"""Repair the selected model's actual shell boundaries; export UE clockwise faces."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from collections import Counter
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018'
for folder in ('Authoring','Textures','Preview','Reports','Receipts'):(O/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/Saiga12KDetail20261018/Authoring/Saiga12K_SurfaceRebuilt.blend'));bpy.context.preferences.filepaths.save_version=0
records=[]
def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def islands(bm):
 bm.verts.ensure_lookup_table();seen=set();out=[]
 for v in bm.verts:
  if v in seen:continue
  stack=[v];seen.add(v);vs=[]
  while stack:
   a=stack.pop();vs.append(a)
   for e in a.link_edges:
    b=e.other_vert(a)
    if b not in seen:seen.add(b);stack.append(b)
  out.append((vs,{e for v in vs for e in v.link_edges},{f for v in vs for f in v.link_faces}))
 return out
def annotation(vs,faces,me):
 names={me.materials[f.material_index].name for f in faces}
 if names=={'Saiga12K_LaserMark'}:return True
 q=np.array([v.co[:] for v in vs]);extent=np.ptp(q,axis=0)
 return len(faces)<110 and min(extent)<.0001 and max(extent)<.7 and any('Magazine' in x for x in names)
def bands(part):
 out=[];mat=bpy.data.materials['Saiga12K_'+part]
 for side in (-1,1):
  for z in (-.20,.48,1.16):
   bpy.ops.mesh.primitive_cube_add(size=1,location=(.08+side*1.075,-12.12,z));a=bpy.context.object;a.name='Closed molded magazine throat band';a.dimensions=(.13,7.18,.22);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);a.data.materials.append(mat)
   mod=a.modifiers.new('Molded radius','BEVEL');mod.width=.035;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
   for f in a.data.polygons:f.use_smooth=True
   wn=a.modifiers.new('Manufactured normals','WEIGHTED_NORMAL');wn.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=wn.name);out.append(a)
 return out
def stitch_t_junctions(bm):
 for _ in range(3):
  edges=[e for e in bm.edges if e.is_boundary];vertices={v for e in edges for v in e.verts};changed=False
  for e in edges:
   if not e.is_valid:continue
   a,b=e.verts;delta=b.co-a.co;length=delta.length_squared
   if length<1e-12:continue
   for v in vertices:
    if not v.is_valid or v in e.verts:continue
    t=(v.co-a.co).dot(delta)/length
    if .00001<t<.99999 and (v.co-a.co-delta*t).length<.00001:
     _,nv=bmesh.utils.edge_split(e,a,t);bmesh.ops.weld_verts(bm,targetmap={nv:v});changed=True;break
  if not changed:break
for ob,key,part in [(bpy.data.objects['Saiga12K_SurfaceRebuilt'],'gun','Magazine'),(bpy.data.objects['Saiga12K_Ext12_SurfaceRebuilt'],'ext12','ExtMagazine')]:
 me=ob.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);stitch_t_junctions(bm);removed=0;filled=[]
 # The old two throat rib islands contain self-intersections. Replace those
 # exact islands with closed molded bands; preserve the seating throat itself.
 for vs,es,fs in islands(bm):
  names={me.materials[f.material_index].name for f in fs}
  if names=={'Saiga12K_'+part} and any(len(e.link_faces)>2 for e in es):
   removed+=len(fs);bmesh.ops.delete(bm,geom=list(vs),context='VERTS')
 for vs,es,fs in islands(bm):
  boundary=[e for e in es if e.is_boundary]
  if not boundary or annotation(vs,fs,me):continue
  mid=Counter(f.material_index for f in fs).most_common(1)[0][0]
  new=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
  for f in new:f.material_index=mid;f.smooth=True
  filled.append({'part':me.materials[mid].name,'boundary_edges':len(boundary),'new_faces':len(new)})
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle()>math.radians(50))
 bm.to_mesh(me);bm.free();select(ob)
 wn=ob.modifiers.new('Authored hard surface normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50;bpy.ops.object.modifier_apply(modifier=wn.name)
 extra=bands(part) if removed else []
 select(ob)
 for a in extra:a.select_set(True)
 if extra:bpy.ops.object.join()
 ob=bpy.context.object;me=ob.data;tri=ob.modifiers.new('Final triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
 bm=bmesh.new();bm.from_mesh(me);collapsed=0
 for f in list(bm.faces):
  if not f.is_valid or f.calc_area()>=1e-10:continue
  e=min(f.edges,key=lambda e:e.calc_length())
  if e.calc_length()>.0002:raise RuntimeError('Large degenerate patch requires local repair')
  bmesh.ops.pointmerge(bm,verts=list(e.verts),merge_co=sum((v.co for v in e.verts),Vector())/2);collapsed+=1
 if collapsed:
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me)
 bm.free()
 if collapsed:
  wn=ob.modifiers.new('Repaired submicron seam normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50;bpy.ops.object.modifier_apply(modifier=wn.name)
 # Every real shell must be closed. Intentional markings are separate thin
 # surfaces, and tube bores remain open passages bounded by their annular rims.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bad=[];decal_edges=0
 for vs,es,fs in islands(bm):
  n=sum(e.is_boundary for e in es);non=sum(len(e.link_faces)>2 for e in es)
  if annotation(vs,fs,me):decal_edges+=n;continue
  if n or non:bad.append({'parts':dict(Counter(me.materials[f.material_index].name for f in fs)),'boundary':n,'nonmanifold':non,'bounds':[[min(v.co[i] for v in vs) for i in range(3)],[max(v.co[i] for v in vs) for i in range(3)]]})
 bm.free()
 records.append({'key':key,'replaced_bad_rib_triangles':removed,'patches':filled,'collapsed_submicron_seams':collapsed,'remaining_structural_issues':bad,'intentional_marking_boundary_edges':decal_edges})
 if bad:
  (O/'Reports/closure-author.json').write_text(json.dumps(records,indent=2));raise RuntimeError('Unclosed structural shell: '+key)
 while me.uv_layers:me.uv_layers.remove(me.uv_layers[0])
 me.uv_layers.new(name='UV0');select(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.002,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT');uv=me.uv_layers['UV0']
 for f in me.polygons:
  ids=list(f.loop_indices);a,b,c=[uv.data[i].uv.copy() for i in ids]
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<2e-14:
   centre=(a+b+c)/3
   for i,delta in zip(ids,[(-.000002,-.000002),(.000002,-.000002),(0,.000002)]):uv.data[i].uv=centre+Vector(delta)
 me.uv_layers.new(name='UV1')
 for a,b in zip(uv.data,me.uv_layers['UV1'].data):b.uv=a.uv
 names=[m.name.removeprefix('Saiga12K_') for m in me.materials];payload={'positions':[[v.co.x,-v.co.y,v.co.z] for v in me.vertices],'triangles':[],'normals':[],'uv':[],'parts':[],'slot_names':names,'seated_root_cm':True,'ue_clockwise':True};areas={};uva={}
 for f in me.polygons:
  # Reflection Y is the handedness change. UE faces use clockwise winding,
  # so keep Blender corner order while reflecting positions and normals.
  ids=list(f.loop_indices);payload['triangles'].append([me.loops[i].vertex_index for i in ids]);payload['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in ids]);vals=[[float(uv.data[i].uv.x),1-float(uv.data[i].uv.y)] for i in ids];payload['uv'].append(vals);name=names[f.material_index];payload['parts'].append(name);areas[name]=areas.get(name,0)+f.area;a,b,c=np.array(vals);uva[name]=uva.get(name,0)+abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))*.5
 payload['uv_per_cm']={k:float(math.sqrt(uva[k]/a)) for k,a in areas.items()};(O/('Authoring/'+key+'.json')).write_text(json.dumps(payload,separators=(',',':')));records[-1]['triangles']=len(me.polygons)
bpy.data.objects['Saiga12K_Ext12_SurfaceRebuilt'].hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_ClosedShell.blend'),compress=True)
(O/'Reports/closure-author.json').write_text(json.dumps(records,indent=2));print('CLOSED_SHELLS_SAVED',[(r['key'],r['triangles']) for r in records])
