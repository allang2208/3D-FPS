"""Narrow QR housing/receiver investigation requested by the user."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).parent
stage=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Before'
out=R/'Diagnosis20260913'/stage;out.mkdir(parents=True,exist_ok=True)
report={}
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for key,origin in [('M4',(0,3.85,7.25)),('AKM',(.08,8.3,3.5))]:
 source=(out/key if stage=='Before' else R/key)/'QRStock_Refined_Parts.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
 own=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
 housing=bpy.data.objects['Rounded_cheek_housing'];mesh=housing.data
 planar=[]
 for p in mesh.polygons:
  if abs(p.normal.y)>.999 and p.area>.02:
   angles=[math.degrees(p.normal.angle(mesh.corner_normals[i].vector)) for i in p.loop_indices]
   planar.append(max(angles))
 report[key]={'housing_material':[m.name for m in mesh.materials], 'planar_side_max_corner_normal_degrees':max(planar,default=0),'planar_faces_above_5_degrees':sum(a>5 for a in planar)}
 inv=(Matrix.Translation(origin)@Matrix.Rotation(math.pi/2,4,'Z')).inverted()
 ref=R.parent.parent/'SkeletonStock20260912'/(key.lower()+'_fit_reference.blend')
 with bpy.data.libraries.load(str(ref),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('FIT_')]
 gun=[]
 for o in b.objects:
  scene.collection.objects.link(o);o.matrix_world=inv@o.matrix_world
  if not o.hide_render:gun.append(o)
 def tree(o):
  o.data.calc_loop_triangles()
  return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
 crossings=[]
 mount_parts=[housing,bpy.data.objects['Retopologized_QR_frame'],bpy.data.objects['Front_metal_coupling']]
 if key=='AKM':mount_parts.append(bpy.data.objects['AKM_receiver_cover'])
 for part in mount_parts:
  ht=tree(part)
  for o in gun:
   overlaps=ht.overlap(tree(o))
   if overlaps:
    ids={j for i,j in overlaps};pts=[o.matrix_world@o.data.vertices[v].co for j in ids for v in o.data.loop_triangles[j].vertices]
    crossings.append({'stock_part':part.name,'gun_object':o.name,'triangle_pairs':len(overlaps),'gun_triangles_bbox_stock_cm':[[min(p[a] for p in pts) for a in range(3)],[max(p[a] for p in pts) for a in range(3)]]})
 report[key]['mount_gun_surface_crossings']=crossings
 scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
 scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.5
 world=bpy.data.worlds.new('Assembly_studio');world.use_nodes=True;scene.world=world;n=world.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');bg.inputs[0].default_value=(.20,.23,.27,1);bg.inputs[1].default_value=.65;op=n.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],op.inputs[0])
 target=(5,0,-3.4)
 for pos,power,size in [((-6,-19,24),33000,17),((25,-12,9),13000,14),((10,15,18),30000,11)]:
  d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.size=size;o=bpy.data.objects.new('Softbox',d);scene.collection.objects.link(o);o.location=pos;aim(o,target)
 d=bpy.data.cameras.new('Mount_preview');o=bpy.data.objects.new('Mount_preview',d);scene.collection.objects.link(o);d.type='ORTHO';d.ortho_scale=34;o.location=(-5,-40,12);aim(o,target);scene.camera=o
 scene.render.filepath=str(out/(key+'_Mount.png'));bpy.ops.render.render(write_still=True)
 print('QR_ASSEMBLY_DIAG',key,json.dumps(report[key]),flush=True)
(out/'housing_findings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
