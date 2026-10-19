import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/StaffLivingShoulder20261017')
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets')
report={}
for role,file in [('FemaleA',ROOT/'FacelessReceptionist20261007/V04/Delivery/SK_FacelessReceptionist_Body_V04.fbx'),('FemaleB',ROOT/'FacelessResearcher20261009/V01/Delivery/SK_FacelessResearcher_Body_V01.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(file),use_anim=False)
 mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
 coords=[mesh.matrix_world@v.co for v in mesh.data.vertices]
 bm=bmesh.new();bm.from_mesh(mesh.data)
 for v in bm.verts:v.co=mesh.matrix_world@v.co
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005)
 bm.verts.ensure_lookup_table();bm.verts.index_update()
 adj={}
 for e in bm.edges:
  if e.is_boundary:
   a,b=e.verts;adj.setdefault(a.index,[]).append(b.index);adj.setdefault(b.index,[]).append(a.index)
 unseen=set(adj);loops=[]
 while unseen:
  todo=[unseen.pop()];ids=[]
  while todo:
   v=todo.pop();ids.append(v)
   for n in adj[v]:
    if n in unseen:unseen.remove(n);todo.append(n)
  pp=[bm.verts[i].co for i in ids];center=sum(pp,Vector())/len(pp)
  loops.append({'vertices':len(ids),'center':list(center),'min':[min(p[d] for p in pp) for d in range(3)],'max':[max(p[d] for p in pp) for d in range(3)],'degrees':sorted(set(len(adj[i]) for i in ids))})
 loops.sort(key=lambda x:-x['vertices'])
 report[role]={'source':str(file),'object':mesh.name,'vertices':len(mesh.data.vertices),'faces':len(mesh.data.polygons),'world_bounds':[[min(p[d] for p in coords) for d in range(3)],[max(p[d] for p in coords) for d in range(3)]],'boundary_components':loops,'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),'materials':[m.name if m else None for m in mesh.data.materials]}
 bm.free()
 # Single reference-pose diagnostic image. No game or animation acceptance.
 sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100
 sc.world=bpy.data.worlds.new('DiagnosticWorld')
 sh=sc.display.shading;sh.light='STUDIO';sh.color_type='SINGLE';sh.single_color=(.65,.68,.72);sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=False;sh.show_backface_culling=True
 sh.background_type='WORLD';sc.world.color=(.035,.035,.035)
 camdata=bpy.data.cameras.new('Diagnostic');cam=bpy.data.objects.new('Diagnostic',camdata);sc.collection.objects.link(cam);sc.camera=cam
 camdata.type='ORTHO';camdata.ortho_scale=1.35
 center=Vector((0,0,1.45))
 for view,pos in [('front',(0,-3,1.6)),('back',(0,3,1.6))]:
  cam.location=pos;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
  sc.render.filepath=str(OUT/'Diagnosis'/f'{role}_{view}.png');bpy.ops.render.render(write_still=True)
(OUT/'Diagnosis/source_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHOULDER_DIAG',json.dumps(report),flush=True)
