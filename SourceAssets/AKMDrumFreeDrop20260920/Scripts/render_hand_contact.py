"""Actual skinned hand/drum close-ups, isolated in magazine space for pose review."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]);out=Path(args[1]);out.mkdir(exist_ok=True,parents=True)
frame=int(args[2]) if len(args)>2 else 178
bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;s.frame_set(frame)
for layer in s.view_layers:layer.material_override=None
r=bpy.data.objects['SK_M4_Infima'];skin=bpy.data.objects['SK_Manny_Arms_Export']
mag=r.matrix_world@r.pose.bones['WPN_SOCKET_Magazine'].matrix
to_mag=mag.inverted()@skin.matrix_world
gn={g.index:g.name for g in skin.vertex_groups}
selected=set();ownership={}
for v in skin.data.vertices:
 w=sum(g.weight for g in v.groups if gn[g.group].endswith('_l') and gn[g.group].startswith(('hand','index','middle','ring','pinky','thumb')))
 if w>.80:
  selected.add(v.index);ownership[v.index]=gn[max(v.groups,key=lambda g:g.weight).group].split('_')[0]
dg=bpy.context.evaluated_depsgraph_get();ev=skin.evaluated_get(dg);mesh=ev.to_mesh()
verts=[tuple(to_mag@v.co) for v in mesh.vertices]
faces=[tuple(p.vertices) for p in mesh.polygons if all(i in selected for i in p.vertices)]
ev.to_mesh_clear()
joints={n:list(mag.inverted()@r.matrix_world@r.pose.bones[n].matrix.translation) for n in r.pose.bones.keys() if n.endswith('_l') and n.startswith(('hand','index','middle','ring','pinky','thumb'))}
(out/'joints.json').write_text(json.dumps(joints,indent=2))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
s=bpy.data.scenes.new('IsolatedHandContactReview');bpy.context.window.scene=s
hm=bpy.data.meshes.new('EvaluatedHand');hm.from_pydata(verts,[],faces);hm.update()
hand=bpy.data.objects.new('EvaluatedHand',hm);s.collection.objects.link(hand)
for p in hm.polygons:p.use_smooth=True
def material(name,color,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 node=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=rough
 return m
hand.data.materials.clear();hand.data.materials.append(material('HandPoseReviewClay',(.38,.48,.59),.65))
with bpy.data.libraries.load(str(O.parent/'LargeDrumUpgrade20260920/AKM/Drum_Integrated.blend'),link=False) as (src,dst):dst.objects=['SM_AKM_LargeDrum_Upgrade']
drum=dst.objects[0];drum.matrix_world=Matrix.Identity(4);s.collection.objects.link(drum)
bvh=BVHTree.FromPolygons([v.co.copy() for v in drum.data.vertices],[tuple(p.vertices) for p in drum.data.polygons])
measure={}
for label in ['hand','index','middle','ring','pinky','thumb']:
 points=[]
 # All deformed hand vertices are in the same magazine-space coordinates.
 # Per-digit ownership was retained from the original, unmodified skin.
 for i in selected:
  if ownership.get(i)!=label:continue
  p=Vector(verts[i]);hit,n,_,d=bvh.find_nearest(p)
  if hit is not None:points.append((p-hit).dot(n))
 if points:
  points.sort();measure[label]={'min_signed_surface_m':points[0],'max_signed_surface_m':points[-1],'vertices_deeper_than_2mm':sum(v<-.002 for v in points),'vertices_within_3mm':sum(abs(v)<.003 for v in points)}
(out/'contact_distances.json').write_text(json.dumps(measure,indent=2))
drum.data.materials.clear();drum.data.materials.append(material('DrumPoseReviewClay',(.075,.082,.09),.47))
for p in drum.data.polygons:p.material_index=0
world=bpy.data.worlds.new('ContactReviewWorld');s.world=world;world.use_nodes=True
background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs[0].default_value=(.14,.17,.21,1);background.inputs[1].default_value=.55
target=Vector((0,0,-.078))
for name,pos,power,size in [('Key',(.28,-.30,.35),35,.35),('Fill',(-.3,-.15,.06),20,.3),('Rim',(.1,.28,.18),45,.3),('Under',(-.1,-.1,-.4),12,.3)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
 ob=bpy.data.objects.new(name,ld);s.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.245
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=8
s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100
s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=90;s.render.film_transparent=False
s.render.use_compositing=False;s.render.use_sequencer=False;s.view_settings.view_transform='AgX';s.view_settings.exposure=0;s.view_settings.gamma=1
views=[('front',(.28,-.40,-.19)),('back',(-.28,.32,-.12)),('underside',(.16,-.35,-.36))]
for name,pos in views:
 cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/(name+'.jpg'));bpy.ops.render.render(write_still=True)
print('HAND_CONTACT_RENDER_COMPLETE '+str(out),flush=True)
