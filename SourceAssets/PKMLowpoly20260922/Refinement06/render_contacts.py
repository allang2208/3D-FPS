import bpy,pathlib,sys,json
from mathutils import Matrix,Vector
O=pathlib.Path(__file__).parent;R=O.parent
src=O/'PKM_Gameplay_Editable.blend'
if not src.exists():src=R/'Integration04/PKM_Gameplay_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig']
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
s.render.resolution_x=1000;s.render.resolution_y=800;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('PKM_ContactWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.19,.22,1)
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
def aim(o,t):o.rotation_euler=(t-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.lens=42
for label,pow,pos in [('Key',95,(.3,.15,.9)),('Fill',55,(-.7,.1,.4)),('Rim',65,(0,-.5,.6))]:
 o=bpy.data.objects.new(label,bpy.data.lights.new(label,'AREA'));s.collection.objects.link(o);o.location=pos;o.data.energy=pow;o.data.size=1.5;aim(o,Vector((0,.15,-.1)))
for clip,f,label in [('PKM_Game_idle',0,'idle'),('PKM_Reload_Normal',156,'box'),('PKM_Reload_Normal',282,'belt')]:
 a=bpy.data.actions[clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 W=r.pose.bones['WPN_root'].matrix@fit
 for o in s.objects:
  if o.type=='MESH':
   unwanted='mechanical_bone' not in o and o.name!='SK_Manny_Arms_Export'
   oldhide=o.get('mechanical_bone','').startswith('PKM_Belt') or o.get('mechanical_bone','') in ['PKM_Box','PKM_BoxLid']
   o.hide_render=unwanted or (o.name.startswith('New_') if f<210 else oldhide)
 cam.location=W@Vector((.36,.62,.32));aim(cam,W@Vector((0,.105,-.04)))
 s.render.filepath=str(O/(('after_' if src.parent==O else 'before_')+label+'.png'));bpy.ops.render.render(write_still=True)
