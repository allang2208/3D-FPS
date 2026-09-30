import bpy,json,gzip,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent/'Inspection'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20
sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Inspection');sc.world.color=(.22,.22,.22)
mats={}
for role,col,metal,rough in [('Case',(.48,.315,.105),.98,.31),('Copper',(.46,.19,.09),.98,.30),('Link',(.09,.105,.115),.93,.40),('Cloth',(.08,.09,.055),0,.87),('Glove',(.055,.045,.035),0,.75),('Body',(.045,.054,.064),.8,.4)]:
 m=bpy.data.materials.new(role);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;mats[role]=m
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,power in [((.22,.02,.24),16),((-.15,.12,.15),10),((.07,.33,.14),8)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=.18;aim(o,(.025,.13,.01))
bpy.ops.object.camera_add(location=(.245,-.025,.115));cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.235;aim(cam,(.01,.13,.005))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['before_209','after_209','after_458','after_526','after_574']
for name in args:
 for o in list(bpy.data.objects):
  if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
 with gzip.open(O/(name+'.json.gz'),'rt') as f:parts=json.load(f)
 for row in parts:
  me=bpy.data.meshes.new(row['role']);me.from_pydata(row['p'],[],row['t']);me.update();ob=bpy.data.objects.new(row['role'],me);bpy.context.collection.objects.link(ob);me.materials.append(mats[row['role']])
  for p in me.polygons:p.use_smooth=row['role'] in ['Case','Copper','Cloth','Glove']
 sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
 print('B53_RENDER',name,flush=True)
