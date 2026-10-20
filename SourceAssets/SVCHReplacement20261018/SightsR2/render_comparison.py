"""Same camera and lighting for the requested local sight review."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;B=O.parent
receipt=json.loads((O/'authoring_receipt.json').read_text());eye={k:Vector((p[0]/100,-p[1]/100,p[2]/100)) for k,p in receipt['landmarks_component_cm'].items() if k in ('RearSight','FrontSight')}
for revision,file in [('before',B/'SVCH_Replacement_Editable.blend'),('after',O/'SVCH_SightsR2_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);sc=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';rig.animation_data_clear()
 for ob in list(sc.objects):
  if ob.type in ('LIGHT','CAMERA') or ob.name=='SVCH_BareArmsV9':bpy.data.objects.remove(ob,do_unlink=True)
 sc.render.engine='CYCLES';sc.cycles.samples=64;sc.cycles.use_denoising=True;sc.render.resolution_x=1300;sc.render.resolution_y=1050;sc.render.resolution_percentage=100;sc.render.film_transparent=False
 world=bpy.data.worlds.new('SightStudio');world.use_nodes=True;world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.025,.032,.045,1);bg.inputs[1].default_value=.65;sc.world=world
 cam=bpy.data.objects.new('SightCamera',bpy.data.cameras.new('SightCamera'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.data.lens=65
 lights=[]
 for name,offset,power,size in [('Key',(.25,-.15,.40),12,.3),('Fill',(-.20,-.05,.15),7,.25),('Rim',(-.12,.25,.25),14,.22)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);lights.append((o,Vector(offset)))
 for label,key in [('rear','RearSight'),('front','FrontSight'),('assembly','RearSight')]:
  center=eye[key]-Vector((0,0,.015))
  if label=='assembly':center=(eye['RearSight']+eye['FrontSight'])/2-Vector((0,0,.015))
  cam.location=center+Vector((.11,-.14,.075) if label!='assembly' else (.32,-.38,.30));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.105 if label!='assembly' else .63
  for light,offset in lights:light.location=center+offset;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
  sc.render.filepath=str(O/(revision+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('SIGHT_COMPARISON_RENDERED',flush=True)
