"""Read the active authoring sources and inspect stock/arm trajectories."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'M4QuickMeleeRefine20260919K'))
from arm_support import ArmSupport
data={};summary={}
for weapon in ['SVD','PKM']:
 for family in ['base','vertical','canted','prism','angled']:
  source=S/'SVDHandRepair20260923'/f'SVD_{family}_Editable.blend' if weapon=='SVD' else S/'PKMLowpoly20260922/Melee24'/f'PKM_{family}_Melee24.blend'
  bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
  r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
  idle_name='A_SVD_'+('' if family=='base' else family+'_')+'idle' if weapon=='SVD' else ('PKM_Game_idle_Wrist12' if family=='base' else f'A_PKM_{family}_idle_Contact15')
  melee_name='A_SVD_'+('' if family=='base' else family+'_')+'quick_melee' if weapon=='SVD' else f'PKM24_{family}_quick_melee'
  def sample(name,f):
   a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE'
   scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
   return {b.name:b.matrix.copy() for b in r.pose.bones}
  idle=sample(idle_name,0);rest={b.name:b.matrix_local.copy() for b in r.data.bones}
  stations=ArmSupport(r,idle).stations
  stock=Vector((0,.348,-.035) if weapon=='SVD' else (-.00003818,.359063,-.027))
  row={'source':str(source),'rig':r.name,'idle_action':idle_name,'melee_action':melee_name,'fps':scene.render.fps,'stock':list(stock),
       'idle':{n:list(map(list,m)) for n,m in idle.items()},'rest':{n:list(map(list,m)) for n,m in rest.items()},
       'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'stations':stations,'before':[]}
  for f in range(round(.9*scene.render.fps)+1):
   p=sample(melee_name,f);W=p['WPN_root'];info={'time':f/scene.render.fps,'stock':list(W@stock),'root':list(map(list,W)),'arms':{}}
   for side in 'rl':
    sh,el,wr=[p[n+'_'+side].translation for n in ['upperarm','lowerarm','hand']]
    ref=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
    natural=p['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@ref
    g=W.inverted()@p['hand_'+side];g0=idle['WPN_root'].inverted()@idle['hand_'+side]
    info['arms'][side]={'bend':math.degrees(natural.angle((wr-el).normalized())),'grip_error':(g.translation-g0.translation).length,
      'shoulder':list(sh),'elbow':list(el),'wrist':list(wr)}
   row['before'].append(info)
  data[weapon+'/'+family]=row
  contact=row['before'][round(scene.render.fps/6)]
  summary[weapon+'/'+family]={'max_wrist':{s:max(p['arms'][s]['bend'] for p in row['before']) for s in 'rl'},
     'max_grip_error_mm':max(p['arms'][s]['grip_error'] for p in row['before'] for s in 'rl')*1000,'contact':contact}
  print('MELEE_SOURCE',weapon,family,json.dumps({k:v for k,v in summary[weapon+'/'+family].items() if k!='contact'}),flush=True)
(O/'sources.json').write_text(json.dumps(data))
(O/'inspection_before.json').write_text(json.dumps(summary,indent=2))
