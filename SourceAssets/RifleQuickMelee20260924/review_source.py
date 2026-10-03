"""Small source-only pose sheets for the requested melee diagnosis."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
revision=sys.argv[-1] if sys.argv[-1] in ['before','after'] else 'before'
sources=json.loads((O/'sources.json').read_text())
for weapon in ['SVD','PKM']:
 d=sources[weapon+'/base']
 bpy.ops.wm.open_mainfile(filepath=d['source'] if revision=='before' else str(O/f'{weapon}_base_QuickMelee.blend'),use_scripts=False)
 r=bpy.data.objects[d['rig']];s=bpy.context.scene
 a=bpy.data.actions[d['melee_action'] if revision=='before' else f'{weapon}_base_QuickMelee20260924']
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE'
 for ob in s.objects:
  if ob.type=='MESH':
   keep=any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers) and not ob.name.startswith('New_')
   ob.hide_render=not keep
   if keep:ob.hide_set(False)
   ob.color=(.48,.55,.63,1) if 'Arms' in ob.name else (.18,.21,.25,1)
 cd=bpy.data.cameras.new('SourceInspection');cam=bpy.data.objects.new('SourceInspection',cd);s.collection.objects.link(cam);s.camera=cam
 cd.clip_start=.005;cd.lens=13.2
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
 s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
 s.display.shading.background_type='WORLD'
 if not s.world:s.world=bpy.data.worlds.new('SourceReviewWorld')
 s.world.color=(.06,.06,.06)
 s.render.resolution_x=720;s.render.resolution_y=480;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for t in [.075,1/6,.3,.52,.72]:
  f=t*s.render.fps;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  for view in ['fp','oblique']:
   if view=='fp':
    x=max(0,min(1,(t/.9-.6)/.4));w=min(1-math.exp(-16*t),1-x*x*x*(10+x*(-15+6*x)))
    hip=(.07,.06,.07) if weapon=='SVD' else (.09,.09,.11)
    cam.location=(-hip[0]*(1-w),-hip[1]*(1-w)-.10*w,hip[2]*(1-w)+.05*w)
    cam.rotation_euler=(math.pi/2,0,0);cd.type='PERSP';cd.lens=13.2
   else:
    center=Vector((-.12,.08,-.10));cam.location=(1,-1.35,.9)
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=1.65
   dest=O/'Review';dest.mkdir(exist_ok=True);s.render.filepath=str(dest/f'{revision}_{weapon}_{view}_{round(t*1000):03}.png');bpy.ops.render.render(write_still=True)
print('MELEE_SOURCE_REVIEW',revision,flush=True)
