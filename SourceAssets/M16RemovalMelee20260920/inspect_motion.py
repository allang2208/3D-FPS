import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent;out={}
jobs=[('m4_remove','ExtMagContact20260919/A_M4_ExtContact_reload.blend',None,[18,26]),('m16_remove','M16M4Insert20260920/Animations/base/A_M16_reload.blend',None,[18,26]),('m4_melee','M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend',None,[20,32]),('m16_melee','M16Gameplay20260919/M16_Manny_Editable.blend','M16_quick_melee',[10,16]),('qbz_melee','QBZ191QuickMeleeGrip20260919O/Base/QBZ191_QuickCombat_Base_Editable.blend',None,[20]),('m16_vertical','M16UniversalAttachments20260920/M16_vertical_Animations_Editable.blend','M16_vertical_QuickCombat',[10])]
if '--candidate' in sys.argv:
 jobs=[('after_remove','M16RemovalMelee20260920/Animations/base/A_M16_reload.blend',None,[18,26]),('after_empty_remove','M16RemovalMelee20260920/Animations/base/A_M16_reload_empty.blend',None,[13,20]),('after_melee','M16RemovalMelee20260920/Animations/base/A_M16_quick_melee.blend',None,[10,16]),('after_vertical','M16RemovalMelee20260920/Animations/vertical/A_M16_vertical_QuickCombat.blend',None,[10,16])]
for label,file,act,frames in jobs:
 bpy.ops.wm.open_mainfile(filepath=str(S/file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 if act:r.animation_data.action=bpy.data.actions[act];r.animation_data.action_slot=r.animation_data.action.slots[0]
 out[label]={'action':r.animation_data.action.name,'fps':s.render.fps,'range':list(r.animation_data.action.frame_range),'poses':{}}
 for ob in s.objects:
  if ob.type in ['MESH','ARMATURE','FONT']:
   keep=ob==r or (ob.type=='MESH' and any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers));ob.hide_render=not keep
   if ob.name in bpy.context.view_layer.objects:ob.hide_set(not keep)
   if ob.type=='MESH':ob.color=(.27,.42,.57,1) if 'Arms' in ob.name else (.7,.43,.13,1) if 'Magazine' in ob.name else (.25,.27,.3,1)
 if not s.world:s.world=bpy.data.worlds.new('InspectWorld')
 s.world.color=(.09,.09,.09);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.render.resolution_x=720;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
 c=bpy.data.objects.new('InspectCamera',bpy.data.cameras.new('InspectCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.clip_start=.001
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};out[label]['poses'][f]={n:[list(row) for row in m] for n,m in p.items()}
  if 'remove' in label:
   wrist=r.matrix_world@p['hand_l'].translation;center=wrist+Vector((0,.02,.0));offset=Vector((.36,-.2,.1));c.data.ortho_scale=.35
  else:
   center=r.matrix_world@((p['hand_l'].translation+p['hand_r'].translation+p['lowerarm_l'].translation+p['lowerarm_r'].translation)/4);offset=Vector((.6,-.6,.25));c.data.ortho_scale=.75
  c.location=center+offset;c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{label}_{f}.png');bpy.ops.render.render(write_still=True)
(O/('candidate_poses.json' if '--candidate' in sys.argv else 'source_poses.json')).write_text(json.dumps(out,indent=2));print('M16_SOURCE_MOTION_READ',flush=True)
