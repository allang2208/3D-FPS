"""Four requested before/after authoring previews. Does not launch UE/PIE."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
stage=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'Belt08'
source=R/stage
bpy.ops.wm.open_mainfile(filepath=str(source/'PKM_Gameplay_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig']
if 'PKM_Reload_Normal' not in bpy.data.actions:
 with bpy.data.libraries.load(str(source/'PKM_Manny_Reload_Editable.blend'),link=False) as (src,dst):dst.actions=['PKM_Reload_Normal']
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
if any(d.use for d in prefs.devices):s.cycles.device='GPU'
s.render.resolution_x=1280;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Belt08Studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.085,.105,.14,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.45
s.view_settings.view_transform='AgX';s.view_settings.exposure=-.15
def aim(o,p):o.rotation_euler=(p-o.location).to_track_quat('-Z','Y').to_euler()
for ob in list(s.objects):
 if ob.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(ob,do_unlink=True)
cam=bpy.data.objects.new('Belt08Camera',bpy.data.cameras.new('Belt08Camera'));s.collection.objects.link(cam);s.camera=cam
lights=[]
for name,power,pos,size in [('Key',55,(-.4,-.1,.6),.65),('Fill',22,(.4,.2,.25),.9),('Rim',32,(-.3,.45,.35),.55)]:
 ob=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(ob);ob.data.energy=power;ob.data.size=size;lights.append((ob,Vector(pos)))
for shot,t in [('idle',0),('open',1.15),('clear',1.75),('place',4.9)]:
 a=bpy.data.actions['PKM_Game_idle' if shot=='idle' else 'PKM_Reload_Normal']
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(round(t*60));bpy.context.view_layer.update()
 W=r.pose.bones['WPN_root'].matrix@fit
 for ob in s.objects:
  if ob.type!='MESH':continue
  b=ob.get('mechanical_bone','');visible=bool(b) or ob.name=='SK_Manny_Arms_Export'
  if b.startswith('New_'):visible=t>=3.55
  elif b.startswith('PKM_Belt_') or b in ['PKM_Box','PKM_BoxLid']:visible=shot=='idle' or t<3.2
  if ob.get('attachment_id')=='pkm_bipod':visible=False
  ob.hide_render=not visible
  if visible:ob.hide_set(False)
 for ob,pos in lights:ob.location=W@pos;aim(ob,W@Vector((-.04,.04,.045)))
 cam.location=W@Vector((-.38,.24,.205));aim(cam,W@Vector((-.04,.035,.045)));cam.data.type='ORTHO';cam.data.ortho_scale=.33
 s.render.filepath=str(O/(stage+'_'+shot+'.png'));bpy.ops.render.render(write_still=True)
 print('BELT08_PREVIEW',stage,shot,flush=True)
