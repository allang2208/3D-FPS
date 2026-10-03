"""Requested continuous source review and arm/weapon surface intersections."""
import bpy,json,ast,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;out=O/'Review'/'Sequence';out.mkdir(exist_ok=True)
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
family=next((v for v in sys.argv if v in ['vertical','canted','prism','angled']),'base')
info=json.loads((O/'authoring.json').read_text())[family+'/reload_empty'];bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions[info['action']];s=bpy.context.scene;arms=bpy.data.objects['SK_Manny_Arms_Export']
group_ids={g.index for g in arms.vertex_groups if g.name.endswith('_r') and g.name.startswith(('clavicle','upperarm','lowerarm'))}
arm_ids={v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if g.group in group_ids)/max(1e-8,sum(g.weight for g in v.groups))>.90}
arm_faces=[(p.vertices[0],p.vertices[i],p.vertices[i+1]) for p in arms.data.polygons if all(v in arm_ids for v in p.vertices) for i in range(1,len(p.vertices)-1)]
def narrow_hits(av,af,bv,bf,pairs):
 if not pairs:return 0
 pairs=np.array(pairs);ta=np.array(av)[np.array(af)[pairs[:,0]]];tb=np.array(bv)[np.array(bf)[pairs[:,1]]];hit=np.zeros(len(pairs),dtype=bool)
 for one,two in [(ta,tb),(tb,ta)]:
  e1=two[:,1]-two[:,0];e2=two[:,2]-two[:,0]
  for i in range(3):
   start=one[:,i];direction=one[:,(i+1)%3]-start;h=np.cross(direction,e2);det=np.sum(e1*h,axis=1);valid=np.abs(det)>1e-12;inv=np.zeros(len(det));inv[valid]=1/det[valid]
   s=start-two[:,0];u=np.sum(s*h,axis=1)*inv;q=np.cross(s,e1);v=np.sum(direction*q,axis=1)*inv;t=np.sum(e2*q,axis=1)*inv
   hit|=valid&(u>1e-5)&(v>1e-5)&(u+v<1-1e-5)&(t>1e-5)&(t<1-1e-5)
 return int(hit.sum())
parts=[o for o in s.objects if o.type=='MESH' and o.name in ['SM_SVD_Body','SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_Magazine']]
for ob in s.objects:
 if ob.type=='MESH':
  ob.hide_render=not any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers);ob.color=(.55,.63,.70,1) if ob==arms else (.20,.23,.27,1)
cam=bpy.data.objects.new('SequenceCamera',bpy.data.cameras.new('SequenceCamera'));s.collection.objects.link(cam);s.camera=cam;cam.location=(0,-.1,.05);cam.rotation_euler=(math.pi/2,0,0)
cam.data.clip_start=.005;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)))
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_backface_culling=True;s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD'
if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
s.world.color=(.055,.065,.08);s.render.resolution_x=640;s.render.resolution_y=360;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
report={};review_frames=list(range(220,516,4))+[515]
for f in review_frames:
 sample(r,a,f);dg=bpy.context.evaluated_depsgraph_get();ev=arms.evaluated_get(dg);vertices=[ev.matrix_world@v.co for v in ev.data.vertices]
 arm=BVHTree.FromPolygons(vertices,arm_faces,all_triangles=True);row={}
 for ob in parts:
  ev=ob.evaluated_get(dg);bv=[ev.matrix_world@v.co for v in ev.data.vertices];bf=[(p.vertices[0],p.vertices[i],p.vertices[i+1]) for p in ev.data.polygons for i in range(1,len(p.vertices)-1)]
  b=BVHTree.FromPolygons(bv,bf,all_triangles=True);hits=arm.overlap(b);confirmed=narrow_hits(vertices,arm_faces,bv,bf,hits)
  if confirmed:row[ob.name]=confirmed
 if row:report[str(f)]=row
 if '--geometry-only' not in sys.argv:s.render.filepath=str(out/f'frame_{f:03}.png');bpy.ops.render.render(write_still=True)
(O/('arm_weapon_intersections'+('' if family=='base' else '_'+family)+'.json')).write_text(json.dumps({'family':family,'frames':review_frames,'sample_step_frames':4,'threshold_right_arm_weight':.9,'intersections':report,'method':'BVH broad phase plus strict segment/triangle narrow phase, actual evaluated surfaces; excludes intentional hand/handle contact.'},indent=2))
print('SVD_GRASP_SEQUENCE',family,len(review_frames),'intersection_frames',len(report),json.dumps(report),flush=True)
