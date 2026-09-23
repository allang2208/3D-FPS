import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;R=O.parent;S=R.parent
report={}
specs=[('PKM',R/'Combat17/PKM_base_Combat_Editable.blend','PKM_Manny_Rig','PKM17_base_quick_melee',(-.00003818,.359063,-.027)),
 ('QBZ191',S/'QBZ191QuickMeleeGrip20260919O/Base/QBZ191_QuickCombat_Base_Editable.blend','SK_M4_Infima','QBZ191_QuickCombat_O_Base',(.00072809,.20850360,.05925570)),
 ('M4',S/'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend','SK_M4_Infima','M4_QuickCombatRefineN_Base',(0,.235,.025))]
for name,path,rig_name,action_name,point in specs:
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False);r=bpy.data.objects[rig_name];s=bpy.context.scene
 a=bpy.data.actions[action_name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE'
 s.frame_set(0);bpy.context.view_layer.update();idle={b.name:b.matrix.copy() for b in r.pose.bones}
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};stock=Vector(point);rows=[]
 for f in [0,4,8,12,16,20,24,32,48,60,72,86,100,108]:
  s.frame_set(f);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};W=p['WPN_root']
  row={'frame':f,'stock':list(W@stock),'root':list(map(list,W)),'arms':{}}
  for side in ['r','l']:
   sh,el,wr=[p[n+'_'+side].translation for n in ['upperarm','lowerarm','hand']]
   ref=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
   natural=p['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@ref
   row['arms'][side]={'shoulder':list(sh),'elbow':list(el),'wrist':list(wr),
    'bend_deg':math.degrees(natural.angle((wr-el).normalized())),
    'reach':(wr-sh).length/((el-sh).length+(wr-el).length),
    'grip_root':list(map(list,W.inverted()@p['hand_'+side]))}
  rows.append(row)
 report[name]={'file':str(path),'action':action_name,'fps':s.render.fps,'rows':rows,
  'idle':{n:list(map(list,m)) for n,m in idle.items()},'rest':{n:list(map(list,m)) for n,m in rest.items()}}
 if name=='PKM':
  report[name]['parts']={}
  for ob in s.objects:
   if ob.type=='MESH' and ob.name.startswith('PKM_Part_') and int(ob.name[-3:]) in [42,43,45,46,66,130,131,132,133,135]:
    points=[rest['WPN_root'].inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
    report[name]['parts'][ob.name]={'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]}
  for ob in s.objects:
   if ob.type=='MESH':
    keep=any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers) and not ob.name.startswith('New_')
    ob.hide_render=not keep
    if keep:ob.hide_set(False)
    ob.color=(.5,.57,.66,1) if 'Arms' in ob.name else (.16,.19,.23,1)
  cd=bpy.data.cameras.new('PKM_MeleeInspection');cam=bpy.data.objects.new('PKM_MeleeInspection',cd);s.collection.objects.link(cam);s.camera=cam
  cam.location=(-.07,0,.07);cam.rotation_euler=(math.pi/2,0,0);cd.clip_start=.001;cd.lens=13.2
  s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
  s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
  s.display.shading.background_type='WORLD';s.world.color=(.06,.06,.06)
  s.render.resolution_x=800;s.render.resolution_y=550;s.render.resolution_percentage=100
  s.render.image_settings.file_format='PNG'
  for f in [0,8,12,20,32,60,86,108]:
   s.frame_set(f);s.render.filepath=str(O/f'before_{f:03}.png');bpy.ops.render.render(write_still=True)
(O/'source_analysis.json').write_text(json.dumps(report,indent=2))
print('MELEE24_SOURCES',json.dumps({k:[{'f':r['frame'],'stock':r['stock'],'wrists':{s:round(v['bend_deg'],1) for s,v in r['arms'].items()}} for r in v['rows']] for k,v in report.items()}),flush=True)
